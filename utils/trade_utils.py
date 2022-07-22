import logging
from tqsdk import TqApi
from utils.tools import Trade_Book
from trade.trades import Future_Trade_Util


def get_logger():
    return logging.getLogger(__name__)


# 调用该方法执行交易策略，等待合适的交易时机进行交易。
# api：天勤量化api对象，ftu：主力合约交易对象
def wait_to_trade(api: TqApi, zl_symbol: str, trade_book: Trade_Book) -> None:
    logger = get_logger()
    ftu = Future_Trade_Util(api, zl_symbol, trade_book)
    logger.debug("准备开始交易，调用天勤接口，等待交易时机")
    while True:
        api.wait_update()
        ftu.start_trading()
