import logging
from tqsdk import TqApi, BacktestFinished
from utils.tools import Trade_Book
from trade.trades import Future_Trade_Util
import yaml


def get_logger():
    return logging.getLogger(__name__)


# 调用该方法执行交易策略，等待合适的交易时机进行交易。
# api：天勤量化api对象，ftu：主力合约交易对象
def wait_to_trade(api: TqApi) -> None:
    logger = get_logger()
    trade_config = get_trade_config()
    ftu_list = []
    symbols_config = trade_config['rules']
    tb = Trade_Book()
    for symbol_config in symbols_config:
        if symbol_config['is_active']:
            trade_sheet = tb.create_sheet(symbol_config['symbol'])
            ftu = Future_Trade_Util(api, symbol_config, trade_sheet)
            ftu_list.append(ftu)
    logger.debug("准备开始交易，调用天勤接口，等待交易时机")

    try:
        while True:
            api.wait_update()
            for ftu in ftu_list:
                ftu.start_trading()

    except BacktestFinished:
        try:
            tb.finish()
        finally:
            raise BacktestFinished(api)


def get_trade_config() -> dict:
    with open('utils/trade_config.yaml', 'r') as f:
        trade_config = yaml.safe_load(f.read())
        return trade_config
