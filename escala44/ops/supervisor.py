"""Keep the local API, HTTPS tunnel and discovery heartbeat running."""
import json,os,queue,re,signal,subprocess,sys,threading,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REGISTRY='https://mgvnrmzfnttwzvwqaozd.supabase.co/functions/v1/escala44-tunnel-registry'
STOP=threading.Event()
def log(message):print(message,flush=True)
def stop_child(child):
 if child and child.poll() is None:
  child.terminate()
  try:child.wait(timeout=8)
  except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
def check(url,key):
 req=urllib.request.Request(url,headers={'X-Escala-Gateway-Key':key})
 with urllib.request.urlopen(req,timeout=8) as r:
  body=json.load(r)
  if r.status!=200 or 'setup' not in body:raise RuntimeError('API health check failed')
def register(url,key):
 req=urllib.request.Request(REGISTRY,data=json.dumps({'url':url}).encode(),headers={'Content-Type':'application/json','X-Escala-Registry-Key':key})
 with urllib.request.urlopen(req,timeout=10) as r:
  if not json.load(r).get('ok'):raise RuntimeError('Registry update failed')
def start_tunnel(events):
 child=subprocess.Popen([str(ROOT/'cloudflared'),'tunnel','--url','http://127.0.0.1:8080','--protocol','http2','--no-autoupdate'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
 def reader():
  for line in child.stdout:
   match=re.search(r'https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com',line)
   if match:events.put((child.pid,match.group(0)))
  child.stdout.close()
 threading.Thread(target=reader,daemon=True).start()
 return child
def main():
 key=(ROOT/'.connection-key').read_text().strip()
 if len(key)<32:raise RuntimeError('Missing connection key')
 env=dict(os.environ,ESCALA_GATEWAY_KEY=key,ESCALA_HTTPS='1',PYTHONUNBUFFERED='1')
 env.pop('ESCALA_SETUP_KEY',None)
 api=None;tunnel=None;url=None;events=queue.Queue();local_failures=0;tunnel_failures=0
 for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,lambda *_:STOP.set())
 try:
  while not STOP.is_set():
   if api is None or api.poll() is not None:
    api=subprocess.Popen([sys.executable,str(ROOT/'app.py')],cwd=ROOT,env=env)
    local_failures=0;log('Local API started.')
   if tunnel is None or tunnel.poll() is not None:
    tunnel=start_tunnel(events);url=None;tunnel_failures=0;log('HTTPS tunnel started; waiting for address.')
   while True:
    try:
     pid,found=events.get_nowait()
     if pid==tunnel.pid:url=found;log('New HTTPS address discovered.')
    except queue.Empty:break
   try:check('http://127.0.0.1:8080/api/status',key);local_failures=0
   except Exception:
    local_failures+=1
    if local_failures>=3:log('Restarting unresponsive local API.');stop_child(api);api=None
   if url and local_failures==0:
    try:
     check(url+'/api/status',key);tunnel_failures=0
     register(url,key)
    except Exception:
     tunnel_failures+=1;log('Public connection unavailable; retrying automatically.')
     if tunnel_failures>=3:stop_child(tunnel);tunnel=None;url=None
   STOP.wait(15)
 finally:
  stop_child(tunnel);stop_child(api)
if __name__=='__main__':main()
