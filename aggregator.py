import aioprocessing
from decimal import Decimal
from operator import itemgetter
from typing import Any, Dict, List


def aggregate_cex_orderbooks(orderbooks: Dict[str, Dict[str, Any]]) -> Dict[str, List[List[Decimal]]]:
    """
    :param orderbooks:
    {
        'binance': {'source': 'cex', 'type': 'orderbook', ... },
        'okx': {'source': 'cex', 'type': 'orderbook', ... },
    }
    """
    bids, asks = [], []
    
    for exchange, orderbook in orderbooks.items():
        bids.extend([b + [exchange] for b in orderbook['bids']])
        asks.extend([a + [exchange] for a in orderbook['asks']])
    
    bids = sorted(bids, key=itemgetter(0), reverse=True)
    asks = sorted(asks, key=itemgetter(0))
    
    return {'bids': bids, 'asks': asks}


def aggregate_dex_updates():
    pass
    

async def event_handler(event_queue: aioprocessing.AioQueue):
    orderbooks = {}
    
    while True:
        data = await event_queue.coro_get()
        
        symbol = data['symbol']
        
        if data['source'] == 'cex':
            if symbol not in orderbooks:
                orderbooks[symbol] = {}
                
            orderbooks[symbol][data['exchange']] = data
            multi_orderbook = aggregate_cex_orderbooks(orderbooks[symbol])
            print(multi_orderbook)
    
    
if __name__ == '__main__':
    import asyncio
    import nest_asyncio
    from functools import partial
    
    from utils import reconnecting_websocket_loop
    from cex_streams import stream_binance_usdm_orderbook, stream_okx_usdm_orderbook
    
    nest_asyncio.apply()
    
    symbols = ['ETH/USDT']
    event_queue = aioprocessing.AioQueue()
    
    # Testing CEX aggregator
    binance_stream = reconnecting_websocket_loop(
        partial(stream_binance_usdm_orderbook, symbols, event_queue, False),
        tag='binance_stream'
    )
    
    okx_stream = reconnecting_websocket_loop(
        partial(stream_okx_usdm_orderbook, symbols, event_queue, False),
        tag='okx_stream'
    )
    
    event_handler_loop = event_handler(event_queue)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([
        binance_stream,
        okx_stream,
        event_handler_loop,
    ]))