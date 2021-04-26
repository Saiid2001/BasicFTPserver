
from connections.mainConnection import MainConnection

conn = MainConnection()

# conn = conn.connectFTP('UDP')
# fileList = conn.getFiles()
#
# print('ID\tFILE')
# for file in fileList:
#     print(str(file['id'])+'\t'+file['file'])
#
# filename = input('Choose filename to download: ')
#
# id=  [f['id'] for f in fileList if f['file']==filename][0]
#
# conn.downloadFile(id, input('Directory: '))
# conn.sendFile(input('directory: '), input('name: '), input('type: '))
# conn.close()




