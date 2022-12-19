import os
from utils import common
import sys
import logging
from trading_department.managers import Manager

now = common.now
is_back_test = False
start_year = now.year
start_month = 1
end_year = now.year
log_level = "info"
trade_type = 2
env_name = os.environ['ENV_NAME']


def main():
    try:
        common.get_argumets()
        log_config_file = f'log_config_{env_name}'
        common.setup_log_config(log_level, log_config_file)
        logger = logging.getLogger(__name__)
        manager = Manager(trade_type, is_back_test, start_year,
                          start_month, end_year)
        manager.start_trading()
    except Exception as e:
        logger.exception(e)
        return str(e)


if __name__ == "__main__":
    sys.exit(main())
