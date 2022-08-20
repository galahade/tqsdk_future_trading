from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished
from datetime import date
from utils.trade_utils import wait_to_trade
import logging


acc = TqSim()


def trade(start_year, start_month, end_year):
    logger = logging.getLogger(__name__)
    start_time = date(start_year, start_month, 1)
    end_time = date(end_year, 12, 31)

    logger.debug(f"回测开始日期：{start_time} 结束日期：{end_time}")
    try:
        # api = TqApi(acc,
        api = TqApi(acc, web_gui=":10000",
                    backtest=TqBacktest(start_dt=start_time, end_dt=end_time),
                    auth=TqAuth("galahade", "211212"))
        wait_to_trade(api)

    except BacktestFinished:
        logger.info(f"回测完成:结束时间:{end_time}")
        # api.close()
        # 打印回测的详细信息
        # print("trade log:", acc.trade_log)

        # 账户交易信息统计结果
        # print("tqsdk stat:", acc.tqsdk_stat)
        while True:
            api.wait_update()
