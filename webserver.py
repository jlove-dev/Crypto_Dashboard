import threading
import time

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
import pandas
import plotly.express as px
from dash.dependencies import Input, Output
from cryptofeed_worker import OrderBook, start_feed, TimeKeeper
from coins import MasterObject
from CB_candle_worker import CandleWorker
import logging
import plotly.graph_objects as go

# Stop DASH from printing every POST result which is often due to interval callbacks
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Object which acts as the carrier through the app and is passed between child threads

master = MasterObject()

timeKeeperObject = TimeKeeper()


# Function which holds the Dash web server and starts the web server
def run_server():
    base_trade = [({'Currency Pair': 'BTC-USD', 'Side': 'bid', 'Amount': '100', 'Price': '3000'})]

    base_df = pandas.DataFrame(base_trade)

    app = dash.Dash(__name__, update_title=None, external_stylesheets=[dbc.themes.SLATE])
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
                            placeholder='Token',
                            options=[
                                {'label': 'BTC', 'value': 'btc'},
                                {'label': 'ETH', 'value': 'eth'},
                                {'label': 'ADA', 'value': 'ada'},
                                {'label': 'MATIC', 'value': 'matic'},
                                {'label': 'BAT', 'value': 'bat'},
                                {'label': 'DOT', 'value': 'dot'},
                                {'label': 'ALGO', 'value': 'algo'},
                                {'label': 'UNI', 'value': 'uni'},
                                {'label': 'SOL', 'value': 'sol'},
                                {'label': 'CHZ', 'value': 'chz'},
                                {'label': 'MANA', 'value': 'mana'},
                                {'label': 'ETC', 'value': 'etc'},
                                {'label': 'XTZ', 'value': 'xtz'}
                            ]
                        ),
                        dcc.Dropdown(
                            id='graph-selector',
                            placeholder='Chart Type',
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
                              figure=px.ecdf(master.get_books("eth").get_asks(), x='ETH-USD Price', y="size",
                                             ecdfnorm=None,
                                             color="side",
                                             labels={
                                                 "size": "ETH",
                                                 "side": "Side",
                                                 "value": "ETH-USD Price"
                                             },
                                             title="ETH-USD Depth Chart using cryptofeed and Dash"),
                              style={'width': '90%'}
                              ),
                    html.Div(id='gran-slider',
                             children=[dcc.Slider(id='get-slider-value',
                                                  min=0,
                                                  max=5,
                                                  step=None,
                                                  marks={
                                                      0: '1 Min',
                                                      1: '5 Min',
                                                      2: '15 Min',
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
                        style_cell={'textAlign': 'center', 'background-color': '#525252', 'text-color': 'white', 'fontWeight': 'bold'},
                        style_table={'width': '95%'}
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
        if value is not None:
            return get_book_stats_data(master.get_books(value))
        else:
            return get_book_stats_data(master.get_books("eth"))

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
        if value is not None:
            return build_graph(master.get_books(value), g_value, s_value)
        else:
            return build_graph(master.get_books("eth"), g_value, s_value)

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

        fig.update_layout(
            plot_bgcolor='#262626',
            paper_bgcolor='#262626',
            font_color='white'
        )

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

        fig.update_layout(xaxis_rangeslider_visible=False)

        fig.update_layout(
            plot_bgcolor='#262626',
            paper_bgcolor='#262626',
            font_color='white',
            autosize=True
        )

        new_df = pandas.DataFrame(order_book.trade_list)

        return fig, order_book.get_subtitle(), new_df.to_dict('records')

    else:
        fig = px.ecdf(order_book.get_asks(), x=order_book.get_symbol_string(), y="size", ecdfnorm=None, color="side",
                      labels={
                          "size": order_book.get_size(),
                          "side": "Side",
                          "value": order_book.get_symbol_string()
                      },
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

        fig.update_layout(
            plot_bgcolor='#262626',
            paper_bgcolor='#262626',
            font_color='white'
        )

        new_df = pandas.DataFrame(order_book.trade_list)

        return fig, order_book.get_subtitle(), new_df.to_dict('records')


def get_book_stats_data(orderbook):
    return timeKeeperObject.get_time_elapse(), \
           orderbook.get_num_buys(), \
           orderbook.get_num_sells(), \
           orderbook.get_value_buys(), \
           orderbook.get_value_sells()


if __name__ == "__main__":
    # Web server thread
    t2 = threading.Thread(target=run_server)
    t2.start()
    time.sleep(1)

    # Start threading for both the cryptofeed worker and web server
    # Cryptofeed thread takes the global carrier object as a parameter which is passed in as a callback
    # This object is then passed back and forth between cryptofeed and the webserver

    t1 = threading.Thread(target=start_feed, args=[master.get_books("btc"),
                                                   master.get_books('eth'),
                                                   master.get_books('ada'),
                                                   master.get_books('matic'),
                                                   master.get_books('bat'),
                                                   master.get_books('dot'),
                                                   master.get_books('algo'),
                                                   master.get_books('uni'),
                                                   master.get_books('sol'),
                                                   master.get_books('chz'),
                                                   master.get_books('mana'),
                                                   master.get_books('etc'),
                                                   master.get_books('xtz')])
    t1.start()
    t2.join()
    t1.join()

    # run_server()
