from collections import deque
import socket
import time
import traceback

from Qt import QtCore

from chatterbox.networking.message import Message
from chatterbox.logger import LOG
from chatterbox.networking.utils import BROADCAST_PORT, BROADCAST_ADDR, getUser, MessageType


class BroadcasterMode(object):
    BROADCAST = 1


class SocketBroadcaster(QtCore.QObject):
    def __init__(self, user=None, sock=None, addr=None, port=None, mode=None, parent=None):
        super(SocketBroadcaster, self).__init__(parent)

        self.user = user or getUser()
        self.hostname = socket.gethostname()
        self.addr = addr or BROADCAST_ADDR
        self.port = port or BROADCAST_PORT
        self.mode = mode or BroadcasterMode.BROADCAST
        self.message_queue = deque([])
        self.sock = sock or None
        self.stop = False

    @QtCore.Slot(str, str)
    def postMessage(self, message, message_type):
        self.message_queue.appendleft(self.prepareMessage(
            message=message, message_type=message_type
        ))

    def setup_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def sendMessage(self, message):
        if self.sock is None:
            self.setup_socket()

        try:
            LOG.debug("Sending message to %s:%s" % (self.addr, self.port))
            self.sock.sendto(message.to_str(), (self.addr, self.port))
        except Exception as err:
            LOG.debug(traceback.format_exc())
            LOG.warning("Could not send message to %s:%s  - \"%s\"" % (
                self.addr, self.port, message.to_str()
            ))

    def prepareMessage(self, message, message_type):
        return Message(
            user=self.user,
            hostname=self.hostname,
            message_type=message_type,
            message=message
        )

    def run(self):
        while not self.stop:
            if len(self.message_queue):
                message = self.message_queue.pop()
                self.sendMessage(message)
            else:
                time.sleep(0.5)

        self.finished.emit()

    def ehlo(self, message=None):
        self.postMessage(message, message_type=MessageType.ehlo)
