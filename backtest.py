from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished
from datetime import date
from tools import calc_indicator, Underlying_symbol_trade


acc = TqSim()

try:
    api = TqApi(acc, web_gui=":10000",
                backtest=TqBacktest(start_dt=date(2021, 8, 18),
                                    end_dt=date(2022, 5, 24)),
                auth=TqAuth("galahade", "wombat-gazette-pillory"))
    # symbol = "SHFE.rb2210"
    # symbol = "DCE.a2207"
    symbol = "KQ.m@SHFE.rb"
    # week_klines = api.get_kline_serial(symbol, 60*60*24*5)
    rb_trade = Underlying_symbol_trade(api, symbol)

    account = api.get_account()

    while True:
        api.wait_update()
        # 处理更换主力合约问题
        if api.is_changing(rb_trade.quote, "underlying_symbol"):
            rb_trade.switch_contract()
        if api.is_changing(rb_trade.m30_klines.iloc[-1], "datetime"):
            calc_indicator(rb_trade.m30_klines)
        if api.is_changing(rb_trade.daily_klines.iloc[-1], "datetime"):
            calc_indicator(rb_trade.daily_klines)

        if api.is_changing(rb_trade.quote, "last_price"):
            rb_trade.open_volumes(account)
            rb_trade.upgrade_stop_loss_price()
            rb_trade.try_stop_loss()

    while True:
        api.wait_update()


except BacktestFinished:
#    api.close()
    # 打印回测的详细信息
    # print("trade log:", acc.trade_log)

    # 账户交易信息统计结果
    # print("tqsdk stat:", acc.tqsdk_stat)
    while True:
        api.wait_update()
