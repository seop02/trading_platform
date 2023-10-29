import logging
import random

logging.basicConfig(level=logging.WARNING)
logging.getLogger().setLevel(logging.INFO)
LOG = logging.getLogger(__name__)

class trade_simulator():
    def __init__(
        self, price_data:list, time_data:list, 
        upbit_data:dict, step: int,
        n: int, currency:str):
        self.price_data = price_data
        self.time_data = time_data
        self.upbit_price = upbit_data[currency]
        self.upbit_time = upbit_data[currency+'_time']
        self.n = n
        self.currency = currency
        self.step = step
        
    def simulate(self, balance):
        initial_asset = balance[0]
        condition = random.randint(0, 1)
        if len(self.upbit_price) > self.n:
 
            LOG.info(f'currency: {self.currency}')

            upbit_price = self.upbit_price[-1]
            ordered_price = 0
            #Enter buying condition here
            if condition == 0:
                LOG.info(f'----------------{self.currency}---------------------')
                LOG.info(f'BOUGHT price is {upbit_price}')
                amount = 0.9995*upbit_price/(balance[0]+self.step)
                balance = [0, amount]
                ordered_price = upbit_price
                profit = balance[0] + balance[1]*(upbit_price-self.step) - initial_asset
                LOG.info(f'current profit is {profit}')
                LOG.info('-------------------------------------------------')
            #Enter selling condition here
            elif condition == 1:
                LOG.info(f'******************{self.currency}**********************')

                LOG.info(f'SOLD price is {upbit_price}')
                amount = 0.9995*upbit_price*balance[1]
                balance = [amount, 0]
                ordered_price = upbit_price
                profit = balance[0] + balance[1]*(upbit_price-self.step) - initial_asset
                LOG.info(f'current profit is {profit}')
                LOG.info('*************************************************')