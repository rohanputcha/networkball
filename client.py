import threading
import socket
import time
import json

SLEEP_TIME = 0.05
SLEEP_TIMEOUT = 1

class Client:
    def __init__(self, host, port, manager_host, manager_port, location):
        self.host = host
        self.port = port
        self.registered = False
        self.manager_host = manager_host
        self.manager_port = manager_port
        self.location = location
        self.player_locations = {}
        self.player_time_updated = {}
        self.signals = {"shutdown": False}
    
    def run(self):
        self.register()
        update_location = threading.Thread(target=self.update_location)
        udp_queue = []
        update_player_locations = threading.Thread(target=self.update_player_locations, args=(udp_queue,))
        remove_dead_players = threading.Thread(target=self.remove_dead_players)
        update_location.start()
        update_player_locations.start()
        remove_dead_players.start()
        while not self.signals["shutdown"]:
            while udp_queue and not self.signals["shutdown"]:
                message = udp_queue.pop(0)
                locations = message["locations"]
                for location in locations:
                    self.player_locations[(location["host"], location["port"])] = (location["location"][0], location["location"][1])
                    self.player_time_updated[(location["host"], location["port"])] = time.time()
            time.sleep(SLEEP_TIME)
        update_location.join()
        update_player_locations.join()

    def register(self):
        register_response = threading.Thread(target=self.register_response)
        register_response.start()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.manager_host, self.manager_port))
            message = json.dumps({"type": "register",
                                  "host": self.host,
                                  "port": self.port,
                                  "location": self.location})
            sock.sendall(message.encode('utf-8'))
        register_response.join()
        if not self.registered:
            raise Exception("Failed to register with manager")

    def register_response(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen()
            sock.settimeout(1)
            while not self.signals["shutdown"] and not self.registered:
                try:
                    server_socket, _ = sock.accept()
                except socket.timeout:
                    continue
                server_socket.settimeout(1)
                with server_socket:
                    while not self.signals["shutdown"] and not self.registered:
                        try:
                            data_recv = server_socket.recv(4096)
                        except socket.timeout:
                            continue
                        if not data_recv:
                            break
                        try:
                            data_json = json.loads(data_recv)
                        except json.JSONDecodeError:
                            continue
                        if data_json["type"] == "register_ack":
                            self.registered = True
                            break

    def update_location(self):
        while not self.signals["shutdown"]:
            if not self.registered:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((self.manager_host, self.manager_port))
                message = {
                    "type": "location",
                    "host": self.host,
                    "port": self.port,
                    "location": self.location
                }
                messagejson = json.dumps(message)
                sock.sendall(messagejson.encode('utf-8'))
            time.sleep(SLEEP_TIME)

    def set_location(self, location):
        self.location = location

    def get_player_locations(self):
        return self.player_locations
    
    def update_player_locations(self, udp_queue):
        while not self.signals["shutdown"]:
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
                    except json.JSONDecodeError:
                        continue
                    udp_queue.append(message)

    def remove_dead_players(self):
        while not self.signals["shutdown"]:
            to_remove = []
            for player in self.player_time_updated.keys():
                if time.time() - self.player_time_updated[player] > 5:
                    to_remove.append(player)
            for player in to_remove:
                del self.player_locations[player]
                del self.player_time_updated[player]
            time.sleep(SLEEP_TIMEOUT)

    def shutdown(self):
        self.signals = {"shutdown": True}