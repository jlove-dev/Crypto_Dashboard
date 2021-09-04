from datetime import datetime

import pandas as pd
import requests
import datetime
from requests import HTTPError

API = 'https://api.pro.coinbase.com/products'

'''
Inspiration for this class comes from 
https://levelup.gitconnected.com/load-and-visualise-bitcoin-market-data-from-coinbase-pro-via-python-and-rest-api-fa5198e62646
'''
default_time = [({
    "low": "0",
    "high": "0",
    "open": "0",
    "close": "0",
    "volume": "0",
    "date": "2021-08-31 17:18:00"
})]


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
        self.time_since_last = 0
        self.df = pd.DataFrame(data=default_time)
        self.current_gran = 0

    def get_data(self, gran):

        if self.time_since_last != 0:
            if gran != self.current_gran:
                return self.build_df(gran)
            if datetime.datetime.today().timestamp() - self.time_since_last < gran:
                return self.df
            else:
                return self.build_df(gran)

        else:
            self.current_gran = 0
            return self.build_df(gran)

    def build_df(self, gran):

        start_date = (datetime.datetime.today() - datetime.timedelta(minutes=gran * 5)).isoformat()
        end_date = datetime.datetime.today().isoformat()

        params = {'start': start_date, 'end': end_date, 'granularity': gran}
        response = connect(API + '/' + self.name + '/candles', params)
        response_text = response.text

        df = pd.read_json(response_text)

        df.columns = ['time', 'low', 'high', 'open', 'close', 'volume']
        df['date'] = pd.to_datetime(df['time'], unit='s')
        del df['time']

        self.time_since_last = datetime.datetime.today().timestamp()
        self.df = df

        return df
