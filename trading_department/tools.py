import os
from tqsdk import TqAuth, TqSim
# from tqsdk2 import TqRohon, TqAuth, TqSim
from utils.tools import get_yaml_config, sendSystemStartupMsg
from utils.common import LoggerGetter
from utils.future_config_utils import prepare_future_configs
from pymongo import MongoClient
import uuid
from datetime import date, datetime
import logging
import dao.dao_service as dao_service
from trading_department.brokers import LongTermTradeBrokerManager


ACCOUNT_TYPE = int(os.environ['ACCOUNT_TYPE'])
ACCOUNT_BALANCE = int(os.getenv('ACCOUNT_BALANCE', '10000000'))


def get_logger():
    return logging.getLogger(__name__)


def get_mongo_conf() -> dict:
    return get_yaml_config(os.environ['MONGO_CONF_FILE'])


def get_rohon_conf() -> dict:
    return get_yaml_config(os.environ['ROHON_CONF_FILE'])


def get_tq_conf() -> dict:
    return get_yaml_config(os.environ['TQ_CONF_FILE'])


class StorageTool:
    logger = LoggerGetter()

    def __init__(self, is_backtest=False):
        logger = self.logger
        mongo_conf = get_mongo_conf()
        host = mongo_conf['mongo']['host']
        user = mongo_conf['mongo']['user']
        password = mongo_conf['mongo']['password']
        port = mongo_conf['mongo']['port']
        url = (f'mongodb://{user}:{password}@{host}:{port}/')
        self.db_client = MongoClient(url)
        self.uid = str(uuid.uuid4())
        self.is_backtest = is_backtest
        if self.is_backtest:
            logger.info(f'Test db name is {self.uid}')

    def get_db(self):
        if self.is_backtest:
            return self.db_client.get_database(self.uid)
        return self.db_client.get_database('future_trade')


class AuthTool:
    def __init__(self):
        # rohon_conf = get_rohon_conf()
        tq_conf = get_tq_conf()
        # td_url = rohon_conf['rohon']['url']
        # broker_id = rohon_conf['rohon']['broker_id']
        # app_id = rohon_conf['rohon']['app_id']
        # auth_code = rohon_conf['rohon']['auth_code']
        # user_name = rohon_conf['rohon']['user_name']
        # password = rohon_conf['rohon']['password']
        # self._rohon_account = TqRohon(td_url, broker_id, app_id, auth_code,
        #                              user_name, password)
        self._test_account = TqSim(init_balance=ACCOUNT_BALANCE)
        self.tq_auth = TqAuth(tq_conf['tq']['user'],
                              tq_conf['tq']['password'])

    def get_account(self):
        if ACCOUNT_TYPE == 0:
            return self._test_account
        elif ACCOUNT_TYPE == 1:
            return self._rohon_account

    def is_just_check(self):
        return ACCOUNT_TYPE == 0


class BackTestTool:
    """
    回测用到的各种数据和方法统一在这个类中管理
    """
    def __init__(self, s_year, s_month, end_year, storageTool):
        self.start_date = date(s_year, s_month, 1)
        self.end_date = date(end_year, 12, 31)
        self.account = TqSim()
        prepare_future_configs('trade_config_backtest.yaml',
                               storageTool.get_db())


class TradeTool:
    logger = LoggerGetter()

    def __init__(self, direction, storageTool):
        self.direction = direction
        self.service = dao_service.DBService(storageTool.get_db())

    def start_trading(self, api, just_check=False, is_backtest=False):
        logger = self.logger
        future_configs = self.service.get_future_configs()
        ftu_list = [LongTermTradeBrokerManager(
            api, fc, self.direction, just_check, self.service, is_backtest)
                    for fc in future_configs]
        sendSystemStartupMsg(datetime.now())
        logger.debug("准备开始交易.")
        api.wait_update()
        logger.debug("天勤服务器端已更新，开始交易日工作")

        while True:
            api.wait_update()
            for ftu in ftu_list:
                ftu.daily_opration()
