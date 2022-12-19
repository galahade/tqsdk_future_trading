from datetime import date
from tqsdk import TqApi, TqAuth, TqBacktest, BacktestFinished

api = TqApi(backtest=TqBacktest(start_dt=date(2020, 1, 1),
                                end_dt=date(2020, 10, 1)),
            auth=TqAuth("galahade", "211212"))
print(api.get_quote("SHFE.rb1805"))
quote = api.get_quote("KQ.m@DCE.i")
print(quote.datetime, quote.underlying_symbol)
try:
    while True:
        api.wait_update()
        if api.is_changing(quote, "underlying_symbol"):
            print(quote.datetime, quote.underlying_symbol)
except BacktestFinished:
    api.close()
