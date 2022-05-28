from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished, \
        TargetPosTask
from datetime import date

acc = TqSim()

api = TqApi(acc, web_gui=":10000",
            auth=TqAuth("galahade", "wombat-gazette-pillory"))

symbol = "KQ.m@SHFE.rb"
quote = api.get_quote(symbol)
daily_klines = api.get_kline_serial(symbol, 60*60*24)

try:
    while True:
        api.wait_update()
        # if api.is_changing(quote, "underlying_symbol"):
            # print(quote.datetime, examine_one_symbol(quote.underlying_symbol))
except BacktestFinished:
    api.close()
