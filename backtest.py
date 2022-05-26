from tqsdk import TqApi, TqAuth, TqBacktest, TqSim, BacktestFinished, \
        TargetPosTask
from datetime import date
from tools import calc_indicator, can_open_volumes, calc_volume_by_price


base_persent = 0.02
stop_loss_price = 0.0


# 挂止损单
def stop_loss(_target_pos, _quote, _position):
    if _quote.last_price <= stop_loss_price:
        _target_pos.set_target_volume(_position.pos_long)


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
            calc_indicator(daily_klines)
            calc_indicator(m30_klines)

        # 如果前一天日k线符合条件
        if can_open_volumes(api, daily_klines, m30_klines, position):
            wanted_volume = calc_volume_by_price(quote, account)
            target_pos.set_target_volume(wanted_volume)
            # 设置初始止损价格
            stop_loss_price = position.open_price_long * (1 - base_persent)

        if api.is_changing(quote, "last_price"):
            if quote.last_price >= position.open_price_long * (1 + base_persent
                                                               * 3):
                stop_loss_price = position.open_price_long * (1 + base_persent)
                stop_loss(target_pos, quote, position)

    while True:
        api.wait_update()


except BacktestFinished:
    print("持仓的浮动盈亏：", position.float_profit)
    print("开仓均价：", position.open_price_long)
    print("持仓均价: ", position.position_price_long)
    api.close()
    # 打印回测的详细信息
    # print("trade log:", acc.trade_log)

    # 账户交易信息统计结果
    # print("tqsdk stat:", acc.tqsdk_stat)
#    while True:
#        api.wait_update()
