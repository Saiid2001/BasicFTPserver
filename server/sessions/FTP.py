from .session import Session
from file import compileData, writeFile, getFileList, getFile, segmentData
import time
import json
from config import FILE_PATH

# code for TCP FTP Session by Rim and Elie
class TcpFTPSession(Session):
    def __init__(self):

        # Constants
        self.SEPERATOR = b'\x1c'  # used to separate argument list.
        # data relevant to the file in transit if it exists
        self.fileToReceive = None
        self.fileToSend = None
        # Dictionary of available commands to be requested from Client Session
        self.commands = {
            b'211': self.requestReceiveFile,
            b'212': self.receiveSegment,
            b'230': self.getFiles,
            b'241': self.startSendFile
        }
        Session.__init__(self, 'TCP FTP Session', TcpFTPSession.port(), 'TCP')

    def waitClientRequest(self):
        print(f'[{self.name}]: Available for Clients')

        # tcp is not connectionless. But we want to handle one client per session.
        # We wait for the first message and save the user address that is contacting session.

        conn, addr = self.socket.accept()

        self.client = {
            'connection': conn,
            'address': addr
        }

        # handle any subsequent requests by going to run()
        try:
            super().waitClientRequest()
        except ConnectionResetError:
            self.close()

    def sendMessage(self, message, isString=True, waitSuccess=False):
        """
                Sends a message to the client.
                :param waitSuccess: bool - wait for client for acknowledgment on message
                :param message: byteArray - the payload of the message to be sent
                :param isString: bool - specify if message is utf-8 encoded
                """
        if self.client is not None:
            # decode the data to a byte array
            data = message.encode('utf-8') if isString else message

            # send message to client
            ticSend = time.perf_counter_ns() / 1000.0
            self.client['connection'].sendall(data)
            tocSend = time.perf_counter_ns() / 1000.0
            tocAll = tocSend

            if waitSuccess:
                resp = self.client['connection'].recv(1024)
                assert resp[:3] == b'100', 'Wrong response'

            return ticSend, tocSend, tocAll, tocSend - ticSend, tocAll - ticSend

    def run(self):

        # infinite loop to read multiple requests
        while True:
            # save the received message in data

            data = self.client['connection'].recv(1024)
            timestamp = time.perf_counter_ns() / 1000.0
            if not data:
                # close on no data
                break

            try:
                self.onReceived(data, timestamp)

            except AssertionError as e:
                print(f'[{self.name}]:', e)
                self.sendMessage(f'400 ' + str(e))

        # if connection closed close it
        return self.close()

    def onReceived(self, payload, timestamp=None):

        """
                Handle the received message from the client.
                Parses the received message and decodes it.
                :param timestamp: float - optional - the time of arrival of message
                :param payload: byteArray - the received request
                """

        # assert payload contains 3 digit opcode
        assert len(payload) >= 3, "Invalid request length"

        # parse the incoming message into the format   [opcode|args] with opcode as a 3 digit integer
        opcode, args = payload[:3], payload[3:]

        # assert the opcode is available
        assert opcode in self.commands, f'Invalid request OPCODE = "{opcode}"'

        # assert waiting for a file before receiving a segment
        assert (not self.fileToReceive) or (
                self.fileToReceive and opcode == b'212'), "Cannot make another request while receiving a file"

        # super().onReceived(payload)

        # executing the command requested by the client
        try:
            self.commands[opcode](args, timestamp)

        except AssertionError as e:
            print(f'[{self.name}]:', e)
            self.sendMessage(f'400 ' + str(e))

    def requestReceiveFile(self, args, timestamp=None):
        """
        OPCODE 211
        Initiates receiving a new file procedure.

        :param timestamp: float - optional - time at which the data is received
        :param args: byteArray:
            number of fields: 3
            index   length(chars)  name         values     description
            0       -              fileName     str        the file name of file to be received
            1       -              fileType     str        the extension of the file
            2       -              numSegments  int>0      segmentation number
        :sends
        opcode  description
        100     manual acknowledgment of request
        """

        # example: 211mytext\x1ctxt\x1c400
        # args: mytext\x1ctxt -> split with \x1c -> [mytext, txt, 200]

        # split args string
        argList = args.split(self.SEPERATOR)

        # make sure the number of arguments is 3
        assert len(argList) == 3, "Expected 3 arguments: fileName, fileType, segmentsNumber"

        # parse args
        fileName, fileType, numSegments = argList
        fileName, fileType, numSegments = fileName.decode('utf-8'), fileType.decode('utf-8'), int(
            numSegments.decode('utf-8'))

        print(f'[{self.name}]:', f'Receiving file [{fileName}.{fileType}] - (0/{numSegments}) ')

        # generate file data
        self.fileToReceive = {
            'name': fileName,
            'type': fileType,
            'segments': [],  # list of arriving segments
            'received': 0,  # number of received segments
            'total': numSegments,  # total number of segments
            'timestamps': [time.perf_counter_ns() / 1000.0],  # timestamps of arrival of segments
            'rate': 0  # realtime average of bitrate
        }

        # # manual acknowledgment
        # self.sendMessage(f'100 file ready to be received')

    def receiveSegment(self, args, timestamp):
        """
        OPCODE 212
        Receives a segment of file data

        :param timestamp: float - optional - time at which the data is received
        :param args: byteArray:
            number of fields: 2
            index   length(chars)  name         values     description
            0       -              seqNum       str        index of segment in file
            1       -              data         bytes      binary data
        :sends
        opcode  description                        args
        100     manual acknowledgment of segment   segment index
        """
        # example: 212001\x1cDATASEGMENT
        # args: mytext\x1ctxt -> split with \x1c -> [mytext, txt, 200]

        assert self.fileToReceive is not None, "Server not expecting file"
        assert self.fileToReceive['received'] != self.fileToReceive['total'], "Received all segments"

        data = args
        # save the segment data
        self.fileToReceive['segments'].append(data)
        self.fileToReceive['timestamps'].append(timestamp)
        self.fileToReceive['received']+=1

        self.fileToReceive['rate'] = getAverageRate(
            sampleNumber=self.fileToReceive['received'],
            oldAverage=self.fileToReceive['rate'],
            newSampleSize=len(data),
            duration= timestamp - self.fileToReceive['timestamps'][-2]
        )

        print(f'[{self.name}]:',
              f'Receiving file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] - ({self.fileToReceive["received"]}/{self.fileToReceive["total"]}) - {round(self.fileToReceive["rate"])} bps ')

        self.sendMessage('100 received')
        if self.fileToReceive['received'] == self.fileToReceive['total']:
            data = compileData(self.fileToReceive['segments'])
            writeFile(self.fileToReceive['name'], self.fileToReceive['type'], FILE_PATH, data)

            print(f'[{self.name}]:',
                  f'file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] Received successfully')

            self.fileToReceive = None

    def getFiles(self, args, timestamp=None):
        print(f'[{self.name}]:', 'Sending File list')
        files = json.dumps(getFileList())
        self.sendMessage('230' + files)

    def startSendFile(self, args, timestamp=None):

        # example: 2411

        # make sure args exist
        assert args, "Expected 3 arguments: fileName, fileType, segmentsNumber"

        # parse args
        fileID = int(args.decode('utf-8'))

        fileName, fileType, data = getFile(fileID, FILE_PATH)

        segments, numSegments = segmentData(1012, data)

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

        self.sendMessage(f'241{fileName}\x1c{fileType}\x1c{numSegments}')

        start = None
        end = None
        for i, s in enumerate(segments):
            startS, endS, bitrate = self.sendSegment(s)
            print(f'[{self.name}]:',
                  f'Sending file [{fileName}.{fileType}] - ({i + 1}/{numSegments}) - {round(bitrate)} bps')

            if not start:
                start = startS
            end = endS

        throughput = len(data) * 8 / (end - start) * 1E6
        print(f'[{self.name}]:', f'Finished Sending file [{fileName}.{fileType}] - throughput: {throughput} bps')

    def sendSegment(self,  segment):
        msg = f'212'
        startSend, endSend, endAll, durationSend, durationAll = self.sendMessage(bytes(msg, 'utf-8') + segment,
                                                                                 isString=False, waitSuccess=True)
        bitrate = len(segment) * 8 / durationAll * 1E6
        return startSend, endAll, bitrate

    @staticmethod
    def port():
        return 6001


# code for udp session by Saiid El Hajj Chehade
class UdpFTPSession(Session):
    """
        UdpFTPSession handles file transfer using the UDP protocol.
        Scope of requests include:
        211 - requestReceiveFile
        212 - receiveSegment
        """

    def __init__(self):

        # Constants
        self.SEPERATOR = b'\x1c'  # used to separate argument list.
        # data relevant to the file in transit if it exists
        self.fileToReceive = None
        self.fileToSend = None
        # Dictionary of available commands to be requested from Client Session
        self.commands = {
            b'211': self.requestReceiveFile,
            b'212': self.receiveSegment,
            b'230': self.getFiles,
            b'241': self.startSendFile,
            b'600': self.close
        }
        Session.__init__(self, 'UDP FTP Session', UdpFTPSession.port(), 'UDP')

    def waitClientRequest(self):
        print(f'[{self.name}]: Available for Clients')

        # udp is connectionless. But we want to handle one client per session.
        # We wait for the first message and save the user address that is contacting session.
        data, addr = self.socket.recvfrom(1024)
        self.client = {'address': addr}
        # handle the first request
        try:
            self.onReceived(data, time.perf_counter_ns() / 1000.0)
        except AssertionError as e:
            print(f'[{self.name}]:', e)
            self.sendMessage(f'400 ' + str(e))
        # handle any subsequent requests by going to run()
        super().waitClientRequest()

    def sendMessage(self, message, isString=True, waitSuccess=False):
        """
                Sends a message to the client.
                :param waitSuccess: bool - wait for client for acknowledgment on message
                :param message: byteArray - the payload of the message to be sent
                :param isString: bool - specify if message is utf-8 encoded
                """
        if self.client is not None:
            # decode the data to a byte array
            data = message.encode('utf-8') if isString else message

            # send message to client
            ticSend = time.perf_counter_ns()/1000.0
            self.socket.sendto(data, self.client['address'])
            tocSend = time.perf_counter_ns()/1000.0
            tocAll = tocSend
            if waitSuccess:
                # wait message from client
                rec, addr = self.socket.recvfrom(1024)
                tocAll = time.perf_counter_ns() / 1000.0
                # ignore all messages if not from client
                while addr != self.client['address']:
                    rec, addr = self.socket.recvfrom(1024)
                    tocAll = time.perf_counter_ns() / 1000.0

                # verify acknowledgment message
                if rec and rec[:3] == b'100':
                    return ticSend, tocSend,tocAll, tocSend-ticSend, tocAll-ticSend
                else:
                    ticSend, tocSend, tocAll,_, _ = self.sendMessage(data, isString=False, waitSuccess=True)

            return ticSend, tocSend,tocAll, tocSend-ticSend, tocAll-ticSend

    def run(self):

        # infinite loop to read multiple requests
        while True:
            # save the received message in data
            data, addr = self.socket.recvfrom(1024)
            timestamp = time.perf_counter_ns() / 1000.0
            if not data:
                # close on no data
                break

            # check if data from client we are servicing
            if addr == self.client['address']:
                # handle the received data
                try:
                    self.onReceived(data, timestamp=timestamp)

                except AssertionError as e:
                    print(f'[{self.name}]:', e)
                    self.sendMessage(f'400 ' + str(e))


        # if connection closed wait for a new one.

        return self.waitClientRequest()

    def onReceived(self, payload, timestamp=None):

        """
                Handle the received message from the client.
                Parses the received message and decodes it.
                :param timestamp: float - optional - the time of arrival of message
                :param payload: byteArray - the received request
                """

        # assert payload contains 3 digit opcode
        assert len(payload) >= 3, "Invalid request length"

        # parse the incoming message into the format   [opcode|args] with opcode as a 3 digit integer
        opcode, args = payload[:3], payload[3:]

        # assert the opcode is available
        assert opcode in self.commands, f'Invalid request OPCODE = "{opcode}"'

        # assert waiting for a file before receiving a segment
        assert (not self.fileToReceive) or (
                    self.fileToReceive and opcode == b'212'), "Cannot make another request while receiving a file"

        #super().onReceived(payload)


        # executing the command requested by the client
        try:
            back = self.commands[opcode](args, timestamp)

        except AssertionError as e:
            print(f'[{self.name}]:', e)
            self.sendMessage(f'400 ' + str(e))

    def requestReceiveFile(self, args, timestamp=None):
        """
        OPCODE 211
        Initiates receiving a new file procedure.

        :param timestamp: float - optional - time at which the data is received
        :param args: byteArray:
            number of fields: 3
            index   length(chars)  name         values     description
            0       -              fileName     str        the file name of file to be received
            1       -              fileType     str        the extension of the file
            2       -              numSegments  int>0      segmentation number
        :sends
        opcode  description
        100     manual acknowledgment of request
        """

        # example: 211mytext\x1ctxt\x1c400
        # args: mytext\x1ctxt -> split with \x1c -> [mytext, txt, 200]

        # split args string
        argList = args.split(self.SEPERATOR)

        # make sure the number of arguments is 3
        assert len(argList) == 3, "Expected 3 arguments: fileName, fileType, segmentsNumber"

        # parse args
        fileName, fileType, numSegments = argList
        fileName, fileType, numSegments = fileName.decode('utf-8'), fileType.decode('utf-8'), int(
            numSegments.decode('utf-8'))

        print(f'[{self.name}]:', f'Receiving file [{fileName}.{fileType}] - (0/{numSegments}) ')

        # generate file data
        self.fileToReceive = {
            'name': fileName,
            'type': fileType,
            'segments': [None] * numSegments,  # list of arriving segments
            'received': 0,  # number of received segments
            'total': numSegments,  # total number of segments
            'timestamps': [time.perf_counter_ns() / 1000.0],  # timestamps of arrival of segments
            'rate': 0  # realtime average of bitrate
        }

        # manual acknowledgment
        self.sendMessage(f'100 file ready to be received')

    def receiveSegment(self, args, timestamp):
        """
        OPCODE 212
        Receives a segment of file data

        :param timestamp: float - optional - time at which the data is received
        :param args: byteArray:
            number of fields: 2
            index   length(chars)  name         values     description
            0       -              seqNum       str        index of segment in file
            1       -              data         bytes      binary data
        :sends
        opcode  description                        args
        100     manual acknowledgment of segment   segment index
        """
        # example: 212001\x1cDATASEGMENT
        # args: mytext\x1ctxt -> split with \x1c -> [mytext, txt, 200]

        assert self.fileToReceive is not None, "Server not expecting file"
        assert self.fileToReceive['received'] != self.fileToReceive['total'], "Received all segments"

        # find index of first separator
        separateAt = args.find(self.SEPERATOR)
        assert separateAt != -1, "Expected 2 arguments: sequence number, data"
        # split args
        seqNum, data = [args[:separateAt], args[separateAt+1:]]
        seqNum = int(seqNum.decode('utf-8'))

        assert seqNum < self.fileToReceive['total'], "Sequence number not in range"
        assert self.fileToReceive['segments'][seqNum] is None, "Segment already received"

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

        print(f'[{self.name}]:',
              f'Receiving file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] - ({self.fileToReceive["received"]}/{self.fileToReceive["total"]}) - {round(self.fileToReceive["rate"])} bps ')

        self.sendMessage(f'100{seqNum}')

        if self.fileToReceive['received'] == self.fileToReceive['total']:
            data = compileData(self.fileToReceive['segments'])
            writeFile(self.fileToReceive['name'], self.fileToReceive['type'], FILE_PATH, data)

            # self.sendMessage(f'100')
            print(f'[{self.name}]:',
                  f'file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] Received successfully')

            self.fileToReceive = None

    def getFiles(self, args, timestamp = None):
        print(f'[{self.name}]:', 'Sending File list')
        files = json.dumps(getFileList())
        self.sendMessage('230'+files)

    def startSendFile(self, args, timestamp = None):

        # example: 2411

        # make sure args exist
        assert args, "Expected 1 argument: file id"

        # parse args
        fileID = int(args.decode('utf-8'))

        fileName, fileType, data= getFile(fileID, FILE_PATH)

        segments, numSegments= segmentData(1012, data)

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

        self.sendMessage(f'241{fileName}\x1c{fileType}\x1c{numSegments}', waitSuccess=True)

        start = None
        end = None
        for i, s in enumerate(segments):
            startS, endS, bitrate = self.sendSegment(i, s)
            print(f'[{self.name}]:', f'Sending file [{fileName}.{fileType}] - ({i+1}/{numSegments}) - {round(bitrate)} bps')

            if not start:
                start = startS
            end = endS

        throughput = len(data)*8/(end-start)*1E6
        print(f'[{self.name}]:', f'Finished Sending file [{fileName}.{fileType}] - throughput: {throughput} bps')

    def sendSegment(self,index, segment):
        msg = f'212{index}\x1c'
        startSend, endSend, endAll, durationSend, durationAll = self.sendMessage(bytes(msg,'utf-8')+segment,isString=False, waitSuccess=True)
        bitrate = len(segment)*8/durationAll*1E6
        return startSend, endAll, bitrate


    @staticmethod
    def port():
        return 6000


def getBitrate(dataSize, duration):
    bits = dataSize * 8
    return bits / duration * 1E6

def getAverageRate(sampleNumber, oldAverage, newSampleSize, duration):
        newRate = getBitrate(newSampleSize, duration )
        #return (sampleNumber - 1) * 1.0 / sampleNumber * oldAverage + newRate / sampleNumber
        return newRate
