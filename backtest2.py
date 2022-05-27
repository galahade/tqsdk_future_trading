from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished, \
        TargetPosTask
from datetime import date
from tools import calc_indicator, get_date_from_kline, \
        is_match_daily_kline_condition, is_match_30m_kline_condition, \
        calc_volume_by_price


acc = TqSim()

try:
    api = TqApi(acc, web_gui=":10000",
                backtest=TqBacktest(start_dt=date(2021, 10, 18),
                                    end_dt=date(2022, 5, 24)),
                auth=TqAuth("galahade", "wombat-gazette-pillory"))
    symbol = "SHFE.rb2210"
    daily_klines = api.get_kline_serial(symbol, 60*60*24)
    m30_klines = api.get_kline_serial(symbol, 60*30)
    quote = api.get_quote(symbol)
    print(quote.instrument_id)
    target_pos = TargetPosTask(api, symbol)
    account = api.get_account()
    position = api.get_position(symbol)

    calc_indicator(daily_klines)
    calc_indicator(m30_klines)
    count = 0
    while True:
        api.wait_update()
        count = count + 1
        # 当创建出新日K线时，执行以下操作
        if api.is_changing(daily_klines.iloc[-1], "datetime"):
            print("更新日线-", get_date_from_kline(daily_klines.iloc[-1]))
            calc_indicator(daily_klines)
            calc_indicator(m30_klines)

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
                print(daily_klines.iloc[-1])
                print(last_30m_kline)
                if api.is_changing(quote, "last_price"):
                    wanted_volume = calc_volume_by_price(quote, account)
                    target_pos.set_target_volume(wanted_volume)
                    break
    print("开始进行止损/止盈操作")

except BacktestFinished:
    api.close()
    # 打印回测的详细信息
    # print("trade log:", acc.trade_log)

    # 账户交易信息统计结果
    # print("tqsdk stat:", acc.tqsdk_stat)
#    while True:
#        api.wait_update()
