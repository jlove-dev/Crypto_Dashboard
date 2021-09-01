import threading
import time

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas
import plotly.express as px
from dash.dependencies import Input, Output
from cryptofeed_worker import OrderBook, start_feed, TimeKeeper
from CB_candle_worker import CandleWorker
import logging
import plotly.graph_objects as go

# Stop DASH from printing every POST result which is often due to interval callbacks
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Object which acts as the carrier through the app and is passed between child threads

btcBookObject = OrderBook('btc',
                          'BTC-USD',
                          'BTC',
                          "BTC-USD Depth Chart using cryptofeed and Dash",
                          'BTC-USD Live Depth Chart')

ethBookObject = OrderBook('eth',
                          'ETH-USD',
                          'ETH',
                          "ETH-USD Depth Chart using cryptofeed and Dash",
                          'ETH-USD Live Depth Chart')

adaBookObject = OrderBook('ada',
                          'ADA-USD',
                          'ADA',
                          "ADA-USD Depth Chart using cryptofeed and Dash",
                          'ADA-USD Live Depth Chart')

timeKeeperObject = TimeKeeper()


# Function which holds the Dash web server and starts the web server
def run_server():
    base_trade = [({'Currency Pair': 'BTC-USD', 'Side': 'bid', 'Amount': '100', 'Price': '3000'})]

    base_df = pandas.DataFrame(base_trade)

    app = dash.Dash(__name__, update_title=None)
    app.layout = html.Div([
        html.Div(
            className='split left',
            children=[
                html.Div([html.H3('ETH-USD Live Depth Chart',
                                  id='header')]),
                html.Div(
                    id='dropdowns',
                    children=
                    [
                        dcc.Dropdown(
                            id='token-selector',
                            options=[
                                {'label': 'BTC', 'value': 'BTC-USD'},
                                {'label': 'ETH', 'value': 'ETH-USD'},
                                {'label': 'ADA', 'value': 'ADA-USD'}
                            ]
                        ),
                        dcc.Dropdown(
                            id='graph-selector',
                            options=[
                                {'label': 'Depth chart', 'value': 'depth'},
                                {'label': 'Wall chart', 'value': 'wall'},
                                {'label': 'Daily Candlestick', 'value': 'candle'}
                            ]
                        )
                    ]

                ),
                html.Div([
                    dcc.Graph(id='live-update-graph',
                              figure=px.ecdf(ethBookObject.get_asks(), x='ETH-USD Price', y="size", ecdfnorm=None,
                                             color="side",
                                             labels={
                                                 "size": "ETH",
                                                 "side": "Side",
                                                 "value": "ETH-USD Price"
                                             },
                                             title="ETH-USD Depth Chart using cryptofeed and Dash"),
                              ),
                    html.Div(id='gran-slider',
                             children=[dcc.Slider(id='get-slider-value',
                                                  min=0,
                                                  max=5,
                                                  step=None,
                                                  marks={
                                                      0: '1 Minute',
                                                      1: '5 Minute',
                                                      2: '15 Minute',
                                                      3: '1 Hour',
                                                      4: '6 Hour',
                                                      5: '24 Hour'
                                                  },
                                                  vertical=True,
                                                  value=0
                                                  )], style={'display': 'none'})
                ]),

                html.Div([
                    dash_table.DataTable(
                        id='trade_table',
                        columns=[{"name": i, "id": i} for i in base_df],
                        data=base_df.to_dict('records'),
                        style_cell={'textAlign': 'center'},
                        style_table={'width': '50vw'}
                    )
                ]),

                dcc.Interval(
                    id='interval-component',
                    interval=1 * 500,  # Updates every half a second
                    n_intervals=0
                ),
                dcc.Interval(
                    id='stats-interval',
                    interval=1 * 1000,
                    n_intervals=0
                )
            ]),
        html.Div(
            className='split right',
            children=[
                html.Div(
                    className='stats',
                    children=[
                        html.H3('Session Stats')
                    ]),
                html.Div(
                    className='stats_area',
                    children=[
                        html.Output(
                            id='statsBox',
                            children=['Time elapsed']
                        ),
                        html.Output(
                            id='buysBox',
                            children=['Number of buys:']
                        ),
                        html.Output(
                            id='sellsBox',
                            children=['Number of sells:']
                        ),
                        html.Output(
                            id='buysValue',
                            children=['Value of buys:']
                        ),
                        html.Output(
                            id='sellsValue',
                            children=['Value of sells:']
                        ),
                        html.Output(
                            id='slider_value',
                            children=['value']
                        )
                    ])
            ])
    ])

    @app.callback(Output('gran-slider', 'style'),
                  Input('graph-selector', 'value'))
    def update_slider(value):
        if value == 'candle':
            return {'display': 'inline-block'}
        else:
            return {'display': 'none'}

    @app.callback([Output('statsBox', "children"),
                   Output('buysBox', "children"),
                   Output('sellsBox', "children"),
                   Output('buysValue', "children"),
                   Output('sellsValue', "children")],
                  [Input('stats-interval', 'n_intervals'),
                   Input('token-selector', 'value')])
    def update_stats(n, value):
        if value == 'BTC-USD':
            return timeKeeperObject.get_time_elapse(), \
                   btcBookObject.get_num_buys(), \
                   btcBookObject.get_num_sells(), \
                   btcBookObject.get_value_buys(), \
                   btcBookObject.get_value_sells()

        elif value == 'ETH-USD':
            return timeKeeperObject.get_time_elapse(), \
                   ethBookObject.get_num_buys(), \
                   ethBookObject.get_num_sells(), \
                   ethBookObject.get_value_buys(), \
                   ethBookObject.get_value_sells()
        elif value == 'ADA-USD':
            return timeKeeperObject.get_time_elapse(), \
                   adaBookObject.get_num_buys(), \
                   adaBookObject.get_num_sells(), \
                   adaBookObject.get_value_buys(), \
                   adaBookObject.get_value_sells()
        else:
            return timeKeeperObject.get_time_elapse(), \
                   ethBookObject.get_num_buys(), \
                   ethBookObject.get_num_sells(), \
                   ethBookObject.get_value_buys(), \
                   ethBookObject.get_value_sells()

    # Callback to update the graph with any updates to the L2 Book or candles
    @app.callback([Output('live-update-graph', 'figure'),
                   Output('header', 'children'),
                   Output('trade_table', "data")],
                  [Input('interval-component', 'n_intervals'),
                   Input('token-selector', 'value'),
                   Input('graph-selector', 'value'),
                   Input('get-slider-value', 'value')])
    def update_graph(n, value, g_value, s_value):
        # Layout the graph
        # BTC
        if value == 'BTC-USD':
            return build_graph(btcBookObject, g_value, s_value)
        elif value == 'ETH-USD':
            return build_graph(ethBookObject, g_value, s_value)
        elif value == 'ADA-USD':
            return build_graph(adaBookObject, g_value, s_value)
        else:
            return build_graph(ethBookObject, g_value, s_value)

    # Run DASH server
    app.run_server()


def build_graph(order_book, g_value, s_value):
    if g_value == 'wall':

        frames = [order_book.get_asks(), order_book.get_bids()]
        result = pandas.concat(frames)
        fig = px.line(result, x=order_book.get_symbol_string(), y='size', color='side',
                      color_discrete_map={
                          'bid': 'rgb(34, 139, 34)',
                          'ask': 'rgb(255, 160, 122)'
                      })
        # Display the mid-market price
        fig.add_vline(x=order_book.mid_market,
                      annotation_text='Mid-Market Price: ' + "{:.2f}".format(order_book.mid_market),
                      annotation_position='top')
        new_df = pandas.DataFrame(order_book.trade_list)
        return fig, order_book.get_subtitle(), new_df.to_dict('records')

    elif g_value == 'candle':

        allowed_nums = {
            0: 60,
            1: 300,
            2: 900,
            3: 3600,
            4: 21600,
            5: 86400
        }

        gran = 0

        if int(s_value) in allowed_nums.keys():
            gran = allowed_nums.get(int(s_value))

        candle = order_book.get_candle_worker()

        df = candle.get_data(gran)

        fig = go.Figure(data=[go.Candlestick(x=df['date'],
                                             open=df['open'],
                                             high=df['high'],
                                             low=df['low'],
                                             close=df['close'])])
        new_df = pandas.DataFrame(order_book.trade_list)

        return fig, order_book.get_subtitle(), new_df.to_dict('records')

    else:
        fig = px.ecdf(order_book.get_asks(), x=order_book.get_symbol_string(), y="size", ecdfnorm=None, color="side",
                      labels={
                          "size": order_book.get_size(),
                          "side": "Side",
                          "value": order_book.get_symbol_string()
                      },
                      title=order_book.get_title(),
                      color_discrete_map={
                          'ask': 'rgb(255, 160, 122)'
                      })
        # fig.data[0].line.color = 'rgb(255, 160, 122)'  # red
        fig.data[0].line.width = 5

        # Opposing side of the graph
        fig2 = px.ecdf(order_book.get_bids(), x=order_book.get_symbol_string(), y="size", ecdfmode='reversed',
                       ecdfnorm=None,
                       color="side",
                       color_discrete_map={
                           'bid': 'rgb(34, 139, 34)'
                       }
                       )
        # fig2.data[0].line.color = 'rgb(34, 139, 34)'  # green
        fig2.data[0].line.width = 5

        # Merge the figures together
        fig.add_trace(fig2.data[0])

        # Display the mid-market price
        fig.add_vline(x=order_book.mid_market,
                      annotation_text='Mid-Market Price: ' + "{:.2f}".format(order_book.mid_market),
                      annotation_position='top')

        new_df = pandas.DataFrame(order_book.trade_list)

        return fig, order_book.get_subtitle(), new_df.to_dict('records')


if __name__ == "__main__":
    # Web server thread
    t2 = threading.Thread(target=run_server)
    t2.start()
    time.sleep(1)

    # Start threading for both the cryptofeed worker and web server
    # Cryptofeed thread takes the global carrier object as a parameter which is passed in as a callback
    # This object is then passed back and forth between cryptofeed and the webserver

    t1 = threading.Thread(target=start_feed, args=[btcBookObject, ethBookObject, adaBookObject])
    t1.start()
