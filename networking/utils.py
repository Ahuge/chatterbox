import os

MS = 1000

BROADCAST_ADDR = "255.255.255.255"
BROADCAST_PORT = 10002
CHAT_PORT = 5000
AUTO_REFRESH_TIME = 20 * MS  # 20 sec


class ChatAppMessageError(Exception):
    pass


class InvalidMessageFormatError(ChatAppMessageError):
    pass


class InvalidMessageVersionError(ChatAppMessageError):
    pass


def getUser():
    return os.environ.get("USER")


class MessageType(object):
    ehlo = 0
    start_chat_server = 1
    start_chat_client = 2
    chat = 3

    types = [ehlo, start_chat_server, start_chat_client, chat]

    TO_NAMES = {
        0: "ehlo",
        1: "start_chat_server",
        2: "start_chat_client",
        3: "chat"
    }
