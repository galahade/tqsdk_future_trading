from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished
from tqsdk.ta import EMA, MACD
from datetime import datetime, date


def get_date_from_kline(kline):
    return datetime.fromtimestamp(kline.datetime/1e9)


def calc_ema22(klines):
    ema22 = EMA(klines, 22)
    klines["ema22"] = ema22.ema


def calc_ema60(klines):
    ema60 = EMA(klines, 60)
    klines["ema60"] = ema60.ema


def calc_macd(klines):
    macd = MACD(klines, 12, 24, 4)
    # 用 K 线图模拟 MACD 指标柱状图
    klines["MACD.open"] = 0.0
    klines["MACD.close"] = macd["bar"]
    klines["MACD.high"] = klines["MACD.close"].where(
        klines["MACD.close"] > 0, 0)
    klines["MACD.low"] = klines["MACD.close"].where(
        klines["MACD.close"] < 0, 0)


def calc_indicator(klines):
    calc_macd(klines)
    calc_ema22(klines)
    calc_ema60(klines)


def diff_two_value(first, second):
    return abs(first - second)/second


def is_match_daily_kline_condition(kline):
    diff1 = diff_two_value(kline.ema60, kline.ema22)
    diff2 = diff_two_value(kline.ema22, kline.ema60)
    # EMA22 < EMA60， 且偏离度小于2时
    if kline["ema22"] < kline["ema60"] and diff1 < 0.02:
        # 收盘价格在EMA60均线上方
        if kline["close"] > kline["ema60"] and kline["MACD.close"] > 0:
            print("符合日线条件1，日期为：", get_date_from_kline(kline))
            return True
    elif kline["ema22"] > kline["ema60"]:
        if diff2 < 0.02 and kline["close"] > kline["ema60"]:
            print("符合日线条件2，日期为：", get_date_from_kline(kline))
            return True
        elif (diff2 > 0.03 and
                ((kline["close"] > kline["ema60"] and
                    kline["close"] < kline["ema22"]) and
                    (kline["open"] > kline["ema60"] and
                        kline["open"] < kline["ema22"]) and
                    (diff_two_value(kline.close, kline.ema60) < 0.02))):
            print("符合日线条件3，日期为：", get_date_from_kline(kline))
            return True
    return False


def is_match_30m_kline_condition(kline):
    if kline["close"] > kline["ema60"] and kline["MACD.close"] > 0:
        if kline["ema22"] < kline["ema60"]:
            diff_persent = abs(kline.close - kline.ema22)/kline.ema22
            if diff_persent <= 0.02:
                print("收盘价与ema22的差值比为：", diff_persent)
                print("符合30分钟线条件1，日期为：",
                      get_date_from_kline(kline))
                return True
        elif kline["ema22"] > kline["ema60"]:
            diff_persent = abs(kline.close - kline.ema60)/kline.ema60
            if diff_persent <= 0.02:
                print("收盘价与ema60的差值比为：", diff_persent)
                print("符合30分钟线条件2，日期为：",
                      get_date_from_kline(kline))
                return True
    return False


acc = TqSim()

try:
    api = TqApi(acc, web_gui=":10000",
                backtest=TqBacktest(start_dt=date(2022, 1, 1),
                                    end_dt=date(2022, 5, 24)),
                auth=TqAuth("galahade", "wombat-gazette-pillory"))
    symbol = "SHFE.rb2210"
    daily_klines = api.get_kline_serial(symbol, 60*60*24)
    m30_klines = api.get_kline_serial(symbol, 60*30)

    while True:
        api.wait_update()
        # 当创建出新日K线时，执行以下操作
        if api.is_changing(daily_klines.iloc[-1], "datetime"):
            calc_indicator(daily_klines)

            # 如果前一天日k线符合条件
            if(is_match_daily_kline_condition(daily_klines.iloc[-1])):
                print(f"前一天日{get_date_from_kline(daily_klines.iloc[-1])}K线符合条件，\
                      开始检测当日30分钟线")
                if api.is_changing(m30_klines.iloc[-1], "datetime"):
                    calc_indicator(m30_klines)
                    last_30m_kline = m30_klines.iloc[-1]
                    if(is_match_30m_kline_condition(last_30m_kline)):
                        print(f"前一根30分钟K线{get_date_from_kline(last_30m_kline)}符合条件，\
                              开始执行开仓操作")
                        break
    while True:
        api.wait_update()
    print("开始进行止损/止盈操作")

except BacktestFinished:
    api.close()
    # 打印回测的详细信息
    # print("trade log:", acc.trade_log)

    # 账户交易信息统计结果
    # print("tqsdk stat:", acc.tqsdk_stat)
