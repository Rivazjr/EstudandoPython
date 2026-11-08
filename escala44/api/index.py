"""Same-origin gateway with automatic discovery of the PC's HTTPS tunnel."""
import os,json,urllib.request,urllib.error
from urllib.parse import urlsplit
from app import Handler
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
def registry_backend():
 endpoint=os.environ.get('ESCALA_REGISTRY_URL','')
 key=os.environ.get('ESCALA_REGISTRY_KEY','')
 if not endpoint or not key:raise ValueError('Registro de conexão não configurado.')
 parsed=urlsplit(endpoint)
 if parsed.scheme!='https' or not parsed.hostname or not parsed.hostname.endswith('.supabase.co'):raise ValueError('Registro inválido.')
 req=urllib.request.Request(endpoint,headers={'X-Escala-Registry-Key':key})
 with urllib.request.build_opener(NoRedirect).open(req,timeout=8) as r:
  info=json.load(r)
 base=str(info.get('url','')).rstrip('/')
 import re
 if not re.fullmatch(r'https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com',base):raise ValueError('Endereço de conexão inválido.')
 return base
class handler(Handler):
 def api(self):
  if not self.path.startswith('/api/') or self.path.startswith('/api//'):
   return self.reply({'error':'Rota inválida.'},404)
  origin=self.headers.get('Origin')
  if self.command=='POST' and origin and urlsplit(origin).netloc!=self.headers.get('Host'):
   return self.reply({'error':'Origem não permitida.'},403)
  try:
   base=registry_backend();parsed=urlsplit(base)
   size=int(self.headers.get('Content-Length',0))
   if size<0 or size>16384:return self.reply({'error':'Requisição muito grande.'},413)
   body=self.rfile.read(size) if self.command=='POST' else None
   headers={'Content-Type':'application/json','Origin':parsed.scheme+'://'+parsed.netloc,'X-Escala-Gateway-Key':os.environ['ESCALA_REGISTRY_KEY']}
   if self.headers.get('Cookie'):headers['Cookie']=self.headers['Cookie']
   req=urllib.request.Request(base+self.path,data=body,method=self.command,headers=headers)
   try:response=urllib.request.build_opener(NoRedirect).open(req,timeout=15)
   except urllib.error.HTTPError as e:response=e
   with response:
    payload=response.read(1024*1024+1)
    if len(payload)>1024*1024:return self.reply({'error':'Resposta do servidor excedeu o limite.'},502)
    if not response.headers.get('Content-Type','').startswith('application/json'):
     return self.reply({'error':'Reconectando ao servidor do batalhão. Tente novamente em instantes.'},503)
    self.send_response(response.status)
    self.send_header('Content-Type','application/json; charset=utf-8')
    self.send_header('Cache-Control','no-store')
    self.send_header('X-Content-Type-Options','nosniff')
    for value in response.headers.get_all('Set-Cookie',[]):
     if 'secure' not in value.lower():value+='; Secure'
     self.send_header('Set-Cookie',value)
    self.end_headers();self.wfile.write(payload)
  except (ValueError,KeyError,urllib.error.URLError,TimeoutError,OSError):
   self.reply({'error':'Servidor do batalhão indisponível ou reconectando. O PC precisa estar ligado e conectado à internet.'},503)
