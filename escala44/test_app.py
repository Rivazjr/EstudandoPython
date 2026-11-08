import unittest,tempfile,threading,json,urllib.request,urllib.error,http.cookiejar,datetime,concurrent.futures
from pathlib import Path
import app
class Integration(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();app.DB=Path(cls.tmp.name)/'test.db';app.KEY=Path(cls.tmp.name)/'.setup-key';app.init();cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=cls.server.serve_forever,daemon=True).start();cls.base='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.tmp.cleanup()
 def client(self):return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def call(self,c,path,data=None):
  req=urllib.request.Request(self.base+'/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
  try:
   with c.open(req) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_full_flow(self):
  admin=self.client();police=self.client();other=self.client()
  self.assertEqual(self.call(admin,'setup',{'email':'admin@example.com','cpf':'52998224725','password':'administrator123','key':app.KEY.read_text()})[0],200)
  self.assertEqual(self.call(admin,'login',{'identity':'529.982.247-25','password':'administrator123'})[0],200)
  self.assertEqual(self.call(police,'register',{'email':'police@example.com','cpf':'11144477735','password':'password1234'})[0],200)
  self.assertEqual(self.call(police,'login',{'identity':'police@example.com','password':'password1234'})[0],400)
  future=datetime.date.today()+datetime.timedelta(days=40);m=future.strftime('%Y-%m');s=self.call(admin,'state?month='+m)[1]
  uid=next(u['id'] for u in s['users'] if u['email']=='police@example.com')
  self.assertEqual(self.call(admin,'approve',{'id':uid})[0],200)
  self.assertEqual(self.call(police,'login',{'identity':'police@example.com','password':'password1234'})[0],200)
  self.assertEqual(self.call(police,'rules',{'month':m,'rules':s['rules']})[0],403)
  self.assertEqual(self.call(police,'profile',{'name':'SD Silva'})[0],200)
  self.assertEqual(self.call(admin,'profile',{'name':'Comando'})[0],200)
  dates=[datetime.date(future.year,future.month,n) for n in range(1,29)]
  weekday=[d.isoformat() for d in dates if d.weekday()<5 and d>=datetime.date.today()];sat=next(d.isoformat() for d in dates if d.weekday()==5)
  rules=s['rules']
  for r in rules:
   if r['op']=='pmf':r['weekday_limit']=1;r['capacity']=1
  self.assertEqual(self.call(admin,'rules',{'month':m,'rules':rules})[0],200)
  booking={'day':weekday[0],'op':'pmf','city':'Salinópolis'}
  # Concurrent submissions competing for last quota: exactly one winner.
  with concurrent.futures.ThreadPoolExecutor() as pool:
   results=list(pool.map(lambda c:self.call(c,'book',booking)[0],[admin,police]))
  self.assertEqual(sorted(results),[200,400])
  winner=admin if results[0]==200 else police
  self.assertEqual(self.call(winner,'book',{**booking,'city':'Santarém Novo'})[0],400)
  self.assertEqual(self.call(winner,'book',{**booking,'day':weekday[1]})[0],400)
  self.assertEqual(self.call(police,'book',{'day':sat,'op':'escola','city':'Salinópolis'})[0],400)
  self.assertEqual(self.call(police,'book',{'day':weekday[0],'op':'escola','city':'Salinópolis'})[0],200)
  self.assertEqual(self.call(police,'book',{'day':weekday[0],'op':'escola','city':'São João de Pirabas'})[0],400)
  own=self.call(winner,'state?month='+m)[1]['bookings'];bid=next(b['id'] for b in own if b['op']=='pmf')
  self.assertEqual(self.call(winner,'cancel',{'id':bid})[0],200)
  self.assertEqual(self.call(winner,'book',booking)[0],200)
  # Monthly school capacity spans dates.
  for r in rules:
   if r['op']=='escola' and r['city']=='Salinópolis':r['capacity']=1
  self.call(admin,'rules',{'month':m,'rules':rules})
  self.assertEqual(self.call(admin,'book',{'day':weekday[2],'op':'escola','city':'Salinópolis'})[0],400)
  self.assertEqual(self.call(other,'state')[0],401)
if __name__=='__main__':unittest.main()
