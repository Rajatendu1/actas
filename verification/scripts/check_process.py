"""New real-process recovery drill; loopback only and fictional inputs."""
import json,os,shutil,socket,sqlite3,subprocess,sys,tempfile,time
from contextlib import contextmanager
from pathlib import Path
import httpx,jwt
from actas import dpop
count=0

def check(ok,label):
 global count
 assert ok,label
 count+=1;print('PASS',label)

def free_port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

@contextmanager
def server(module,env,port):
 with tempfile.TemporaryFile() as log:
  p=subprocess.Popen([sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port)],cwd='/tmp',env=env,stdout=log,stderr=log)
  try:
   for _ in range(160):
    if p.poll() is not None:raise RuntimeError('local server exited before health check')
    try:
     if httpx.get(f'http://127.0.0.1:{port}/healthz').status_code==200:break
    except httpx.HTTPError:pass
    time.sleep(.05)
   else:raise RuntimeError('local server health timeout')
   yield
  finally:
   p.terminate()
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:p.kill();p.wait()

def command(args,env):
 return subprocess.run([sys.executable,'-m',*args],cwd='/tmp',env=env,capture_output=True,text=True)

with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);original=root/'original';original.mkdir();restored=root/'restored';restored.mkdir()
 env={k:v for k,v in os.environ.items() if not k.startswith('ACTAS_') and k!='PYTHONPATH'}
 env.update(ACTAS_DATA_DIR=str(original),ACTAS_KEY_PASSPHRASE='fictional-recovery-fixture-not-user-secret',ACTAS_ADMIN_TOKEN='fictional-local-admin-fixture')
 port=free_port();base=f'http://127.0.0.1:{port}';c=httpx.Client(base_url=base,timeout=5)
 def exchange(token,headers=None):
  return c.post('/oauth/token',data=dict(grant_type='urn:ietf:params:oauth:grant-type:token-exchange',subject_token_type='urn:ietf:params:oauth:token-type:jwt',subject_token=token,client_id='planner-bot',scope='read:calendar',audience='calendar-api'),headers=headers or {})
 def auth(token,key=None,uri=None):
  h={'Authorization':'Bearer '+token}
  if key:h['DPoP']=dpop.make_proof(key,method='GET',uri=uri or base+'/api/calendar/events',access_token=token)
  return h
 key,jwk=dpop.generate_key()
 with server('actas.app:app',env,port):
  user=c.get('/demo/usertoken').text
  r=exchange(user);check(r.status_code==200,'process exchange issues token');parent=r.json()['access_token']
  r=exchange(parent);check(r.status_code==200,'process narrowed child');child=r.json()['access_token']
  r=exchange(user,{'DPoP':dpop.make_proof(key,method='POST',uri=base+'/oauth/token')});check(r.status_code==200,'process bound issue');bound=r.json()['access_token']
  used=auth(bound,key);check(c.get('/api/calendar/events',headers=used).status_code==200,'holder accepted before stop')
  check(c.get('/api/calendar/events',headers=used).status_code==401,'proof replay refused before stop')
  check(c.post('/oauth/revoke',data={'token':parent},headers={'Authorization':'Bearer '+env['ACTAS_ADMIN_TOKEN']}).status_code==200,'parent revoked')
  check(c.get('/api/calendar/events',headers=auth(child)).status_code==401,'child cascade refused')
  jwks=c.get('/.well-known/jwks.json').json();head=c.get('/audit/checkpoint').json()
 # Real OS process stopped before backup, as required by command acknowledgement.
 backup=root/'snapshot.db';r=command(['actas.snapshot','backup',str(original/'actas.db'),str(backup),'--server-stopped'],env)
 check(r.returncode==0,'offline backup CLI succeeds')
 check(backup.stat().st_mode&0o777==0o600,'snapshot private mode0600')
 with sqlite3.connect(backup) as db:
  check(all(b'ENCRYPTED PRIVATE KEY' in bytes(x[0]) for x in db.execute('SELECT pem FROM keys')),'snapshot key encryption retained')
 wrong={**env,'ACTAS_KEY_PASSPHRASE':'wrong-fictional-passphrase'}
 dest=restored/'actas.db';r=command(['actas.snapshot','restore',str(backup),str(dest),'--server-stopped'],wrong)
 check(r.returncode==2 and not dest.exists(),'wrong passphrase restore refuses cleanly')
 r=command(['actas.snapshot','restore',str(backup),str(dest),'--server-stopped'],env);check(r.returncode==0,'offline restore to new path')
 digest=__import__('hashlib').sha256(dest.read_bytes()).hexdigest();r=command(['actas.snapshot','restore',str(backup),str(dest),'--server-stopped'],env)
 check(r.returncode==2 and __import__('hashlib').sha256(dest.read_bytes()).hexdigest()==digest,'existing destination never overwritten')
 shutil.rmtree(original);env['ACTAS_DATA_DIR']=str(restored)
 with server('actas.app:app',env,port):
  check(c.get('/.well-known/jwks.json').json()==jwks,'restored keys identical after original removed')
  check(c.get('/audit/checkpoint').json()['head']==head['head'],'restored audit head identical')
  check(c.get('/audit/verify').json()['ok'],'restored audit integrity')
  check(c.get('/api/calendar/events',headers=auth(child)).status_code==401,'cascade revocation survives restore')
  check(c.get('/api/calendar/events',headers=used).status_code==401,'used proof remains refused after restore')
  check(c.get('/api/calendar/events',headers=auth(bound,key)).status_code==200,'fresh holder proof succeeds after restore')
 # Rotation overlap must use retirement time even for a key created long ago.
 with sqlite3.connect(dest) as db:db.execute('UPDATE keys SET created_at=? WHERE current=1',(time.time()-100000,));db.commit()
 r=command(['actas.rotate_key','--retire-older-than','3600'],env);check(r.returncode==0,'offline rotation CLI')
 with server('actas.app:app',env,port):
  check(len(c.get('/.well-known/jwks.json').json()['keys'])==2,'newly retired old-created key retained')
  check(c.get('/api/calendar/events',headers=auth(bound,key)).status_code==200,'pre-rotation token survives overlap')
  check(exchange(c.get('/demo/usertoken').text).status_code==200,'fresh issuance after restart rotation')
  # Truly separate resource process fetches only public JWKS and revocation feed.
  remote_port=free_port();remote=f'http://127.0.0.1:{remote_port}';renv={k:v for k,v in env.items() if not k.startswith('ACTAS_')}
  renv.update(ACTAS_JWKS_URL=base+'/.well-known/jwks.json',ACTAS_REVOKED_URL=base+'/oauth/revoked',ACTAS_REVOKED_TTL='0')
  with server('actas.resource_server:app',renv,remote_port):
   check(httpx.get(remote+'/events',headers=auth(bound,key,remote+'/events')).status_code==200,'separate JWKS resource accepts holder')
   check(httpx.get(remote+'/events',headers=auth(bound)).status_code==401,'separate resource rejects thief')
   check(httpx.get(remote+'/events',headers=auth(child)).status_code==401,'separate resource sees cascade revocation')
 c.close()
print(count,'NEW real-process recovery checks passed; old suite not recovered')
