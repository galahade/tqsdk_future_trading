import logging
from .tools import examine_symbol, get_date_str, calc_indicator
from trade import Underlying_symbol_trade
from tqsdk import tafunc
from datetime import datetime


def get_logger():
    return logging.getLogger(__name__)


def __get_date_from_symbol(symbol_last_part):
    temp = int(symbol_last_part)
    year = int(temp / 100) + 2000
    month = temp % 100
    day = 1
    return datetime(year, month, day, 15, 0, 0)


def __need_switch_contract(last_symbol, underlying_symbol, quote):
    logger = get_logger()
    last_symbol_list = examine_symbol(last_symbol)
    today_symbol_list = examine_symbol(underlying_symbol)
    if not last_symbol_list or not today_symbol_list:
        logger.warning('新/旧合约代码有误，请检验')
        return False
    if today_symbol_list[0] != last_symbol_list[0] or \
            today_symbol_list[1] != last_symbol_list[1]:
        logger.warning('新/旧合约品种不一，请检验')
        return False
    if underlying_symbol <= last_symbol:
        logger.warning('新合约非远月合约，不换月')
        return False
    last_date = __get_date_from_symbol(last_symbol_list[2])
    current_date = tafunc.time_to_datetime(quote.datetime)
    timedelta = last_date - current_date
    if timedelta.days <= 5:
        return True
    return False


'''
def switch_contract(ust, api):
    logger = get_logger()
    # 获取最新主力合约
    underlying_symbol = ust.quote.underlying_symbol
    if __need_switch_contract(ust.underlying_symbol, underlying_symbol):
        new_ust = Underlying_symbol_trade(api, ust.symbol, ust.account)
        last_pos_long = ust.position.pos_long
        diff = diff_two_value(new_ust.daily_klines.iloc[-2].ema9,
                              new_ust.daily_klines.iloc[-2].ema60)
        if last_pos_long > 0:
            if diff < 6:
                ust.target_pos.set_target_volume(0)
                new_ust.target_pos.set_target_volume(last_pos_long)
            else:
                ust.target_pos.set_target_volume(0)
            while True:
                api.wait_update()
                if diff < 6:
                    if ust.position.pos_long == 0\
                       and new_ust.position.pos_long == last_pos_long:
                        logger.info(f"{get_date_str(ust.quote.datetime)}\
换月买入:换月前-多头{last_pos_long}手 换月后-多头{last_pos_long}手")
                        new_ust.set_stop_loss_price()
                        break
                elif ust.position.pos_long == 0:
                    logger.info(f"{get_date_str(ust.quote.datetime)} \
换月平仓:换月前-多头{last_pos_long}手 换月后-多头{new_ust.position.pos_long}手")
                    break
            logger.info(f"{get_date_str(ust.quote.datetime)}换月完成:旧合约{ust.underlying_symbol},\
新合约{new_ust.underlying_symbol}")
            return new_ust
    return ust
'''


def switch_contract(ust, api):
    logger = get_logger()
    # 获取最新主力合约
    underlying_symbol = ust.quote.underlying_symbol
    if ust.trade_status.ready_s_contract \
       and __need_switch_contract(ust.underlying_symbol, underlying_symbol,
                                  ust.quote):
        new_ust = Underlying_symbol_trade(api, ust.symbol, ust.account)
        last_pos_long = ust.position.pos_long
        if last_pos_long > 0:
            ust.target_pos.set_target_volume(0)
            while True:
                api.wait_update()
                if ust.position.pos_long == 0:
                    logger.info(f"{get_date_str(ust.quote.datetime)} \
换月平仓:换月前-多头{last_pos_long}手 换月后-多头{new_ust.position.pos_long}手")
                    break
        logger.info(f"{get_date_str(ust.quote.datetime)}换月完成:旧合约{ust.underlying_symbol},\
新合约{new_ust.underlying_symbol}")
        return new_ust
    return ust


# 调用该方法执行交易策略，等待合适的交易时机进行交易。
# api：天勤量化api对象，ust：主力合约交易对象
def wait_to_trade(api, ust):
    logger = get_logger()
    logger.debug("准备开始交易，调用天勤接口，等待交易时机")
    while True:
        api.wait_update()
        # 处理更换主力合约问题
        if api.is_changing(ust.quote, "underlying_symbol"):
            logger.info(f"{get_date_str(ust.quote.datetime)}平台主力合约已更换,\
开始准备切换合约")
            ust.trade_status.ready_s_contract = True
        if api.is_changing(ust.daily_klines.iloc[-1], "datetime"):
            calc_indicator(ust.daily_klines)
            ust = switch_contract(ust, api)
        if api.is_changing(ust.h2_klines.iloc[-1], "datetime"):
            calc_indicator(ust.h2_klines)
        if api.is_changing(ust.m30_klines.iloc[-1], "datetime"):
            calc_indicator(ust.m30_klines)
        if api.is_changing(ust.m5_klines.iloc[-1], "datetime"):
            calc_indicator(ust.m5_klines)
        if api.is_changing(ust.quote, "last_price"):
            ust.open_volumes()
            ust.scan_order_status()
