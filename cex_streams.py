import json
import asyncio
import requests
import websockets
import aioprocessing
from typing import List
from decimal import Decimal


# Binance USDM-Futures orderbook stream
async def stream_binance_usdm_orderbook(symbols: List[str],
                                        event_queue: aioprocessing.AioQueue,
                                        debug: bool = False):
    async with websockets.connect('wss://fstream.binance.com/ws/') as ws:
        params = [
            f'{s.replace("/", "").lower()}@depth5@100ms' for s in symbols]
        subscription = {
            'method': 'SUBSCRIBE',
            'params': params,
            'id': 1,
        }
        await ws.send(json.dumps(subscription))
        _ = await ws.recv()

        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(msg)
            orderbook = {
                'source': 'cex',
                'type': 'orderbook',
                'exchange': 'binance',
                'symbol': data['s'],
                'bids': [[Decimal(d[0]), Decimal(d[1])] for d in data['b']],
                'asks': [[Decimal(d[0]), Decimal(d[1])] for d in data['a']]
            }
            if not debug:
                event_queue.put(orderbook)
            else:
                print(orderbook)
            
            
# OKX USDM-Futures orderbook stream
# At OKX, they call perpetuals by the name of swaps.
async def stream_okx_usdm_orderbook(symbols: List[str],
                                    event_queue: aioprocessing.AioQueue,
                                    debug: bool = False):
    instruments = requests.get('https://www.okx.com/api/v5/public/instruments?instType=SWAP').json()
    multipliers = {
        d['instId'].replace('USD', 'USDT'): Decimal(d['ctMult']) / Decimal(d['ctVal'])
        for d in instruments['data']
    }
    
    async with websockets.connect('wss://ws.okx.com:8443/ws/v5/public') as ws:
        args = [{'channel': 'books5', 'instId': f'{s.replace("/", "-")}-SWAP'} for s in symbols]
        subscription = {
            'op': 'subscribe',
            'args': args,
        }
        await ws.send(json.dumps(subscription))
        _ = await ws.recv()

        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(msg)
            multiplier = multipliers[data['arg']['instId']]
            symbol = data['arg']['instId'].replace('-SWAP', '').replace('-', '')
            bids = [[Decimal(d[0]), Decimal(d[1]) * multiplier] for d in data['data'][0]['bids']]
            asks = [[Decimal(d[0]), Decimal(d[1]) * multiplier] for d in data['data'][0]['asks']]
            orderbook = {
                'source': 'cex',
                'type': 'orderbook',
                'exchange': 'okx',
                'symbol': symbol,
                'bids':  bids,
                'asks': asks,
            }
            if not debug:
                event_queue.put(orderbook)
            else:
                print(orderbook)
            
            
if __name__ == '__main__':
    import nest_asyncio
    from functools import partial
    
    from utils import reconnecting_websocket_loop
    
    nest_asyncio.apply()
    
    symbols = ['ETH/USDT']
    
    binance_stream = reconnecting_websocket_loop(
        partial(stream_binance_usdm_orderbook, symbols, None, True),
        tag='binance_stream'
    )
    
    okx_stream = reconnecting_websocket_loop(
        partial(stream_okx_usdm_orderbook, symbols, None, True),
        tag='okx_stream'
    )
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([
        binance_stream,
        okx_stream,
    ]))
