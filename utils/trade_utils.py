import logging
from tqsdk2 import TqApi
import dao.mongo_dao as mongo_dao
from trade.broker import Future_Trade_Broker
import yaml
from pymongo import database


def get_logger():
    return logging.getLogger(__name__)


# 调用该方法执行交易策略，等待合适的交易时机进行交易。
# api：天勤量化api对象，ftu：主力合约交易对象
def wait_to_trade(api: TqApi, trade_type: int, db: database.Database) -> None:
    logger = get_logger()
    trade_config = get_trade_config()
    ftu_list = []
    symbols_config = trade_config['rules']
    mongo_dao.db = db
    for symbol_config in symbols_config:
        if symbol_config['is_active']:
            ftu = Future_Trade_Broker(api, symbol_config, trade_type)
            ftu_list.append(ftu)
    logger.debug("准备开始交易，调用天勤接口，等待交易时机")
    api.wait_update()
    logger.debug("天勤服务器端已更新，开始交易日工作")

    while True:
        # logger.debug("before wait update")
        api.wait_update()
        # logger.debug("after wait update")
        for ftu in ftu_list:
            ftu.daily_opration()


def get_trade_config() -> dict:
    with open('conf/trade_config.yaml', 'r') as f:
        trade_config = yaml.safe_load(f.read())
        return trade_config
