from Qt import QtWidgets, QtCore

from chatterbox.networking.core import BroadcastServerCore
from chatterbox.networking.utils import MessageType
from chatterbox.gui.user_list import UserList
from chatterbox.gui.chat import ChatTab


class Dialog(QtWidgets.QDialog):
    def __init__(self, username, parent=None):
        super(Dialog, self).__init__(parent)
        self.username = username

        self.server = BroadcastServerCore(self.username)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.users = UserList(self)
        self.chats = ChatTab(self)
        self.layout().addWidget(self.users)
        self.layout().addWidget(self.chats)

        self.chats.messageSendRequest.connect(self._send_chat_message)
        self.users.request_open_chat.connect(self._open_new_chat)
        self.users.request_refresh_user_list.connect(self.server.refresh)
        self.server.userConnected.connect(self.users.addUser)

    @QtCore.Slot(str, str)
    def _open_new_chat(self, user, host):
        self.chats.addChat(user, host)
        self.users.mark_user_open(user)

    @QtCore.Slot(str, str, str)
    def _send_chat_message(self, user, host, message):
        self.server.broadcaster.sendMessage(message, message_type=MessageType.chat)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    d = Dialog()
    d.show()
    app.exec_()

