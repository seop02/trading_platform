import asyncio
import ccxt
import logging
import numpy as np
import pprint
import time
# from decouple import config
import pyupbit
import math
import time

logging.basicConfig(level=logging.WARNING)
logging.getLogger().setLevel(logging.INFO)
LOG = logging.getLogger(__name__)

class trade_fast:
    with open("api.txt") as f:
        lines = f.readlines()
        key_b = lines[0].strip() 
        secret_b = lines[1].strip()

    with open("api_upbit.txt") as f:
        lines = f.readlines()
        key_u = lines[0].strip() 
        secret_u = lines[1].strip()


    def __init__(self, currency):
        self.currency = currency
        
    def round_sigfigs(self, num, sig_figs):
        if num != 0:
            return round(num, -int(math.floor(math.log10(abs(num)))) + (sig_figs - 1))
        else:
            return 0.0
        

    def current_balance(self, market, currency):
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
            
        LOG.info(balance)
        
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
        
    def insert_order(self, coin, action, current_price, amount):
        upbit = pyupbit.Upbit(self.key_u, self.secret_u)

        if action == 'buy':
            # if coin == 'KRW-SOL':
            #     price = current_price
            #     amount = amount*(current_price+step_size)/0.9995
            #     LOG.info(f'buying with current price: {price} currency: {coin} amount: {amount}')
            #     order = upbit.buy_market_order(coin, amount)
            #     pprint.pprint(order)
            #     return order

            #else:
            price = current_price
            LOG.info(f'buying with current price: {price} currency: {coin} amount: {amount}')
            order = upbit.buy_limit_order(coin, price, amount)
            pprint.pprint(order)
            return order
        
        elif action == 'sell':
            price = current_price
            LOG.info(f'selling with current price: {price} currency: {coin} amount: {amount}')
            order = upbit.sell_limit_order(coin, price, amount)
            pprint.pprint(order)
            return order
        
    def market_buy(self, coin, amount):
        upbit = pyupbit.Upbit(self.key_u, self.secret_u)
        order = upbit.buy_market_order(coin, amount)
        pprint.pprint(order)
        return order
        
    def market_sell(self, coin, amount):
        upbit = pyupbit.Upbit(self.key_u, self.secret_u)
        order = upbit.sell_market_order(coin, amount)
        pprint.pprint(order)
        return order
        
    def cancel_order(self, orderID):
        upbit = pyupbit.Upbit(self.key_u, self.secret_u)

        resp = upbit.cancel_order(
            uuid=orderID
        )
        return resp 
    
    def get_order(self, orderID):
        upbit = pyupbit.Upbit(self.key_u, self.secret_u)

        resp = upbit.get_order(
            orderID
        )
        #LOG.info(f'remaining order: {resp}')
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
    
    def buy(self, coin:str, balance: dict, price:float, step:dict, 
            bought_price: dict, order:dict, order_time:float, 
            order_id:dict, status:dict):
        if coin == 'KRW-BTC':
            bought_price[coin] = self.round_sigfigs(price-2*step[coin], 5)
        else:
            bought_price[coin] = self.round_sigfigs(price-2*step[coin], 4)
        a = (balance['KRW']/(bought_price[coin]))*0.9995
        order[coin] = self.insert_order(coin, 'buy', bought_price[coin], a)
        balance['KRW'] = 0
        balance[coin] = a
        status[coin] = 'BUY'
        order_time[coin] = time.time()
        order_id[coin] = self.get_order(order[coin]['uuid'])
        return balance, bought_price, order, order_time, order_id, status
    
    def upper_sell(self, coin:str, bought_price:dict, balance:dict,
                   status:dict, order:dict, order_id:dict, order_time:dict):
        status[coin] = 'BOUGHT'
        balance[coin] = float(order_id[coin]['volume'])
        target_price = (1.003*bought_price[coin])/self.transaction
        if coin == 'KRW-BTC':
            final_price = self.round_sigfigs(target_price, 5)
        else:
            final_price = self.round_sigfigs(target_price, 4)
        order_time[coin] = time.time()
        LOG.info(f'order filled for {coin} status: {status[coin]} balance: {balance}')
        LOG.info(f'sending selling for {coin} at price: {final_price} status: {status[coin]} balance: {balance}')
        order[coin] = self.insert_order(coin, 'sell', final_price, balance[coin])
        order_id[coin] = self.get_order(order[coin]['uuid'])
        order_time[coin] = time.time()
        status[coin] = 'SELL'
        return balance, bought_price, order, order_time, order_id, status
    
    def cancel_protocol(self, now, coin:float, balance:dict,
                        order_time:dict, order_id:dict, order:dict, 
                        status:dict, initial_krw:float):
        if now-order_time[coin]>50 and order_id[coin]['state'] == 'wait' and status[coin] == 'BUY':
            LOG.info(f'cancelling the orders for {coin}')
            LOG.info(f'balance before: {balance}')
            order_id[coin] = self.get_order(order[coin]['uuid'])
            upbit = pyupbit.Upbit(self.key_u, self.secret_u)
            self.cancel_order(order_id[coin]['uuid'])
            LOG.info(f'cancelled buy order {order_id[coin]}')
            upbit_balance = upbit.get_balance(coin)
            krw_balance = upbit.get_balance('KRW')
            balance['KRW'] = 1000000+krw_balance-initial_krw
            LOG.info(upbit_balance)
            cry_balance = 0
            LOG.info(f'balance after: {balance}')
            status[coin] = 'SOLD'
        if now-order_time[coin]>3600 and order_id[coin]['state'] == 'wait' and status[coin] == 'SELL':
            LOG.info(f'cancelling the orders for {coin}')
            LOG.info(f'balance before: {balance}')
            order_id[coin] = self.get_order(order[coin]['uuid'])
            upbit = pyupbit.Upbit(self.key_u, self.secret_u)
            self.cancel_order(order_id[coin]['uuid'])
            LOG.info('cancelled sell order')
            upbit_balance = upbit.get_balance(coin)
            krw_balance = upbit.get_balance('KRW')
            balance['KRW'] = 0
            LOG.info(upbit_balance)
            cry_balance = float(upbit_balance)
            balance[coin] = cry_balance
            LOG.info(f'balance after: {balance}')
            status[coin] = 'BOUGHT'
        return order_id, status, balance, order
            
            