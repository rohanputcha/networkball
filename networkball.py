import game
import threading
from manager import Manager
import logging
import socket

HOST_PORT = 9999
PLAYER_PORT = 9990

def get_local_ip():
    try:
        # Create a socket connection to an external server (e.g., Google's public DNS server)
        # The actual destination doesn't matter, as we are just using it to find the local IP address
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except socket.error as e:
        print(f"Error getting local IP address: {e}")
        return "localhost"
    
    # code to get public ip
    # import requests
    # return requests.get('https://api.ipify.org').text

def menu():
    print("Welcome to Network Ball!")
    print("Controls:")
    print("WASD to move")
    print("Press Q to quit")
    print("Press H to host")
    print("Press J to join")
    stdin = input("Enter a command: ")
    stdin = stdin.lower()
    if stdin == "q":
        exit()
    elif stdin == "h":
        host()
    elif stdin == "j":
        join()
    else:
        menu()

def host():
    local_ip = get_local_ip()
    print(f"Hosting on {local_ip}:{HOST_PORT}...")
    manager = Manager(local_ip, HOST_PORT)
    manager_thread = threading.Thread(target=manager.run)
    manager_thread.start()
    game.game(local_ip, HOST_PORT, local_ip, PLAYER_PORT)
    manager.shutdown()
    manager_thread.join()
    print("Host stopped")
def join():
    local_ip = get_local_ip()
    host = input("Enter host: ")
    port = int(input("Enter port: "))
    game.game(host, port, local_ip, PLAYER_PORT)

def main():
    # logging.basicConfig(level=logging.INFO) # logging
    menu()

if __name__ == "__main__":
    main()
