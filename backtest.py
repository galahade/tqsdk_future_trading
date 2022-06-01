from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished
from datetime import date
from tools import Underlying_symbol_trade, wait_to_trade
import logging


logger = logging.getLogger(__name__)
acc = TqSim()


def trade(start_year, end_year):
    try:
        api = TqApi(acc, web_gui=":10000",
                    backtest=TqBacktest(start_dt=date(start_year, 1, 1),
                                        end_dt=date(end_year, 12, 31)),
                    auth=TqAuth("galahade", "wombat-gazette-pillory"))
        # symbol = "SHFE.rb2210"
        # symbol = "DCE.a2207"
        symbol = "KQ.m@SHFE.rb"
        # week_klines = api.get_kline_serial(symbol, 60*60*24*5)
        account = api.get_account()
        rb_trade = Underlying_symbol_trade(api, symbol, account)
        wait_to_trade(api, rb_trade)

    except BacktestFinished:
    #    api.close()
        # 打印回测的详细信息
        # print("trade log:", acc.trade_log)

        # 账户交易信息统计结果
        # print("tqsdk stat:", acc.tqsdk_stat)
        while True:
            api.wait_update()
