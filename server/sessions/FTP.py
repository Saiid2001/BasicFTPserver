from .session import Session
from file import compileData, writeFile
import time
from config import FILE_PATH


class TcpFTPSession(Session):
    def __init__(self):
        print('[TCP FTP Session]: Started')

    @staticmethod
    def port():
        return 6001


class UdpFTPSession(Session):
    def __init__(self):
        # Dictionary of available commands to be requested from Client Session
        self.SEPERATOR = b'\x1c'
        self.fileToReceive = None
        self.commands = {
            b'211': self.requestReceiveFile,
            b'212': self.receiveSegment
        }
        Session.__init__(self, 'UDP FTP Session', UdpFTPSession.port(), 'UDP')

    def waitClientRequest(self):
        print(f'[{self.name}]: Available for Clients')

        data, addr = self.socket.recvfrom(1024)
        self.client = {'address': addr}
        self.onReceived(data, time.perf_counter_ns()/1000.0)
        super().waitClientRequest()

    def sendMessage(self, message, isString=True, waitSuccess=False):
        """
                Sends a message to the client.
                :param waitSuccess: bool - wait for client for acknowledgment on message
                :param data: byteArray - the payload of the message to be sent
                """
        if self.client is not None:
            data = message.encode('utf-8') if isString else message
            self.socket.sendto(data, self.client['address'] )

            if waitSuccess:
                data, addr = self.socket.recvfrom(1024)
                while addr != self.client['address']:
                    data, addr = self.socket.recvfrom(1024)

                if data and data[:3] == b'100':
                    return
                else:
                    self.sendMessage(data, waitSuccess=True)


    def run(self):

        # infinite loop to read multiple requests
        while True:
            # save the received message in data
            data, addr = self.socket.recvfrom(1024)
            timestamp = time.perf_counter_ns() /1000.0
            if not data:
                # close on no data
                break

            #check if data from client we are servicing
            if addr == self.client['address']:
                # handle the received data
                try:
                    self.onReceived(data, timestamp = timestamp)

                except AssertionError as e:
                    print(f'[{self.name}]:', e)
                    self.sendMessage(f'400 ' + str(e))


        # if connection closed wait for a new one.

        return self.waitClientRequest()

    def onReceived(self, payload, timestamp = None):

        """
                Handle the received message from the client.
                Parses the received message and decodes it.
                :param payload: byteArray - the received request
                """

        assert len(payload) >= 3, "Invalid request length"

        # parse the incoming message into the format   [opcode|args] with opcode as a 3 digit integer
        opcode, args = payload[:3], payload[3:]

        assert opcode in self.commands, f'Invalid request OPCODE = "{opcode}"'
        assert (not self.fileToReceive) or (self.fileToReceive and opcode == b'212'), "Cannot make another request while receiving a file"
        super().onReceived(payload)

        # executing the command requested by the client
        try:
            self.commands[opcode](args, timestamp)

        except AssertionError as e:
            print(f'[{self.name}]:', e)
            self.sendMessage(f'400 ' + str(e))

    def requestReceiveFile(self, args, timestamp = None):

        # example: 211mytext\x1ctxt\x1c400
        #args: mytext\x1ctxt -> split with \x1c -> [mytext, txt, 200]
        argList = args.split(self.SEPERATOR)

        assert len(argList) == 3, "Expected 3 arguments: fileName, fileType, segmentsNumber"

        fileName, fileType, numSegments = argList
        fileName, fileType, numSegments = fileName.decode('utf-8'), fileType.decode('utf-8'), int(numSegments.decode('utf-8'))

        print(f'[{self.name}]:', f'Receiving file [{fileName}.{fileType}] - (0/{numSegments}) ')
        segments = [None]*numSegments

        self.fileToReceive = {
            'name': fileName,
            'type': fileType,
            'segments': segments,
            'received': 0,
            'total': numSegments,
            'timestamps': [time.perf_counter_ns() /1000.0],
            'rate': 0
        }

    def receiveSegment(self, args, timestamp):

        # example: 212001\x1cDATASEGMENT
        #args: mytext\x1ctxt -> split with \x1c -> [mytext, txt, 200]

        assert self.fileToReceive is not None, "Server not expecting file"
        assert self.fileToReceive['received']!=self.fileToReceive['total'], "Received all segments"

        argList = args.split(self.SEPERATOR)

        assert len(argList) == 2, "Expected 2 arguments: sequence number, data"

        seqNum, data = argList
        seqNum = int(seqNum.decode('utf-8'))

        assert seqNum < self.fileToReceive['total'], "Sequence number not in range"
        assert self.fileToReceive['segments'][seqNum] is None, "Segment already received"

        self.fileToReceive["received"] += 1
        self.fileToReceive['segments'][seqNum] = data
        self.fileToReceive['timestamps'].append(timestamp)

        delta = self.fileToReceive['timestamps'][-1] - self.fileToReceive['timestamps'][-2]
        bits = len(data)*8
        rate = bits/delta*1E6
        n = self.fileToReceive['received']
        self.fileToReceive['rate'] = (n-1)*1.0/n * self.fileToReceive['rate']+rate/n

        print(f'[{self.name}]:', f'Receiving file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] - ({self.fileToReceive["received"]}/{self.fileToReceive["total"]}) - {self.fileToReceive["rate"]} bps ')

        self.sendMessage(f'100{seqNum}')

        if self.fileToReceive['received'] == self.fileToReceive['total']:

            data = b''.join(self.fileToReceive['segments'])
            writeFile(self.fileToReceive['name'], self.fileToReceive['type'], FILE_PATH, data)

            self.sendMessage(f'100')
            print(f'[{self.name}]:', f'file [{self.fileToReceive["name"]}.{self.fileToReceive["type"]}] Received successfully')

            self.fileToReceive = None


    @staticmethod
    def port():
        return 6000
