import random
import socket
import time
from threading import Thread

from colorama import Fore

import myProtocol.chat as chat_protocol
import myProtocol.udp as udp_protocol

# Constants

BROADCAST_PORT = 37020
BROADCAST_INTERVAL = 20
AF_INET = socket.AF_INET
SOCK_DGRAM = socket.SOCK_DGRAM
IPPROTO_UDP = socket.IPPROTO_UDP
SOL_SOCKET = socket.SOL_SOCKET
SO_BROADCAST = socket.SO_BROADCAST
SOCK_STREAM = socket.SOCK_STREAM

# Colors
CL_REGULAR = Fore.WHITE
CL_MY_MESSAGE = Fore.BLUE
CL_MY_MESSAGE_TEXT = "BLUE"
CL_OTHER_MESSAGE = Fore.GREEN
CL_OTHER_MESSAGE_TEXT = "GREEN"
CL_ERROR = Fore.RED


class Chat:
    def __init__(self):
        self.my_chat_port = random.randrange(0, 65535)
        self.broadcast_port = random.randrange(0, 65535)
        self.other_addr = ('0', 0)
        self.is_connected = False
        self.name = input("Enter your name: ")

        print(CL_REGULAR + "My chat port is ", self.my_chat_port)
        print(CL_REGULAR + "My broadcast port is ", self.broadcast_port)
        pass

    def start(self):
        self.start_udp_threads()
        pass

    def set_other(self, ip, port):
        port = int(port)
        self.other_addr = (ip, port)
        pass

    def udp_broadcast(self):
        with socket.socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP) as server:
            server.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            server.settimeout(0.2)

            is_bind = False
            while not is_bind:
                try:
                    server.bind(("", self.broadcast_port))
                    is_bind = True
                except OSError:
                    is_bind = False

            while not self.is_connected:
                server.sendto(udp_protocol.send_broadcast_request(self.my_chat_port), ('<broadcast>', BROADCAST_PORT))
                print(CL_REGULAR + "****Broadcast****")
                try:
                    data, addr = server.recvfrom(1024)
                    received_port = udp_protocol.receive_broadcast_response(data)
                    if self.my_chat_port != received_port:
                        print(CL_REGULAR + "UDP_B {addr}: \"port={port}\"".format(addr=addr, port=received_port))
                        self.set_other(addr[0], received_port)
                        self.listen()
                        server.sendto(udp_protocol.send_listening_message(self.my_chat_port), addr)
                        break
                except (ValueError, Exception):
                    print(CL_REGULAR + "Broadcast has no answer", )
                time.sleep(BROADCAST_INTERVAL)
        pass

    def udp_listen(self):
        with socket.socket(AF_INET, socket.SOCK_DGRAM) as client:
            client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            try:
                client.bind(("", BROADCAST_PORT))
            except (ValueError, Exception):
                pass
            print(CL_REGULAR + "I'm listening on ", BROADCAST_PORT)
            while not self.is_connected:
                data, addr = client.recvfrom(1024)
                received_port = udp_protocol.receive_broadcast_request(data)
                if self.broadcast_port != addr[1]:
                    client.sendto(udp_protocol.send_broadcast_response(self.my_chat_port), addr)
                    self.set_other(addr[0], received_port)
                    print(CL_REGULAR + "UDP_L: {}: \"port={}\"".format(addr, received_port))
                    client.recvfrom(1024)
                    self.connect()
                    break
        pass

    def start_udp_threads(self):
        thread1 = Thread(target=self.udp_broadcast, )
        thread2 = Thread(target=self.udp_listen, )

        thread1.start()
        thread2.start()
        pass

    def connect(self):
        self.is_connected = True
        print(CL_REGULAR + "Connecting to {}...".format(self.other_addr))
        try:
            client = socket.socket(AF_INET, SOCK_STREAM)
            client.connect(self.other_addr)
            print(CL_REGULAR + "{} connected".format(self.other_addr))
            print(CL_REGULAR + "I am chat client")
            self.handle_chat(client)
        except ConnectionRefusedError:
            self.is_connected = False
            self.start_udp_threads()
        pass

    def listen(self):
        self.is_connected = True
        print(CL_REGULAR + "Listening at {}...".format(self.my_chat_port))
        try:
            server = socket.socket(AF_INET, SOCK_STREAM)
            server.bind(('', self.my_chat_port))
            server.listen(5)
            client, addr = server.accept()
            print(CL_REGULAR + "{} accepted".format(addr))
            print(CL_REGULAR + "I am chat server")
            self.handle_chat(client)
        except (ValueError, Exception):
            print(CL_ERROR + "Connection Refused")
            self.is_connected = False
            self.start_udp_threads()
        pass

    def receive_chat(self, client):
        while True:
            try:
                request = client.recv(1024)
                sender, message = chat_protocol.receive(request)
                print(CL_OTHER_MESSAGE + "{}>>>>{}".format(sender, message))
            except (ValueError, Exception):
                if not client._closed:
                    self.close_tcp_connection(client)
                break
        pass

    def send_chat(self, client):
        while True:
            message = input()
            if message != "EXIT":
                try:
                    client.send(chat_protocol.send(self.name, message))
                    print(CL_MY_MESSAGE + "ME>>>>{}".format(message))
                except (ValueError, Exception):
                    self.close_tcp_connection(client)
                    break
            else:
                self.close_tcp_connection(client)
                break
        pass

    def close_tcp_connection(self, client):
        try:
            print(CL_ERROR + "Closing...\r", end="")
            client.shutdown(socket.SHUT_RDWR)
            client.close()
            self.is_connected = False
            print(CL_ERROR + "Connection Closed")
            self.start_udp_threads()
        except (ValueError, Exception):
            pass
        pass

    def handle_chat(self, client):
        print(Fore.LIGHTRED_EX + "Your messages are ", end="")
        print(CL_MY_MESSAGE + CL_MY_MESSAGE_TEXT)
        print(Fore.LIGHTRED_EX + "Messages of your contact are ", end="")
        print(CL_OTHER_MESSAGE + CL_OTHER_MESSAGE_TEXT)
        print(Fore.LIGHTRED_EX + "Insert a text and press \"Enter\" to send")
        print(Fore.LIGHTRED_EX + "Insert \"EXIT\" to close the connection")

        thread1 = Thread(target=self.receive_chat, args=(client,))
        thread2 = Thread(target=self.send_chat, args=(client,))

        thread1.start()
        thread2.start()
        pass


if __name__ == "__main__":
    chat = Chat()
    chat.start()
