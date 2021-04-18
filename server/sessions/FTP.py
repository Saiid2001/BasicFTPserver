from .session import Session
class TcpFTPSession(Session):
    def __init__(self):
        print('[TCP FTP Session]: Started')

    @staticmethod
    def port():
        return 6001


class UdpFTPSession(Session):
    def __init__(self):
        print('[UDP FTP Session]: Started')

    @staticmethod
    def port():
        return 6000
