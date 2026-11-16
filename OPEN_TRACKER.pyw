"""Open the journal or supervise its local server without opening a window."""
import ctypes
import errno
import json
import msvcrt
import os
from http.client import HTTPConnection, HTTPException
import subprocess
import sys
import time
import urllib.request
from contextlib import redirect_stderr

from server import HEALTH_BODY, ROOT, TRACKER_PORT

ADDRESS = f'http://127.0.0.1:{TRACKER_PORT}'


CHECK_SECONDS = 10
FAILURE_LIMIT = 3


def health_status():
    connection = HTTPConnection('127.0.0.1', TRACKER_PORT, timeout=2)
    try:
        try:
            connection.connect()
        except (ConnectionRefusedError, TimeoutError):
            return 'offline'
        connection.request('GET', '/health')
        response = connection.getresponse()
        if response.status == 200 and response.read(len(HEALTH_BODY) + 1) == HEALTH_BODY:
            return 'healthy'
        return 'unexpected response'
    except (OSError, HTTPException):
        return 'unresponsive'
    finally:
        connection.close()


def log_event(message):
    print(time.strftime('%Y-%m-%d %H:%M:%S'), message, file=sys.stderr, flush=True)


def verify_journal():
    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with direct.open(ADDRESS + '/api/workouts', timeout=3) as response:
        if not isinstance(json.load(response).get('workouts'), list):
            raise ValueError('The training history could not be read.')
    with direct.open(ADDRESS + '/', timeout=3) as response:
        if b'<meta name="application-name" content="local-training-journal">' not in response.read():
            raise ValueError('Another application is using the journal address.')


def open_browser():
    try:
        os.startfile(ADDRESS + '/')
    except OSError as error:
        print(f'Journal ready at {ADDRESS}/. Browser launch failed: {error}', file=sys.stderr, flush=True)


def claim_checker(lock, temporary):
    # Byte zero is locked. Byte one tells a Windows launcher whether to wait
    # for a temporary chat checker to exit or leave an existing Windows checker alone.
    while True:
        try:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            break
        except OSError as error:
            if error.errno != errno.EACCES:
                raise
            lock.seek(1)
            if temporary or lock.read(1) != b'T':
                return False
            time.sleep(1)
    lock.seek(1)
    lock.write(b'T' if temporary else b'W')
    lock.flush()
    return True


def serve_in_background(temporary=False):
    path = ROOT / '.background-server.lock'
    path.touch(exist_ok=True)
    with path.open('r+b', buffering=0) as lock:
        if not claim_checker(lock, temporary):
            return
        child = None
        failures = 0
        try:
            while True:
                if child is not None and child.poll() is not None:
                    log_event(f'Tracker server {child.pid} exited with code {child.returncode}.')
                    child = None
                status = health_status()
                if child is None and status == 'offline':
                    try:
                        child = subprocess.Popen(
                            [sys.executable, '-u', str(ROOT / 'server.py'), '--port', str(TRACKER_PORT)],
                            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                        log_event(f'Checker started tracker server {child.pid}.')
                    except OSError as error:
                        log_event(f'Could not start the tracker: {error}')
                    failures = 0
                elif child is not None:
                    failures = 0 if status == 'healthy' else failures + 1
                    if failures >= FAILURE_LIMIT:
                        log_event(f'Restarting tracker server {child.pid} after {failures} failed checks ({status}).')
                        child.terminate()
                        child.wait()
                        child = None
                        continue
                time.sleep(CHECK_SECONDS)
        finally:
            if child is not None and child.poll() is None:
                child.terminate()
                child.wait()


def open_journal():
    subprocess.Popen([sys.executable, str(ROOT / 'OPEN_TRACKER.pyw'), '--background'],
                     cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic() + CHECK_SECONDS + 5
    while True:
        try:
            verify_journal()
            break
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.5)
    open_browser()


if __name__ == '__main__':
    temporary = '--session' in sys.argv[1:]
    background = temporary or '--background' in sys.argv[1:]
    with (ROOT / 'server.log').open('a', encoding='utf-8') as log, redirect_stderr(log):
        try:
            if background:
                serve_in_background(temporary)
            else:
                open_journal()
        except Exception as error:
            print(f'Startup failed: {error}', file=sys.stderr, flush=True)
            if not background:
                ctypes.windll.user32.MessageBoxW(0, str(error), 'Journal startup', 16)
            raise
