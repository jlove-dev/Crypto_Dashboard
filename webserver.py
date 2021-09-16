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
import logging
import plotly.graph_objects as go
from flask import Flask
from cb_socket import CbSocket


# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

def create_app():
    master = CbSocket(500)
    t_socket = threading.Thread(target=master.socket.run_forever)
    t_socket.start()
    app = dash.Dash(__name__, update_title=None, external_stylesheets=[dbc.themes.SLATE])
    server = app.server
    app.layout = html.Div([
        html.Div(
            children=[
                html.Div(
                    children=[
                        html.H3('ETH-USD Live Depth Chart', id='header')
                    ]
                ),
                html.Br(),
                html.Div(
                    id='dropdowns',
                    children=
                    [
                        dcc.Dropdown(
                            id='token-selector',
                            placeholder='Token',
                            options=[
                                {'label': 'BTC', 'value': 'BTC-USD'},
                                {'label': 'ETH', 'value': 'ETH-USD'},
                                {'label': 'ADA', 'value': 'ADA-USD'},
                                {'label': 'MATIC', 'value': 'MATIC-USD'},
                                {'label': 'ALGO', 'value': 'ALGO-USD'},
                                {'label': 'SOL', 'value': 'SOL-USD'},
                                {'label': 'XTZ', 'value': 'XTZ-USD'},
                                {'label': 'ATOM', 'value': 'ATOM-USD'},
                                {'label': 'DOT', 'value': 'DOT-USD'},
                                {'label': 'AAVE', 'value': 'AAVE-USD'}
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

                html.Div(
                    children=[
                        dcc.Graph(id='live-update-graph',
                                  figure=px.ecdf(master.get_asks('ETH-USD'), x='price', y='size',
                                                 ecdfnorm=None,
                                                 color='side',
                                                 labels={
                                                     'size': 'ETH',
                                                     'side': 'Side',
                                                     'value': 'ETH-USD Price'
                                                 },
                                                 title="ETH-USD Depth Chart"),
                                  style={'width': '90%'}),

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
                                                      value=0)], style={'display': 'None'})
                    ]
                )
            ]
        ),

        dcc.Interval(
            id='interval-component',
            interval=1 * 1000,
            n_intervals=0
        )
    ])

    @app.callback(Output('gran-slider', 'style'),
                  Input('graph-selector', 'value'))
    def update_slider(value):
        if value == 'candle':
            return {'display': 'inline-block'}
        else:
            return {'display': 'none'}

    @app.callback(Output('live-update-graph', 'figure'),
                  [Input('interval-component', 'n_intervals'),
                   Input('token-selector', 'value'),
                   Input('graph-selector', 'value'),
                   Input('get-slider-value', 'value')])
    def update_graph(n, value, g_value, s_value):
        if value is not None:
            return build_graph(master.get_book(value), g_value, s_value)
        else:
            return build_graph(master.get_book('ETH-USD'), g_value, s_value)

    def build_graph(order_book, g_value, s_value):
        if g_value == 'wall':
            bids = order_book.get_bids()
            asks = order_book.get_asks()
            frames = [bids, asks]
            result = pandas.concat(frames)
            fig = px.line(result, x='price', y='size', color='side',
                          color_discrete_map={
                              'bid': 'rgb(34, 139, 34)',
                              'asks': 'rgb(255, 160, 122)'
                          })
            fig.update_layout(
                plot_bgcolor='#262626',
                paper_bgcolor='#262626',
                font_color='white'
            )

            fig.data[0].line.width = 3

            fig.add_layout_image(
                dict(
                    source=order_book.get_logo(),
                    xref='paper',
                    yref='paper',
                    x=0.475,
                    y=1,
                    sizex=1,
                    sizey=1,
                    layer='below',
                    sizing='contain',
                    opacity=0.075
                )
            )

            return fig

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

            fig.add_layout_image(
                dict(
                    source=order_book.get_logo(),
                    xref='paper',
                    yref='paper',
                    x=0.475,
                    y=1,
                    sizex=1,
                    sizey=1,
                    layer='below',
                    sizing='contain',
                    opacity=0.075
                )
            )

            return fig
        else:
            bids = order_book.get_bids()
            asks = order_book.get_asks()
            fig = px.ecdf(asks, x='price', y="size", color="side",
                          ecdfnorm=None,
                          labels={
                              "size": order_book.get_name(),
                              "side": "Side",
                              "value": order_book.get_name() + 'price'
                          },
                          color_discrete_map={
                              'asks': 'rgb(255, 160, 122)'
                          })

            fig.data[0].line.width = 5

            fig2 = px.ecdf(bids, x='price', y="size", ecdfmode='reversed',
                           ecdfnorm=None,
                           color='side',
                           color_discrete_map={
                               'bids': 'rgb(34, 139, 34)'
                           })

            fig2.data[0].line.width = 5

            fig.add_trace(fig2.data[0])

            fig.update_layout(
                plot_bgcolor='#262626',
                paper_bgcolor='#262626',
                font_color='white'
            )

            fig.add_layout_image(
                dict(
                    source=order_book.get_logo(),
                    xref='paper',
                    yref='paper',
                    x=0.475,
                    y=1,
                    sizex=1,
                    sizey=1,
                    layer='below',
                    sizing='contain',
                    opacity=0.075
                )
            )

            return fig

    return server


app = create_app()

