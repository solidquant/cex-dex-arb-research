import os
import time
import json
import requests

from typing import List, Dict
from dotenv import load_dotenv

load_dotenv(override=True)

INCH_API = os.getenv('1INCH_API')

CHAIN_ID = {
    'ethereum': 1,
    'bsc': 56,
    'polygon': 137,
    'optimism': 10,
    'arbitrum': 42161,
}

def _headers():
    return {'accept': 'accept: application/json', 'Authorization': f'Bearer {INCH_API}'}


def get_orderbook_events():
    url = 'https://api.1inch.dev/orderbook'
    res = requests.get(f'{url}/v3.0/1/events?limit=50', headers=_headers())
    orders = res.json()
    return orders


def get_spot_price(tokens: List[str]):
    url = 'https://api.1inch.dev/price/v1.1/1'
    payload = {'tokens': tokens}
    res = requests.post(url, json=payload, headers=_headers())
    if res.status_code == 200:
        prices = res.json()
        return prices


def get_tokens_on_1inch():
    url = 'https://api.1inch.dev/swap/v5.2/1/tokens'
    headers = {'accept': 'accept: application/json', 'Authorization': f'Bearer {INCH_API}'}
    res = requests.get(url, headers=headers)
    return res.json()


def get_quotes(chain: str, token_in: str, token_out: str, amount_in: int):
    chain_id = CHAIN_ID.get(chain)
    if not chain_id:
        return
    
    url = f'https://api.1inch.dev/v5.2/{chain_id}/quote?src={token_in}&dst={token_out}&amount={amount_in}'
    
    res = requests.get(url)
    data = json.loads(res.text)
    return data


def get_orderbook(buy_token: str, sell_token: str, depth: int):
    url = 'https://api.1inch.dev/orderbook'
    res = requests.get(f'{url}/v3.0/1/all?limit={depth}&sortBy=takerRate&makerAsset={buy_token}&takerAsset={sell_token}', headers=_headers())
    orders = res.json()
    return orders
    
def get_1inch_limit_orderbook(symbol: str,
                              tokens: Dict[str, str],
                              decimals: Dict[str, int],
                              depth: int = 20):
    """
    Creates an orderbook of bids/asks using the 1inch limit orderbook API
    """
    symbols = symbol.split('/')
    token0 = tokens[symbols[0]]
    token1 = tokens[symbols[1]]
    
    _tokens = {v.lower(): k for k, v in tokens.items()}
    _decimals = {tokens[k].lower(): v for k, v in decimals.items()}
    
    bids_orderbook = get_orderbook(buy_token=token1, sell_token=token0, depth=depth)
    time.sleep(1)  # rate limit (429 error)
    asks_orderbook = get_orderbook(buy_token=token0, sell_token=token1, depth=depth)
    
    bids = []
    asks = []
    
    for o in bids_orderbook:
        depth = {
            'hash': o['orderHash'],
            'created': o['createDateTime'],
            'selling_token': _tokens[o['data']['makerAsset'].lower()],
            'buying_token': _tokens[o['data']['takerAsset'].lower()],
            'selling_decimals': _decimals[o['data']['makerAsset'].lower()],
            'buying_decimals': _decimals[o['data']['takerAsset'].lower()],
            'selling_amount': int(o['data']['makingAmount']),
            'buying_amount': int(o['data']['takingAmount']),
            'maker_rate': float(o['makerRate']),
            'taker_rate': float(o['takerRate']),
            'remaining': int(o['remainingMakerAmount']),
        }
        selling_amount = float(depth['selling_amount']) / 10 ** depth['selling_decimals']
        buying_amount = float(depth['buying_amount']) / 10 ** depth['buying_decimals']
        price_1 = selling_amount / buying_amount
        price_2 = buying_amount / selling_amount
        quantity = depth['remaining'] / 10 ** depth['selling_decimals']
        bids.append({'price': price_1, 'quantity': quantity, 'created': depth['created']})
        
    for o in asks_orderbook:
        depth = {
            'hash': o['orderHash'],
            'created': o['createDateTime'],
            'selling_token': _tokens[o['data']['makerAsset'].lower()],
            'buying_token': _tokens[o['data']['takerAsset'].lower()],
            'selling_decimals': _decimals[o['data']['makerAsset'].lower()],
            'buying_decimals': _decimals[o['data']['takerAsset'].lower()],
            'selling_amount': int(o['data']['makingAmount']),
            'buying_amount': int(o['data']['takingAmount']),
            'maker_rate': float(o['makerRate']),
            'taker_rate': float(o['takerRate']),
            'remaining': int(o['remainingMakerAmount']),
        }
        selling_amount = float(depth['selling_amount']) / 10 ** depth['selling_decimals']
        buying_amount = float(depth['buying_amount']) / 10 ** depth['buying_decimals']
        price_1 = selling_amount / buying_amount
        price_2 = buying_amount / selling_amount
        quantity = depth['remaining'] / 10 ** depth['selling_decimals']
        asks.append({'price': price_2, 'quantity': quantity, 'created': depth['created']})
        
    return {'bids': bids, 'asks': asks}
    
    
    
if __name__ == '__main__':
    WEI = 10 ** 18
    
    chain = 'ethereum'
    USDT = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
    WETH = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    amount_in = 1 ** WEI
    
    tokens = {
        'ETH': WETH,
        'USDT': USDT,
    }
    
    decimals = {
        'ETH': 18,
        'USDT': 6,
    }
    
    orderbook = get_1inch_limit_orderbook('ETH/USDT', tokens, decimals, 20)
    print(orderbook)
