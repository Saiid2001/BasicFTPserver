from .connection import Connection
import time
from file import readFile, compileData, writeFile,  segmentData
import json

from config import FILE_PATH, SERVER_IP

# Rim Barakat and Elie Melki
class TcpFTPConnection(Connection):
#rim and elie
    def __init__(self, port, server_ip=None):
        self.fileToReceive = None
        self.SEPERATOR = b'\x1c'

        self.BUFFER_SIZE = 1000
        Connection.__init__(self, 'TCP FTP Connection', port, 'TCP', server_ip=server_ip)

    # get the list of files available in the server
    def getFiles(self):
        self.sendMessage("230")
        opcode, fileListString, _ = self.listen()

        assert opcode == b'230', f'Incorrect response {opcode}'

        fileListString.decode('utf-8')

        fileList = json.loads(fileListString)

        return fileList

    # client downloads files from server
    def downloadFile(self, fileID, directory, log= lambda a,b,c: None ):
        self.sendMessage(f'241{fileID}')
        opcode, args, timestamp = self.listen()

        assert opcode == b'241', "Incorrect Response"

        fileName, fileType, numSegments = args.split(b'\x1c')
        fileName, fileType, numSegments = fileName.decode('utf-8'), fileType.decode('utf-8'), int(
            numSegments.decode('utf-8'))

        # generate file data
        self.fileToReceive = {
            'name': fileName,
            'type': fileType,
            'segments': [],  # list of arriving segments
            'received': 0,  # number of received segments
            'total': numSegments,  # total number of segments
            'timestamps': [time.perf_counter_ns() / 1000.0],  # timestamps of arrival of segments
            'rate': 0,  # realtime average of bitrate
            'path': directory
        }
        

        while self.fileToReceive:
            opcode, args, timestamp = self.listen()
            assert opcode == b'212', "Incorrect Response"
            self.receiveSegment(args, timestamp, log)

    def receiveSegment(self, args, timestamp, log= lambda a,b,c: None ):

        assert self.fileToReceive is not None, "Server not expecting file"
        assert self.fileToReceive['received'] != self.fileToReceive['total'], "Received all segments"

        data = args
        # increment the number of segments received
        self.fileToReceive["received"] += 1
        # save the segment data and append data
        self.fileToReceive['segments'].append(data)
        # add the timestamp of arrival of segment
        self.fileToReceive['timestamps'].append(timestamp)

        # get average rate
        self.fileToReceive['rate'] = getAverageRate(
            sampleNumber=self.fileToReceive['received'],
            oldAverage=self.fileToReceive['rate'],
            newSampleSize=len(data),
            duration=timestamp - self.fileToReceive['timestamps'][-2]
        )
        self.sendMessage('100 received')
        print(f'[{self.name}]:',
              f'Receiving file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] - ({self.fileToReceive["received"]}/{self.fileToReceive["total"]}) - {round(self.fileToReceive["rate"])} bps ')

        log(self.fileToReceive["received"],self.fileToReceive["total"],self.fileToReceive["rate"])

        if self.fileToReceive['received'] == self.fileToReceive['total']:
            data = compileData(self.fileToReceive['segments'])
            writeFile(self.fileToReceive['name'], self.fileToReceive['type'], self.fileToReceive['path'], data)

            print(f'[{self.name}]:',
                  f'file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] Received successfully')

            self.fileToReceive = None

    # client uploads files on server
    def sendFile(self, directory, fileName, fileType, log = lambda a,b,c: None):
        data = readFile(fileName, fileType, directory)

        segments, numSegments = segmentData(self.BUFFER_SIZE, data)

        print(f'[{self.name}]:', f'Sending file [{fileName}.{fileType}] - (0/{numSegments}) ')

        # generate file data
        self.fileToSend = {
            'name': fileName,
            'type': fileType,
            'ACKS': [False] * numSegments,  # list of arriving segments
            'sent': 0,  # number of received segments
            'total': numSegments,  # total number of segments
            'bitrates': [time.perf_counter_ns() / 1000.0],  # timestamps of arrival of segments
        }

        self.sendMessage(f'211{fileName}\x1c{fileType}\x1c{numSegments}')
        # generate average bitrate 
        start = None
        end = None
        for i, s in enumerate(segments):
            startS, endS, bitrate = self.sendSegment(i, s)
            print(f'[{self.name}]:',
                  f'Sending file [{fileName}.{fileType}] - ({i + 1}/{numSegments}) - {round(bitrate)} bps')
            log(i + 1,numSegments,bitrate )

            if not start:
                start = startS
            end = endS

        throughput = len(data) * 8 / (end - start) * 1E6
        print(f'[{self.name}]:', f'Finished Sending file [{fileName}.{fileType}] - throughput: {throughput} bps')

    def sendSegment(self, index, segment):
        msg = f'212'
        startSend, endSend, endAll, durationSend, durationAll = self.sendMessage(bytes(msg, 'utf-8') + segment,
                                                                                 isString=False, waitSuccess=True)
        bitrate = len(segment) * 8 / durationAll * 1E6
        return startSend, endAll, bitrate

    def sendMessage(self, message, isString=True, waitSuccess=False):
        """
                    Sends a message to the client.
                    :param waitSuccess: bool - wait for client for acknowledgment on message
                    :param message: byteArray - the payload of the message to be sent
                    :param isString: bool - specify if message is utf-8 encoded
                    """
        if self.server is not None:
        # decode the data to a byte array
            data = message.encode('utf-8') if isString else message

            # send message to client
            ticSend = time.perf_counter_ns() / 1000.0
            self.socket.sendall(data)
            tocSend = time.perf_counter_ns() / 1000.0
            tocAll = tocSend
            if waitSuccess:
                # wait message from client
                rec = self.socket.recv(1024)
                tocAll = time.perf_counter_ns() / 1000.0

                # verify acknowledgment message
                if rec and rec[:3] == b'100':
                    return ticSend, tocSend, tocAll, tocSend - ticSend, tocAll - ticSend
                else:
                    ticSend, tocSend, tocAll, _, _ = self.sendMessage(data, isString=False, waitSuccess=True)


    def listen(self):
        data = self.socket.recv(1024)
        timestamp = time.perf_counter_ns() / 1000.0
        assert len(data) > 3, "No agrs received"
        return data[:3], data[3:], timestamp

    def type():
        return 0  # type 0 for TCP 

# Marc Andraos
class UdpFTPConnection(Connection):
    #Mark
    def __init__(self, port, server_ip=None):

        self.fileToReceive  = None
        self.SEPERATOR = b'\x1c'
        self.BUFFER_SIZE = 1000
        Connection.__init__(self, 'UDP FTP Connection', port, 'UDP', server_ip=server_ip)


    def getFiles(self):
        self.sendMessage("230")
        opcode, fileListString, _ = self.listen()

        assert opcode == b'230', f'Incorrect response {opcode}'

        fileListString.decode('utf-8')

        fileList = json.loads(fileListString)

        return fileList


    def downloadFile(self, fileID, directory, log= lambda a,b,c: a ):
        self.sendMessage(f'241{fileID}')
        opcode, args, timestamp = self.listen()

        assert opcode == b'241', "Incorrect Response"

        fileName, fileType, numSegments = args.split(b'\x1c')
        fileName, fileType, numSegments = fileName.decode('utf-8'), fileType.decode('utf-8'), int(numSegments.decode('utf-8'))

        # generate file data
        self.fileToReceive = {
            'name': fileName,
            'type': fileType,
            'segments': [None] * numSegments,  # list of arriving segments
            'received': 0,  # number of received segments
            'total': numSegments,  # total number of segments
            'timestamps': [time.perf_counter_ns() / 1000.0],  # timestamps of arrival of segments
            'rate': 0 , # realtime average of bitrate
            'path': directory
        }
        self.sendMessage(f'100 file ready to receive')

        while self.fileToReceive:
            opcode, args, timestamp = self.listen()
            assert opcode == b'212', "Incorrect Response"
            self.receiveSegment(args, timestamp,log)


    def receiveSegment(self, args, timestamp, log= lambda a,b,c: a ):

        assert self.fileToReceive is not None, "Server not expecting file"
        assert self.fileToReceive['received'] != self.fileToReceive['total'], "Received all segments"

        # find index of first separator
        separateAt = args.find(self.SEPERATOR)
        assert separateAt != -1, "Expected 2 arguments: sequence number, data"
        # split args
        seqNum, data = [args[:separateAt], args[separateAt+1:]]
        seqNum = int(seqNum.decode('utf-8'))

        assert seqNum < self.fileToReceive['total'], "Sequence number not in range"
        if self.fileToReceive['segments'][seqNum] is not None:
            self.sendMessage(f'100{seqNum}')
            return
        # increment the number of segments received
        self.fileToReceive["received"] += 1
        # save the segment data
        self.fileToReceive['segments'][seqNum] = data
        # add the timestamp of arrival of segment
        self.fileToReceive['timestamps'].append(timestamp)

        self.fileToReceive['rate'] = getAverageRate(
            sampleNumber=self.fileToReceive['received'],
            oldAverage=self.fileToReceive['rate'],
            newSampleSize=len(data),
            duration=timestamp - self.fileToReceive['timestamps'][-2]
        )
        self.sendMessage(f'100{seqNum}')
        print(f'[{self.name}]:',
              f'Receiving file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] - ({self.fileToReceive["received"]}/{self.fileToReceive["total"]}) - {round(self.fileToReceive["rate"])} bps ')

        log(self.fileToReceive["received"],self.fileToReceive["total"],self.fileToReceive["rate"] )

        if self.fileToReceive['received'] == self.fileToReceive['total']:
            data = compileData(self.fileToReceive['segments'])
            writeFile(self.fileToReceive['name'], self.fileToReceive['type'], self.fileToReceive['path'], data)
            print(f'[{self.name}]:',
                  f'file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] Received successfully')

            self.fileToReceive = None


    def sendFile(self, directory, fileName, fileType, log = lambda a,b,c: None):

        data = readFile(fileName, fileType, directory)

        segments, numSegments = segmentData(self.BUFFER_SIZE, data)

        print(f'[{self.name}]:', f'Sending file [{fileName}.{fileType}] - (0/{numSegments}) ')

        # generate file data
        self.fileToSend = {
            'name': fileName,
            'type': fileType,
            'ACKS': [False] * numSegments,  # list of arriving segments
            'sent': 0,  # number of received segments
            'total': numSegments,  # total number of segments
            'bitrates': [time.perf_counter_ns() / 1000.0],  # timestamps of arrival of segments
        }

        self.sendMessage(f'211{fileName}\x1c{fileType}\x1c{numSegments}', waitSuccess=True)

        start = None
        end = None
        for i, s in enumerate(segments):
            startS, endS, bitrate = self.sendSegment(i, s)
            print(f'[{self.name}]:',
                  f'Sending file [{fileName}.{fileType}] - ({i + 1}/{numSegments}) - {round(bitrate)} bps')
            log(i + 1,numSegments,bitrate)

            if not start:
                start = startS
            end = endS

        throughput = len(data) * 8 / (end - start) * 1E6
        print(f'[{self.name}]:', f'Finished Sending file [{fileName}.{fileType}] - throughput: {throughput} bps')

    def sendSegment(self,index, segment):
        msg = f'212{index}\x1c'
        startSend, endSend, endAll, durationSend, durationAll = self.sendMessage(bytes(msg,'utf-8')+segment,isString=False, waitSuccess=True)
        bitrate = len(segment)*8/durationAll*1E6
        return startSend, endAll, bitrate

    def sendMessage(self, message, isString=True, waitSuccess=False):
        """
                Sends a message to the client.
                :param waitSuccess: bool - wait for client for acknowledgment on message
                :param message: byteArray - the payload of the message to be sent
                :param isString: bool - specify if message is utf-8 encoded
                """
        if self.server is not None:
            # decode the data to a byte array
            data = message.encode('utf-8') if isString else message

            # send message to client
            ticSend = time.perf_counter_ns()/1000.0
            self.socket.sendto(data, self.server)
            tocSend = time.perf_counter_ns()/1000.0
            tocAll = tocSend
            if waitSuccess:
                # wait message from client

                try:
                    self.socket.settimeout(5)
                    rec, addr = self.socket.recvfrom(1024)
                    tocAll = time.perf_counter_ns() / 1000.0
                    self.socket.settimeout(1000)
                    # ignore all messages if not from client
                    while addr != self.server:
                        rec, addr = self.socket.recvfrom(1024)
                        tocAll = time.perf_counter_ns() / 1000.0

                    # verify acknowledgment message
                    if rec and rec[:3] == b'100':
                        return ticSend, tocSend,tocAll, tocSend-ticSend, tocAll-ticSend
                    else:
                        ticSend, tocSend, tocAll,_, _ = self.sendMessage(data, isString=False, waitSuccess=True)
                except Exception:
                    ticSend, tocSend, tocAll, _, _ = self.sendMessage(data, isString=False, waitSuccess=True)



            return ticSend, tocSend,tocAll, tocSend-ticSend, tocAll-ticSend

    def listen(self):

        data, addr = self.socket.recvfrom(1024)

        timestamp = time.perf_counter_ns()/1000.0
        assert addr == self.server, "Received message not from server"
        assert len(data)>3, f'No args received {data}'
        return data[:3], data[3:], timestamp

    def close(self):
        '''
        Closes Connection and socket connection.
        '''

        print(f'[{self.name}]: Closing Connection')
        self.sendMessage('600 close')


    def type():
        return 1  # type 1 for UDP

def getBitrate(dataSize, duration):
    bits = dataSize * 8
    return bits / duration * 1E6

def getAverageRate(sampleNumber, oldAverage, newSampleSize, duration):
        newRate = getBitrate(newSampleSize, duration )
        #return (sampleNumber - 1) * 1.0 / sampleNumber * oldAverage + newRate / sampleNumber
        return newRate
