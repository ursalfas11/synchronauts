#!/usr/bin/env python3
"""For e2e.sh: a keys URL that takes its time. Serves <dir>/<login>.keys as /<login>.keys on 127.0.0.1, on a free port
that it writes into <portfile>. For a login that starts with `slow` it answers at once but holds the keys back until
the file <dir>/go exists, at most <delay> seconds: meanwhile it sends a `#` every half second (one comment line that
syn skips), so that no single read waits as long as syn's timeout of 10 s, also on a slow machine. A test can thus
hold a check of signatures in flight for as long as it looks at it. Ends once the file <dir>/stop exists.
Usage: slowkeys.py <dir> <portfile> <delay>. Python 3.9 syntax."""
import os
import socketserver
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FOLDER, PORTFILE, DELAY = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3])


class Keys(BaseHTTPRequestHandler):
    def do_GET(self):
        name = self.path.split('?')[0].lstrip('/')
        path = FOLDER / name
        if '/' in name or '\\' in name or not name.endswith('.keys') or not path.is_file():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()  # no length: the answer ends when the connection closes (HTTP/1.0)
        if name.startswith('slow'):
            end, beat = time.time() + DELAY, 0.0
            while time.time() < end and not (FOLDER / 'go').exists():
                if time.time() >= beat:
                    self.wfile.write(b'#')
                    beat = time.time() + 0.5
                time.sleep(0.05)
            self.wfile.write(b'\n')
        self.wfile.write(path.read_bytes())

    def log_message(self, *args):  # quiet: the test's output is its ok lines
        pass


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self):  # without HTTPServer's reverse DNS lookup, which can take seconds (as syn.py's board)
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


server = Server(('127.0.0.1', 0), Keys)
tmp = PORTFILE.with_name(f'{PORTFILE.name}.tmp')
tmp.write_text(str(server.server_address[1]), encoding='utf-8')
os.replace(tmp, PORTFILE)  # the test reads the port only once it is complete


def stopper():  # a file, not a signal: the same on Windows
    while not (FOLDER / 'stop').exists():
        time.sleep(0.1)
    server.shutdown()


threading.Thread(target=stopper, daemon=True).start()
server.serve_forever()
