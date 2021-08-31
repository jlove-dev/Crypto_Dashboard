from datetime import datetime

import pandas as pd
import requests
import datetime
from requests import HTTPError

REST_API = 'https://api.pro.coinbase.com'
PRODUCTS = REST_API + '/products'

'''
Inspiration for this class comes from 
https://levelup.gitconnected.com/load-and-visualise-bitcoin-market-data-from-coinbase-pro-via-python-and-rest-api-fa5198e62646
'''


def connect(url, params):
    try:
        response = requests.get(url, params)

        return response

    except HTTPError as http_err:
        print(f'HTTP ERROR: {http_err}')

    except Exception as err:
        print(f'Other error: {err}')


class CandleWorker:
    def __init__(self, name):
        self.name = name

    def get_data(self):
        start_date = (datetime.datetime.today() - datetime.timedelta(days=300)).isoformat()
        end_date = datetime.datetime.today().isoformat()
        params = {'start': start_date, 'end': end_date, 'granularity': '86400'}
        response = connect(PRODUCTS + '/' + self.name + '/candles', params)
        response_text = response.text

        df_history = pd.read_json(response_text)

        df_history.columns = ['time', 'low', 'high', 'open', 'close', 'volume']
        df_history['time'] = pd.to_datetime(df_history['time'], unit='s')
        print(df_history)
        return df_history
