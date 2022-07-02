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


def __need_switch_contract(last_symbol, underlying_symbol, ust):
    '''判断是否需要换月，规则是：如果原合约有持仓，则在合约交割月之前10天换月
    否则，在交割月之前一个月月初换月。
    '''
    logger = get_logger()
    if ust.trade_status.ready_s_contract:
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
        current_date = tafunc.time_to_datetime(ust.ticks.iloc[-1].datetime)
        timedelta = last_date - current_date
        logger.debug(f'原合约{last_symbol},下一个合约{underlying_symbol}'
                     f'当前时间与原合约交易截止月相差{timedelta.days}天')
        if ust.position.pos != 0 and timedelta.days <= 11:
            return True
        elif ust.position.pos == 0 and timedelta.days <= 31:
            return True
    return False


def switch_contract(ust, api):
    '''在主连合约更换主力合约后调用，
    这时，quote的主力合约和交易对象最初的主力合约已不同。
    如果满足换月条件，则进行换月操作。
    '''
    logger = get_logger()
    # 获取最新主力合约
    logger.debug("try to switch contract")
    underlying_symbol = ust.quote.underlying_symbol
    if __need_switch_contract(ust.underlying_symbol, underlying_symbol, ust):
        new_ust = Underlying_symbol_trade(api, ust.symbol, ust.account, ust.tb)
        last_pos_long = ust.position.pos_long
        trade_time = ust.trade_status.current_date_str()
        trade_price = ust.trade_status.current_price()
        if last_pos_long > 0:
            ust.target_pos.set_target_volume(0)
            while True:
                api.wait_update()
                if ust.position.pos_long == 0:
                    logger.info(f'{trade_time}'
                                f'换月平仓:换月前-多头{last_pos_long}手'
                                f'换月后-多头{new_ust.position.pos_long}手'
                                )
                    ust.tb.r_l_sold_pos(ust.underlying_symbol,
                                        ust.trade_status.tb_count,
                                        trade_time,
                                        '换月平仓',
                                        trade_price,
                                        last_pos_long)
                    break
        logger.info(f'{trade_time}换月完成:'
                    f'旧合约{ust.underlying_symbol},'
                    f'新合约{new_ust.underlying_symbol}')
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
        trade_time = ust.trade_status.current_date_str()
        if api.is_changing(ust.quote, "underlying_symbol"):
            logger.debug(f'{trade_time}平台主力合约已更换,'
                         f'原合约{ust.underlying_symbol},'
                         f'新合约{ust.quote.underlying_symbol}'
                         f'开始准备切换合约')
            ust.trade_status.ready_s_contract = True
        if api.is_changing(ust.daily_klines.iloc[-1], "datetime"):
            calc_indicator(ust.daily_klines)
            logger.debug(f'日线日期:{trade_time}')
            ust = switch_contract(ust, api)
        if api.is_changing(ust.h2_klines.iloc[-1], "datetime"):
            calc_indicator(ust.h2_klines)
        if api.is_changing(ust.m30_klines.iloc[-1], "datetime"):
            calc_indicator(ust.m30_klines)
        if api.is_changing(ust.m5_klines.iloc[-1], "datetime"):
            calc_indicator(ust.m5_klines)
        if api.is_changing(ust.ticks):
            ust.start_trade()
