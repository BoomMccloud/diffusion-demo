"""Forward localhost:8085 inside the map pod to Nominatim on the host.

The map site's nominatim_url is used both by the Rails server (inside the
rootless pod, where the host is 10.0.2.2) and by the visitor's browser (on the
host, where Nominatim is localhost:8085). Setting it to localhost:8085 and
running this relay in the pod lets both reach it. Before this, directions by
place name never resolved in the agent's browser.
"""

import socket
import socketserver
import threading

TARGET = ("10.0.2.2", 8085)


def pipe(src, dst):
    try:
        while data := src.recv(65536):
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


class Relay(socketserver.BaseRequestHandler):
    def handle(self):
        upstream = socket.create_connection(TARGET, timeout=30)
        upstream.settimeout(None)
        t = threading.Thread(target=pipe, args=(upstream, self.request), daemon=True)
        t.start()
        pipe(self.request, upstream)
        t.join()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    Server(("127.0.0.1", 8085), Relay).serve_forever()
