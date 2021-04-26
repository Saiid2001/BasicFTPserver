# Code for main connection by Saiid El Hajj Chehade

from .connection import Connection
from .FTP import TcpFTPConnection, UdpFTPConnection
import time
class MainConnection(Connection):
    """
    ClientConnection is the connection that handles user entry and main operations.
    Scope of requests include:
    210 - startFTPConnection
    222 - keepAlive
    """

    def __init__(self, server_ip=None):

        # Dictionary of available commands to be requested from Client Connection
        # self.commands = {
        #     b'210': self.startFTPConnection,
        #     b'222': self.keepAlive
        # }
        Connection.__init__(self, 'Client Connection', 5000, 'TCP', server_ip=server_ip)

    def sendMessage(self, message, waitSuccess=False):
        """
        Sends a message to the client.
        :param waitSuccess: bool - wait for client for acknowledgment on message
        :param message: str - the payload of the message to be sent
        """
        if self.socket is not None:
            raw = bytes(message + "\n\r", 'utf-8')
            self.socket.sendall(raw)

            if waitSuccess:
                data = self.socket.recv(1024)
                if data and data[:3] == b'100':
                    return
                else:
                    self.sendMessage(message, waitSuccess = True)

    # def run(self):
    #
    #     try:
    #         # infinite loop to read multiple requests
    #         while True:
    #             # save the received message in data
    #             data = connection.recv(1024)
    #             if not data:
    #                 # close on no data
    #                 break
    #
    #             # handle the received data
    #             try:
    #                 self.onReceived(data)
    #
    #             except AssertionError as e:
    #                 print(f'[{self.name}]:', e)
    #                 self.sendMessage(f'400 '+str(e))
    #
    #     except ConnectionResetError:
    #         # is triggered if the connection is closed remotely
    #         print(f'[{self.name}]: Client Ended Connection')
    #
    #         # if connection closed wait for a new one.
    #         return self.waitClientRequest()

    def listen(self):

        data = self.socket.recv(1024)
        return self.onReceived(data)

    def onReceived(self, payload):
        """
        Handle the received message from the client.
        Parses the received message and decodes it.
        :param payload: byteArray - the received request
        """

        assert len(payload)>=3, "Invalid request length"

        # parse the incoming message into the format   [opcode|args] with opcode as a 3 digit integer
        opcode, args = payload[:3], payload[3:]

        return opcode, args

    # OPCODE 210
    def connectFTP(self, typeCode):

        # definitions
        FTPConnection = {
            'TCP': TcpFTPConnection,
            'UDP': UdpFTPConnection
        }

        if typeCode not in FTPConnection:
            self.sendMessage(f'400 Connection Type invalid. possible values  TCP, UDP.')
            return

        # send a message about the port of FTP Server
        self.sendMessage(f'210{FTPConnection[typeCode].type()}')

        opcode, args = self.listen()

        assert opcode == b'210', 'No Confirmation from server'

        self.sendMessage(f'100')

        start = time.perf_counter_ns()/1000.0

        while time.perf_counter_ns()/1000.0-start < 1000:
            pass

        print(f'[{self.name}]: Starting FTP Connection')
        self.close()

        return FTPConnection[typeCode](int(args.decode('utf-8')), server_ip = self.server[0])

    # OPCODE 222
    def keepAlive(self, args):
        """
        OPCODE 210
        Starts an FTP Connection to handle user file operations.

        :param args: byteArray:
            no fields expected

        :sends
        opcode  description
        222     connection still available
        """
        self.sendMessage(f'222 Connection Available')
