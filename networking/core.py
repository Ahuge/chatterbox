from Qt import QtCore

from chatterbox.networking.listener import SocketListener
from chatterbox.networking.broadcaster import SocketBroadcaster
from chatterbox.networking.chat import SocketChat
from chatterbox.networking import utils
from chatterbox.networking.message import Message


class BroadcastServerCore(QtCore.QObject):
    userConnected = QtCore.Signal(str, str)
    requestNewChatWindow = QtCore.Signal(str, str, SocketChat)
    broadcastNewChatServer = QtCore.Signal(str, str, int)
    requestNewChat = QtCore.Signal(str, str, object)

    def __init__(self, name, parent=None):
        super(BroadcastServerCore, self).__init__(parent)

        self.listenerThread = QtCore.QThread(self)
        self.listener = SocketListener()
        self.listener.moveToThread(self.listenerThread)

        self.broadcasterThread = QtCore.QThread(self)
        self.broadcaster = SocketBroadcaster(name)
        self.broadcaster.moveToThread(self.broadcasterThread)

        self.listenerThread.finished.connect(self.listener.exit_slot)
        self.listenerThread.started.connect(self.listener.run)

        self.listener.newChatClientRequested.connect(self.create_new_chat_client_slot)
        self.listener.newChatServerRequested.connect(self.create_new_chat_server_slot)
        self.listener.userConnected.connect(self.user_connected_slot)
        self.listener.response.connect(self.new_user)
        self.listener.start_chat.connect(self.new_chat)

        self.broadcasterThread.started.connect(self.broadcaster.run)
        self.broadcaster.finished.connect(self.broadcasterThread.quit)

        self.listenerThread.start()

        # Timer to automatically refresh who is online
        self.auto_refresh_timer = QtCore.QTimer(self)
        self.auto_refresh_timer.setInterval(utils.AUTO_REFRESH_TIME)
        self.auto_refresh_timer.timeout.connect(self.refresh)
        self.auto_refresh_timer.start(utils.AUTO_REFRESH_TIME)

    @QtCore.Slot(str, str)
    def user_connected_slot(self, user, host):
        self.userConnected.emit(user, host)

    def _create_socket_chat(self, isServer, user, host, port=None):
        key = "{user}@{host}".format(user=user, host=host)
        if isServer:
            chat = SocketChat.create_server()
        else:
            chat = SocketChat.create_client(host, port)

        chat_thread = QtCore.QThread(self)
        self.chats[key] = (
            chat, chat_thread
        )
        chat.moveToThread(self.listenerThread)
        chat_thread.started.connect(chat.run)
        chat.finished.connect(chat_thread.quit)
        return chat, chat_thread


    @QtCore.Slot(str, str, int)
    def create_new_chat_client_slot(self, user, host, port):
        chat, chat_thread = self._create_socket_chat(
            isServer=False,
            user=user,
            host=host,
            port=port
        )
        self.requestNewChatWindow.emit(user, host, chat)
        chat_thread.start()

    @QtCore.Slot(str, str)
    def create_new_chat_server_slot(self, user, host):
        chat, chat_thread = self._create_socket_chat(
            isServer=True,
            user=user,
            host=host,
        )
        # Post a global message telling the client to connect to me!
        self.broadcaster.postMessage(
            Message.SEP.join(user, chat.port),
            message_type=utils.MessageType.start_chat_client
        )
        self.requestNewChatWindow.emit(user, host, chat)
        chat_thread.start()

    @QtCore.Slot()
    def refresh(self):
        self.broadcaster.ehlo("")
        if not self.broadcasterThread.isRunning():
            self.broadcasterThread.start()

    @QtCore.Slot(str)
    def setName(self, name):
        self.broadcaster.setName(name)
