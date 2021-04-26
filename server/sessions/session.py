from sockets import openPort


# Saiid EL Hajj Chehade
class SessionClosedException(Exception):
    def str(self):
        return "Closed Session"


class Session:
    '''
    Session is a base class for the possible socket sessions on the server.
    Children:
    [ClientSession]
    [TcpFTPSession]
    [UdpFTPSession]

    The session handles application logic APIs
    '''

    def __init__(self, name, port, conType):
        '''
        Initializes the Session Object
        :param name: str -optional name of the session object.
        :param port: int - Port number to bind the session to.
        :param conType: str - Connection Type. "TCP" or "UDP"
        '''
        # definitions
        self.name = name
        self.client = None  # the client address connecting

        # opening the socket for the session
        self.socket = openPort(port, conType)

        # wait for clients
        self.waitClientRequest()

    # gets called and runned when the session is created
    def run(self):
        '''
        The main loop of a session. Keeps running until the session is closed. Handles waiting for incoming data and
        parsing them accordingly.
        This base method is abstract
        '''
        pass

    def close(self, *args):
        '''
        Closes session and socket connection.
        '''
        if self.socket:

            #self.sendMessage('500 Closing Connection')
            self.socket.close()

        raise SessionClosedException()

    def onReceived(self, payload, acknowledge=False):
        '''
        Handles Received Messages.
        In base class, this prints the received message
        :param payload: byteArray - the payload of the received message
        '''

        # decode received message into string
        text = payload.decode('utf-8')

        print("[" + self.name + "]:", self.client["address"][0] + ":" + str(self.client['address'][1]), 'sent: ', text)

        # send optional acknowledgment
        if acknowledge:
            self.sendMessage('100 Received')

    def waitClientRequest(self):
        # for the base class we assume connection is immediate
        self.onConnection()

    def onConnection(self):
        # for the base class we just want to run on connection
        print(f'[{self.name}]: Connected - Client = {self.client["address"]}')

        self.run()

    def sendMessage(self, message):
        pass
