from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished
from datetime import date
from utils.trade_utils import wait_to_trade
import logging
from pymongo import MongoClient
import uuid


acc = TqSim()


def trade(trade_type, start_year, start_month, end_year):
    logger = logging.getLogger(__name__)
    start_time = date(start_year, start_month, 1)
    end_time = date(end_year, 12, 31)

    logger.debug(f"回测开始日期：{start_time} 结束日期：{end_time}")
    try:
        # api = TqApi(acc,
        api = TqApi(acc, web_gui=":10000",
                    backtest=TqBacktest(start_dt=start_time, end_dt=end_time),
                    auth=TqAuth("galahade", "211212"))
        client = MongoClient('mongodb://root:example@localhost:27017/')
        uid = str(uuid.uuid4())
        # uid = '9ab5e9c3-331a-44a8-b916-08b585d3ceaf'
        db = client.get_database(uid)
        wait_to_trade(api, trade_type, db)

    except BacktestFinished:
        logger.info(f"回测完成:结束时间:{end_time}")
        # api.close()
        # 打印回测的详细信息
        # print("trade log:", acc.trade_log)

        # 账户交易信息统计结果
        # print("tqsdk stat:", acc.tqsdk_stat)
        while True:
            api.wait_update()
