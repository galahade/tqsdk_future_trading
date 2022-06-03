from utils import common
import sys
import logging
import backtest

now = common.now
is_back_test = False
start_year = now.year
end_year = now.year
log_level = "warning"


def main():
    try:
        common.get_argumets()
        common.setup_log_config(log_level)
        logger = logging.getLogger(__name__)
        if is_back_test:
            logger.debug("开始进行回测")
            backtest.trade(start_year, end_year)
        else:
            logger.debug("开始进行正式交易")
    except Exception as e:
        logger.exception(e)
        return str(e)


if __name__ == "__main__":
    sys.exit(main())
