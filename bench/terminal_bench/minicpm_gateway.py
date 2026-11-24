"""Expose the Spark's private MiniCPM listener over a shared Unix socket."""

import socket
import socketserver
import threading
from pathlib import Path


def copy(source, destination):
    try:
        while data := source.recv(65536):
            destination.sendall(data)
    except OSError:
        pass
    finally:
        try:
            destination.shutdown(socket.SHUT_WR)
        except OSError:
            pass


class Relay(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.create_connection(("172.17.0.1", 18742), timeout=30) as upstream:
            upstream.settimeout(None)
            outgoing = threading.Thread(target=copy, args=(self.request, upstream), daemon=True)
            outgoing.start()
            copy(upstream, self.request)
            self.request.shutdown(socket.SHUT_RDWR)
            outgoing.join()


if __name__ == "__main__":
    path = Path("/gateway/minicpm.sock")
    with socketserver.ThreadingUnixStreamServer(str(path), Relay) as server:
        path.chmod(0o666)
        server.serve_forever()
