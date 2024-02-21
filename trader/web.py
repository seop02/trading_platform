import json
import time
import logging
import threading 
import websocket
import websockets
import multiprocessing as mp
import pyupbit
import math
import pandas as pd
from __init__ import data_path
import os
import numpy as np
from trading_main import trade_fast
from acc_trader import accumulated_trade
import asyncio
import multiprocessing
import concurrent.futures
from datetime import timezone, datetime
from catboost import CatBoostClassifier
from decouple import config
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score


logging.basicConfig(level=logging.WARNING)
logging.getLogger().setLevel(logging.INFO)
LOG = logging.getLogger(__name__)

async def get_current_volume(
    coins:list, current_volume:dict, trial: dict, 
    balance:dict, status:dict,
    bought_time:dict, order: dict,
    bought_price:dict, order_id:dict,
    sold_price:dict, order_time:dict,
    max_dev:dict, max_price:dict, initial_krw:float):
    
    uri = "wss://api.upbit.com/websocket/v1" 
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    transaction = 0.9995**2
    year = int(date[0:4])
    month = int(date[5:7])
    day = int(date[8:10])
    initialized = {coin: 0 for coin in coins}
    step = {}
    specified_time = datetime(year, month, day, 0, 0, 0, tzinfo=timezone.utc)
    start_time = specified_time.timestamp()
    if not os.path.exists(f'{data_path}/acc/{date}'):
        os.mkdir(f'{data_path}/acc/{date}')
        
    # X = np.load(f'{data_path}/training/0.7_0.01_tot_X_2024-02-03.npy', allow_pickle=True)
    # y = np.load(f'{data_path}/training/0.7_0.01_tot_Y_2024-02-03.npy', allow_pickle=True)
    # LOG.info(X[0])
    
    # parameter_path = f'{data_path}/training/0.7_0.01_tot_parameters_2024-02-02.json'
    
    # with open(parameter_path, 'r') as json_file:
    #     parameters = json.load(json_file)

    # clf = CatBoostClassifier(learning_rate=parameters['Catboost']['learning_rate'],
    #                          iterations=parameters['Catboost']['iterations'],
    #                          depth=parameters['Catboost']['depth'],
    #                          l2_leaf_reg=parameters['Catboost']['l2_leaf_reg'],
    #                          class_weights=[1.0, 0.31])
    # clf.fit(X, y)

    # predicted_labels = clf.predict(X)
    # accuracy = balanced_accuracy_score(y, predicted_labels)
    # LOG.info(f'ACCURACY: {accuracy}')
    time_threshold = 12*3600
    beginning = time.time()
    
    trader = accumulated_trade('hi')
    
    while True:
        try:
            #LOG.info(f'starting acc for {coins}!!!')
            async with websockets.connect(uri) as ws:
                payload = [{"ticket": "your-ticket"}, {"type": 'ticker', "codes": coins}]  
                await ws.send(json.dumps(payload))
                while True:
                    try:
                        response = await ws.recv()
                        data = json.loads(response)
                    except Exception as e:
                        LOG.info('Current location in line 44')
                        LOG.error(f'Error: {e}')
                        await asyncio.sleep(1)
                        break

                    #LOG.info('running')
                    now = time.time()
                    time_diff = now-start_time

                    coin = data['code']
                    price = data['trade_price']
                    vol = data['acc_trade_volume']
                    max_price[coin] = max(price, max_price[coin])
                    
                    if initialized[coin] == 0:
                        if price<0.01:
                            step[coin] = 0.000001
                        elif 0.01<=price<0.1:
                            step[coin] = 0.00001
                        elif 1<price<10:
                            step[coin] = 0.001
                        elif 10<=price<100:
                            step[coin] = 0.01
                        elif 100<=price<1000:
                            step[coin] = 0.1
                        elif 1000<=price<10000:
                            step[coin] = 1
                        elif 10000<=price<100000:
                            step[coin] = 10
                        elif 100000<=price<1000000:
                            step[coin] = 50
                        elif 1000000<=price:
                            step[coin] = 1000
                        LOG.info(f'updating step of {coin} to {step[coin]}')
                        initialized[coin] = 1

                    
                    #LOG.info(f'{coin}: max_price: {max_price[coin]}')
                    #LOG.info(f"current {coin} time_diff: {time_diff}")
                    
                    file_path = f'{data_path}/acc/{date}/{date}_{coin}_upbit_volume_{trial[coin]}.csv'
                    
                    
                    current_volume[coin]['acc_trade_volume'].append(data['acc_trade_volume'])
                    current_volume[coin]['time'].append(now)
                    current_volume[coin]['trade_price'].append(data['trade_price'])
                    
                    dev = 0
                    
                    if len(current_volume[coin]['time']) >= 2 and vol - current_volume[coin]['acc_trade_volume'][-2] >= 0:
                        vol_diff = vol - current_volume[coin]['acc_trade_volume'][-2]
                        inst_time_diff = now - current_volume[coin]['time'][-2]
                        dev = vol_diff/inst_time_diff
                        current_volume[coin]['dev'].append(dev)
                        #LOG.info(dev)
                    
                    #cLOG.info(current_volume[coin]['acc_trade_volume'])
                    
                    if len(current_volume[coin]['time']) > 1 and vol - current_volume[coin]['acc_trade_volume'][-2] < 0:
                        LOG.info('day has passed updating max_vol and start_price')
                        #max_vol[coin] = current_volume[coin]['acc_trade_volume'][-2]
                        inst_time_diff = now - current_volume[coin]['time'][-2]
                        dev = vol/inst_time_diff
                        current_volume[coin]['dev'].append(dev)
                        start_time = time.time()
                    
                    if status[coin] == 'SOLD' and now-beginning>1800:
                        #LOG.info(f'activating buy protocol: {coin} {max_price[coin]}')
                        balance, status, bought_time, bought_price, order, order_id = trader.scalp(
                                                                                coin, price, order_time, balance, 
                                                                                status, order, dev, max_dev, 
                                                                                max_price, order_id, bought_price, 
                                                                                initial_krw, bought_time, step)
                        
                    if dev>0.4*max_dev[coin]:
                        max_dev[coin] = max(dev, 0.8*max_dev[coin])
                        #LOG.info(f'{coin}: max_dev: {max_dev[coin]}')
                        
                        #LOG.info(f'updating max_dev for {coin} to {max_dev[coin]}')
                        # if now-beginning>3600 and len(current_volume[coin]['dev'])>20:
                        #     rawlist = current_volume[coin]['dev'][-20:]
                        #     sublist = np.array(rawlist) / np.linalg.norm(rawlist)
                        #     contains_nan = np.isnan(sublist)
                        #     ver = np.any(contains_nan)
                        #     if not ver:
                        #         signal = clf.predict([sublist])
                        #         probs = clf.predict_proba([sublist])
                        #         prob = probs[0,0]
                        #         LOG.info(f'running classifier coin: {coin} time: {now} price: {price} signal:{signal} prob: {prob}')
                        #         #LOG.info(f'coin: {coin} sublist: {sublist}')
                        #         #LOG.info(f'rawlist: {rawlist}')
                        #     else:
                        #         signal = [1]
                        #         prob = 0
                                
                    
                            #LOG.info(f'{coin} {signal}')
                            
                            
                    if bought_price[coin] != 0 and status[coin] == 'BUY':
                        profit = ((transaction*price)/bought_price[coin])-1
                    else:
                        profit = 0
                        
                    if status[coin] != "SOLD":
                        balance, status, bought_time, order, order_id, sold_price = trader.sell_protocol(
                                                                                balance, profit, status, coin,
                                                                                order, order_time, price, sold_price, 
                                                                                order_id, bought_time,
                                                                                bought_price, initial_krw)
            
                    #LOG.info('saving file')
                    df1 = pd.DataFrame(current_volume[coin])
                    #LOG.info(current_volume[coin] )
                    df1.to_csv(file_path)

                    if len(current_volume[coin]['time'])>1000:
                        root_path = f'{data_path}/acc/{date}/{date}_{coin}_upbit_volume.csv'
                        if trial[coin] == 0:
                            df = pd.DataFrame(current_volume[coin])
                            df.to_csv(root_path)
                        else:
                            df = pd.read_csv(root_path, index_col=0)
                            df = pd.concat([df, df1], ignore_index=True)
                            df.to_csv(root_path)
                        os.remove(file_path)
                        #LOG.info(f'removing trade_data and creating new file for {coin}')
                        trial[coin] += 1
                        current_volume[coin]['acc_trade_volume'] = current_volume[coin]['acc_trade_volume'][-1:]
                        current_volume[coin]['time'] = current_volume[coin]['time'][-1:]
                        current_volume[coin]['trade_price'] = current_volume[coin]['trade_price'][-1:]
                        current_volume[coin]['dev'] = current_volume[coin]['dev'][-1:]

                        
                    # if len(devs[coin]['time'])>1000:
                    #     root_path = f'{data_path}/acc/{date}/{date}_{coin}_upbit_dev.csv'
                    #     if trial1[coin] == 0:
                    #         df = pd.DataFrame(devs[coin])
                    #         df.to_csv(root_path)
                    #     else:
                    #         df = pd.read_csv(root_path, index_col=0)
                    #         df = pd.concat([df, dd], ignore_index=True)
                    #         df.to_csv(root_path)
                    #     os.remove(dev_path)
                    #     #LOG.info(f'removing trade_data and creating new file for {coin}')
                    #     trial1[coin] += 1
                    #     devs[coin]['time'] = devs[coin]['time'][-20:]
                    #     devs[coin]['dev'] = devs[coin]['dev'][-20:]

        except Exception as e:
            LOG.info('Current location in line 68')
            LOG.error(f'Error: {e}')
            await asyncio.sleep(1)
            LOG.info('return to the loop')

def binance_websocket(symbol:str, exchange_rate: int, price_data: list, time_data: list):
    def message(ws, message):
        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")
        data = json.loads(message)
        ask_price = float(data['a'])
        bid_price = float(data['b'])
        mid_price = (ask_price + bid_price) * exchange_rate / 2
        now = time.time()
        
        price_data.append(mid_price)
        time_data.append(now)

    def close(ws):
        print("WebSocket connection closed")

    url = f'wss://stream.binance.com:9443/ws/{symbol}@bookTicker'
    
    while True:
        try:
            ws = websocket.WebSocketApp(url, on_message=message, on_close=close)
            ws.run_forever()
        except Exception as e:
            LOG.error(f'Binance WebSocket error: {e}')
        finally:
            LOG.info(f'return to the LOOP for {symbol}')
            
async def binance_futures_trade(data: dict, coin: str, trial: dict):
    uri = f"wss://fstream.binance.com/ws/{coin}@trade"
    LOG.info('starting binance***********')  # Replace with your desired Binance Futures stream
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d")
    if not os.path.exists(f'{data_path}/future/{date}'):
        os.mkdir(f'{data_path}/future/{date}')
    async with websockets.connect(uri) as ws:
        while True:
            response = await ws.recv()
            res = json.loads(response)
            price  = float(res['p'])
            traded_volume = float(res['q'])
            now = time.time()
            
            data[coin]['price'].append(price)
            data[coin]['traded_volume'].append(traded_volume)
            data[coin]['time'].append(now)
            
            df = pd.DataFrame(
                    data[coin]
                )
            df.to_csv(f'{data_path}/future/{date}/{date}_binance_{coin}_{trial[coin]}.csv')
            
            if len(data[coin]['time']) > 5000:
                trial[coin] += 1
                data[coin]['price'] = []
                data[coin]['traded_volume'] = []
                data[coin]['time'] = []

async def upbit_ws(coins:list, upbit_orderbook:dict, upbit_trade:dict, 
    kind:str, balance:dict, step:dict,
    ordered_price:dict, max_sig: dict, min_sig: dict,
    trial:dict, order: dict, order_time: dict, order_id:dict, cutoff:dict, mode:str):
    uri = "wss://api.upbit.com/websocket/v1" 
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d")
    run_once = 0
    #date = '2023-12-27'
    #coins = list(step.keys())
    if not os.path.exists(f'{data_path}/{date}'):
        os.mkdir(f'{data_path}/{date}')
    while True:
        try:
            LOG.info(f'starting upbit for {coins}!!!')
            async with websockets.connect(uri) as ws:
                payload = [{"ticket": "your-ticket"}, {"type": kind, "codes": coins}]  
                await ws.send(json.dumps(payload))
                while True:
                    try:
                        response = await ws.recv()
                        data = json.loads(response)
                    except Exception as e:
                        LOG.info('Current location in line 105')
                        LOG.error(f'Error: {e}')
                        await asyncio.sleep(1)
                        break
                    #LOG.info('running')
                    now = time.time()
                    
                    coin = data['code']

                    file_path = f'{data_path}/{date}/{date}_{coin}_upbit_{kind}_{trade_trial[coin]}.csv'
                    current_price = data['trade_price']
                    if data['ask_bid'] == 'ASK':
                        sign = 1
                    elif data['ask_bid'] == 'BID':
                        sign = -1
                    asset = balance[coin][0] + (current_price-step[coin])*balance[coin][1]
                    upbit_trade[coin]['trade_price'].append(data['trade_price'])
                    upbit_trade[coin]['trade_volume'].append(sign*data['trade_volume'])     
                    upbit_trade[coin]['time'].append(now)
                    upbit_trade[coin]['asset'].append(asset)

                    df = pd.DataFrame(upbit_trade[coin])
                    df.to_csv(file_path)
                    
                    if trial[coin]>=1 and coin == 'KRW-STORJ':
                            current_momentum = sign*data['trade_volume']
                            #LOG.info(f'{coin} ready for trading {mode}')
                            momentum_trader = max_trade(coin)
                            balance[coin], asset, ordered_price[coin], order[coin], order_time[coin] =  momentum_trader.run(
                                coin, step[coin], current_price, ordered_price[coin],
                                max_mo[coin], min_mo[coin], current_momentum, balance[coin], currency[coin], 
                                order_time[coin], order[coin], order_id[coin], cutoff[coin]
                            )
                            
                    if len(upbit_trade[coin]['time'])>cutoff[coin][0]:
                        LOG.info('removing trade_data and creating new file')
                        momentum_list = df['trade_volume'].values
                        max_mo[coin] = max(max(momentum_list), 0.95*max_mo[coin])
                        min_mo[coin] = min(min(momentum_list), 0.95*min_mo[coin])
                        LOG.info(f'coin: {coin} max: {max_sig[coin]} min: {min_sig[coin]}')
                        trial[coin] += 1
                        upbit_trade[coin]['trade_price'] = upbit_trade[coin]['trade_price'][-1:]
                        upbit_trade[coin]['trade_volume'] = upbit_trade[coin]['trade_volume'][-1:]
                        upbit_trade[coin]['time'] = upbit_trade[coin]['time'][-1:]
                        upbit_trade[coin]['asset'] = upbit_trade[coin]['asset'][-1:]
                            
                    if asset<=1200000 and coin == 'KRW-STORJ' and run_once == 0:
                        LOG.info('too much loss selling everything')
                        terminate = max_trade(coin)
                        terminate.sell_everything(coin, current_price, step[coin])
                        run_once = 1
                        break
        except Exception as e:
            LOG.info('Current location in line 158')
            LOG.error(f'Error: {e}')
            await asyncio.sleep(1)

        finally:
            LOG.info('return to the loop')
            continue
            # except asyncio.exceptions.IncompleteReadError as e:
            #     LOG.error(f'IncompleteReadError: {e}')
            #     # Handle the IncompleteReadError here, for example, by reconnecting to the WebSocket
            #     # or taking other necessary actions.
            #     # You might want to add a sleep before retrying to avoid a busy loop.
            #     await asyncio.sleep(1)
            #     continue
            
        
                
                    
            
    
                

        
            
def check_and_restart_thread(thread, data_list, symbol, exchange_rate: int, price_data: list, time_data: list):
    last_length = 0  # Initialize the length of the data list
    while True:
        time.sleep(20)  # Wait for the specified timeout (e.g., 10 seconds)
        current_length = len(data_list)
        if current_length == last_length:
            LOG.info(f'*********restarting bynance {symbol}**************')
            # If the length hasn't increased, restart the thread
            print("Restarting the thread...")
            thread.join()  # Wait for the existing thread to finish
            thread = threading.Thread(target=binance_websocket, args=(symbol, exchange_rate, price_data, time_data))  # Create a new thread
            thread.start()  # Start the new thread
        last_length = current_length  # Update the last length
        
def cancel_order(coins, orders, order_times, currency):
    for coin in coins:
        now = time.time()
        if now - order_times[coin] > 100 and order_times[coin] != 0:
            trade_fast.cancel_order(orders[coin]['uuid'], currency[coin])
            
def transform_currency_pair(input_str):
    if isinstance(input_str, str) and '-' in input_str:
        base_currency, quote_currency = input_str.split('-')
        return f"{quote_currency}/{base_currency}"
    else:
        return "Invalid input format"

async def main(coins: dict, upbit_orderbook:dict, upbit_trade:dict, kind:str, 
               balance:dict, step:dict, ordered_price:dict, max_mo: dict, 
               min_mo: dict,upbit_trial:dict, order: dict, order_time: dict, order_id:dict, 
               data: dict, binance_coin: str, bin_trial: dict, cutoff:dict,
               coins2:list, current_volume:dict, trial2: dict):
    
    await asyncio.gather(
        #binance_futures_trade(data, binance_coin, bin_trial), 
        get_current_volume(coins2, current_volume, trial2),
        upbit_ws(coins, upbit_orderbook, upbit_trade, kind, balance, step, ordered_price,
                max_mo, min_mo,upbit_trial, order, order_time, order_id, cutoff, 'test'))
        

if __name__ == '__main__':
    LOG.info('hi')
    coins = pyupbit.get_tickers(fiat="KRW")
    df = {}
    yesteday = {}
    past_raw = {}
    LOG.info(coins)

    
    # for ticker in tickers:
    #     df[ticker] = pyupbit.get_ohlcv(ticker=ticker, count=2)

    #     if df[ticker] is not None:
    #         yesteday[ticker] = df[ticker]['volume'].values[0]*df[ticker]['close'].values[0]
    #         LOG.info(df[ticker]['volume'])
    #         past_raw[ticker] = df[ticker]['volume'].values[0]

    #LOG.info(yesteday)
    # sorted_dict = dict(sorted(yesteday.items(), key=lambda item: item[1], reverse=True))
    # top_values = dict(list(sorted_dict.items())[:30])
    #LOG.info(top_values)
        
    #coins = list(top_values.keys())
    #coins = list(past_raw.keys())
    # coins.remove('KRW-BTT')
    #LOG.info(coins)
    #past = {coin: past_raw[coin] for coin in coins}
    #LOG.info(past)
   
    step = {coin: 0.5 for coin in coins}
    #coins = list(step.keys())

    upbit_orderbook = {coin:  {'ask1_price': [], 'ask1_volume': [],  
            'ask2_price': [], 'ask2_volume': [],  
            'bid1_price': [], 'bid1_volume': [],  
            'bid2_price': [], 'bid2_volume': [],  
            'time': []} for coin in coins}
    
    upbit_trade = {coin: {'trade_price': [], 'trade_volume': [], 
                          'time': [], 'asset': []} 
                   for coin in coins}
    
    binance_coin = ['storjusdt']
    binance_data = {coin: {'price': [], 'traded_volume': [], 
                          'time': []} 
                   for coin in binance_coin}
    
    binance_trial = {coin: 0 for coin in binance_coin}
    starting_balance = 10000
    balance = {coin: [starting_balance, 0] for coin in coins}
    balance['KRW-STORJ'] = [1300000, 0]
    

    
    
    trade_trial = {coin: 0 for coin in coins}

    
    ordered_price = {coin: 0 for coin in coins}
    #ordered_price['KRW-STORJ'] = 1170
    order_id = {key: {'uuid': []} for key in ordered_price.keys()}
    ordered_time = {key: [0, 'null'] for key in ordered_price.keys()}

    
    max_mo = {key: 0 for key in upbit_trade.keys()}
    min_mo = {key: 0 for key in upbit_trade.keys()}


    
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    date = '2023-11-30'


    currency = {coin: transform_currency_pair(coin) for coin in coins}



    tickers = pyupbit.get_tickers(fiat="KRW")
    df = {}
    yesteday = {}


    
    current_volume = {coin: {'time': [], 'acc_trade_volume': [], 'trade_price': [], 'dev': [0]} for coin in coins}
    devs = {coin: {'time': [], 'dev': []} for coin in coins}
    
    max_dev = {coin: 0 for coin in coins}
    max_price = {coin: 0 for coin in coins}
    
    status = {coin: 'SOLD' for coin in coins}
    start_time = {coin: time.time() for coin in coins}
    order = {coin: [] for coin in coins}
    bought_time = {coin: 0 for coin in coins}
    balance = {'KRW': 1000000}
    
    sold = {coin: 1 for coin in coins}
    bought_price = {coin: 0 for coin in coins}
    sold_price = {coin: 0 for coin in coins}
    max_dev = {coin: 0 for coin in coins}
    order_time = {coin: 0 for coin in coins}
    order_id = {coin:  {'state': 'null'} for coin in coins}
    
    key_u=config('API_U')
    secret_u=config('KEY_U')
    
    upbit = pyupbit.Upbit(key_u, secret_u)
    initial_krw = upbit.get_balance('KRW')
    LOG.info(f'initial krw: {initial_krw}')

    

    trial2 = {coin: 0 for coin in coins}

    

    asyncio.run(get_current_volume(
        coins, current_volume, trial2, 
        balance, status, bought_time, order,
        bought_price, order_id, sold_price, order_time,
        max_dev, max_price, initial_krw
        ))


    LOG.info('the end')
 

    
    
        
           
