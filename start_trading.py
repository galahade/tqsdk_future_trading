from tqsdk2 import TqApi, TqAuth, TqSim, TqRohon
from utils.trade_utils import wait_to_trade
from utils.tools import get_yaml_config, send_msg
from pymongo import MongoClient
import os
from datetime import datetime
import time
import logging

mongo_conf_file = os.environ['MONGO_CONF_FILE']
rohon_conf_file = os.environ['ROHON_CONF_FILE']
tq_conf_file = os.environ['TQ_CONF_FILE']

mongo_conf = get_yaml_config(mongo_conf_file)
rohon_conf = get_yaml_config(rohon_conf_file)
tq_conf = get_yaml_config(tq_conf_file)

mongo_host = mongo_conf['mongo']['host']
mongo_user = mongo_conf['mongo']['user']
mongo_pasw = mongo_conf['mongo']['password']
mongo_port = mongo_conf['mongo']['port']
tq_user = tq_conf['tq']['user']
tq_pass = tq_conf['tq']['password']


def trade(trade_type: int):
    logger = logging.getLogger(__name__)
    mongo_url = (f'mongodb://{mongo_user}:{mongo_pasw}'
                 f'@{mongo_host}:{mongo_port}/')
    api = TqApi(get_test_acc(), auth=TqAuth(tq_user, tq_pass))
    logger.info(f'账户信息:{api.get_account()}')
    client = MongoClient(mongo_url)
    db = client.get_database('future_trade')
    send_msg('future trade', 'Start to trade')
    wait_to_trade(api, trade_type, db)


def get_rohon_acc():
    td_url = rohon_conf['rohon']['url']
    broker_id = rohon_conf['rohon']['broker_id']
    app_id = rohon_conf['rohon']['app_id']
    auth_code = rohon_conf['rohon']['auth_code']
    user_name = rohon_conf['rohon']['user_name']
    password = rohon_conf['rohon']['password']
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
