import argparse, json, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from record_workout import record
ROOT=Path(__file__).resolve().parent
TRACKER_PORT = 8766
HEALTH_BODY = b'local-training-journal\n'

class JournalServer(ThreadingHTTPServer):
    allow_reuse_address = False

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response_only(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(HEALTH_BODY)))
            self.end_headers()
            self.wfile.write(HEALTH_BODY)
            return
        routes={'/':('index.html','text/html'),'/api/workouts':('workouts.json','application/json')}
        if self.path not in routes:
            self.send_error(404); return
        name,kind=routes[self.path]
        data=(ROOT/name).read_bytes()
        self.send_response(200)
        if self.path == '/api/workouts':
            self.send_header('X-Journal-Weigh-Ins', 'writable')
        self.send_header('Content-Type',kind+'; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        port = self.server.server_port
        origins = (f'http://localhost:{port}', f'http://127.0.0.1:{port}')
        if self.path not in ('/api/workouts','/api/weigh-ins') or self.headers.get('Origin') not in origins:
            self.send_error(403); return
        try:
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<100000: raise ValueError()
            entry=json.loads(self.rfile.read(size))
            if not isinstance(entry,dict) or not entry.get('date'): raise ValueError()
            if self.path == '/api/weigh-ins':
                day = date.fromisoformat(entry['date'])
                today = datetime.now(timezone(timedelta(hours=7))).date()
                if day.isoformat() != entry['date'] or day > today:
                    raise ValueError('Choose a weigh-in date on or before today')
                reading = {'id': entry['date'], 'date': entry['date'], 'weight_kg': entry.get('weight_kg'),
                           'source': 'Entered in Body Weight', 'weight_source': 'Entered in Body Weight'}
                record(reading, ROOT, 'daily_energy', preserve_source=True)
            else:
                entry['id']=str(time.time_ns()); entry['source']='Entered in tracker'
                record(entry, ROOT)
            self.send_response(201); self.end_headers()
        except (ValueError,TypeError):
            self.send_error(400)
        except OSError:
            self.send_error(503, 'Could not save the journal')
if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=TRACKER_PORT)
    port = parser.parse_args().port
    server=JournalServer(('127.0.0.1',port),Handler)
    print(f'HYROX tracker: http://127.0.0.1:{server.server_port}',flush=True)
    server.serve_forever()
