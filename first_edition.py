from tqsdk import TqApi, TqAuth
from tqsdk.ta import EMA, MACD
from datetime import datetime


api = TqApi(web_gui=":10000",
            auth=TqAuth("galahade", "wombat-gazette-pillory"))

symbol = "SHFE.rb2210"

klines = api.get_kline_serial(symbol, 60*60*24, 500)
# klines30m = api.get_kline_serial(symbol, 60*30, data_length=500)

def calc_and_draw_ema22(klines):
    ema22 = EMA(klines, 22)
    klines["ema22"] = ema22.ema
    klines["ema22.board"] = "MAIN"
    klines["ema22.color"] = "red"
    return ema22


def calc_and_draw_ema60(klines):
    ema60 = EMA(klines, 60)
    klines["ema60"] = ema60.ema
    klines["ema60.board"] = "MAIN"
    klines["ema60.color"] = "green"
    return ema60


def calc_and_draw_macd(klines):
    macd = MACD(klines, 12, 24, 4)
    # 用 K 线图模拟 MACD 指标柱状图
    klines["MACD.open"] = 0.0
    klines["MACD.close"] = macd["bar"]
    klines["MACD.high"] = klines["MACD.close"].where(
        klines["MACD.close"] > 0, 0)
    klines["MACD.low"] = klines["MACD.close"].where(
        klines["MACD.close"] < 0, 0)
    klines["MACD.board"] = "MACD"
    # 在 board=MACD 上添加 diff、dea 线
    klines["diff"] = macd["diff"]
    klines["diff.board"] = "MACD"
    klines["diff.color"] = "gray"
    klines["dea"] = macd["dea"]
    klines["dea.board"] = "MACD"
    klines["dea.color"] = "rgb(255,128,0)"


def ema22_diff_ema60(kline):
    return abs(kline["ema60"] - kline["ema22"]) / kline["ema22"]


def ema60_diff_ema22(kline):
    return abs(kline["ema22"] - kline["ema60"]) / kline["ema60"]


def ema60_diff_close(kline):
    return abs(kline.close - kline.ema60)/kline.ema60

def is_match_daily_kline_condition(kline_tuple):
    kline = kline_tuple[1]
    diff1 = ema22_diff_ema60(kline)
    diff2 = ema60_diff_ema22(kline)
    # EMA22 < EMA60， 且偏离度小于2时
    if kline["ema22"] < kline["ema60"] and diff1 < 0.02:
        # 收盘价格在EMA60均线上方
        if kline["close"] > kline["ema60"] and kline["MACD.close"] > 0:
            return True
    elif kline["ema22"] > kline["ema60"]:
        if diff2 < 0.02 and kline["close"] > kline["ema60"]:
            return True
        elif diff2 > 0.03 and ((kline["close"] > kline["ema60"] and
                                kline["close"] < kline["ema22"]) and
                               (kline["open"] > kline["ema60"] and
                                kline["open"] < kline["ema22"]) and
                               (ema60_diff_close(kline) < 0.02)):
            return True
    return False


def is_match_30m_kline_condition(kline_tuple):
    kline = kline_tuple[1]
#    print(datetime.datetime.fromtimestamp(kline.datetime / 1e9))
    if kline["close"] > kline["ema60"] and kline["MACD.close"] > 0:
        if kline["ema22"] < kline["ema60"]:
            diff_persent = abs(kline.close - kline.ema22)/kline.ema22
            if diff_persent <= 0.02:
                print("收盘价与ema22的差值比为：", diff_persent)
                return True
        elif kline["ema22"] > kline["ema60"]:
            diff_persent = abs(kline.close - kline.ema60)/kline.ema60
            if diff_persent <= 0.02:
                print("收盘价与ema60的差值比为：", diff_persent)
                return True
    return False


calc_and_draw_macd(klines)
calc_and_draw_ema22(klines)
calc_and_draw_ema60(klines)

daily_results = filter(is_match_daily_kline_condition, klines.iterrows())
# m30_results = filter(is_match_30m_kline_condition, klines30m.iterrows())

# 标记符合条件的日K线
for result in daily_results:
    kline = result[1]
    k_date = datetime.fromtimestamp(kline.datetime / 1e9)
    if k_date.year > 2021:
        text = f'{k_date.month}-{k_date.day}'
        api.draw_text(klines, text, x=kline.name, y=kline.low - 50, color=0xFFFF3333)
        start_date = datetime(k_date.year, k_date.month, k_date.day+1, 9, 0, 0)
        end_date = datetime(k_date.year, k_date.month, k_date.day+1, 23, 0, 0)
        # 根据符合条件的日线筛后一天12根30分钟线
        kline_30m = api.get_kline_data_series(symbol=symbol, duration_seconds=60*30,
                                              start_dt=start_date,
                                              end_dt=end_date)
        calc_and_draw_macd(kline_30m)
        calc_and_draw_ema22(kline_30m)
        calc_and_draw_ema60(kline_30m)

        m30_results = filter(is_match_30m_kline_condition, kline_30m.iterrows())
        # 如果当天没有适合的30分钟K线，就继续检查第二天的30分钟K线
        try:
            m30_result = next(m30_results)
            print(text, m30_result[1])
            print(datetime.fromtimestamp(m30_result[1].datetime / 1e9))
            print(kline)
            break
        except StopIteration:
            continue

# 标记符合开仓条件的30分钟线
# for result in m30_results:
#     kline = result[1]
#     text = '开仓'
#     api.draw_text(klines30m, text, x=kline.name, y=kline.low - 20, color=0xFFFF3333)
while True:
    api.wait_update()

api.close()
