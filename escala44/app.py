from contextlib import contextmanager
import os, sqlite3, secrets, hashlib, hmac, json, re, datetime, http.cookies
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
ROOT=Path(__file__).parent
DB=Path(os.environ.get('ESCALA_DB', str(ROOT/'data.sqlite3')))
KEY=ROOT/'.setup-key'
@contextmanager
def connect():
 if os.environ.get('VERCEL'):
  raise RuntimeError('O banco local só deve ser acessado pelo servidor deste PC.')
 c=sqlite3.connect(DB,timeout=20); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON')
 try:
  with c:yield c
 finally:c.close()
def setup_key():
 return os.environ.get('ESCALA_SETUP_KEY') or (KEY.read_text().strip() if KEY.exists() else '')
def init():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,cpf TEXT UNIQUE NOT NULL,password TEXT NOT NULL,name TEXT,admin INTEGER DEFAULT 0,approved INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,uid INTEGER REFERENCES users(id),expires INTEGER); CREATE TABLE IF NOT EXISTS rules(month TEXT,op TEXT,city TEXT,capacity INTEGER,period TEXT,weekday_limit INTEGER,weekend_limit INTEGER,PRIMARY KEY(month,op,city)); CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY,uid INTEGER REFERENCES users(id),day TEXT,op TEXT,city TEXT,UNIQUE(uid,day,op));''')
  empty=c.execute('SELECT count(*) FROM users WHERE admin=1').fetchone()[0]==0
 if empty and not KEY.exists():
  fd=os.open(KEY,os.O_CREAT|os.O_WRONLY|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:f.write(secrets.token_urlsafe(32))
def password(p,salt=None):
 salt=salt or secrets.token_hex(16)
 return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),310000).hex()
def cpf_ok(v):
 if len(v)!=11 or len(set(v))==1:return False
 for n in (9,10):
  if int(v[n]) != (sum(int(v[i])*(n+1-i) for i in range(n))*10%11)%10:return False
 return True
def month_rules(c,m):
 for op,caps,period in [('pmf',[11,60,60],'day'),('escola',[240,60,60],'month')]:
  for city,cap in zip(['Salinópolis','São João de Pirabas','Santarém Novo'],caps):
   c.execute('INSERT OR IGNORE INTO rules VALUES(?,?,?,?,?,?,?)',(m,op,city,cap,period,4,2))
def weekend(day):return datetime.date.fromisoformat(day).weekday()>=5
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def reply(self,data,status=200,cookie=None):
  b=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(b)
 def do_GET(self):
  if self.path.startswith('/api/'):
   self.api();return
  p=ROOT/'static'/('style.css' if self.path=='/style.css' else 'app.js' if self.path=='/app.js' else 'index.html')
  b=p.read_bytes();self.send_response(200);self.send_header('Content-Type', {'css':'text/css','js':'text/javascript','html':'text/html'}[p.suffix[1:]]+'; charset=utf-8');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
 def do_POST(self):self.api()
 def api(self):
  try:
   if self.command=='POST':
    origin=self.headers.get('Origin')
    if origin and origin.split('://')[-1]!=self.headers.get('Host'):raise ValueError('Origem não permitida.')
    size=int(self.headers.get('Content-Length',0))
    if size>16384:raise ValueError('Requisição muito grande.')
    d=json.loads(self.rfile.read(size) or b'{}')
   else:d={}
   with connect() as c:
    path=self.path.split('?')[0]
    if self.command!='POST' and path not in ['/api/state','/api/status']:return self.reply({'error':'Método não permitido.'},405)
    token=http.cookies.SimpleCookie(self.headers.get('Cookie',''));token=token['session'].value if 'session' in token else ''
    u=c.execute('SELECT u.* FROM users u JOIN sessions s ON s.uid=u.id WHERE s.token=? AND s.expires>strftime(\'%s\',\'now\')',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if path=='/api/status':return self.reply({'setup':not c.execute('SELECT 1 FROM users WHERE admin=1').fetchone()})
    if path in ['/api/register','/api/setup']:
     email=str(d.get('email','')).strip().lower();cpf=re.sub(r'\D','',str(d.get('cpf','')));p=str(d.get('password',''))
     if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or not cpf_ok(cpf) or len(p)<10:raise ValueError('Informe email válido, CPF válido e senha com pelo menos 10 caracteres.')
     admin=path.endswith('setup')
     c.execute('BEGIN IMMEDIATE')
     if admin and (c.execute('SELECT 1 FROM users WHERE admin=1').fetchone() or not setup_key() or not hmac.compare_digest(str(d.get('key','')),setup_key())):raise ValueError('Chave de instalação inválida ou administrador já criado.')
     c.execute('INSERT INTO users(email,cpf,password,admin,approved) VALUES(?,?,?,?,?)',(email,cpf,password(p),int(admin),int(admin)));c.commit()
     if admin:KEY.unlink(missing_ok=True)
     return self.reply({'ok':True})
    if path=='/api/login':
     identity=str(d.get('identity','')).strip().lower();person=c.execute('SELECT * FROM users WHERE email=? OR cpf=?',(identity,re.sub(r'\D','',identity))).fetchone()
     encoded=person['password'] if person else password('dummy-password','0'*32)
     valid=hmac.compare_digest(password(str(d.get('password','')),encoded.split(':')[0]),encoded)
     if not person or not valid:raise ValueError('Credenciais inválidas.')
     if not person['approved']:raise ValueError('Cadastro aguardando aprovação do administrador.')
     tok=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,strftime(\'%s\',\'now\')+43200)',(hashlib.sha256(tok.encode()).hexdigest(),person['id']));c.commit()
     return self.reply({'ok':True},cookie='session='+tok+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'+('; Secure' if os.environ.get('ESCALA_HTTPS')=='1' else ''))
    if not u:return self.reply({'error':'Faça login para continuar.'},401)
    if path=='/api/logout':
     c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),));c.commit();return self.reply({'ok':True},cookie='session=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict')
    if path=='/api/profile':
     name=str(d.get('name','')).strip()
     if not 2<=len(name)<=40:raise ValueError('Nome de guerra deve ter entre 2 e 40 caracteres.')
     if u['name']:raise ValueError('Nome de guerra já definido.')
     c.execute('UPDATE users SET name=? WHERE id=?',(name,u['id']));c.commit();return self.reply({'ok':True})
    if path=='/api/state':
     from urllib.parse import parse_qs,urlsplit
     m=parse_qs(urlsplit(self.path).query).get('month',[datetime.date.today().strftime('%Y-%m')])[0]
     if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',m):raise ValueError('Mês inválido.')
     month_rules(c,m);c.commit()
     own=[dict(r) for r in c.execute('SELECT * FROM bookings WHERE uid=? AND substr(day,1,7)=? ORDER BY day',(u['id'],m))]
     usage=[dict(r) for r in c.execute('SELECT day,op,city,count(*) AS n FROM bookings WHERE substr(day,1,7)=? GROUP BY day,op,city',(m,))]
     users=[dict(r) for r in c.execute('SELECT id,email,name,approved,admin FROM users ORDER BY approved,name')] if u['admin'] else []
     allb=[dict(r) for r in c.execute('SELECT b.*,u.name FROM bookings b JOIN users u ON u.id=b.uid WHERE substr(day,1,7)=? ORDER BY day',(m,))] if u['admin'] else []
     return self.reply({'user':{'id':u['id'],'name':u['name'],'admin':bool(u['admin'])},'rules':[dict(r) for r in c.execute('SELECT * FROM rules WHERE month=?',(m,))],'bookings':own,'usage':usage,'users':users,'roster':allb})
    if path=='/api/approve':
     if not u['admin']:return self.reply({'error':'Acesso restrito.'},403)
     c.execute('UPDATE users SET approved=1 WHERE id=?',(d['id'],));c.commit();return self.reply({'ok':True})
    if path=='/api/rules':
     if not u['admin']:return self.reply({'error':'Acesso restrito.'},403)
     rows=d['rules'];m=d['month']
     if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',m) or len(rows)!=6:raise ValueError('Configuração inválida.')
     c.execute('BEGIN IMMEDIATE');month_rules(c,m)
     expected={(r['op'],r['city']) for r in c.execute('SELECT * FROM rules WHERE month=?',(m,))}
     if {(r['op'],r['city']) for r in rows}!=expected:raise ValueError('Operações e municípios inválidos.')
     for opkey in ['pmf','escola']:
      matching=[r for r in rows if r['op']==opkey]
      if len({int(r['weekday_limit']) for r in matching})!=1 or len({int(r['weekend_limit']) for r in matching})!=1:raise ValueError('Limites por policial devem ser iguais nos três municípios.')
     for r in rows:
      vals=[int(r[k]) for k in ['capacity','weekday_limit','weekend_limit']]
      if any(v<0 or v>100000 for v in vals) or r['period'] not in ['day','month']:raise ValueError('Limites inválidos.')
      c.execute('UPDATE rules SET capacity=?,weekday_limit=?,weekend_limit=?,period=? WHERE month=? AND op=? AND city=?',(*vals,r['period'],m,r['op'],r['city']))
     c.commit();return self.reply({'ok':True})
    if path=='/api/cancel':
     c.execute('DELETE FROM bookings WHERE id=? AND uid=?',(d['id'],u['id']));c.commit();return self.reply({'ok':True})
    if path=='/api/book':
     if not u['name']:raise ValueError('Defina seu nome de guerra primeiro.')
     day=d['day'];date=datetime.date.fromisoformat(day)
     if day!=date.isoformat():raise ValueError('Data inválida; use AAAA-MM-DD.')
     if date<datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).date():raise ValueError('Não é possível agendar no passado.')
     op=d['op'];city=d['city'];m=day[:7];we=weekend(day)
     if op=='escola' and we:raise ValueError('Escola Segura disponível apenas de segunda a sexta-feira.')
     c.execute('BEGIN IMMEDIATE');month_rules(c,m)
     rule=c.execute('SELECT * FROM rules WHERE month=? AND op=? AND city=?',(m,op,city)).fetchone()
     if not rule:raise ValueError('Operação ou município inválido.')
     if c.execute('SELECT 1 FROM bookings WHERE uid=? AND day=? AND op=?',(u['id'],day,op)).fetchone():raise ValueError('Você já possui agendamento nesta operação e data, inclusive em outro município.')
     mine=c.execute('SELECT day FROM bookings WHERE uid=? AND op=? AND substr(day,1,7)=?',(u['id'],op,m)).fetchall()
     limit=min(r[0] for r in c.execute('SELECT '+('weekend_limit' if we else 'weekday_limit')+' FROM rules WHERE month=? AND op=?',(m,op)))
     if sum(weekend(r['day'])==we for r in mine)>=limit:raise ValueError('Limite mensal por policial atingido para este tipo de dia.')
     n=c.execute('SELECT count(*) FROM bookings WHERE op=? AND city=? AND '+('day=?' if rule['period']=='day' else 'substr(day,1,7)=?'),(op,city,day if rule['period']=='day' else m)).fetchone()[0]
     if n>=rule['capacity']:raise ValueError('Cotas esgotadas para este município e período.')
     c.execute('INSERT INTO bookings(uid,day,op,city) VALUES(?,?,?,?)',(u['id'],day,op,city));c.commit();return self.reply({'ok':True})
    self.reply({'error':'Rota não encontrada.'},404)
  except sqlite3.IntegrityError:self.reply({'error':'Cadastro já existente ou agendamento duplicado.'},409)
  except (ValueError,KeyError,TypeError) as e:self.reply({'error':str(e)},400)
  except Exception:self.reply({'error':'Falha interna. Tente novamente.'},500)
if __name__=='__main__':
 init();host=os.environ.get('ESCALA_HOST','127.0.0.1');port=int(os.environ.get('PORT','8080'));print(f'Escala 44: http://{host}:{port}',flush=True);ThreadingHTTPServer((host,port),Handler).serve_forever()
