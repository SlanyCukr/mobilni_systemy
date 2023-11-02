import socket
import json
import time
import threading

class Client:
    def __init__(self, host, port):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))
        self.items = {}
        self.last_update_time = time.time()  # Initialize with current time
        threading.Thread(target=self.ask_for_updates_periodically).start()

    def ask_for_updates_periodically(self):
        try:
            while True:
                time.sleep(30)  # Ask for updates every 30 seconds
                request = {"type": "get_invalidated", "since": self.last_update_time}
                self.client_socket.send(json.dumps(request).encode())
                data = self.client_socket.recv(1024)
                response = json.loads(data)
                if response["type"] == "updated_items":
                    for item in response["items"]:
                        item_id = item["item_id"]
                        print(f"Item {item_id} has been updated, fetching latest content...")
                        self.ask_for_item(item_id)
                        if item["time_changed"] > self.last_update_time:
                            self.last_update_time = item["time_changed"]
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.close_connection()

    def close_connection(self):
        self.client_socket.close()
        print("Connection closed")

    def ask_for_item(self, item_id):
        request = {"type": "get_item", "item_id": item_id}
        self.client_socket.send(json.dumps(request).encode())
        data = self.client_socket.recv(1024)
        response = json.loads(data)
        if response["type"] == "item":
            self.items[item_id] = response["item"]
            print(f"Updated item {item_id}: {response['item']}")
        else:
            print("Error:", response["message"])

    def listen_for_updates(self):
        print("Listening for updates...")
        try:
            while True:
                data = self.client_socket.recv(1024)

                if not data:
                    break

                print("Got a periodic update from server...")
                response = json.loads(data)
                if response["type"] == "updated_ids":
                    for item_id in response["item_ids"]:
                        print(f"Item {item_id} has been updated, fetching latest content...")
                        self.ask_for_item(item_id)
        except Exception as e:
            print(f"An error occurred: {e}")
            raise e
        finally:
            self.close_connection()

    def start(self):
        threading.Thread(target=self.listen_for_updates).start()


if __name__ == "__main__":
    client = Client("localhost", 12345)
    client.start()
