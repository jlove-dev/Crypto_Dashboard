import json
import pprint

import pandas
import websocket


class CbSocket:

    def __init__(self):
        self.socket = websocket.WebSocketApp("wss://ws-feed.pro.coinbase.com",
                                             on_message=lambda ws, msg: self.on_message(ws, msg),
                                             on_open=lambda ws: self.on_open(ws))
        self.snapshot = 0
        self.update = 0
        self.book = pandas.DataFrame(data=None)

    def on_message(self, ws, message):
        msg = json.loads(message)
        if msg['type'] == 'snapshot':
            self.book = pandas.DataFrame.from_records(msg)

        print(self.book)

    def on_open(self, ws):
        ws.send(open('subscribe.json').read())

    def run_socket(self):
        self.socket.run_forever()
