from tqsdk2 import TqApi, TqAuth, TqSim, TqRohon
from utils.trade_utils import wait_to_trade
from pymongo import MongoClient
import os
from datetime import datetime
import time
import logging

mongo_host = os.environ['MONGO_HOST']
mongo_user = os.environ['MONGO_ADMINUSERNAME']
mongo_pasw = os.environ['MONGO_ADMINPASSWORD']
mongo_port = os.environ['MONGO_PORT']


def trade(trade_type: int):
    logger = logging.getLogger(__name__)
    mongo_url = (f'mongodb://{mongo_user}:{mongo_pasw}'
                 f'@{mongo_host}:{mongo_port}/')
    api = TqApi(get_test_acc(), auth=TqAuth("galahade", "211212"))
    logger.info(f'账户信息:{api.get_account()}')
    client = MongoClient(mongo_url)
    db = client.get_database('future_trade')
    wait_to_trade(api, trade_type, db)


def get_rohon_acc():
    td_url = "tcp://139.196.40.170:11001"
    broker_id = "RohonReal"
    app_id = "MQT_MQT_1.0"
    auth_code = "mVuQfsHT3qbTBEYV"
    user_name = "wxlg018"
    password = "345678"
    return TqRohon(td_url, broker_id, app_id, auth_code, user_name, password)


def get_test_acc():
    return TqSim()


def test_order(api):
    logger = logging.getLogger(__name__)
    logger.debug("Start test order")
    order = api.insert_order(
        symbol="DCE.p2301", direction="BUY", offset="OPEN",
        limit_price=100, volume=1)
    order_time = datetime.now()
    while order.status != "FINISHED":
        api.wait_update()
        time.sleep(5)
        now = datetime.now()
        logger.debug(
            "委托单状态: %s, 未成交手数: %d 手" % (order.status, order.volume_left))
        if (now - order_time).seconds > 600:
            api.cancel_order(order)
