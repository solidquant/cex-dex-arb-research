# CEX-DEX Arbitrage Research Template

A CEX-DEX arbitrage research template for Whack-A-Mole.

This project borrows from the code in Whack-A-Mole to focus on realtime data streams.

We can search for MEV opportunities using this repository on multiple CEXs and DEXs.

The main entry point for this project is the Jupyter Notebook file: **cex-dex-arb.ipynb**.

#### 1. Setup environment variables:

First, you need to setup your environment variables by simply copying and pasting the file content of .env.example to .env file.

```bash
HTTP_RPC_URL=http://localhost:8545
WS_RPC_URL=ws://localhost:8546
```

#### 2. Understanding CEX streams and DEX streams:

This research template can stream data from CEXs and DEXs.

At the current state, you can stream CEX orderbook and DEX reserves data from:

|Exchange|Implemented|
|---|---|
|Binance|✅|
|OKX|✅|
|Uniswap V2|✅|
|Sushiswap V2|✅|

More support for other exchanges will be added quickly, to begin MEV alpha hunting.

Each of the files: *cex_streams.py, dex_streams.py* have examples below the code that you can run and see how the websocket streams work. You can run these streams in "debug" mode, which will print out all the data it publishes on the terminal.

#### 3. Aggregator:

DEX aggregating is pretty simple at this state. It simply collects data from multiple DEX sources, so it isn't necessary to have a separate aggregator.

However, CEX aggregation is needed.

Say we are looking at two sources of CEX: Binance, OKX.

We receive bid, ask data as such:

- Binance: [[bid_1_price, bid_1_quantity], [bid_2_price, bid_2_quantity], ...]
- OKX: [[bid_1_price, bid_1_quantity], [bid_2_price, bid_2_quantity], ...]

We want to merge these orderbook depths together to create what we will call a: **MultiOrderbook**.

The logic behind the creation of a MultiOrderbook is rather simple:

```python
# aggregator.py
bids, asks = [], []

for exchange, orderbook in orderbooks.items():
    bids.extend([b + [exchange] for b in orderbook['bids']])
    asks.extend([a + [exchange] for a in orderbook['asks']])

bids = sorted(bids, key=itemgetter(0), reverse=True)
asks = sorted(asks, key=itemgetter(0))
```

#### 4. Event handler:

Once you start streaming real-time orderbook data and blockchain events data, you send these data to the event_handler, that you have to define.

These handlers are currently defined in **cex-dex-arb.ipynb**.

```python
from threading import Thread

from constants import TOKENS, POOLS

def event_handler_loop(port: int, event_queue: aioprocessing.AioQueue):
    asyncio.run(cex_event_handler(port, event_queue))

# define an event_queue to publish realtime data
event_queue = aioprocessing.AioQueue()

symbols = ['ETH/USDT']

# CEX related streams
binance_stream = reconnecting_websocket_loop(
    partial(stream_binance_usdm_orderbook, symbols, event_queue),
    tag='binance_stream'
)

okx_stream = reconnecting_websocket_loop(
    partial(stream_okx_usdm_orderbook, symbols, event_queue),
    tag='okx_stream'
)
    
# start event_handler_loop in a new thread
chart_port = 9999

t = Thread(target=event_handler_loop, args=(chart_port, event_queue,))
t.start()

nest_asyncio.apply()

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.wait([
    binance_stream,
    okx_stream,
]))
```

Running this will start a separate thread running the event_handler, and two async threads running: binance_stream and okx_stream.

Note here that there is a variable defined for "port".

This is used to send price spread data to ChartWindow defined in **spread_chart.py**. This will pop up a new window using PyQt6, and draw a real-time line chart updating the price spread values. To use this, you'll have to separately run the: **spread_chart.py** file:

```bash
python spread_chart.py
```

Doing this will result in the below:

![Chart](https://github.com/solidquant/cex-dex-arb-research/assets/134243834/de097386-da42-4f3f-9a56-8ac2180b4ed8)

---

⚡️ If anyone is interested in developing this MEV research template together, or in searching for opportunities together, please join the Discord community! 🌎🪐

https://discord.com/invite/e6KpjTQP98