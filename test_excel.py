from trade.trades import Trade_Status_Long
import logging
from utils.common import setup_log_config


# logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    setup_log_config('DEBUG')
    logger = logging.getLogger(__name__)
    position = []
    quote = []
    symbol = ''
    tb = None
    ts = Trade_Status_Long(position, symbol, quote, tb)
    if 20.08 < ts.calc_price(20, True, 1):
        print("success")
    print(ts.calc_price(20, True, 1))
