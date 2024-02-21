from trading_main import trade_fast
import logging
import time
import ccxt
import pyupbit
import math
from sklearn.tree import DecisionTreeClassifier
from catboost import CatBoostClassifier

logging.basicConfig(level=logging.WARNING)
logging.getLogger().setLevel(logging.INFO)
LOG = logging.getLogger(__name__)

def round_sigfigs(num, sig_figs):
    if num != 0:
        return round(num, -int(math.floor(math.log10(abs(num)))) + (sig_figs - 1))
    else:
        return 0.0

class accumulated_trade(trade_fast):
    transaction = 0.9995**2
    def run(self, coin: str, price: float, vol: float, change: str, 
            max_vol: dict, balance: dict, status: dict, 
            bought_vol: dict, bought_price: dict, time_diff: float):
        if vol > max_vol[coin] and balance['KRW'] >= 10000 and status[coin] == 'SOLD' and change == 'RISE' and price>100 and time_diff<14*3600:
            order = self.market_buy(coin, 10000)
            time.sleep(3)
            upbit = pyupbit.Upbit(self.key_u, self.secret_u)
            amount = upbit.get_balance(coin)
            balance['KRW'] -= 10000
            balance[coin] = float(amount)
            bought_price[coin] = price
            bought_vol[coin] = vol
            status[coin] = 'BOUGHT'
            LOG.info(f'buying at price {price} balance: {balance} vol: {vol} max:vol: {max_vol[coin]}')
        elif vol < bought_vol[coin] and status[coin] == 'BOUGHT':
            order = self.market_sell(coin, balance[coin])
            time.sleep(3)
            krw_balance = 0.9995*(price)*balance[coin]
            balance[coin] = 0
            balance['KRW'] += krw_balance
            sold_price = price
            status[coin] = 'SOLD'
            LOG.info(f'selling at price {price} balance: {balance}')
        return balance, status, bought_vol
    
    def run_with_lm(self, coin: str, price: float,
            order_time: dict, balance: dict, status: dict, 
            bought_time: dict, order: dict,signal: list, 
            order_id:dict,  bought_price:dict, prob:float):
        LOG.info(f'{coin} activating buying protocol with {signal} and prob: {prob}')
        if prob >= 0.6 and balance['KRW'] >= 5100 and status[coin] == 'SOLD':
            a = (balance['KRW']/price)*0.9995
            order[coin] = self.insert_order(coin, 'buy', price, a)
            #time.sleep(3)
            upbit = pyupbit.Upbit(self.key_u, self.secret_u)
            amount = upbit.get_balance(coin)
            balance['KRW'] = 0
            balance[coin] = float(amount)
            bought_price[coin] = price
            bought_time[coin] = time.time()
            order_time[coin] = time.time()
            order_id[coin] = self.get_order(order[coin]['uuid'])
            status[coin] = 'BUY'
            LOG.info(f'buying at price {price} balance: {balance} order_id: {order_id[coin]}')
            
        elif signal == 0 and balance['KRW'] < 5100:
            LOG.info(f'buying signal generated for {coin} for price: {price} but could not buy')
            a = balance[coin]
            LOG.info(f'selling {coin} at price {price} balance: {balance} profit: {profit}')
            order[coin] = self.insert_order(coin, 'sell', price, a)
            order_time[coin] = time.time()
            #time.sleep(3)
            #krw_balance = 0.9995*(price)*balance[coin]
            #balance[coin] = 0
            #balance['KRW'] += krw_balance
            sold_price[coin] = price
            #sold[coin] = 1
            order_id[coin] = self.get_order(order[coin]['uuid'])
            status[coin] = 'SELL'
            LOG.info(f'good sold {coin} at price {price} balance: {balance} profit: {profit}')
            
        # if status[coin] == 'BUY' or status[coin] == 'SELL':
        #     LOG.info(f'updating {coin} orderID')
        #     order_id[coin] = self.get_order(order[coin]['uuid'])
        #     if order_id[coin]['state'] != 'wait':
        #         if status[coin] == 'BUY':
        #             status[coin] = 'BOUGHT'
        #             balance[coin] = float(order_id[coin]['volume'])
        #             LOG.info(f'order filled for {coin} status: {status[coin]} balance: {balance}')
        #         elif status[coin] == 'SELL':
        #             status[coin] = 'SOLD'
        #             balance['KRW'] += float(order_id[coin]['price'])*float(order_id[coin]['volume'])
        #             balance[coin] = 0
        #             LOG.info(f'order filled for {coin} status: {status[coin]} balance: {balance}')
            
        return balance, status, bought_time, bought_price, order, order_id
            
    def sell_protocol(self, balance:dict, profit:float, status:dict, coin:str, 
                      order:dict, order_time:dict, price:float, sold_price:dict,
                      order_id:dict, bought_time:dict, bought_price:dict, initial_krw:float):
        now = time.time()
        if profit<-0.01 and status[coin] == 'BOUGHT':
            a = balance[coin]
            LOG.info(f'kind of bad selling {coin} at price {price} balance: {balance} profit: {profit}')
            order[coin] = self.insert_order(coin, 'sell', price, a)
            order_time[coin] = time.time()
            sold_price[coin] = price
            order_id[coin] = self.get_order(order[coin]['uuid'])
            status[coin] = 'SELL'
            LOG.info(f'kind of bad sold {coin} at price {price} balance: {balance} profit: {profit}')
            
        if status[coin] == 'BUY' or status[coin] == 'SELL':
            LOG.info(f'updating {coin} orderID')
            order_id[coin] = self.get_order(order[coin]['uuid'])
            if order_id[coin]['state'] != 'wait':
                if status[coin] == 'BUY':
                    balance, bought_price, order, order_time, order_id, status = self.upper_sell(coin, bought_price, balance, 
                                                                                                 status, order, order_id, order_time)
                elif status[coin] == 'SELL':
                    status[coin] = 'SOLD'
                    balance['KRW'] += float(order_id[coin]['price'])*float(order_id[coin]['volume'])
                    balance[coin] = 0
                    LOG.info(f'order filled for {coin} status: {status[coin]} balance: {balance}')
            
        order_id, status, balance, order = self.cancel_protocol(now, coin, balance, order_time, 
                                                                order_id, order, status, initial_krw)
            
        return balance, status, bought_time, order, order_id, sold_price
            
            
    
    def scalp(self, coin: str, price: float,
            order_time: dict, balance: dict, status: dict, 
            order: dict, dev:dict, max_dev:dict, max_price:dict,
            order_id:dict,  bought_price:dict, initial_krw:float,
            bought_time:dict, step:dict):
        # if coin == 'KRW-BTC':
        #     upbit = pyupbit.Upbit(self.key_u, self.secret_u)
        #     upbit_balance = upbit.get_balance(coin)
        #     krw_balance = upbit.get_balance('KRW')
        #     LOG.info(f'{coin} balance: {type(upbit_balance)}')
        #     LOG.info(f'KRW balance: {type(krw_balance)}')
            
        # LOG.info(f'{coin} activating buying protocol with {signal} and prob: {prob}')
        if dev > 7*max_dev[coin] and balance['KRW'] >= 5100 and status[coin] == 'SOLD' and price<0.99*max_price[coin]:
            balance, bought_price, order, order_time, order_id, status = self.buy(
                                                                                coin, balance, price, step, 
                                                                                bought_price, order, order_time, 
                                                                                order_id, status
                                                                                )
            LOG.info(f'buying at price {bought_price[coin]} balance: {balance} order_id: {order_id[coin]}')
            
        elif dev > 7*max_dev[coin] and price<0.999*max_price[coin] and balance['KRW'] < 5100 and status[coin] == 'SOLD':
            LOG.info(f'buying signal generated for {coin} for price: {price} but could not buy')
            
        return balance, status, bought_time, bought_price, order, order_id
            
            
        

class max_trade(trade_fast):
            
    def run(self, coin, step, current_price, 
            current_vol, balance, currency, 
            order_time, order, order_id, cutoff):
        asset = balance[0] + (current_price-step)*balance[1]

        if current_vol >= cutoff and balance[1] != 0 and current_price != ordered_price and order_time[1] == 'BOUGHT':
        #if asset > 1.01*initial_asset and balance[1] != 0:
            LOG.info(f'selling {coin} at price {current_price} with {current_momentum} {max_mo}')
            #order = self.market_sell(coin, balance[1])
            order = self.insert_order(coin, 'sell', current_price, balance[1], step)
            #a = (balance[1]*(current_price-step))*0.9995
            #balance = [a, 0]
            ordered_price = current_price
            asset = balance[0] + (current_price-step)*balance[1]
            LOG.info(f'current asset for {coin}: {asset}')
            max_mo = current_momentum
            order_time = [time.time(), 'SELL']
            LOG.info(f'selling order: {order}')
            order_id = self.get_order(order['uuid'])
        
        elif cutoff[3]*min_mo <= current_momentum and current_momentum<= cutoff[4]*min_mo and ordered_price != current_price and (order_time[1] == 'SOLD' or order_time[1] =='null'):
            a = (balance[0]/(current_price+step))*0.9995
            LOG.info(balance)
            LOG.info(order_time)
            LOG.info(f'buying {coin} at price {current_price} amount: {a} momentum: {current_momentum} {min_mo}')
            order = self.insert_order(coin, 'buy', current_price, a, step)
            balance = [0, a]
            LOG.info(f'balance after buying: {balance}')
            ordered_price = current_price
            min_mo = current_momentum
            order_time = [time.time(), 'BUY']
            LOG.info(f'buying order: {order}')
            LOG.info(f'buying time: {order_time}')
            order_id = self.get_order(order['uuid'])
        
        if order_time[1] == 'BUY' or order_time[1] == 'SELL':
            LOG.info('updating orderID')
            order_id = self.get_order(order['uuid'])
        now = time.time()
        if now-order_time[0]>3 and order_id['state'] == 'wait':
            LOG.info(f'cancelling the orders for {coin}')
            LOG.info(f'balance before: {balance}')
            order_id = self.get_order(order['uuid'])
            upbit = pyupbit.Upbit(self.key_u, self.secret_u)
            self.cancel_order(order_id['uuid'])
            if order_time[1] == 'BUY':
                LOG.info('cancelled buy order')
                upbit_balance = upbit.get_balance(coin)
                krw_balance = krw_balance = 0.9995*(current_price-step)*balance[1]
                LOG.info(upbit_balance)
                cry_balance = 0
                balance =[krw_balance, cry_balance]
                LOG.info(f'balance after: {balance}')
                order_time = [time.time(), 'SOLD']
            elif order_time[1] == 'SELL':
                LOG.info('cancelled sell order')
                # a = balance[0]/((current_price+step)*0.9995)
                # balance = [0, a]
                upbit_balance = upbit.get_balance(coin)
                krw_balance = 0
                LOG.info(upbit_balance)
                cry_balance = float(upbit_balance)
                balance =[krw_balance, cry_balance]
                LOG.info(f'balance after: {balance}')
                order_time = [time.time(), 'BOUGHT']
            LOG.info(f'order_time after cancellation: {order_time}')

        elif order_id['state'] == 'done' and order_time[1] != 'BOUGHT' and order_time[1] != 'SOLD':
            LOG.info(f'order filled for {coin}')
            upbit = pyupbit.Upbit(self.key_u, self.secret_u)
            if order_time[1] == 'BUY':
                order_time = [time.time(), 'BOUGHT']
                upbit_balance = upbit.get_balance(coin)
                krw_balance = 0
                LOG.info(upbit_balance)
                cry_balance = float(upbit_balance)
                balance =[krw_balance, cry_balance]
                LOG.info(f'balance after buying: {balance}')
            elif order_time[1] == 'SELL':
                order_time = [time.time(), 'SOLD']
                upbit_balance = upbit.get_balance(coin)
                krw_balance = 0.9995*(current_price-step)*balance[1]
                LOG.info(upbit_balance)
                cry_balance = float(upbit_balance)
                balance =[krw_balance, cry_balance]
                LOG.info(f'balance after selling: {balance}')
                
            LOG.info(f'{coin} {order_time} {balance}')
        #LOG.info('moving on')
        #LOG.info(f'current order)time: {order_time}')
        
        return balance, asset, ordered_price, order, order_time
    
    def sell_everything(self, coin, current_price, step):
        upbit = pyupbit.Upbit(self.key_u, self.secret_u)
        upbit_balance = upbit.get_balance(coin)
        cry_balance = float(upbit_balance)
        order = self.market_sell(coin, cry_balance)
        
