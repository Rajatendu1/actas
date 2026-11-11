"""New post-recovery evidence, not the lost original test suite."""
import json,subprocess,sys,os,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from actas.app import app, workbench_limiter
from actas import __version__
E=Path(__file__).resolve().parent/'samples';passed=0

def check(condition,name):
 global passed
 assert condition,name
 passed+=1;print('PASS',name)

def cli(candidate,baseline=None):
 return subprocess.run([sys.executable,'-m','actas.workbench',str(candidate),*([str(baseline)] if baseline else [])],capture_output=True,text=True,cwd='/tmp',env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'})

r=cli(E/'baseline.json');check(r.returncode==0,'installed CLI baseline from outside source directory');check(json.loads(r.stdout)['matched']==8,'baseline8of8')
r=cli(E/'candidate.json');check(r.returncode==1,'candidate mismatch exits1')
r=cli(E/'candidate.json',E/'baseline.json');check(r.returncode==1,'permission change exits1');check(json.loads(r.stdout)==json.loads((E/'actas-policy-comparison.json').read_text())['report'],'downloaded browser comparison equals offline report exactly')
r=cli(E/'intent-matched-candidate.json',E/'baseline.json');check(r.returncode==1,'intent match cannot hide permission-change exit1');check(json.loads(r.stdout)==json.loads((E/'intent-matched-comparison.json').read_text())['report'],'intent-matched API report equals offline report exactly')
r=cli(E/'baseline.json',E/'baseline.json');check(r.returncode==0,'identical baseline passes CI gate')
with tempfile.TemporaryDirectory() as d:
 bad=Path(d)/'bad.json';bad.write_text('{"schema_version":1,"schema_version":1}')
 r=cli(bad);check(r.returncode==2 and not r.stdout and 'Duplicate JSON' in r.stderr,'ambiguous import exits2 without false report')
 r=cli(Path(d)/'missing.json');check(r.returncode==2 and not r.stdout,'missing file exits2')
 c=TestClient(app);workbench_limiter.hits.clear();raw=(E/'baseline.json').read_text();r=c.post('/tools/policy-check',content=raw);check(r.status_code==200 and r.json()['matched']==8,'recovered installed API8of8')
 r=c.get('/',headers={'If-Modified-Since':'Sat, 20 Oct 2018 01:46:40 GMT'});check(r.status_code==200 and 'v0.14.1' in r.text and r.headers['cache-control']=='no-store','recovered HTML/version/cache policy')
 check(c.post('/tools/policy-check',content=bad.read_text()).status_code==400,'API duplicate rejection')
 check(c.get('/actas/app.py').status_code==404,'source private route404');check(c.get('/audit/recent').status_code in [403,404],'admin route disabled')
# A minimal real shell CI step must stop on a permission change, not merely
# show a green intent report. No GitHub workflow is installed or run here.
for candidate,expected in [('baseline.json',0),('intent-matched-candidate.json',1)]:
 command='set -e; "$PYTHON" -m actas.workbench "$CANDIDATE" "$BASELINE" > "$REPORT"; printf gate-passed'
 with tempfile.TemporaryDirectory() as folder:
  env={**os.environ,'PYTHON':sys.executable,'CANDIDATE':str(E/candidate),'BASELINE':str(E/'baseline.json'),'REPORT':str(Path(folder)/'report.json')}
  run=subprocess.run(['sh','-c',command],env=env,cwd=folder,capture_output=True,text=True)
  check(run.returncode==expected and (('gate-passed' in run.stdout)==(expected==0)), 'real minimal CI shell '+candidate)
print(passed,'new recovered-source integration checks passed; original suite not recovered')
