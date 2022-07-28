import logging
from utils.common import setup_log_config, TradeConfigGetter
import yaml


# logging.basicConfig(level=logging.INFO)

class Test:

    profit_start_scale_1 = TradeConfigGetter()

    def __init__(self, config: dict):
        self._rules = config['long']
        self._mains = config['main_list']

    def get_current_month(self):
        return 10

    def get_current_year(self):
        return 22

    def get_next_symbol(self):
        next_index = self._mains.index(test.get_current_month()) + 1
        symbol_year = self.get_current_year()
        if next_index >= len(self._mains):
            next_index = 0
        if next_index == 0:
            symbol_year += 1
        symbol_month = self._mains[next_index]
        return f'{symbol_year}{symbol_month:02}'



if __name__ == '__main__':
    setup_log_config('DEBUG')
    logger = logging.getLogger(__name__)

    with open('utils/trade_config.yaml', 'r') as f:
        trade_config = yaml.safe_load(f.read())
        symbols_config = trade_config['rules']
        for symbol_config in symbols_config:
            if symbol_config['is_active']:
                test = Test(symbol_config)
                print(symbol_config['symbol'])
                print(test._mains)
                print(test.get_next_symbol())
