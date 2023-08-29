import os
import json
import eth_abi
import asyncio
import eth_utils
import websockets
import aioprocessing

from web3 import Web3
from typing import List
from functools import partial


async def stream_1inch_limit_orderbook_events(http_rpc_url: str,
                                              ws_rpc_url: str,
                                              limit_order_contracts: List[str],
                                              event_queue: aioprocessing.AioQueue,
                                              debug: bool = False):
    
    w3 = Web3(Web3.HTTPProvider(http_rpc_url))
    
    order_canceled_event_selector = w3.keccak(text='OrderCanceled(address,bytes32,uint256)').hex()
    order_filled_event_selector = w3.keccak(text='OrderFilled(address,bytes32,uint256)').hex()
    
    async with websockets.connect(ws_rpc_url) as ws:
        subscription = {
            'json': '2.0',
            'id': 1,
            'method': 'eth_subscribe',
            'params': [
                'logs',
                {'topics': [[order_canceled_event_selector, order_filled_event_selector]]}
            ]
        }

        await ws.send(json.dumps(subscription))
        _ = await ws.recv()
        
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=60 * 10)
            event = json.loads(msg)['params']['result']
            address = event['address'].lower()
            
            if address in limit_order_contracts:
                block_number = int(event['blockNumber'], base=16)
                topic = event['topics'][0]
                event_type = 'order_cancel' if topic == order_canceled_event_selector else 'order_filled'
                maker = eth_abi.decode(['address'], eth_utils.decode_hex(event['topics'][1]))[0]
                data = eth_abi.decode(['bytes32', 'uint256'], eth_utils.decode_hex(event['data']))
                order_update = {
                    'source': 'dex',
                    'type': event_type,
                    'block_number': block_number,
                    'exchange': address,
                    'maker': maker,
                    'order_hash': data[0].hex(),
                    'remaining': data[1],
                }
                
                if not debug:
                    event_queue.put(order_update)
                else:
                    print(order_update)
                
            
if __name__ == '__main__':
    import os
    import nest_asyncio
    from functools import partial
    from dotenv import load_dotenv
    
    from utils import reconnecting_websocket_loop
    
    nest_asyncio.apply()

    load_dotenv(override=True)

    HTTP_RPC_URL = os.getenv('HTTP_RPC_URL')
    WS_RPC_URL = os.getenv('WS_RPC_URL')
    
    inch_stream = reconnecting_websocket_loop(
        partial(stream_1inch_limit_orderbook_events, HTTP_RPC_URL, WS_RPC_URL, ['0x1111111254eeb25477b68fb85ed929f73a960582'], None, True),
        tag='inch_stream'
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([
        inch_stream,
    ]))
