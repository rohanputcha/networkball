import game
import threading
from manager import Manager
import logging

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
    print("Hosting...")
    manager = Manager("localhost", 5000)
    manager_thread = threading.Thread(target=manager.run)
    manager_thread.start()
    game.game("localhost", 5000, "localhost", 5001)
    manager.shutdown()
    manager_thread.join()
    print("Host stopped")
def join():
    host = input("Enter host: ")
    port = int(input("Enter port: "))
    game.game(host, port, "localhost", 5002) # change client port depending on how many clients are running

def main():
    # logging.basicConfig(level=logging.INFO) # logging
    menu()

if __name__ == "__main__":
    main()
