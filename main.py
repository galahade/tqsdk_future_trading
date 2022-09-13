from utils import common
import sys
import logging
import backtest
import start_trading

now = common.now
is_back_test = False
start_year = now.year
start_month = 1
end_year = now.year
log_level = "warning"
trade_type = 2


def main():
    try:
        common.get_argumets()
        common.setup_log_config(log_level)
        logger = logging.getLogger(__name__)
        if is_back_test:
            logger.debug("开始进行回测")
            backtest.trade(trade_type, start_year, start_month, end_year)
        else:
            logger.debug("开始进行正式交易")
            start_trading.trade(trade_type)
    except Exception as e:
        logger.exception(e)
        return str(e)


if __name__ == "__main__":
    sys.exit(main())
