"""Local catalogue editor. Runs only on loopback; no dependencies."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json, secrets, base64, re, os
ROOT=Path(__file__).resolve().parent.parent
PUBLIC=ROOT/'docs'
TOKEN=secrets.token_urlsafe(32)
PORT=int(os.environ.get('HOLLOW_PORT','4174'))
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw): super().__init__(*a,directory=str(PUBLIC),**kw)
 def reply(self,status,data):
  body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
 def do_GET(self):
  if self.headers.get('Host') not in [f'127.0.0.1:{PORT}',f'localhost:{PORT}']:return self.reply(403,{'error':'Invalid host'})
  if self.path.split('?')[0]=='/studio':
   data=(ROOT/'studio/index.html').read_text().replace('__TOKEN__',TOKEN).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
  else:super().do_GET()
 def do_POST(self):
  if self.headers.get('Host') not in [f'127.0.0.1:{PORT}',f'localhost:{PORT}'] or self.headers.get('X-Studio-Token')!=TOKEN:return self.reply(403,{'error':'请刷新管理页面后重试'})
  try:
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<16000000:raise ValueError('请求过大，图片请小于 10MB')
   data=json.loads(self.rfile.read(n))
   if self.path=='/api/products':
    if not isinstance(data,list) or len(data)>500:raise ValueError('作品数据不正确')
    seen=set()
    for p in data:
     if not isinstance(p,dict) or not isinstance(p.get('id'),str) or p['id'] in seen:raise ValueError('作品编号重复或缺失')
     seen.add(p['id'])
     for field in ['title','description','category','subtitle','alt']:
      if not isinstance(p.get(field),str) or len(p[field])>5000:raise ValueError('作品文字不正确')
     if not p['title'].strip():raise ValueError('请填写作品名称')
     if not isinstance(p.get('visible'),bool):raise ValueError('请选择展示状态')
     if not isinstance(p.get('frames'),list) or len(p['frames'])>40:raise ValueError('动画最多 40 帧')
     for path in [p.get('image')]+p['frames']:
      if not isinstance(path,str) or not re.fullmatch(r'assets/[a-zA-Z0-9_-]+\.(webp|jpg|jpeg|png)',path) or not (PUBLIC/path).is_file():raise ValueError('请先上传有效的作品照片')
    dest=PUBLIC/'products.json'; backup=ROOT/'studio/backups';backup.mkdir(exist_ok=True)
    (backup/(secrets.token_hex(8)+'.json')).write_bytes(dest.read_bytes())
    tmp=PUBLIC/'products.json.tmp';tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(dest)
    return self.reply(200,{'ok':True})
   if self.path=='/api/upload':
    raw=base64.b64decode(data['data'],validate=True)
    if len(raw)>10000000:raise ValueError('图片请小于 10MB')
    ext='jpg' if raw[:3]==b'\xff\xd8\xff' else 'png' if raw[:8]==b'\x89PNG\r\n\x1a\n' else 'webp' if raw[:4]==b'RIFF' and raw[8:12]==b'WEBP' else None
    if not ext:raise ValueError('仅支持 JPG、PNG、WebP 图片')
    path='assets/upload-'+secrets.token_hex(10)+'.'+ext;(PUBLIC/path).write_bytes(raw);return self.reply(200,{'path':path})
   self.reply(404,{'error':'Not found'})
  except (ValueError,KeyError,TypeError) as e:self.reply(400,{'error':str(e)})
  except Exception:self.reply(500,{'error':'保存失败，请检查文件权限后重试'})
print(f'作品管理：http://127.0.0.1:{PORT}/studio',flush=True)
ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
