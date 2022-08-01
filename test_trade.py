from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished,\
        TargetPosTask, tafunc
from datetime import date
from utils.tools import is_nline, is_decline_2p
acc = TqSim()
start_time = date(2018, 5, 1)
end_time = date(2018, 9, 6)
api = TqApi(acc, backtest=TqBacktest(start_dt=start_time, end_dt=end_time),
            auth=TqAuth("galahade", "wombat-gazette-pillory"))
# quote_near = api.get_quote("SHFE.rb2104")
symbol = "DCE.i1901"
quote = api.get_quote(symbol)
daily_klines = api.get_kline_serial(symbol, 60 * 60 * 24, data_length=15)
m5_klines = api.get_kline_serial(symbol, 5 * 60, data_length=15)
# 创建 m1901 的目标持仓 task，该 task 负责调整 m1901 的仓位到指定的目标仓位
target_pos = TargetPosTask(api, symbol)
pos = api.get_position(symbol)
open_pos_date = None


def is_3days_later(kline):
    today = tafunc.time_to_datetime(kline.datetime)
    timedelta = today - open_pos_date
    print(f'交易时间距离今天:{timedelta.days}')
    if timedelta.days >= 3:
        return True
    return False


try:
    while True:
        api.wait_update()
        if api.is_changing(m5_klines):
            ma = sum(m5_klines.close.iloc[-15:]) / 15
            if m5_klines.close.iloc[-1] < ma:
                # 设置目标持仓为空仓
                target_pos.set_target_volume(-5)
                break
    while True:
        api.wait_update()
        kline = daily_klines.iloc[-1]
        if api.is_changing(kline, "close"):
            print(f'交易时间{quote.datetime}')
            print(f'column is :{kline.get("s_qualified")}')
            if pos.pos_short_today != 0:
                open_pos_date = tafunc.time_to_datetime(kline.datetime)
                print(f'做空开仓日期:{tafunc.time_to_str(open_pos_date)}')
except BacktestFinished:
    api.close()
