import random
import socket

from Qt import QtCore

from chatterbox.logger import LOG
from chatterbox.utils import (
    BROADCAST_ADDR, BROADCAST_PORT,
    MessageType, ChatAppMessageError,
    getUser
)
from chatterbox.message import Message


class ListenerMode(object):
    BROADCAST = 0


class SocketListener(QtCore.QObject):
    handler_template = "_handle_{mtype}"

    userConnected = QtCore.Signal(str, str)
    newChatServerRequested = QtCore.Signal(str, str)
    newChatClientRequested = QtCore.Signal(str, str, int)

    def __init__(self, addr=BROADCAST_ADDR, port=BROADCAST_PORT, mode=ListenerMode.BROADCAST, parent=None):
        super(SocketListener, self).__init__(parent)

        self.stop = False
        self.sock = None
        self.addr = addr
        self.port = port
        self.mode = mode
        self.user = getUser()

    def _bind(self, sock, addr, port, retry=100):
        bound = False
        count = 0
        bind_port = port

        while not bound and count < retry:
            try:
                sock.bind(
                    (addr, bind_port)
                )
                bound = True
            except socket.error:
                bind_port = port
                bind_port -= random.randint(1, 50)
                print("Port %d in use. Retrying on %d" % (port, bind_port))
                count += 1

        return bound

    def _handle_ehlo(self, message):
        """
        _handle_ehlo is a message handler for "ehlo" message types.

        :param message: Message object that we have built from the socket.
        :type message: Message
        """
        LOG.debug("Presence From %s@%s" % (message.user, message.hostname))
        self.userConnected.emit(message.user, message.hostname)

    def _handle_start_chat_server(self, message):
        """
        _handle_start_chat_server is a message handler for "start_chat_server"
            message types.

        :param message: Message object that we have built from the socket.
        :type message: Message
        """
        LOG.debug("%s wants to chat. Chat Server requested" % message.user)
        self.newChatServerRequested.emit(message.user, message.hostname)

    def _handle_start_chat_client(self, message):
        """
        _handle_start_chat_client is a message handler for "start_chat_client"
            message types.

        :param message: Message object that we have built from the socket.
        :type message: Message
        """
        intended_user, port = message.message.split(Message.SEP)
        LOG.debug("%s has setup a server for %s to connect to at port %s" % (
            message.user, intended_user, port
        ))
        if intended_user == self.user:
            self.newChatClientRequested.emit(message.user, message.hostname, port)

    def _handle_chat(self, message):
        """
        _handle_chat is a message handler for "chat" message types.

        :param message: Message object that we have built from the socket.
        :type message: Message
        """
        if self.mode == ListenerMode.BROADCAST:
            raise ValueError("Chat message send to a broadcast listener port!")
        else:
            raise NotImplementedError("Could not handle chat message but I am not a broadcast!")

    def handle_message(self, message):
        """
        handle_message is the where we check to see if the message object we received
            has a handler that can accept it.

        :param message: Message object that we have built from the socket.
        :type message: Message
        """
        message_type = MessageType.TO_NAMES.get(message.message_type, None)
        if message_type:
            if hasattr(self, self.handler_template.format(mtype=message_type)):
                method = getattr(self, self.handler_template.format(mtype=message_type))
                LOG.debug("Calling %s" % method)
                return method(message)

        LOG.debug(
            "Received unknown message from \"{u}\": \"{host}\"\n"
            "{mtype}: \"{msg}\"".format(
                u=message.user, host=message.hostname,
                msg=message.message, mtype=message.message_type
            )
        )

    def run_forever(self):
        while not self.stop:
            data, (host, port) = self.sock.recvfrom(1024)
            try:
                message = Message.from_str(data)
                LOG.debug("Recieved message from %s" % message.user)

                if message.user == self.user:
                    LOG.debug("Message from self. Ignoring")
                    continue

                self.handle_message(message)

            except ChatAppMessageError as err:
                LOG.error("ERROR: \"{err}\"".format(err=err))
        LOG.debug("Listener exitting")

    @QtCore.Slot()
    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.mode == ListenerMode.BROADCAST:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._bind(self.sock, self.addr, self.port)

        self.run_forever()

    @QtCore.Slot()
    def exit_slot(self):
        self.stop = True
