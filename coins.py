from cryptofeed_worker import OrderBook


class MasterObject:

    def __init__(self):
        self.btcBookObject = OrderBook('btc',
                                       'BTC-USD',
                                       'BTC',
                                       'BTC-USD Live Chart')

        self.ethBookObject = OrderBook('eth',
                                       'ETH-USD',
                                       'ETH',
                                       'ETH-USD Live Chart')

        self.adaBookObject = OrderBook('ada',
                                       'ADA-USD',
                                       'ADA',
                                       'ADA-USD Live Chart')

        self.maticBookObject = OrderBook('matic',
                                         'MATIC-USD',
                                         'MATIC',
                                         'MATIC-USD Live Chart')

        self.batBookObject = OrderBook('bat',
                                       'BAT-USD',
                                       'BAT',
                                       'BAT-USD Live Chart')

        self.dotBookObject = OrderBook('dot',
                                       'DOT-USD',
                                       'DOT',
                                       'DOT-USD Live Chart')

        self.algoBookObject = OrderBook('algo',
                                        'ALGO-USD',
                                        'ALGO',
                                        'ALGO-USD Live Chart')

        self.uniBookObject = OrderBook('uni',
                                       'UNI-USD',
                                       'UNI',
                                       'UNI-USD Live Chart')

        self.dict_of_books = {
            "btc": self.btcBookObject,
            "eth": self.ethBookObject,
            "ada": self.adaBookObject,
            "matic": self.maticBookObject,
            "bat": self.batBookObject,
            "dot": self.dotBookObject,
            "algo": self.algoBookObject,
            "uni": self.uniBookObject
        }

    def get_books(self, book):
        if book in self.dict_of_books:
            return self.dict_of_books.get(book)

