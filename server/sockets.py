import socket
#defining custom exceptions
class InvalidConnectionTypeException(Exception):
    def __init__(self, conType):
        self.type = conType

    def str(self):
        return "Type "+self.type+" is not valid. Valid types are [TCP, UDP]."

def openPort(port,conType):
    #constants
    HOST = '127.0.0.1'

    def openTCP():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((HOST, port))
        return sock

    def openUDP():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, port))
        return sock

    if conType == "TCP":
        return openTCP()
    elif conType == "UDP":
        return openUDP()
    else:
        raise InvalidConnectionTypeException(conType)