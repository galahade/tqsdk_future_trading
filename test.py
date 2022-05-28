from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished, \
        TargetPosTask
from datetime import date
from tools import Underlying_symbol_trade

acc = TqSim()

api = TqApi(acc, web_gui=":10000",
                backtest=TqBacktest(start_dt=date(2021, 8, 18),
                                    end_dt=date(2022, 5, 24)),
            auth=TqAuth("galahade", "wombat-gazette-pillory"))

symbol = "KQ.m@SHFE.rb"
quote = api.get_quote(symbol)
daily_klines = api.get_kline_serial(symbol, 60*60*24)
underlying_symbol_trade = Underlying_symbol_trade(api, symbol)
try:
    while True:
        api.wait_update()
        if api.is_changing(quote, "underlying_symbol"):
            underlying_symbol_trade.switch_contract()
        # if api.is_changing(quote, "underlying_symbol"):
except BacktestFinished:
    api.close()
