import asyncio
import threading
from copy import deepcopy
from decimal import Decimal

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas
import plotly.express as px
from cryptofeed.callback import BookCallback, BookUpdateCallback
from cryptofeed.defines import L2_BOOK, BOOK_DELTA, BID, ASK
from cryptofeed.exchanges import Coinbase
from cryptofeed.feedhandler import FeedHandler
from dash.dependencies import Input, Output

bids = [({"side": "bid",
          "ETH-USD Price": Decimal('3000'),
          "size": "0.01"})]

asks = [({"side": "ask",
          "ETH-USD Price": Decimal('3100'),
          "size": "0.01"})]


class OrderBook(object):
    def __init__(self, name):
        self.book = None
        self.name = name
        self.bids = pandas.DataFrame(data=bids)
        self.asks = pandas.DataFrame(data=asks)
        self.L2 = {L2_BOOK: BookCallback(self.add_book),
                   BOOK_DELTA: BookUpdateCallback(self.update_book)}
        self.mid_market = 0.0

    def check_books(self, master):
        for side in (BID, ASK):
            if len(master[side]) != len(self.book[side]):
                return False

            for price in master[side]:
                if price not in self.book[side]:
                    return False

            for price in self.book[side]:
                if price not in master[side]:
                    return False

        return True

    async def add_book(self, feed, symbol, book, timestamp, receipt_timestamp):
        if not self.book:
            self.book = deepcopy(book)
            print('Book set!')
        else:
            assert (self.check_books(book))
            print('Books match!')

        self.flatten_book()

    async def update_book(self, feed, symbol, update, timestamp, receipt_timestamp):
        for side in (BID, ASK):
            for price, size in update[side]:
                if size == 0:
                    del self.book[side][price]
                else:
                    self.book[side][price] = size

        self.flatten_book()

    # Example taken from https://github.com/bmoscon/cryptofeed/blob/master/cryptofeed/backends/_util.py
    # Used to flatten the order book to construct dataframe for usage in Dash
    def flatten_book(self):
        new_list = []
        for side in (BID, ASK):
            for price, data in self.book[side].items():
                new_list.append({'side': side, 'ETH-USD Price': price, 'size': data})

        new_df = pandas.DataFrame(new_list)
        self.bids = new_df.loc[new_df['side'] == 'bid']
        self.asks = new_df.loc[new_df['side'] == 'ask']
        self.mid_market = (float(self.asks.iloc[0]['ETH-USD Price']) + float(self.bids.iloc[-1]['ETH-USD Price'])) / 2

    def get_asks(self):
        return self.asks

    def get_bids(self):
        return self.bids


btcOrderBook = OrderBook('btc')


def main(book):
    handler = FeedHandler()
    handler.add_feed(
        Coinbase(max_depth=100, symbols=['ETH-USD'], channels=[L2_BOOK], callbacks=book.L2))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    handler.run(install_signal_handlers=False)


def run_server():
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    app = dash.Dash(__name__, external_stylesheets=external_stylesheets, update_title=None)
    app.layout = html.Div(
        html.Div([
            html.H4('ETH-USD Live Depth Chart'),
            html.Div(id='live-update-text'),
            dcc.Graph(id='live-update-graph'),
            dcc.Interval(
                id='interval-component',
                interval=1 * 500,  # in milliseconds
                n_intervals=0
            )
        ])
    )

    @app.callback(Output('live-update-graph', 'figure'),
                  Input('interval-component', 'n_intervals'))
    def update_graph(n):
        fig = px.ecdf(btcOrderBook.get_asks(), x='ETH-USD Price', y="size", ecdfnorm=None, color="side",
                      labels={
                          "size": "ETH",
                          "side": "Side",
                          "value": "ETH-USD Price"
                      },
                      title="ETH-USD Depth Chart using cryptofeed and Dash")
        fig.data[0].line.color = 'rgb(255, 160, 122)'  # red
        fig.data[0].line.width = 5
        fig2 = px.ecdf(btcOrderBook.get_bids(), x='ETH-USD Price', y="size", ecdfmode='reversed', ecdfnorm=None,
                       color="side")
        fig2.data[0].line.color = 'rgb(34, 139, 34)'  # green
        fig2.data[0].line.width = 5
        fig.add_trace(fig2.data[0])
        fig.add_vline(x=btcOrderBook.mid_market,
                      annotation_text='Mid-Market Price: ' + "{:.2f}".format(btcOrderBook.mid_market),
                      annotation_position='top')
        return fig

    app.run_server()


if __name__ == "__main__":
    t1 = threading.Thread(target=main, args=[btcOrderBook])
    t1.start()
    t2 = threading.Thread(target=run_server)
    t2.start()
