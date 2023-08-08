import os
import json
import eth_abi
import asyncio
import eth_utils
import websockets
import aioprocessing

from web3 import Web3
from functools import partial
from typing import Any, Dict, List
from multicall import Call, Multicall

from constants import TOKENS, POOLS
from utils import calculate_next_block_base_fee


async def stream_new_blocks(ws_rpc_url: str,
                            event_queue: aioprocessing.AioQueue,
                            debug: bool = False):
    
    async with websockets.connect(ws_rpc_url) as ws:
        subscription = {
            'json': '2.0',
            'id': 1,
            'method': 'eth_subscribe',
            'params': ['newHeads']
        }

        await ws.send(json.dumps(subscription))
        _ = await ws.recv()

        WEI = 10 ** 18

        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=60 * 10)
            block = json.loads(msg)['params']['result']
            block_number = int(block['number'], base=16)
            base_fee = int(block['baseFeePerGas'], base=16)
            next_base_fee = calculate_next_block_base_fee(block)
            event = {
                'source': 'dex',
                'type': 'block',
                'block_number': block_number,
                'base_fee': base_fee / WEI,
                'next_base_fee': next_base_fee / WEI,
            }
            if not debug:
                event_queue.put(event)
            else:
                print(event)
            


async def stream_uniswap_v2_events(http_rpc_url: str,
                                   ws_rpc_url: str,
                                   tokens: Dict[str, List[Any]],
                                   pools: List[List[Any]],
                                   event_queue: aioprocessing.AioQueue,
                                   debug: bool = False):
    
    w3 = Web3(Web3.HTTPProvider(http_rpc_url))
    
    block_number = w3.eth.get_block_number()
    signature = 'getReserves()((uint112,uint112,uint32))'  # reserve0, reserve1, blockTimestampLast
    
    calls = []
    for pool in pools:
        pool_name = f'{pool["exchange"]}_{pool["version"]}_{pool["name"].replace("/", "")}'
        call = Call(
            pool['address'],
            signature,
            [(pool_name, lambda x: x)]
        )
        calls.append(call)
        
    multicall = Multicall(calls, _w3=w3)
    result = multicall()
    reserves = {k: list(v)[:2] for k, v in result.items()}
    """
    reserves:
    {
        'uniswap_2_ETHUSDT': [17368643486106939361172, 31867695075486],
        'sushiswap_2_ETHUSDT': [5033262526671305584632, 9254792586342]
    }
    """
    
    filtered_pools = [pool for pool in pools if pool['version'] == 2]
    pools = {pool['address'].lower(): pool for pool in filtered_pools}
    
    def _publish(block_number: int,
                 pool: Dict[str, Any],
                 data: List[int] = []):
        
        exchange = pool['exchange']
        version = pool['version']
        symbol = f'{pool["token0"]}{pool["token1"]}'

        # save to "reserves" in memory
        symbol_key = f'{exchange}_{version}_{symbol}'
        
        if len(data) == 2:
            # initial publishing occurs without data(=Sync event data)
            reserves[symbol_key][0] = data[0]
            reserves[symbol_key][1] = data[1]
            
        token_idx = {
            pool['token0']: 0,
            pool['token1']: 1,
        }
        
        decimals = {
            pool['token0']: tokens[pool['token0']][1],
            pool['token1']: tokens[pool['token1']][1],
        }
        
        reserve_update = {
            pool['token0']: reserves[symbol_key][0],
            pool['token1']: reserves[symbol_key][1],
        }
        
        pool_update = {
            'source': 'dex',
            'type': 'pool_update',
            'block_number': block_number,
            'exchange': pool['exchange'],
            'version': pool['version'],
            'symbol': symbol,
            'token_idx': token_idx,
            'decimals': decimals,
            'reserves': reserve_update,
        }
        
        if not debug:
            event_queue.put(pool_update)
        else:
            print(pool_update)
            
    """
    Send initial reserve data so that price can be calculated even if the pool is idle
    """
    for address, pool in pools.items():
        _publish(block_number, pool)

    sync_event_selector = w3.keccak(text='Sync(uint112,uint112)').hex()
    
    async with websockets.connect(ws_rpc_url) as ws:
        subscription = {
            'json': '2.0',
            'id': 1,
            'method': 'eth_subscribe',
            'params': [
                'logs',
                {'topics': [sync_event_selector]}
            ]
        }

        await ws.send(json.dumps(subscription))
        _ = await ws.recv()

        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=60 * 10)
            event = json.loads(msg)['params']['result']
            address = event['address'].lower()

            if address in pools:
                block_number = int(event['blockNumber'], base=16)
                pool = pools[address]
                data = eth_abi.decode(
                    ['uint112', 'uint112'],
                    eth_utils.decode_hex(event['data'])
                )
                _publish(block_number, pool, data)
                

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
    
    new_blocks_stream = reconnecting_websocket_loop(
        partial(stream_new_blocks, WS_RPC_URL, None, True),
        tag='new_blocks_stream'
    )
    
    uniswap_v2_stream = reconnecting_websocket_loop(
        partial(stream_uniswap_v2_events, HTTP_RPC_URL, WS_RPC_URL, TOKENS, POOLS, None, True),
        tag='uniswap_v2_stream'
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([
        new_blocks_stream,
        uniswap_v2_stream,
    ]))
