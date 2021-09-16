import threading
import websocket
import json
import pandas as pd
import time
import itertools
import collections


# Class which holds each coin/token's data
# This class tracks the entire L2 Order Book for both the bids/asks side
# It takes advantage of the average O(1) for search/addition/deletion
# This results in a very fast class which operates well under hardware constraints

class Coin:

    # Class takes a name, such as ETH-USD, which is used to retrieve that coin's specific data
    def __init__(self, name):
        self.name = name
        self.bids = {}
        self.asks = {}

    # This class must always be tied to the on_message of the CbSocket class
    # It requires a websocket message and then it's decided what type of message it is/what to do with it
    def set_dicts(self, result):
        # This message is only received one per coin
        if result['type'] == 'snapshot':

            # Add each row in the snapshot of the 'bids' side to the object
            for price, size in result['bids']:
                self.bids[float(price)] = {'side': 'bids', 'size': float(size)}

            # Add each row in the snapshot of the 'asks side to the object
            for price, size in result['asks']:
                self.asks[float(price)] = {'side': 'asks', 'size': float(size)}

        # These messages are streamed following the snapshot
        elif result['type'] == 'l2update':

            # Adjust the self.bids dictionary based on the message
            if result['changes'][0][0] == 'buy':

                # Check if the price level is already in the dictionary
                if float(result['changes'][0][1]) in self.bids:

                    # This checks if the size in the message is equal to zero
                    # According to CB API docs, this indicates it can be removed
                    # https://docs.pro.coinbase.com/#the-level2-channel
                    if float(result['changes'][0][2]) == 0.0:

                        # Delete the entry which corresponds to the size above
                        del self.bids[float(result['changes'][0][1])]

                    # Don't delete the entry, instead update its size
                    else:
                        self.bids[float(result['changes'][0][1])]['size'] = float(result['changes'][0][2])

                # No entry found in the dictionary, add it to the bottom
                else:
                    self.bids[float(result['changes'][0][1])] = {'side': 'bids', 'size': float(result['changes'][0][2])}

            # All of the comments for the sell side are the same as the buy side above
            elif result['changes'][0][0] == 'sell':
                if float(result['changes'][0][1]) in self.asks:
                    if float(result['changes'][0][2]) == 0.0:
                        del self.asks[float(result['changes'][0][1])]
                    else:
                        self.asks[float(result['changes'][0][1])]['size'] = float(result['changes'][0][2])
                else:
                    self.asks[float(result['changes'][0][1])] = {'side': 'asks', 'size': float(result['changes'][0][2])}

    # This function returns a pandas DataFrame of shape 500 with price, side and size as the columns
    def get_df(self):

        # Request both the self.bids and self.asks dictionary be sorted
        bids_df = self.get_bids()
        asks_df = self.get_asks()

        # Return both dataframes
        return bids_df, asks_df

    # Return a Pandas DataFrame of shape 500 with only the bids side of the object
    def get_bids(self):

        bids = self.bid_sort()

        # Create the new bids dataframe, limited to 500 entries, reset the index and insert the index as a new column
        bids_df = pd.DataFrame.from_dict(data=dict(itertools.islice(bids.items(), 500)), orient='index')
        bids_df.reset_index(level=0, inplace=True)
        bids_df = bids_df.rename(columns={'index': 'price'})

        return bids_df

    # Return a Pandas DataFrame of shape 500 with only the asks side of the object
    def get_asks(self):

        asks = self.ask_sort()

        # Create the new asks dataframe, limited to 500 entries, reset the index and insert the index as a new column
        asks_df = pd.DataFrame.from_dict(data=dict(itertools.islice(asks.items(), 500)), orient='index')
        asks_df.reset_index(level=0, inplace=True)
        asks_df = asks_df.rename(columns={'index': 'price'})

        return asks_df

    # Sort the self.asks dictionary into an OrderedDict
    def bid_sort(self):
        ordered_dict = collections.OrderedDict(sorted(self.bids.items(), reverse=True))
        return ordered_dict

    # Sort the self.bids dictionary into an OrderedDict
    def ask_sort(self):
        ordered_dict = collections.OrderedDict(sorted(self.asks.items()))
        return ordered_dict

    # Return the name of the object such as ETH-USD
    def get_name(self):
        return self.name


# Websocket class which aggregates data from the level2 websocket on Coinbase API

class CbSocket:

    def __init__(self, limit):
        # this socket utilizes lambda functions to assign the on_message and on_open to local object functions
        self.socket = websocket.WebSocketApp("wss://ws-feed.pro.coinbase.com",
                                             on_message=lambda ws, msg: self.on_message(ws, msg),
                                             on_open=lambda ws: self.on_open(ws))
        self.limit = limit
        self.bids = {}
        self.asks = {}

        # Dictionary which creates Coin objects for each message type which can be received
        self.coins = {
            'ETH-USD': Coin('ETH-USD'),
            'BTC-USD': Coin('BTC-USD'),
            'ADA-USD': Coin('ADA-USD'),
            'SOL-USD': Coin('SOL-USD'),
            'XTZ-USD': Coin('XTZ-USD'),
            'ALGO-USD': Coin('ALGO-USD'),
            'ATOM-USD': Coin('ATOM-USD'),
            'MATIC-USD': Coin('MATIC-USD'),
            'DOT-USD': Coin('DOT-USD'),
            'AAVE-USD': Coin('AAVE-USD')
        }

        '''
        dict format --
        {
            price:
                {'side': 'bids', 'size': 0.1111},
        }
        '''

    # Returns the selected coins bids/asks dataframes, thus the request must be bids, asks = book.get_df()
    # Accepts an _id of type String which picks the correct object from the above dictionary of Coin objects
    def get_df(self, _id: str):
        book = self.coins.get(_id)
        return book.get_df()

    # Request only the asks portion of the object
    def get_asks(self, _id: str):
        book = self.coins.get(_id)
        return book.get_asks()

    # Request only the bids portion of the object
    def get_bids(self, _id: str):
        book = self.coins.get(_id)
        return book.get_bids()

    # Receives the messages from the websocket
    def on_message(self, ws, message):
        result = json.loads(message)  # Load the JSON message sent

        # Select the proper coin based on message type and pass the message to that object
        if result['product_id'] in self.coins:
            book = self.coins.get(result['product_id'])
            book.set_dicts(result)
        else:
            print('key not found')

    # Initial handshake with CB websocket which requires a subscribe message
    # More information can be found here: https://docs.pro.coinbase.com/#subscribe
    def on_open(self, ws):
        ws.send(open('subscribe.json').read())

    # Run this websocket worker in a separate thread forever
    def run(self):
        t_run = threading.Thread(target=self.socket.run_forever)
        t_run.start()


# Main function
if __name__ == "__main__":
    new = CbSocket(10)
    new.run()  # Runs the websocket worker in separate thread
