from trade.trades import Trade_Status_Long
import logging
from utils.common import setup_log_config


# logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    setup_log_config('DEBUG')
    logger = logging.getLogger(__name__)
    position = []
    quote = []
    ts = Trade_Status_Long(position, quote)
    print(ts.calc_price(20, True, 1))
