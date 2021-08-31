# Crypto_Dashboard

This project is a WIP as a way to display useful information about cryptocurrencies. It's currently being actively developed as a proof of concept, and a way to visualize more useful data about various cryptocurrencies.

It currently uses cryptofeed (https://github.com/bmoscon/cryptofeed) and Dash by Plotly (https://plotly.com/dash/) to display live Coinbase data.

# Installation

To begin, download this project as a zip or clone through your normal Git methods. In this project's current status, it's recommended to download PyCharm in order to run rather than command line. 

Open the project in Pycharm and then in the terminal, install the modules:

```python
pip install requirements.txt
```

# Running

To run, simply open the ```main.py``` file and run the ```if __name__ == "__main__"``` function or simply run the project via the top bar in Pycharm.

The project should then be viewable through any web browser at ```127.0.0.1:8050```. I've had some trouble with Brave and the way it blocks websites so I'd recommend any other web browser.

# Usage

In this project's current state, the only available options are for users to change the selected cryptocurrency. The default view is for ETH-USD however there's also BTC-USD and ADA-USD available. 

# Understanding

This project utilizes two threads in order to manage both the cryptofeed worker and the Dash webserver. In the background, the cryptofeed worker is storing Level2 orderbooks for the cryptocurrencies inside objects which correspond to each coin. 

Once an update has been recieved, it then updates the appropriate object. Every 500ms, the Dash server requests any changes from the currently selected currency (which corresponds to an object).

It then updates the graph with new information as well as updates the table with the 10 latest trades for that coin. 

# To do

I have a lot of visions for this project. Some of the todos include:

|file|idea|status|
|----|----|------|
|webserver.py|Add another widget to display current price|incomplete|
|webserver.py|Allow the user to change graph types|incomplete|
|webserver.py|Reduce size of currency table|incomplete|
|webserver.py|Display cumulative statistics for session|incomplete|
|cryptofeed_worker.py|Change class to not store L2 updates if the coin isn't selected - performance update|incomplete|
|cryptofeed_worker.py|Potential long term change to remove cryptofeed dependency and make custom coinbase API requests|incomplete|
|webserver.py|Rename main.py to webserver.py|complete|