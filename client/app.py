# disclaimer: this is for testing purposes only

# import socket
#
# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# sock.connect(('127.0.0.1', 5000))
#
# while True:
#     d = input('send: ')
#     sock.sendall(bytes(d,'utf-8'))
#     data= sock.recv(1024)
#     if not data:
#         break
#     print(repr(data))

from connections.mainConnection import MainConnection

conn = MainConnection()
conn = conn.connectFTP('UDP')
fileList = conn.getFiles()

print('ID\tFILE')
for file in fileList:
    print(str(file['id'])+'\t'+file['file'])

filename = input('Choose filename to download: ')

id=  [f['id'] for f in fileList if f['file']==filename][0]

conn.downloadFile(id, input('Directory: '))
conn.sendFile(input('directory: '), input('name: '), input('type: '))
conn.close()

