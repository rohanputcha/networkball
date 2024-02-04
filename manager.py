import threading
import socket
import time
import json
import logging

LOGGER = logging.getLogger(__name__)
SLEEP_TIME = 0.05
SLEEP_TIMEOUT = 1

class Manager:
    def __init__(self, host, port):
        LOGGER.info(
            "Starting manager host=%s port=%s",
            host, port,
        )
        self.host = host
        self.port = port
        self.clients = []
        self.clients_timeout = {}
        self.clients_location = {}
        self.message_queue = []
        self.signals = {"shutdown": False}
    
    def run(self):
        tcp_listen = threading.Thread(target=self.tcp_listen)
        udp_listen = threading.Thread(target=self.udp_listen)
        check_timeout = threading.Thread(target=self.check_timeout)
        send_locations = threading.Thread(target=self.send_locations)
        tcp_listen.start()
        udp_listen.start()
        check_timeout.start()
        send_locations.start()

        while not self.signals["shutdown"]:
            while self.message_queue:
                message = self.message_queue.pop(0)
                self.handle_udp_message(message)
            time.sleep(SLEEP_TIME)

        tcp_listen.join()
        udp_listen.join()
        LOGGER.info("Manager stopped")

    def tcp_listen(self):
        LOGGER.info("Starting TCP listener")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.settimeout(1)
            sock.listen()
            while not self.signals["shutdown"]:
                try:
                    clientsocket, _ = sock.accept()
                except socket.timeout:
                    continue
                clientsocket.settimeout(1)
                with clientsocket:
                    while True:
                        try:
                            data = clientsocket.recv(4096)
                        except socket.timeout:
                            continue
                        if not data:
                            break
                        try:
                            message = json.loads(data)
                            LOGGER.info("Received TCP message %s", message)
                        except json.JSONDecodeError:
                            continue
                        self.handle_tcp_message(message)
        LOGGER.info("TCP listener stopped")

    def udp_listen(self):
        LOGGER.info("Starting UDP listener")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.settimeout(1)
            while not self.signals["shutdown"]:
                try:
                    data, _ = sock.recvfrom(4096)
                except socket.timeout:
                    continue
                try:
                    message = json.loads(data)
                    LOGGER.info("Received UDP message %s", message)
                except json.JSONDecodeError:
                    continue
                self.message_queue.append(message)
        LOGGER.info("UDP listener stopped")

    def send_udp_message(self, host, port, message):
        LOGGER.info("Sending UDP message %s", message)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect((host, port))
            messagejson = json.dumps(message)
            sock.sendall(messagejson.encode('utf-8'))

    def send_tcp_message(self, host, port, message):
        LOGGER.info("Sending TCP message %s", message)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            messagejson = json.dumps(message)
            sock.sendall(messagejson.encode('utf-8'))

    def handle_tcp_message(self, message):
        print(message)
        if message["type"] == "register":
            self.clients.append((message["host"], message["port"]))
            self.clients_location[(message["host"], message["port"])] = message["location"]
            self.clients_timeout[(message["host"], message["port"])] = time.time()
            LOGGER.info("Registered client %s", message)
            reply = {"type": "register_ack"}
            self.send_tcp_message(message["host"], message["port"], reply)
    
    def handle_udp_message(self, message):
        if (message['host'], message['port']) not in self.clients:
            LOGGER.info("Client %s not registered", message)
            return
        if message["type"] == "location":
            self.clients_timeout[(message["host"], message["port"])] = time.time()
            LOGGER.info("Received location %s", message)
            self.clients_location[(message["host"], message["port"])] = message["location"]

    def check_timeout(self):
        LOGGER.info("Starting timeout checker")

        while not self.signals["shutdown"]:
            to_remove = None
            for client in self.clients_timeout:
                if time.time() - self.clients_timeout[client] > 5:
                    to_remove = client
                    break
            if to_remove:
                LOGGER.info("Client %s timed out", to_remove)
                self.clients.remove(to_remove)
                del self.clients_timeout[to_remove]
                del self.clients_location[to_remove]
            time.sleep(SLEEP_TIMEOUT)
        LOGGER.info("Timeout checker stopped")

    def send_locations(self):
        LOGGER.info("Starting location sender")

        while not self.signals["shutdown"]:
            for client in self.clients:
                locations = []
                for client_info in self.clients:
                    locations.append({
                        "host": client_info[0],
                        "port": client_info[1],
                        "location": self.clients_location[client_info]
                    })
                reply = {
                    "type": "players_locations",
                    "locations": locations
                }
                self.send_udp_message(client[0], client[1], reply)
            time.sleep(SLEEP_TIME)
        LOGGER.info("Location sender stopped")

    def shutdown(self):
        self.signals["shutdown"] = True