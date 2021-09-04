import requests

url = 'https://api.pro.coinbase.com/products'

result = requests.get(url)

iterate = result.json()

for i in iterate:
    if i['quote_currency'] == 'USD':
        print(
            'self.' + i['base_currency'].lower() + 'BookObject = OrderBook(\'' + i['base_currency'].lower() + '\',' + '\n',
            '\'' + i['base_currency'] + '-USD\',' + '\n',
            '\'' + i['base_currency'] + '\',' + '\n',
            '\'' + i['base_currency'] + '-USD Live Chart\')' + ','
        )

for i in iterate:
    if i['quote_currency'] == 'USD':
        print(
            '\'' + i['base_currency'].lower() + '\'' ': self.' + i['base_currency'].lower() + 'BookObject,'
        )