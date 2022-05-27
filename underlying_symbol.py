
from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished, \
        TargetPosTask
from tools import examine_one_symbol
from datetime import date

acc = TqSim()

api = TqApi(acc, web_gui=":10000",
            backtest=TqBacktest(start_dt=date(2020, 1, 1),
                                end_dt=date(2022, 5, 24)),
            auth=TqAuth("galahade", "wombat-gazette-pillory"))

symbol = "KQ.m@SHFE.rb"
quote = api.get_quote(symbol)


try:
    while True:
        api.wait_update()
        if api.is_changing(quote, "underlying_symbol"):
            print(quote.datetime, examine_one_symbol(quote.underlying_symbol))
except BacktestFinished:
    api.close()
