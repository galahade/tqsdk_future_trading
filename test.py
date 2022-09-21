from tqsdk import TqApi, TqAuth, TqKq

api = TqApi(TqKq(), auth=TqAuth("galahade", "211212"))
ts = api.get_trading_status("DCE.p2301")
klines = api.get_kline_serial("DCE.p2301", 60*60*24)
zl_quote = api.get_quote("KQ.m@DCE.i")
while True:
    api.wait_update
    if api.is_changing(zl_quote, "datetime"):
        print(f'trade status is: {ts.trade_status}')
        print(f'trade time is: {klines.iloc[-1].datetime}')
