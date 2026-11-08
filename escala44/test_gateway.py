import io,json,os,unittest
from unittest.mock import patch,MagicMock
from api.index import handler,registry_backend
class Gateway(unittest.TestCase):
 def gateway(self,path='/api/status',method='GET',origin=None):
  obj=object.__new__(handler);obj.path=path;obj.command=method
  obj.headers={'Host':'escala44.vercel.app'}
  if origin:obj.headers['Origin']=origin
  obj.rfile=io.BytesIO(b'');obj.wfile=io.BytesIO();obj.reply=MagicMock();obj.send_response=MagicMock();obj.send_header=MagicMock();obj.end_headers=MagicMock()
  return obj
 def test_reject_cross_origin_write(self):
  g=self.gateway(method='POST',origin='https://attacker.example');g.api()
  self.assertEqual(g.reply.call_args.args[1],403)
 def test_disconnected_pc_returns_service_error(self):
  g=self.gateway()
  with patch('api.index.registry_backend',side_effect=ValueError('offline')):g.api()
  self.assertEqual(g.reply.call_args.args[1],503)
 def test_no_arbitrary_proxy_destination(self):
  response=MagicMock();response.__enter__.return_value=io.BytesIO(json.dumps({'url':'https://example.com'}).encode())
  opener=MagicMock();opener.open.return_value=response
  with patch.dict(os.environ,{'ESCALA_REGISTRY_URL':'https://test.supabase.co/functions/v1/registry','ESCALA_REGISTRY_KEY':'fake-test-key'}),patch('urllib.request.build_opener',return_value=opener):
   with self.assertRaises(ValueError):registry_backend()
 def test_forward_authentication_and_cookie(self):
  g=self.gateway();response=MagicMock();response.__enter__.return_value=response;response.status=200;response.read.return_value=b'{"setup":false}'
  response.headers={'Content-Type':'application/json'}
  class Headers(dict):
   def get_all(self,name,default=None):return ['session=sample; HttpOnly; SameSite=Strict']
  response.headers=Headers(response.headers)
  opener=MagicMock();opener.open.return_value=response
  g.headers['Cookie']='session=sample'
  with patch.dict(os.environ,{'ESCALA_REGISTRY_KEY':'fake-test-key'}),patch('api.index.registry_backend',return_value='https://new-address.trycloudflare.com'),patch('urllib.request.build_opener',return_value=opener):g.api()
  request=opener.open.call_args.args[0]
  self.assertEqual(request.get_header('X-escala-gateway-key'),'fake-test-key')
  self.assertEqual(request.get_header('Cookie'),'session=sample')
  self.assertIn('Secure',next(args.args[1] for args in g.send_header.call_args_list if args.args[0]=='Set-Cookie'))
  self.assertEqual(g.wfile.getvalue(),b'{"setup":false}')
if __name__=='__main__':unittest.main()
