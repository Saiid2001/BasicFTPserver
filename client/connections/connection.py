# Code for base connection by Saiid El Hajj Chehade

import socket
from sockets import openSocket
from config import SERVER_IP
class Connection:
    '''
    Connection is a base class for the possible socket connections to the server.
    Children:
    [MainConnection]
    [TcpFTPConnection]
    [UdpFTPConnection]

    '''

    def __init__(self, name, port, conType, server_ip=None):
        '''
        Initializes the Session Object
        :param name: str -optional name of the session object.
        :param port: int - Port number to bind the session to.
        :param conType: str - Connection Type. "TCP" or "UDP"
        '''
        # definitions
        self.name = name
        if server_ip:
            self.server = (SERVER_IP, port)
        else:
            self.server = (SERVER_IP, port)

        # opening the socket for the session
        self.socket = openSocket(port, conType, server_ip)
        # wait for clients
        self.onConnection()

    # gets called and runned when the session is created
    # def run(self):
    #     '''
    #     The main loop of a session. Keeps running until the session is closed. Handles waiting for incoming data and
    #     parsing them accordingly.
    #     This base method is abstract
    #     '''
    #     pass

    def close(self):
        '''
        Closes session and socket connection.
        '''

        print(f'[{self.name}]: Closing Connection')
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()



    def onReceived(self, payload):
        '''
        Handles Received Messages.
        In base class, this prints the received message
        :param payload: byteArray - the payload of the received message
        '''

        # decode received message into string
        text = payload.decode('utf-8')

        print("[" + self.name + "]: Received:", text)

        # send optional acknowledgment
        self.sendMessage('100 Received')

    def onConnection(self):
        # for the base class we just want to run on connection
        print(f'[{self.name}]: Connected')


    def sendMessage(self, message):
        pass

