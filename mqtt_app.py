from typing import Callable
import paho.mqtt.client as mqtt


class MqttApp:
    def __init__(self,
                 host: str,
                 port: int,
                 on_message: Callable,
                 topic: str,
                 user: str,
                 password: str,
                 keepalive: int = 60
    ):
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = on_message

        self.topic = topic

        client.username_pw_set(user, password)
        client.connect(host, port, keepalive)

        # client.loop_forever()
        client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        """
        The callback for when the client receives a CONNACK response from the server.
        :param client:
        :param userdata:
        :param flags:
        :param rc:
        :return:
        """
        print(f"Connected with result code {rc}")

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe(self.topic)