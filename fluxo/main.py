import os, sqlite3, hashlib, secrets, time, re
from pathlib import Path
from datetime import date
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
DB = os.environ.get('TASK_DB', str(ROOT / 'tarefas.db'))
def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c
def init():
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),expires INTEGER);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),title TEXT NOT NULL,description TEXT NOT NULL,due TEXT,status TEXT NOT NULL,priority TEXT NOT NULL);''')
@asynccontextmanager
async def lifespan(app):
    init()
    yield
app = FastAPI(title='Fluxo · Gerenciador de tarefas', lifespan=lifespan)
class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8,max_length=128)
class Signup(Credentials):
    name: str = Field(min_length=2,max_length=80)
class Task(BaseModel):
    title: str = Field(min_length=1,max_length=160)
    description: str = Field(default='',max_length=4000)
    due: date | None = None
    status: str = 'pending'
    priority: str = 'medium'
def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(password.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex()
def user(request: Request):
    raw = request.cookies.get('session','')
    with connect() as c:
        row = c.execute('SELECT users.id,name,email FROM users JOIN sessions ON users.id=sessions.user_id WHERE token=? AND expires>?',(hashlib.sha256(raw.encode()).hexdigest(),int(time.time()))).fetchone()
    if not row: raise HTTPException(401,'Entre para continuar.')
    return dict(row)
def session(response, uid):
    raw = secrets.token_urlsafe(32)
    with connect() as c:
        c.execute('DELETE FROM sessions WHERE expires<?',(int(time.time()),))
        c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(raw.encode()).hexdigest(),uid,int(time.time())+604800))
    response.set_cookie('session',raw,httponly=True,samesite='strict',secure=os.environ.get('COOKIE_SECURE')=='1',max_age=604800)
@app.middleware('http')
async def security(request, call_next):
    if request.method in ('POST','PUT','DELETE'):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return Response('Origem não autorizada',status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Cache-Control']='no-store'
    return response
@app.get('/')
def index(): return FileResponse(ROOT/'index.html')
@app.post('/api/register',status_code=201)
def register(data: Signup,response: Response):
    email = data.email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or not data.name.strip(): raise HTTPException(422,'Confira o nome e o e-mail.')
    try:
        with connect() as c:
            uid = c.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(data.name.strip(),email,password_hash(data.password))).lastrowid
    except sqlite3.IntegrityError: raise HTTPException(409,'Este e-mail já está cadastrado.')
    session(response,uid)
    return {'id':uid,'name':data.name.strip(),'email':email}
@app.post('/api/login')
def login(data: Credentials,response: Response):
    with connect() as c: row=c.execute('SELECT * FROM users WHERE email=?',(data.email.strip().lower(),)).fetchone()
    encoded = row['password'] if row else password_hash('dummy-password')
    valid=secrets.compare_digest(password_hash(data.password,encoded.split(':')[0]),encoded)
    if not row or not valid: raise HTTPException(401,'E-mail ou senha incorretos.')
    session(response,row['id'])
    return {'id':row['id'],'name':row['name'],'email':row['email']}
@app.get('/api/me')
def me(u=Depends(user)): return u
@app.post('/api/logout')
def logout(request: Request,response: Response):
    with connect() as c: c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(request.cookies.get('session','').encode()).hexdigest(),))
    response.delete_cookie('session')
    return {'ok':True}
def values(t):
    if not t.title.strip() or t.status not in ('pending','progress','done') or t.priority not in ('low','medium','high'): raise HTTPException(422,'Confira título, status e prioridade.')
    return (t.title.strip(),t.description,t.due.isoformat() if t.due else None,t.status,t.priority)
@app.get('/api/tasks')
def tasks(u=Depends(user)):
    with connect() as c: return [dict(r) for r in c.execute('SELECT id,title,description,due,status,priority FROM tasks WHERE user_id=? ORDER BY id DESC',(u['id'],))]
@app.post('/api/tasks',status_code=201)
def create(t: Task,u=Depends(user)):
    with connect() as c: uid=c.execute('INSERT INTO tasks(title,description,due,status,priority,user_id) VALUES(?,?,?,?,?,?)',(*values(t),u['id'])).lastrowid
    return {'id':uid}
@app.put('/api/tasks/{tid}')
def update(tid: int,t: Task,u=Depends(user)):
    with connect() as c:
        if not c.execute('UPDATE tasks SET title=?,description=?,due=?,status=?,priority=? WHERE id=? AND user_id=?',(*values(t),tid,u['id'])).rowcount: raise HTTPException(404,'Tarefa não encontrada.')
    return {'ok':True}
@app.delete('/api/tasks/{tid}')
def delete(tid: int,u=Depends(user)):
    with connect() as c:
        if not c.execute('DELETE FROM tasks WHERE id=? AND user_id=?',(tid,u['id'])).rowcount: raise HTTPException(404,'Tarefa não encontrada.')
    return {'ok':True}
