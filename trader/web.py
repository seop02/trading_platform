import json
import time
import logging
import threading 
import websocket
import multiprocessing as mp
import pyupbit
from trade_simulator import trade_simulator
import pandas as pd
from __init__ import data_path
import datetime
import os

logging.basicConfig(level=logging.WARNING)
logging.getLogger().setLevel(logging.INFO)
LOG = logging.getLogger(__name__)

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
       
def upbit_websocket(coins:list, upbit_data:dict):
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d")
    queue_u = mp.Queue()
    proc = mp.Process(
        target=pyupbit.WebSocketClient,
        args=('orderbook', coins, queue_u),
        daemon=True
    )
    proc.start()
    time1 = coins[0] + '_time'
    time2 = coins[1] + '_time'
    while True:
        data = queue_u.get()
        for coin in coins: 
            # LOG.info(f'*************{coin}**************')
            # LOG.info(data)
            if coin == data['code']:
                #ask_price = data['orderbook_units'][0]['ask_price']
                #bid_price = data['orderbook_units'][0]['bid_price']
                now = time.time()
                
                file_path = f'{data_path}/{date}_{coin}_upbit_data.json'
                if not os.path.exists(file_path):
                    #LOG.info(f'screating json for {coin}')
                    upbit_data[coin]['orderbook'].append(data['orderbook_units'])
                    upbit_data[coin]['time'].append(now)
                    with open(file_path, "w") as json_file:
                        json.dump(upbit_data[coin], json_file)
                    time.sleep(2)
                else:
                    #LOG.info('loading json file')
                    #LOG.info(file_path)
                    with open(file_path, 'r') as file:
                        upbit_new = json.load(file)
                        
                    #LOG.info('json loaded')
                    upbit_new['orderbook'].append(data['orderbook_units'])
                    upbit_new['time'].append(now)
                    
                    upbit_data[coin]['orderbook'].append(data['orderbook_units'])
                    upbit_data[coin]['time'].append(now)
                    
                    with open(file_path, "w") as json_file:
                        json.dump(upbit_new, json_file)
                        
                    if len(upbit_data[coin]['orderbook'])>1000:
                        upbit_data[coin]['orderbook'].pop(0)
                        upbit_data[coin]['time'].pop(0)
                    n = len(upbit_data[coin]['orderbook'])
                    LOG.info(f'current file size: {n}')
                        
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
            

if __name__ == '__main__':
    upbit_data = {
        'KRW-STORJ': {'orderbook': [], 'time': []}, 
        'KRW-STX': {'orderbook': [], 'time': []},
        'KRW-GAS': {'orderbook': [], 'time': []},
        'KRW-ARK': {'orderbook': [], 'time': []},
        'KRW-LOOM': {'orderbook': [], 'time': []},
        'KRW-XRP': {'orderbook': [], 'time': []}
    }
    
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d")
    
    coins = ['KRW-STORJ', 'KRW-STX', 'KRW-GAS', 'KRW-ARK', 'KRW-LOOM']
    stx_b = 'stxusdt'
    storj_b = 'storjusdt'
    
    storj_krw = []
    storj_timek = []
    
    stx_krw = []
    stx_timek = []
    
    storj_price = []
    storj_time = []
    
    stx_price = []
    stx_time = []
    i = 0
    j = 0
    
    storj_balance = [100,0]
    stx_balance = [100,0]
    
    storj_ordered = 0
    stx_ordered = 0
    
    exchange_rate = 1350
    
    upbit_websocket(coins, upbit_data)
   
        
           
