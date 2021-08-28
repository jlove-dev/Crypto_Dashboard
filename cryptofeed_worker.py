import asyncio
from copy import deepcopy
from decimal import Decimal

import pandas
from cryptofeed import FeedHandler
from cryptofeed.callback import BookCallback, TradeCallback, BookUpdateCallback
from cryptofeed.defines import L2_BOOK, BOOK_DELTA, TRADES, BID, ASK


# Default lists (with a dictionary inside) to avoid errors on run
from cryptofeed.exchanges import Coinbase

bids = [({"side": "bid",
          "ETH-USD Price": Decimal('3000'),
          "size": "0.01"})]

asks = [({"side": "ask",
          "ETH-USD Price": Decimal('3100'),
          "size": "0.01"})]

handler = FeedHandler()


# Inspiration for this class comes from the cryptofeed example at
# https://github.com/bmoscon/cryptofeed/blob/master/examples/demo_book_delta.py
# Credit to Bryant Moscon (http://www.bryantmoscon.com/)

class OrderBook(object):
    def __init__(self, name, symbol, size, title, sub_title):
        self.book = None
        self.name = name
        self.bids = pandas.DataFrame(data=bids)
        self.asks = pandas.DataFrame(data=asks)

        # This holds the callbacks for when cryptofeed returns data
        self.L2 = {L2_BOOK: BookCallback(self.add_book),
                   BOOK_DELTA: BookUpdateCallback(self.update_book),
                   TRADES: TradeCallback(self.add_trade)}

        self.mid_market = 0.0
        self.symbol = symbol + ' Price'
        self.size = size
        self.title = title
        self.sub_title = sub_title
        self.depth = 0
        self.trade_list = []

    # Function to check if the current book matches the most recent message
    def check_books(self, master):
        for side in (BID, ASK):
            if len(master[side]) != len(self.book[side]):
                return False  # Does not match

            for price in master[side]:
                if price not in self.book[side]:
                    return False  # Does not match

            for price in self.book[side]:
                if price not in master[side]:
                    return False  # Does not match

        return True  # Matches

    # Function which adds the initial book to the object
    # Only the book parameter is used however according to cryptofeed documentation
    # Best practice is to include the rest of the parameters
    async def add_book(self, feed, symbol, book, timestamp, receipt_timestamp):
        if not self.book:  # First entry
            self.book = deepcopy(book)
            print('Book set!')
        else:  # Checks if the message contains new data
            assert (self.check_books(book))
            print('Books match!')

        # Flatten book into list
        self.flatten_book()

    # Updates the L2 book
    async def update_book(self, feed, symbol, update, timestamp, receipt_timestamp):
        for side in (BID, ASK):
            for price, size in update[side]:
                if size == 0:  # Message indicates that the price level can be removed
                    del self.book[side][price]
                else:  # Adjust price level
                    self.book[side][price] = size

        # Flatten book into list
        self.flatten_book()

    # Example taken from https://github.com/bmoscon/cryptofeed/blob/master/cryptofeed/backends/_util.py
    # Used to flatten the order book to construct dataframe for usage in Dash
    def flatten_book(self):
        new_list = []
        for side in (BID, ASK):
            for price, data in self.book[side].items():
                # This format allows for easy transference into a Pandas dataframe
                # This was tested with 5000 entries and no noticeable performance issues were present
                new_list.append({'side': side, self.symbol: price, 'size': data})

        new_df = pandas.DataFrame(new_list)
        self.bids = new_df.loc[new_df['side'] == 'bid']
        self.asks = new_df.loc[new_df['side'] == 'ask']
        self.mid_market = (float(self.asks.iloc[0][self.symbol]) + float(self.bids.iloc[-1][self.symbol])) / 2

    def add_trade(self, feed, symbol, order_id, timestamp, side, amount, price, receipt_timestamp):
        if len(self.trade_list) >= 10:
            self.trade_list.pop(0)
            self.trade_list.append(({'Currency Pair': symbol, 'Side': side, 'Amount': amount, 'Price': price}))
        else:
            self.trade_list.append(({'Currency Pair': symbol, 'Side': side, 'Amount': amount, 'Price': price}))

    def get_trades(self):
        return pandas.DataFrame(self.trade_list)

    # Return asks DF
    def get_asks(self):
        return self.asks

    # Return bids DF
    def get_bids(self):
        return self.bids

    def get_symbol(self):
        return self.symbol

    def get_size(self):
        return self.size

    def get_title(self):
        return self.title

    def get_subtitle(self):
        return self.sub_title


def get_btc_feed():
    return ['BTC-USD']


def get_eth_feed():
    return ['ETH-USD']


def get_ada_feed():
    return ['ADA-USD']


def start_feed(btc_book, eth_book, ada_book):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    handler.add_feed(Coinbase(max_depth=100, symbols=get_btc_feed(), channels=[L2_BOOK, TRADES], callbacks=btc_book.L2))
    handler.add_feed(Coinbase(max_depth=100, symbols=get_eth_feed(), channels=[L2_BOOK, TRADES], callbacks=eth_book.L2))
    handler.add_feed(Coinbase(max_depth=100, symbols=get_ada_feed(), channels=[L2_BOOK, TRADES], callbacks=ada_book.L2))
    handler.run(install_signal_handlers=False)