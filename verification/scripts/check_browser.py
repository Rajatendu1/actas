"""New localhost Chrome workflow coverage around unchanged recovered HTML."""
import base64,json,os,socket,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
import websocket
HERE=Path(__file__).resolve();ROOT=HERE.parents[2];chrome=None;server=None
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
base=f'http://127.0.0.1:{port}'
with socket.socket() as s:s.bind(('127.0.0.1',0));debug=s.getsockname()[1]
with tempfile.TemporaryDirectory() as temp:
 log=open(Path(temp)/'server.log','w')
 env={k:v for k,v in os.environ.items() if not k.startswith('ACTAS_')}
 server=subprocess.Popen([sys.executable,'-m','uvicorn','actas.app:app','--host','127.0.0.1','--port',str(port)],cwd='/tmp',env=env,stdout=log,stderr=log)
 try:
  for _ in range(160):
   try:urllib.request.urlopen(base+'/healthz');break
   except Exception:time.sleep(.05)
  chrome=subprocess.Popen([os.environ.get('CHROME_BIN','/usr/bin/google-chrome'),'--headless=new','--no-sandbox','--disable-gpu','--user-data-dir='+temp+'/chrome','--remote-debugging-port='+str(debug),'--remote-allow-origins=*','about:blank'],stdout=log,stderr=log)
  for _ in range(160):
   try:targets=json.load(urllib.request.urlopen(f'http://127.0.0.1:{debug}/json'));break
   except Exception:time.sleep(.05)
  ws=websocket.create_connection(next(t for t in targets if t['type']=='page')['webSocketDebuggerUrl'],timeout=30);mid=0
  def cmd(method,params=None):
   global mid
   mid+=1;ws.send(json.dumps(dict(id=mid,method=method,params=params or {})))
   while True:
    r=json.loads(ws.recv())
    if r.get('id')==mid:
     if 'error' in r:raise RuntimeError(r['error'])
     return r.get('result',{})
  def js(expression):
   r=cmd('Runtime.evaluate',dict(expression=expression,returnByValue=True,awaitPromise=True,userGesture=True))
   if 'exceptionDetails' in r:raise RuntimeError(r)
   return r['result'].get('value')
  def wait(expression):
   for _ in range(160):
    if js(expression):return
    time.sleep(.05)
   raise RuntimeError(expression)
  def field(id,value):js('$('+json.dumps(id)+').value='+json.dumps(value)+';$('+json.dumps(id)+').dispatchEvent(new Event("input"))')
  def shot(name,selector):
   js('document.querySelector('+json.dumps(selector)+').scrollIntoView({block:"center"})');time.sleep(.1)
   out=ROOT/'verification/pixels';out.mkdir(exist_ok=True)
   (out/(name+'.png')).write_bytes(base64.b64decode(cmd('Page.captureScreenshot',{'format':'png'})['data']))
  def upload(selector,path):
   root=cmd('DOM.getDocument')['root']['nodeId'];inp=cmd('DOM.querySelector',{'nodeId':root,'selector':selector})['nodeId']
   cmd('DOM.setFileInputFiles',{'nodeId':inp,'files':[str(path)]})
  cmd('Page.enable');cmd('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
  for name,width,height,mobile in [('desktop',1440,900,False),('mobile',390,844,True)]:
   cmd('Emulation.setDeviceMetricsOverride',dict(width=width,height=height,deviceScaleFactor=1,mobile=mobile));cmd('Page.navigate',{'url':base+'/'})
   wait('Boolean(document.getElementById("wbPack")?.value)')
   assert js('document.querySelector("footer").textContent.includes("0.14.1")')
   assert js('$("wbInputNotice").compareDocumentPosition($("wbImport")) & Node.DOCUMENT_POSITION_FOLLOWING')
   shot('recovered-'+name+'-notice','#wbInputNotice')
   js('$("wbRun").click()');wait('$("wbStatus").textContent.startsWith("8/8")')
   js('$("wbComparePanel").open=true;$("wbCasePanel").open=true;$("wbPin").click();$("wbCaseLoad").click();$("wbCaseSelect").value=8;$("wbCaseSelect").dispatchEvent(new Event("change"))')
   baseline=js('$("wbBaselineView").textContent')
   for id,value in [('wbCaseName','forbidden-private-write'),('wbCaseRequested','write:private'),('wbCaseSubject','read:documents write:private'),('wbCaseExpected','false')]:field(id,value)
   assert js('$("wbRun").disabled && $("wbCompare").disabled')
   js('$("wbCaseApply").click();$("wbRun").click()');wait('$("wbStatus").textContent.startsWith("9/9")')
   js('$("wbEditLoad").click()');field('wbEditScopes','read:documents write:summary write:private');js('$("wbEditApply").click();$("wbRun").click()');wait('$("wbStatus").textContent.startsWith("8/9")')
   assert js('document.querySelector("#wbResults .mismatch").textContent.includes("forbidden-private-write")')
   js('$("wbCaseLoad").click();$("wbCaseSelect").value=8;$("wbCaseSelect").dispatchEvent(new Event("change"))');field('wbCaseExpected','true');js('$("wbCaseApply").click();$("wbCompare").click()')
   wait('$("wbCompareStatus").textContent.startsWith("1 newly allowed")');assert js('$("wbCompareStatus").textContent.includes("9/9 matched")');assert js('$("wbBaselineView").textContent')==baseline
   shot('recovered-'+name+'-comparison','#wbCompareStatus')
   # Real filesystem download and reimport, not a simulated export.
   download=Path(temp)/name;download.mkdir();cmd('Browser.setDownloadBehavior',dict(behavior='allow',downloadPath=str(download)))
   js('$("wbSave").click()')
   for _ in range(100):
    if (download/'actas-policy-pack.json').exists():break
    time.sleep(.05)
   good=js('$("wbPack").value');assert json.loads((download/'actas-policy-pack.json').read_text())==json.loads(good)
   upload('#wbImport',download/'actas-policy-pack.json');wait('$("wbStatus").textContent.startsWith("Pack imported")');assert json.loads(js('$("wbPack").value'))==json.loads(good)
   # Duplicate import must not overwrite current pack/baseline.
   bad=good.replace('"allowed_scopes": [','"allowed_scopes": [], "allowed_scopes": [',1);badfile=Path(temp)/'bad.json';badfile.write_text(bad);upload('#wbImport',badfile);wait('$("wbStatus").textContent.includes("Duplicate JSON")');assert js('$("wbPack").value')==good
   # Delayed file read cannot erase a newer draft. Release native read later.
   js('window.nativeText=File.prototype.text;File.prototype.text=function(){const f=this;return new Promise(resolve=>window.finishRead=()=>nativeText.call(f).then(resolve));}')
   upload('#wbImport',download/'actas-policy-pack.json');wait('typeof window.finishRead==="function"');js('$("wbCaseLoad").click()');field('wbCaseName','newer-draft')
   js('window.finishRead();File.prototype.text=nativeText');time.sleep(.1)
   assert js('$("wbCaseName").value==="newer-draft" && $("wbRun").disabled && $("wbReport").disabled')
   shot('recovered-'+name+'-draft','#wbCaseStatus')
   js('$("wbCaseDiscard").click();$("wbRun").click()');wait('$("wbStatus").textContent.startsWith("9/9")')
   # Late HTTP response cannot restore a stale report over another case edit.
   js('window.nativeFetch=fetch;window.fetch=async(...args)=>{const r=await nativeFetch(...args);await new Promise(resolve=>window.releaseCheck=resolve);return r;};$("wbRun").click()');wait('typeof window.releaseCheck==="function"')
   js('$("wbCaseLoad").click()');field('wbCaseName','newest-draft');js('window.releaseCheck();window.fetch=nativeFetch');time.sleep(.1)
   assert js('$("wbRun").disabled && $("wbReport").disabled && $("wbStatus").textContent.includes("Case edit pending")')
   assert js('document.documentElement.scrollWidth<=innerWidth')
   print(name,'PASS recovered original HTML custom case9/8/9/comparison/export/reimport/duplicate/delayed-file/delayed-HTTP/draft/no-overflow')
  ws.close()
 finally:
  if chrome:chrome.terminate();chrome.wait()
  if server:server.terminate();server.wait()
  log.close()
