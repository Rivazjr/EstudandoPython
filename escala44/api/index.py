"""Same-origin gateway: Vercel UI -> HTTPS backend on the owner's PC."""
import os,json,urllib.request,urllib.error
from urllib.parse import urlsplit
from app import Handler
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
class handler(Handler):
 def api(self):
  base=os.environ.get('ESCALA_BACKEND_URL','').rstrip('/')
  parsed=urlsplit(base)
  if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
   return self.reply({'error':'O servidor local ainda não foi conectado. Configure ESCALA_BACKEND_URL na Vercel com o endereço HTTPS deste PC.'},503)
  if not self.path.startswith('/api/') or self.path.startswith('/api//'):
   return self.reply({'error':'Rota inválida.'},404)
  origin=self.headers.get('Origin')
  if self.command=='POST' and origin and urlsplit(origin).netloc!=self.headers.get('Host'):
   return self.reply({'error':'Origem não permitida.'},403)
  try:
   size=int(self.headers.get('Content-Length',0))
   if size<0 or size>16384:return self.reply({'error':'Requisição muito grande.'},413)
   body=self.rfile.read(size) if self.command=='POST' else None
   headers={'Content-Type':'application/json','Origin':parsed.scheme+'://'+parsed.netloc}
   if self.headers.get('Cookie'):headers['Cookie']=self.headers['Cookie']
   req=urllib.request.Request(base+self.path,data=body,method=self.command,headers=headers)
   try:response=urllib.request.build_opener(NoRedirect).open(req,timeout=20)
   except urllib.error.HTTPError as e:response=e
   with response:
    payload=response.read(1024*1024+1)
    if len(payload)>1024*1024:return self.reply({'error':'Resposta do servidor excedeu o limite.'},502)
    if not response.headers.get('Content-Type','').startswith('application/json'):
     return self.reply({'error':'O endereço configurado não respondeu como servidor Escala 44.'},502)
    self.send_response(response.status)
    self.send_header('Content-Type','application/json; charset=utf-8')
    self.send_header('Cache-Control','no-store')
    self.send_header('X-Content-Type-Options','nosniff')
    for value in response.headers.get_all('Set-Cookie',[]):
     if 'secure' not in value.lower():value+='; Secure'
     self.send_header('Set-Cookie',value)
    self.end_headers();self.wfile.write(payload)
  except (ValueError,urllib.error.URLError,TimeoutError,OSError):
   self.reply({'error':'Servidor deste PC indisponível. Verifique se ele está ligado e se o endereço HTTPS está ativo.'},502)
