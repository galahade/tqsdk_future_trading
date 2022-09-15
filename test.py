from tqsdk import TqApi, TqAuth, TqKq

api = TqApi(TqKq(), auth=TqAuth("galahade", "211212"))
ts = api.get_trading_status("DCE.p2301")
api.wait_update
print(f'trade status is: {ts.trade_status}')
