import threading

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas
import plotly.express as px
from dash.dependencies import Input, Output
from cryptofeed_worker import OrderBook, start_feed

# Object which acts as the carrier through the app and is passed between child threads

btcBookObject = OrderBook('btc', 'BTC-USD')
ethBookObject = OrderBook('eth', 'ETH-USD')
adaBookObject = OrderBook('ada', 'ADA-USD')


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

        #ETH
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

        #ADA
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

        # Default ETH
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
