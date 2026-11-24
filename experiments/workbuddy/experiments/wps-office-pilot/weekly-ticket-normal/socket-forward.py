import socket,socketserver,select,threading
class Handler(socketserver.BaseRequestHandler):
 def handle(self):
  try:
   with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as upstream:
    upstream.connect(self.server.path)
    peers=[self.request,upstream]
    while True:
     ready,_,_=select.select(peers,[],[],120)
     if not ready:return
     for s in ready:
      data=s.recv(65536)
      if not data:return
      (upstream if s is self.request else self.request).sendall(data)
  except OSError:return
class Server(socketserver.ThreadingTCPServer): allow_reuse_address=True;daemon_threads=True
for port,path in [(18767,"/pilot-sockets/clover.sock"),(18768,"/pilot-sockets/wps.sock")]:
 s=Server(("127.0.0.1",port),Handler);s.path=path;threading.Thread(target=s.serve_forever,daemon=True).start()
threading.Event().wait()
