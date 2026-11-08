"""Open the journal and serve it in the same windowless process."""
import ctypes
import json
import os
import sys
import threading
import urllib.request
from contextlib import redirect_stderr
from http.server import ThreadingHTTPServer

from server import Handler, ROOT, TRACKER_PORT

ADDRESS = f'http://127.0.0.1:{TRACKER_PORT}'


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


def open_journal():
    try:
        verify_journal()
    except (OSError, ValueError):
        pass
    else:
        open_browser()
        return

    try:
        service = ThreadingHTTPServer(('127.0.0.1', TRACKER_PORT), Handler)
    except OSError as error:
        if error.winerror != 10048:
            raise
        verify_journal()
        open_browser()
        return

    with service:
        worker = threading.Thread(target=service.serve_forever, daemon=True)
        worker.start()
        verify_journal()
        open_browser()
        worker.join()


if __name__ == '__main__':
    with (ROOT / 'server.log').open('a', encoding='utf-8') as log, redirect_stderr(log):
        try:
            open_journal()
        except Exception as error:
            print(f'Startup failed: {error}', file=sys.stderr, flush=True)
            ctypes.windll.user32.MessageBoxW(0, str(error), 'Journal startup', 16)
