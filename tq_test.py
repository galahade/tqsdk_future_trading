# from datetime import date
# from tqsdk import TqApi, TqAuth, TqBacktest, BacktestFinished

# api = TqApi(backtest=TqBacktest(start_dt=date(2020, 1, 1),
#                                 end_dt=date(2020, 10, 1)),
#             auth=TqAuth("galahade", "211212"))
# print(api.get_quote("SHFE.rb1805"))
# quote = api.get_quote("KQ.m@DCE.i")
# print(quote.datetime, quote.underlying_symbol)
# try:
#     while True:
#         api.wait_update()
#         if api.is_changing(quote, "underlying_symbol"):
#             print(quote.datetime, quote.underlying_symbol)
# except BacktestFinished:
#     api.close()

from tqsdk import TqApi, TqAuth, tafunc
# From tqsdk.ta import EMA, MACD

api = TqApi(auth=TqAuth("galahade", "211212"))
h3_klines = api.get_kline_serial("SHFE.sn2311", 3 * 60 * 60)
i = 1
for _, kline in h3_klines[::-1].iterrows():
    print(tafunc.time_to_datetime(kline.datetime))
    i += 1
    if i > 9:
        break
# print(h3_klines.iloc[::-1])
api.close()