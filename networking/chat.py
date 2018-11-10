from collections import deque
import random
import socket

from Qt import QtCore

from chatterbox.networking.message import Message
from chatterbox.logger import LOG
from chatterbox.networking.utils import (
    MessageType, BROADCAST_ADDR, BROADCAST_PORT, CHAT_PORT,
    ChatAppMessageError
)


class SocketChat(QtCore.QObject):
    recieved_message = QtCore.Signal(Message)
    sent_message = QtCore.Signal(str)
    finished = QtCore.Signal()
    SERVER = 0
    CLIENT = 1

    def __init__(self, mode=None, host=None, port=None):
        super(SocketChat, self).__init__()
        self.base_sock = self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mode = SocketChat.SERVER
        self.host = host
        self.port = port or CHAT_PORT
        self.stop = False
        self.connected = False
        self.send_message_queue = deque([])

        if mode == SocketChat.SERVER:
            self.listen()
        elif mode == SocketChat.CLIENT:
            self.connect(host, port)

    def connect(self, host, port):
        self.sock.connect((host, port))
        self.mode = SocketChat.CLIENT
        self.connected = True

    def _bind(self):
        localhost = socket.gethostname()
        self.host = localhost
        bound = False
        count = 0
        while not bound and count < 100:
            try:
                self.base_sock.bind((localhost, self.port))
                bound = True
            except socket.error:
                self.port = CHAT_PORT
                self.port -= random.randint(0, 100)

                count += 1
        if not bound:
            raise ValueError("Could not connect!")

    def listen(self):
        self._bind()

        self.base_sock.listen(1)
        client_socket, addr = self.base_sock.accept()
        LOG.debug("Got a connection from %s" % (str(addr)))
        self.sock = client_socket
        self.connected = True

    def run(self):
        if self.mode == SocketChat.SERVER and (self.base_sock is self.sock or not self.connected):
            self.listen()
        elif self.mode == SocketChat.CLIENT and not self.connected:
            self.connect(self.host, self.port)

        while not self.stop:
            data, (host, port) = self.sock.recvfrom(1024)
            try:
                message = Message.from_str(data)
                self.recieved_message.emit(message)
            except ChatAppMessageError as err:
                LOG.debug("ERROR: \"{err}\"".format(err=err))

            while len(self.send_message_queue):
                message = self.send_message_queue.pop()
                LOG.debug("Sending message \"%s\"" % message)
                self.sock.send(message)
                self.sent_message.emit(message)
        LOG.debug("Server exiting")

    @QtCore.Slot(str, str)
    def send_message(self, message, message_type):
        if not self.client:
            raise ValueError("Could not send message. No client connected!")
        formatted_message = self.prepareMessage(
            message=message,
            message_type=message_type,
        ).to_str()
        self.send_message_queue.appendleft(formatted_message)

    @classmethod
    def create_server(cls):
        return SocketChat(mode=SocketChat.SERVER)

    @classmethod
    def create_client(cls, host, port):
        return SocketChat(mode=SocketChat.CLIENT, host=host, port=port)
