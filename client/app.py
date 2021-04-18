# disclaimer: this is for testing purposes only

import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 5000))

while True:
    d = input('send: ')
    sock.sendall(bytes(d,'utf-8'))
    data= sock.recv(1024)
    if not data:
        break
    print(repr(data))

