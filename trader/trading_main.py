import asyncio
import ccxt
import logging
import numpy as np
import pprint
import time
import pyupbit
from decouple import config

class trade_fast:
    key_b=config('API_B')
    secret_b=config('KEY_B')
    
    key_u=config('API_U')
    secret_u=config('KEY_U')

    def __init__(self, currency, market, step_size, scale, crypto_num):
        self.currency_us = currency[0]
        self.currency_usf = currency[1]
        self.currency_kr = currency[2]
        self.currency_c = currency[3]
        self.currency_uc = currency[4]
        
        self.binance = market[0]
        self.binancef = market[1]
        self.upbit = market[2]

        self.step_size = step_size
        self.scale = scale

        self.crypto_num = crypto_num

    def current_balance(self, market):
        if market == 'upbit':
            exchange = ccxt.upbit(config={
            'apiKey': self.key_u,
            'secret': self.secret_u
            }
            )
            # balance
            balance = exchange.fetch_balance()
        elif market == 'binance':
            exchange = ccxt.binance(config={
            'apiKey': trade_fast.key_b,
            'secret': trade_fast.secret_b
            }
            )

            # balance
            balance = exchange.fetch_balance()
        
        if len(balance['info']) == self.crypto_num:
            usd_balance = balance['KRW']
            xrp_balance = {'free': 0.0, 'used': 0.0, 'total': 0.0}
        else:
            usd_balance = balance['KRW']
            xrp_balance = balance[self.currency_c]

        return xrp_balance, usd_balance

    def last_prices(self, market):
        if market == 'binance':
            binance = ccxt.binance(config={
            'apiKey': self.key_b, 
            'secret': self.secret_b,
            'enableRateLimit': True
            })
            binance_market = binance.fetch_ticker(self.currency_us)
            price = binance_market['last']
    
        elif market == 'binance_future':
            binance = ccxt.binance(config={
            'apiKey': self.key_b, 
            'secret': self.secret_b,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future'
            }
            })
            binance_market = binance.fetch_ticker(self.currency_usf)
            price = binance_market['last']

        elif market == 'upbit':
            upbit = ccxt.upbit(config={
            'apiKey': self.key_u, 
            'secret': self.secret_u,
            'enableRateLimit': True
            })
            upbit_market = upbit.fetch_ticker(self.currency_kr)
            price = upbit_market['last']
    
        return price

    def market_volume(self, market):
        if market == 'binance':
            exchange = ccxt.binance(config={
                'apiKey': self.key_b,
                'secret': self.secret_b,
                'enableRateLimit': True
            })
            orderbook = exchange.fetch_order_book(self.currency_us)

        elif market == 'upbit':
            exchange = ccxt.upbit(config={
                'apiKey': self.key_u,
                'secret': self.secret_u,
                'enableRateLimit': True
            })
            orderbook = exchange.fetch_order_book(self.currency_kr)
        
        return orderbook['asks'], orderbook['bids']
        
    def insert_order(self, action, current_price, amount):
        upbit = pyupbit.Upbit(self.key_u, self.secret_u)


        gap = 2*self.step_size

        if action == 'buy':
            if current_price % self.scale == 0:
                price = current_price+gap
            
            else:
                price = current_price+self.step_size
            
            order = upbit.buy_market_order(self.currency_uc, amount)
            pprint.pprint(order)
            return order
        
        elif action == 'sell':
            if current_price % self.scale == 0:
                price = current_price-gap
            
            else:
                price = current_price-self.step_size
                
            order = upbit.sell_market_order(self.currency_uc, amount)
            pprint.pprint(order)
            return order
    
    def cancel_order(self, orderID):
        binance = ccxt.upbit(config={
        'apiKey': self.key_u,
        'secret': self.secret_u
        })

        resp = binance.cancel_order(
            id=orderID,
            symbol=self.currency_kr
        )
        return resp
    
    async def last_prices_async(self, market):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.last_prices(market))
    
    async def current_amount_async(self, market):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.current_balance(market))
    
    async def current_prices_async(self, market):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.market_volume(market))
    
    async def market_fast(self):
        task1 = asyncio.create_task(self.last_prices_async(self.binance))
        task2 = asyncio.create_task(self.last_prices_async(self.binancef))
        task3 = asyncio.create_task(self.current_amount_async(self.upbit))
        task4 = asyncio.create_task(self.current_prices_async(self.upbit))
        
        usd = await task1
        usdf = await task2
        crypto, krw = await task3
        ask, bid = await task4
        

        return usd, usdf, crypto, krw, ask, bid