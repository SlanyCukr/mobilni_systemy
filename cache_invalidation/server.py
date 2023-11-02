import random
import socket
import threading
import time
import json

class Item:
    def __init__(self, item_id, content):
        self.item_id = item_id
        self.content = content
        self.time_changed = time.time()

    def update_content(self, new_content):
        self.content = new_content
        self.time_changed = time.time()

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "content": self.content,
            "time_changed": self.time_changed
        }

class Server:
    def __init__(self, host, port):
        self.items = [Item(i, f"Content {i}") for i in range(5)]
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen()
        print(f"Server listening on {host}:{port}")
        self.connected_clients = []
        threading.Thread(target=self.update_random_item_periodically).start()
        #threading.Thread(target=self.send_updates_to_clients_periodically).start()

    def start(self):
        while True:
            client_socket, address = self.server_socket.accept()
            self.connected_clients.append(client_socket)
            threading.Thread(target=self.handle_client, args=(client_socket, address)).start()

    def update_random_item_periodically(self):
        while True:
            time.sleep(10)  # Update one random item every 10 seconds
            random_item = random.choice(self.items)
            new_content = f"Updated Content {random_item.item_id} at {time.time()}"
            random_item.update_content(new_content)
            print(f"Updated item {random_item.item_id}")

    def send_updates_to_clients_periodically(self):
        while True:
            time.sleep(10)
            print("Sending updates to clients...")
            updated_item_ids = [item.item_id for item in self.items if time.time() - item.time_changed < 10]
            if updated_item_ids:
                response = {"type": "updated_ids", "item_ids": updated_item_ids}
                for client in self.connected_clients:
                    try:
                        client.send(json.dumps(response).encode())
                    except Exception as e:
                        print(f"Failed to send update to client: {e}")
                        self.connected_clients.remove(client)

    def handle_client(self, client_socket, address):
        print(f"Accepted connection from {address}")
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            request = json.loads(data)
            if request["type"] == "get_invalidated":
                print("Got a request for invalidated items...")
                last_update_time = request["since"]
                updated_items = [item.to_dict() for item in self.items if item.time_changed > last_update_time]
                response = {"type": "updated_items", "items": updated_items}
                client_socket.send(json.dumps(response).encode())
            elif request["type"] == "get_item":
                print("Got a request for an item...")
                item_id = request["item_id"]
                item = next((item for item in self.items if item.item_id == item_id), None)
                if item:
                    response = {"type": "item", "item": item.to_dict()}
                else:
                    response = {"type": "error", "message": "Item not found"}
                client_socket.send(json.dumps(response).encode())


if __name__ == "__main__":
    server = Server("localhost", 12345)
    server.start()
