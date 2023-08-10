from web3 import Web3

# Connect to your local Ethereum node
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))  # Change if using different port or IPC

# Uniswap V2 Pair ABI
UNISWAP_V2_PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
        ],
        "type": "function"
    }
]

# Uniswap V3 Pool ABI
UNISWAP_V3_POOL_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            # ... other outputs ...
        ],
        "type": "function"
    }
]

def get_uniswap_v2_price(pair_address):
    contract = w3.eth.contract(address=pair_address, abi=UNISWAP_V2_PAIR_ABI)
    reserve0, reserve1, _ = contract.functions.getReserves().call()
    return reserve1 / reserve0

def get_uniswap_v3_price(pool_address):
    contract = w3.eth.contract(address=pool_address, abi=UNISWAP_V3_POOL_ABI)
    slot_data = contract.functions.slot0().call()
    sqrt_price_x96 = slot_data[0]
    price = (sqrt_price_x96 ** 2) / (1 << 192)
    return price

def main():
    v2_pair_address = "0x...yourUniswapV2PairAddress..."
    v3_pool_address = "0x...yourUniswapV3PoolAddress..."

    v2_price = get_uniswap_v2_price(v2_pair_address)
    v3_price = get_uniswap_v3_price(v3_pool_address)

    print(f"Uniswap V2 Price: {v2_price} TOKEN/ETH")
    print(f"Uniswap V3 Price: {v3_price} TOKEN1/ETH")

if __name__ == "__main__":
    main()
