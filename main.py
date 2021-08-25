import asyncio
import threading
from copy import deepcopy
from decimal import Decimal

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas
import plotly.express as px
from cryptofeed.callback import BookCallback, BookUpdateCallback, TradeCallback
from cryptofeed.defines import L2_BOOK, BOOK_DELTA, BID, ASK, TRADES
from cryptofeed.exchanges import Coinbase
from cryptofeed.feedhandler import FeedHandler
from dash.dependencies import Input, Output

# Default lists (with a dictionary inside) to avoid errors on run

bids = [({"side": "bid",
          "ETH-USD Price": Decimal('3000'),
          "size": "0.01"})]

asks = [({"side": "ask",
          "ETH-USD Price": Decimal('3100'),
          "size": "0.01"})]


# Inspiration for this class comes from the cryptofeed example at
# https://github.com/bmoscon/cryptofeed/blob/master/examples/demo_book_delta.py
# Credit to Bryant Moscon (http://www.bryantmoscon.com/)

class OrderBook(object):
    def __init__(self, name, symbol):
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


# Object which acts as the carrier through the app and is passed between child threads

btcBookObject = OrderBook('btc', 'BTC-USD')
ethBookObject = OrderBook('eth', 'ETH-USD')
adaBookObject = OrderBook('ada', 'ADA-USD')
handler = FeedHandler()


def get_btc_feed():
    return ['BTC-USD']


def get_eth_feed():
    return ['ETH-USD']


def get_ada_feed():
    return ['ADA-USD']


def start_feed(btcBook, ethBook, adaBook):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    handler.add_feed(Coinbase(max_depth=100, symbols=get_btc_feed(), channels=[L2_BOOK, TRADES], callbacks=btcBook.L2))
    handler.add_feed(Coinbase(max_depth=100, symbols=get_eth_feed(), channels=[L2_BOOK, TRADES], callbacks=ethBook.L2))
    handler.add_feed(Coinbase(max_depth=100, symbols=get_ada_feed(), channels=[L2_BOOK, TRADES], callbacks=adaBook.L2))
    handler.run(install_signal_handlers=False)


# Function which holds the Dash web server and starts the web server
def run_server():
    base_trade = [({'Currency Pair': 'BTC-USD', 'Side': 'bid', 'Amount': '100', 'Price': '3000'})]

    base_df = pandas.DataFrame(base_trade)

    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    app = dash.Dash(__name__, external_stylesheets=external_stylesheets, update_title=None)
    app.layout = html.Div(
        html.Div([
            html.H4('ETH-USD Live Depth Chart', id='header'),
            html.Div(id='live-update-text'),
            dcc.Dropdown(
                id='token-selector',
                options=[
                    {'label': 'BTC', 'value': 'BTC-USD'},
                    {'label': 'ETH', 'value': 'ETH-USD'},
                    {'label': 'ADA', 'value': 'ADA-USD'}
                ]
            ),
            dcc.Graph(id='live-update-graph',
                      figure=px.ecdf(ethBookObject.get_asks(), x='ETH-USD Price', y="size", ecdfnorm=None, color="side",
                                     labels={
                                         "size": "ETH",
                                         "side": "Side",
                                         "value": "ETH-USD Price"
                                     },
                                     title="ETH-USD Depth Chart using cryptofeed and Dash")),
            dash_table.DataTable(
                id='trade_table',
                columns=[{"name": i, "id": i} for i in base_df],
                data=base_df.to_dict('records')
            ),
            dcc.Interval(
                id='interval-component',
                interval=1 * 500,  # Updates every half a second
                n_intervals=0
            )
        ])
    )

    # Callback to update the graph with any updates to the L2 Book
    @app.callback([Output('live-update-graph', 'figure'),
                   Output('header', 'children'),
                   Output('trade_table', "data")],
                  [Input('interval-component', 'n_intervals'),
                   Input('token-selector', 'value')])
    def update_graph(n, value):
        # Layout the graph
        # BTC
        if value == 'BTC-USD':
            fig = px.ecdf(btcBookObject.get_asks(), x='BTC-USD Price', y="size", ecdfnorm=None, color="side",
                          labels={
                              "size": "BTC",
                              "side": "Side",
                              "value": "BTC-USD Price"
                          },
                          title="BTC-USD Depth Chart using cryptofeed and Dash")
            fig.data[0].line.color = 'rgb(255, 160, 122)'  # red
            fig.data[0].line.width = 5

            # Opposing side of the graph
            fig2 = px.ecdf(btcBookObject.get_bids(), x='BTC-USD Price', y="size", ecdfmode='reversed', ecdfnorm=None,
                           color="side")
            fig2.data[0].line.color = 'rgb(34, 139, 34)'  # green
            fig2.data[0].line.width = 5

            # Merge the figures together
            fig.add_trace(fig2.data[0])

            # Display the mid-market price
            fig.add_vline(x=btcBookObject.mid_market,
                          annotation_text='Mid-Market Price: ' + "{:.2f}".format(btcBookObject.mid_market),
                          annotation_position='top')

            new_df = pandas.DataFrame(btcBookObject.trade_list)

            return fig, 'BTC-USD Live Depth Chart', new_df.to_dict('records')

        elif value == 'ETH-USD':
            fig = px.ecdf(ethBookObject.get_asks(), x='ETH-USD Price', y="size", ecdfnorm=None, color="side",
                          labels={
                              "size": "ETH",
                              "side": "Side",
                              "value": "ETH-USD Price"
                          },
                          title="ETH-USD Depth Chart using cryptofeed and Dash")
            fig.data[0].line.color = 'rgb(255, 160, 122)'  # red
            fig.data[0].line.width = 5

            # Opposing side of the graph
            fig2 = px.ecdf(ethBookObject.get_bids(), x='ETH-USD Price', y="size", ecdfmode='reversed', ecdfnorm=None,
                           color="side")
            fig2.data[0].line.color = 'rgb(34, 139, 34)'  # green
            fig2.data[0].line.width = 5

            # Merge the figures together
            fig.add_trace(fig2.data[0])

            # Display the mid-market price
            fig.add_vline(x=ethBookObject.mid_market,
                          annotation_text='Mid-Market Price: ' + "{:.2f}".format(ethBookObject.mid_market),
                          annotation_position='top')

            new_df = pandas.DataFrame(ethBookObject.trade_list)

            return fig, 'ETH-USD Live Depth Chart', new_df.to_dict('records')

        elif value == 'ADA-USD':
            fig = px.ecdf(adaBookObject.get_asks(), x='ADA-USD Price', y="size", ecdfnorm=None, color="side",
                          labels={
                              "size": "ADA",
                              "side": "Side",
                              "value": "ADA-USD Price"
                          },
                          title="ADA-USD Depth Chart using cryptofeed and Dash")
            fig.data[0].line.color = 'rgb(255, 160, 122)'  # red
            fig.data[0].line.width = 5

            # Opposing side of the graph
            fig2 = px.ecdf(adaBookObject.get_bids(), x='ADA-USD Price', y="size", ecdfmode='reversed', ecdfnorm=None,
                           color="side")
            fig2.data[0].line.color = 'rgb(34, 139, 34)'  # green
            fig2.data[0].line.width = 5

            # Merge the figures together
            fig.add_trace(fig2.data[0])

            # Display the mid-market price
            fig.add_vline(x=adaBookObject.mid_market,
                          annotation_text='Mid-Market Price: ' + "{:.2f}".format(adaBookObject.mid_market),
                          annotation_position='top')

            new_df = pandas.DataFrame(adaBookObject.trade_list)

            return fig, 'ADA-USD Live Depth Chart', new_df.to_dict('records')

        else:
            fig = px.ecdf(ethBookObject.get_asks(), x='ETH-USD Price', y="size", ecdfnorm=None, color="side",
                          labels={
                              "size": "ETH",
                              "side": "Side",
                              "value": "ETH-USD Price"
                          },
                          title="ETH-USD Depth Chart using cryptofeed and Dash")
            fig.data[0].line.color = 'rgb(255, 160, 122)'  # red
            fig.data[0].line.width = 5

            # Opposing side of the graph
            fig2 = px.ecdf(ethBookObject.get_bids(), x='ETH-USD Price', y="size", ecdfmode='reversed', ecdfnorm=None,
                           color="side")
            fig2.data[0].line.color = 'rgb(34, 139, 34)'  # green
            fig2.data[0].line.width = 5

            # Merge the figures together
            fig.add_trace(fig2.data[0])

            # Display the mid-market price
            fig.add_vline(x=ethBookObject.mid_market,
                          annotation_text='Mid-Market Price: ' + "{:.2f}".format(ethBookObject.mid_market),
                          annotation_position='top')

            new_df = pandas.DataFrame(ethBookObject.trade_list)

            return fig, 'Default ETH-USD Live Depth Chart', new_df.to_dict('records')

    # Run DASH server
    app.run_server()


if __name__ == "__main__":
    # Start threading for both the cryptofeed worker and web server
    # Cryptofeed thread takes the global carrier object as a parameter which is passed in as a callback
    # This object is then passed back and forth between cryptofeed and the webserver
    t1 = threading.Thread(target=start_feed, args=[btcBookObject, ethBookObject, adaBookObject])
    t1.start()

    # Web server thread
    t2 = threading.Thread(target=run_server)
    t2.start()
