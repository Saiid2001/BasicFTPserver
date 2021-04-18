from .session import Session
from .FTP import TcpFTPSession, UdpFTPSession


class ClientSession(Session):
    """
    ClientSession is the session that handles user entry and main operations.
    Scope of requests include:
    210 - startFTPSession
    222 - keepAlive
    """

    def __init__(self):

        # Dictionary of available commands to be requested from Client Session
        self.commands = {
            b'210': self.startFTPSession,
            b'222': self.keepAlive
        }
        Session.__init__(self, 'Client Session', 5000, 'TCP')

    def waitClientRequest(self):
        print(f'[{self.name}]: Available for connection')

        # wait for TCP connection to be sent from a client
        conn, addr = self.socket.accept()

        # update the serviced client of the session
        self.client = {'connection': conn, 'address': addr}

        super().waitClientRequest()

    def sendMessage(self, message, waitSuccess=False):
        """
        Sends a message to the client.
        :param waitSuccess: bool - wait for client for acknowledgment on message
        :param message: str - the payload of the message to be sent
        """
        if self.client is not None:
            raw = bytes(message + "\n\r", 'utf-8')
            self.client['connection'].sendall(raw)

            if waitSuccess:
                data = self.client['connection'].recv(1024)
                if data and data[:3] == '100':
                    return
                else:
                    self.sendMessage(message, waitSuccess = True)

    def run(self):

        # make sure a connection is active
        with self.client['connection'] as connection:
            try:
                # infinite loop to read multiple requests
                while True:
                    # save the received message in data
                    data = connection.recv(1024)
                    if not data:
                        # close on no data
                        break

                    # handle the received data
                    try:
                        self.onReceived(data)

                    except AssertionError as e:
                        print(f'[{self.name}]:', e)
                        self.sendMessage(f'400 '+str(e))

            except ConnectionResetError:
                # is triggered if the connection is closed remotely
                print(f'[{self.name}]: Client Ended Connection')

                # if connection closed wait for a new one.
                return self.waitClientRequest()

    def onReceived(self, payload):
        """
        Handle the received message from the client.
        Parses the received message and decodes it.
        :param payload: byteArray - the received request
        """

        assert len(payload)>=3, "Invalid request length"

        # parse the incoming message into the format   [opcode|args] with opcode as a 3 digit integer
        opcode, args = payload[:3], payload[3:]

        assert opcode in self.commands, f'Invalid request OPCODE = "{opcode}"'

        super().onReceived(payload)

        # executing the command requested by the client

        self.commands[opcode](args)

    # OPCODE 210
    def startFTPSession(self, args):
        """
        OPCODE 210
        Starts an FTP Session to handle user file operations.

        :param args: byteArray:
            number of fields: 1
            index   length(chars)  name      values                  description
            0       1              connType  0 for TCP, 1 for UDP    specifies the type of the FTPSession to be opened

        :sends
        opcode  args
        210     port number of FTP server
        400     error in fetching FTP server type
        """

        # definitions
        FTPSession = {
            b'0': TcpFTPSession,
            b'1': UdpFTPSession
        }

        # extracting args
        typeCode = args[0:1]

        if typeCode not in FTPSession:
            self.sendMessage(f'400 Session Type invalid. possible values 0 -> TCP, 1 ->UDP.')
            return

        # send a message about the port of FTP Server
        self.sendMessage(f'210{FTPSession[typeCode].port()}', waitSuccess=True)

        # opens the FTPSession
        FTPSession[typeCode]()

    # OPCODE 222
    def keepAlive(self, args):
        """
        OPCODE 210
        Starts an FTP Session to handle user file operations.

        :param args: byteArray:
            no fields expected

        :sends
        opcode  description
        222     connection still available
        """
        self.sendMessage(f'222 Connection Available')
