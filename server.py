import argparse, json, os, threading, shutil, time
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
ROOT=Path(__file__).resolve().parent
TRACKER_PORT = 8766
LOCK=threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        routes={'/':('index.html','text/html'),'/api/workouts':('workouts.json','application/json')}
        if self.path not in routes:
            self.send_error(404); return
        name,kind=routes[self.path]
        data=(ROOT/name).read_bytes()
        self.send_response(200); self.send_header('Content-Type',kind+'; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        port = self.server.server_port
        origins = (f'http://localhost:{port}', f'http://127.0.0.1:{port}')
        if self.path!='/api/workouts' or self.headers.get('Origin') not in origins:
            self.send_error(403); return
        try:
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<100000: raise ValueError()
            entry=json.loads(self.rfile.read(size))
            if not isinstance(entry,dict) or not entry.get('date') or not entry.get('notes'): raise ValueError()
            with LOCK:
                path=ROOT/'workouts.json'
                data=json.loads(path.read_text('utf-8'))
                entry['id']=str(time.time_ns()); entry['source']='Entered in tracker'
                data['workouts'].append(entry)
                backup=ROOT/'backups'; backup.mkdir(exist_ok=True)
                shutil.copy2(path,backup/(str(time.time_ns())+'.json'))
                temp=ROOT/'workouts.tmp'; temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8'); os.replace(temp,path)
            self.send_response(201); self.end_headers()
        except (ValueError,TypeError):
            self.send_error(400)
if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=TRACKER_PORT)
    port = parser.parse_args().port
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'HYROX tracker: http://127.0.0.1:{server.server_port}',flush=True)
    server.serve_forever()
