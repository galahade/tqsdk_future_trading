from tqsdk import TqApi, TqAuth
import datetime

api = TqApi( #            backtest=TqBacktest(start_dt=start_time, end_dt=end_time),
            auth=TqAuth("galahade", "wombat-gazette-pillory"))
ls = api.query_quotes(ins_class="FUTURE", product_id="rb")
# quote_near = api.get_quote("SHFE.rb2104")
quote_near = api.get_quote("DCE.i1805")
print(quote_near.delivery_month)
print(quote_near.instrument_id)
print(quote_near.instrument_name)
print(quote_near.volume_multiple)

try:
    api.wait_update()

except Exception:
    api.close()
