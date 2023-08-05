TOKENS = {
    'ETH': ['0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 18],
    'USDT': ['0xdAC17F958D2ee523a2206206994597C13D831ec7', 6],
}

columns = ['exchange', 'version', 'name', 'address', 'fee', 'token0', 'token1']

POOLS = [
    ['uniswap', 2, 'ETH/USDT', '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852', 3000, 'ETH', 'USDT'],
    ['sushiswap', 2, 'ETH/USDT', '0x06da0fd433C1A5d7a4faa01111c044910A184553', 3000, 'ETH', 'USDT'],
]

POOLS = [dict(zip(columns, pool)) for pool in POOLS]