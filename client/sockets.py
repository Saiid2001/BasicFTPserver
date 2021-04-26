# code for sockets by Saiid El Hajj Chehade

import socket
from config import SERVER_IP
#defining custom exceptions
class InvalidConnectionTypeException(Exception):
    def __init__(self, conType):
        self.type = conType

    def str(self):
        return "Type "+self.type+" is not valid. Valid types are [TCP, UDP]."

def openSocket(port,conType, server_ip =None):
    #constants
    SERVER = SERVER_IP

    if server_ip:
        SERVER = server_ip


    def openTCP():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER, port))
        return sock

    def openUDP():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        return sock

    if conType == "TCP":
        return openTCP()
    elif conType == "UDP":
        return openUDP()
    else:
        raise InvalidConnectionTypeException(conType)

