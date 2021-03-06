import logging
from tqsdk import TargetPosTask
from math import floor, ceil
from tqsdk import tafunc
from utils.tools import calc_indicator, diff_two_value, get_date_str,\
    calc_date_delta


def get_logger():
    return logging.getLogger(__name__)


open_volumes_persent = 0.02
l_base_persent = 0.02
s_base_persent = 0.02


def calc_price_by_scale(base_price, base_persent, is_add, scale):
    if is_add:
        return round(base_price * (1 + base_persent * scale), 2)
    else:
        return round(base_price * (1 - base_persent * scale), 2)


def is_last_5_minitus(tick):
    trade_time = tafunc.time_to_datetime(tick.datetime)
    time_num = int(trade_time.time().strftime("%H%M%S"))
    return 150000 > time_num > 145500


class Trade_status:

    def __init__(self, api, position, ticks, trade_book):
        self.api = api
        self.__position = position
        self.__ticks = ticks
        self.__tb = trade_book
        self.__symbol = ticks.iloc[-1].symbol

        self.is_trading = False
        # -1:做空,0:初始状态,1:做多
        self.short_or_long = 0
        self.ready_s_contract = False

        # 做多交易属性
        self.l_stop_loss_price = 0.0
        self.__l_begin_profit = False
        self.l_daily_cond = 0
        self.l_h2_cond = 0
        self.l_profit_cond = 0
        self.l_stop_profit_point = 0.0
        # 以下属性只有在 profit_condition = 3 时使用
        # 1:出售剩余仓位的80%，2:平仓
        self.l_profit_stage = 0

        # 做空交易属性
        self.s_open_pos = 0
        self.s_stop_loss_price = 0.0
        # 一共4做空方式
        self.s_cond = 0

        self.tb_count = 0

    def set_daily_kline(self, kline, short_or_long, num):
        self.__daily_kline = kline
        self.short_or_long = short_or_long
        if self.short_or_long == 1:
            self.l_daily_cond = num
        elif self.short_or_long == -1:
            self.s_cond = num

    def set_h2_kline(self, kline):
        self.__h2_kline = kline

    def set_l_h2_kline(self, kline, num):
        self.__h2_kline = kline
        self.l_h2_cond = num

    def set_m30_kline(self, kline):
        self.__m30_kline = kline

    def make_long_deal(self):
        logger = get_logger()
        if self.is_trading:
            logger.debug("无法创建<做多>新交易状态，交易进行中")
            return False
        if (self.short_or_long != 1 or not self.l_daily_cond
            or self.__daily_kline.empty or self.__h2_kline.empty
           or self.__m30_kline.empty):
            logger.debug("交易状态不符合<做多>条件，请检查相关条件")
            return False
        self.is_trading = True
        self.__make_l_prices()
        self.__make_l_profit_cond()

        self.tb_count = self.__tb.r_l_open_pos(
            self.__symbol,
            self.current_date_str(),
            self.l_daily_cond, self.l_h2_cond,
            self.__position.open_price_long,
            self.__position.pos_long
        )

    def __make_l_prices(self):
        logger = get_logger()
        open_price = self.__position.open_price_long
        curr_date = self.current_date_str()
        self.l_stop_loss_price = calc_price_by_scale(
            open_price, l_base_persent, False, 1)
        self.l_stop_profit_point = calc_price_by_scale(
            open_price, l_base_persent, True, 3)
        logger.info(f'{curr_date}'
                    f'<做多>止损设置为:{self.l_stop_loss_price}')
        logger.info(f'{curr_date}'
                    f'<做多>止赢起始价为:{self.l_stop_profit_point}')

    def __make_l_profit_cond(self):
        '''根据两小时线和日线的条件，设置止盈适用条件。
        默认为0:即达到止盈价格后卖出50%仓位，然后分阶段止盈。
        当止盈条件为1:每日收盘前5分钟判断是否平仓。
        '''
        ema9 = self.__h2_kline.ema9
        ema22 = self.__h2_kline.ema22
        ema60 = self.__h2_kline.ema60
        close = self.__h2_kline.close
        macd = self.__h2_kline["MACD.close"]
        diff_22_60 = diff_two_value(ema22, ema60)
        if (self.l_daily_cond in [1, 2, 3, 4] and close > ema22 > ema60
           and (diff_two_value(close, ema60) < 1.2 or diff_22_60 < 1)):
            self.l_profit_cond = 1
        elif (self.l_daily_cond == 5 and ema60 > ema22 > ema9 and macd > 0
              and close > ema9):
            self.l_profit_cond = 1

    def make_short_deal(self):
        logger = get_logger()
        if self.is_trading:
            logger.debug("无法创建<做空>新交易状态，交易进行中")
            return False
        if (self.short_or_long != -1 or not self.s_daily_cond or
           self.__daily_kline.empty or self.__h2_kline.empty or
           self.__m30_kline.empty):
            logger.debug("交易状态不符合<做空>条件，请检查相关条件")
            return False
        self.is_trading = True
        open_price = self.__position.open_price_short
        self.s_open_pos = self.__position.pos_short
        self.s_stop_loss_price = round(open_price * (1 + s_base_persent), 2)
        curr_date = self.current_date_str()
        if self.s_cond == 4:
            self.trade_date = curr_date
        logger.info(f'{curr_date}'
                    f'<做空>止损设置为:{self.s_stop_loss_price}')

    def check_profit_status(self, s_or_l):
        logger = get_logger()
        if self.is_trading:
            self.api.wait_update()
            c_price = self.current_price()
            log_str = '{} {} 现价:{} 达到止盈价位{} 开始监控'
            if s_or_l == 1:
                if self.__l_begin_profit:
                    return True
                elif c_price >= self.l_stop_profit_point:
                    logger.info(log_str.format(
                        self.current_date_str(),
                        '做多', c_price, self.l_stop_profit_point))
                    self.__l_begin_profit = True
                    return True
            elif s_or_l == -1:
                return True
        return False

    def check_stop_loss_status(self):
        if self.is_trading:
            pos_long = self.__position.pos_long
            pos_short = self.__position.pos_short
            current_price = self.current_price()
            if self.short_or_long == 1:
                if (pos_long > 0 and current_price <=
                   self.l_stop_loss_price):
                    return True
            if self.short_or_long == -1:
                if (pos_short > 0 and current_price >=
                   self.s_stop_loss_price):
                    return True
        return False

    def update_l_profit_status(self, dk, m30k):
        '''当开仓后，使用该方法判断是否达到监控止盈条件，
        当开始监控止盈后，根据最新价格，更新止损价格和止盈阶段
        为止盈提供依据
        '''
        pos_long = self.__position.pos_long
        if pos_long > 0 and self.check_profit_status(1):
            if self.l_profit_stage == 0:
                self.l_profit_stage = 1
            elif self.l_profit_cond == 0:
                if self.l_profit_stage == 1:
                    self.l_profit_stage = 2

    def should_closeout(self, dk, m30k, tick):
        '''在当日交易结束前5分钟，判断是否应该清仓
        可返回3种状态：
        1. True 应该清仓
        2. False 不清仓
        3. 8 售出持有仓位的80%
        '''
        logger = get_logger()
        log_str = '{} 止盈条件:{},当前价:{},售出比例:{}日线EMA22:{},30mEMA60:{}'
        ema22 = dk.ema22
        last_price = self.current_price()
        if is_last_5_minitus(tick):
            if (self.l_profit_cond == 1 and last_price < ema22):
                logger.debug(log_str.format(
                 self.current_date_str(), 1,
                 last_price, '100%', ema22, m30k.ema60))
                return True
            elif self.l_profit_cond == 0:
                if self.l_profit_stage == 2:
                    if last_price < m30k.ema60:
                        logger.debug(log_str.format(
                         self.current_date_str(), 0,
                         last_price, '80%', ema22, m30k.ema60))
                        return 8
                elif self.l_profit_stage == 3:
                    if last_price < ema22:
                        logger.debug(log_str.format(
                         self.current_date_str(), 0,
                         last_price, '100%', ema22, m30k.ema60))
                        return True
        return False

    def reset_long(self):
        self.is_trading = False
        self.l_daily_cond = 0
        self.l_h2_cond = 0
        self.l_stop_loss_price = 0.0
        self.__l_begin_profit = False
        self.l_profit_cond = 0
        self.l_stop_profit_point = 0.0
        self.l_profit_stage = 0

    def reset_short(self):
        self.is_trading = False
        self.s_daily_cond = 0
        self.s_open_pos = 0
        self.s_stop_loss_price = 0.0
        self.__s_begin_profit = False
        self.s_profit_cond = 0
        self.s_stop_profit_point = 0.0
        self.s_profit_stage = 0

    def current_price(self):
        return self.__ticks.iloc[-1].last_price

    def current_date_str(self):
        return get_date_str(self.__ticks.iloc[-1].datetime)


class Underlying_symbol_trade:
    '''
    主力合约交易类

    包括交易一个合约用到的所有功能
    '''

    def __init__(self, api, symbol, account, trade_book):
        self.__api = api
        self.quote = api.get_quote(symbol)
        self.underlying_symbol = self.quote.underlying_symbol
        self.symbol = symbol
        self.position = api.get_position(self.underlying_symbol)
        self.target_pos = TargetPosTask(api, self.underlying_symbol)
        self.account = account
        self.daily_klines = api.get_kline_serial(self.underlying_symbol,
                                                 60*60*24)
        self.h2_klines = api.get_kline_serial(self.underlying_symbol, 60*60*2)
        self.m30_klines = api.get_kline_serial(self.underlying_symbol, 60*30)
        self.m5_klines = api.get_kline_serial(self.underlying_symbol, 60*5)
        self.ticks = api.get_tick_serial(self.underlying_symbol)

        self.tb = trade_book
        self.trade_status = Trade_status(api, self.position, self.ticks,
                                         trade_book)

        calc_indicator(self.daily_klines, is_daily_kline=True)
        calc_indicator(self.m30_klines)
        calc_indicator(self.h2_klines)
        calc_indicator(self.m5_klines)

    def __can_open_volumes_long(self):
        if self.position.pos_long == 0:
            if self.__match_dk_cond_long():
                if self.__match_2hk_cond_long():
                    if(self.__match_30mk_cond_long()):
                        if self.__match_5mk_cond_long():
                            if self.position.pos_long == 0:
                                return True
        return False

    def __can_open_volumes_short(self):
        if self.position.pos_short == 0:
            if self.__match_dk_cond_short():
                if self.__match_2hk_cond_short():
                    if(self.__match_30mk_cond_short()):
                        if self.position.pos_short == 0:
                            return True
        return False

    def __match_5mk_cond_long(self):
        logger = get_logger()
        kline = self.m5_klines.iloc[-2]
        tick = self.ticks.iloc[-1]
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        diff = diff_two_value(close, ema60)
        trade_time = get_date_str(tick.datetime)
        kline_time = get_date_str(kline.datetime)
        log_str = '{} 满足<做多>5分钟线条件:K线生成时间:{},ema60:{},收盘:{},MACD:{},diff:{}'
        logger.debug(log_str.format(trade_time, kline_time,
                     ema60, close, macd, diff))
        if close > ema60 and macd > 0 and diff < 1.2:
            logger.debug(log_str.format(trade_time, kline_time,
                         ema60, close, macd, diff))
            return True
        return False

    def __match_30mk_cond_long(self):
        logger = get_logger()
        kline = self.m30_klines.iloc[-2]
        tick = self.ticks.iloc[-1]
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        diff = diff_two_value(close, ema60)
        trade_time = get_date_str(tick.datetime)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做多>30分钟线条件:K线生成时间:{},ema60:{},收盘:{},'
                   'MACD:{}, diff:{}')
        logger.debug(log_str.format(trade_time, kline_time,
                     ema60, close, macd, diff))
        if kline["l_qualified"]:
            logger.debug('30m K 线重复合')
            return True
        if close > ema60 and macd > 0 and diff < 1.2:
            logger.debug(log_str.format(trade_time, kline_time,
                         ema60, close, macd, diff))
            self.m30_klines.loc[self.m30_klines.id == kline.id,
                                'l_qualified'] = 1
            self.trade_status.set_m30_kline(kline)
            return True
        return False

    def __match_30mk_cond_short(self):
        logger = get_logger()
        kline = self.m30_klines.iloc[-2]
        tick = self.ticks.iloc[-1]
        s_cond = self.trade_status.s_cond
        ema9 = kline.ema9
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        high = kline.high
        diff_c_60 = diff_two_value(close, ema60)
        diff_h_60 = diff_two_value(high, ema60)
        trade_time = get_date_str(tick.datetime)
        log_str = ('{} 满足<做空>30分钟线条件{}:ema9:{},ema22:{},ema60:{},'
                   '收盘:{},最高:{},diff_c_60:{},diff_h_60:{},MACD:{}')
        if kline["s_qualified"]:
            return kline["s_qualified"]
        if ema60 > close:
            if ema60 > ema22 > ema9:
                if s_cond == 1 and diff_h_60 < 1.2:
                    logger.debug(log_str.format(
                        trade_time, 1, ema9, ema22,
                        ema60, close, high, diff_c_60, diff_h_60, macd))
                    self.m30_klines.loc[self.m30_klines.id == kline.id,
                                        's_qualified'] = 1
                    self.trade_status.set_m30_kline(kline)
                    return 1
                elif s_cond == 3 and diff_c_60 < 1.2:
                    logger.debug(log_str.format(
                        trade_time, 3, ema9, ema22,
                        ema60, close, high, diff_c_60, diff_h_60, macd))
                    self.m30_klines.loc[self.m30_klines.id == kline.id,
                                        's_qualified'] = 3
                    self.trade_status.set_m30_kline(kline)
                    return 3
            elif s_cond == 4 and diff_c_60 < 1.2 and macd < 0:
                logger.debug(log_str.format(
                    trade_time, 3, ema9, ema22,
                    ema60, close, high, diff_c_60, diff_h_60, macd))
                self.m30_klines.loc[self.m30_klines.id == kline.id,
                                    's_qualified'] = 3
                self.trade_status.set_m30_kline(kline)
                return 4
        elif s_cond == 2 and close > ema60 > ema22 and diff_c_60 < 1.2:
            logger.debug(log_str.format(
                trade_time, 2, ema9, ema22,
                ema60, close, high, diff_c_60, diff_h_60, macd))
            self.m30_klines.loc[self.m30_klines.id == kline.id,
                                's_qualified'] = 2
            self.trade_status.set_m30_kline(kline)
            return 2
        return 0

    def __match_2hk_cond_long(self):
        logger = get_logger()
        ts = self.trade_status
        kline = self.h2_klines.iloc[-2]
        tick = self.ticks.iloc[-1]
        ema9 = kline.ema9
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        open_price = kline.open
        diff = diff_two_value(close, ema60)
        diff_o_60 = diff_two_value(open_price, ema60)
        diff_22_60 = diff_two_value(ema22, ema60)
        trade_time = get_date_str(tick.datetime)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做多>两小时线条件{}:K线生成时间:{},ema9:{}'
                   'ema22:{},ema60:{},收盘:{},'
                   'MACD:{},diff:{},diff_open_60:{},diff_22_60:{}')
#        logger.debug(log_str.format(
#            trade_time, '不', kline_time, ema9, ema22, ema60, close,
#            macd, diff, diff_o_60, diff_22_60))
        if kline["l_qualified"]:
            return True
        if diff < 3 or diff_o_60 < 3:
            if ts.l_daily_cond in [1, 2]:
                if (ema22 < ema60 and ema9 < ema60 and macd > 0):
                    logger.debug(log_str.format(
                        trade_time, 1, kline_time, ema9, ema22, ema60, close,
                        macd, diff, diff_o_60, diff_22_60))
                    self.h2_klines.loc[self.h2_klines.id == kline.id,
                                       'l_qualified'] = 1
                    self.trade_status.set_l_h2_kline(kline, 1)
                    return True
                elif close > ema9 > ema22 > ema60:
                    logger.debug(log_str.format(
                        trade_time, 2, kline_time, ema9, ema22, ema60, close,
                        macd, diff, diff_o_60, diff_22_60))
                    self.h2_klines.loc[self.h2_klines.id == kline.id,
                                       'l_qualified'] = 2
                    self.trade_status.set_l_h2_kline(kline, 2)
                    return True
            elif ts.l_daily_cond in [3]:
                if (close > ema60 > ema22 and macd > 0):
                    logger.debug(log_str.format(
                        trade_time, 3, kline_time, ema9, ema22, ema60, close,
                        macd, diff, diff_o_60, diff_22_60))
                    self.h2_klines.loc[self.h2_klines.id == kline.id,
                                       'l_qualified'] = 3
                    self.trade_status.set_l_h2_kline(kline, 3)
                    return True
            elif ts.l_daily_cond == 5:
                if (ema60 > ema22 > ema9):
                    logger.debug(log_str.format(
                        trade_time, 4, kline_time, ema9, ema22, ema60, close,
                        macd, diff, diff_o_60, diff_22_60))
                    self.h2_klines.loc[self.h2_klines.id == kline.id,
                                       'l_qualified'] = 4
                    self.trade_status.set_l_h2_kline(kline, 4)
                    return True
        return False

    def __match_2hk_cond_short(self):
        logger = get_logger()
        kline = self.h2_klines.iloc[-2]
        tick = self.ticks.iloc[-1]
        s_cond = self.trade_status.s_cond
        ema9 = kline.ema9
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        high = kline.high
        diff_h_9 = diff_two_value(high, ema9)
        diff_h_22 = diff_two_value(high, ema22)
        diff_c_60 = diff_two_value(close, ema60)
        diff_22_60 = diff_two_value(ema22, ema60)
        trade_time = get_date_str(tick.datetime)
        log_str = ('{} 满足<做空>两小时线条件{}:ema22:{},ema60:{},收盘:{},'
                   'diff_h_9:{},diff_h_22:{},diff_22_60:{},diff_c_60:{},'
                   'MACD:{}')
        if kline["s_qualified"]:
            return kline["s_qualified"]
        if ema60 > ema22 > ema9:
            if ((high >= ema9 or diff_h_9 < 0.02)
               or (high >= ema22 or diff_h_22 < 0.2)) and s_cond == 1:
                logger.debug(log_str.format(
                    trade_time, 1, ema22, ema60, close, diff_h_9,
                    diff_h_22, diff_22_60, diff_c_60, macd))
                self.h2_klines.loc[self.h2_klines.id == kline.id,
                                   's_qualified'] = 1
                self.trade_status.set_h2_kline(kline)
                return 1
            elif ema60 > close and diff_c_60 < 1.2 and s_cond == 2:
                logger.debug(log_str.format(
                    trade_time, 2, ema22, ema60, close, diff_h_9,
                    diff_h_22, diff_22_60, diff_c_60, macd))
                self.h2_klines.loc[self.h2_klines.id == kline.id,
                                   's_qualified'] = 2
                self.trade_status.set_h2_kline(kline)
                return 2
        if macd < 0:
            if (s_cond == 3 and
               (ema60 > ema22 > ema9 and (high >= ema9 or diff_h_9 < 0.02))):
                logger.debug(log_str.format(
                    trade_time, 3, ema22, ema60, close, diff_h_9,
                    diff_h_22, diff_22_60, diff_c_60, macd))
                self.h2_klines.loc[self.h2_klines.id == kline.id,
                                   's_qualified'] = 3
                self.trade_status.set_h2_kline(kline)
                return 3
            elif (s_cond == 4 and ema9 > ema22 > ema60 and diff_22_60) < 1:
                logger.debug(log_str.format(
                    trade_time, 4, ema22, ema60, close, diff_h_9,
                    diff_h_22, diff_22_60, diff_c_60, macd))
                self.h2_klines.loc[self.h2_klines.id == kline.id,
                                   's_qualified'] = 4
                self.trade_status.set_h2_kline(kline)
                return 4
        return 0

    def __match_dk_cond_long(self):
        # 如果id不足59，说明合约成交日还未满60天，ema60均线还不准确
        # 故不能作为判断依据
        logger = get_logger()
        kline = self.daily_klines.iloc[-2]
        tick = self.ticks.iloc[-1]
        ema9 = kline.ema9
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        open_price = kline.open
        trade_time = get_date_str(tick.datetime)
        daily_K_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做多>日线条件{}: 日线生成时间:{},ema9:{},'
                   'ema22:{},ema60:{},收盘:{},diff:{},diff_c_60:{},MACD:{}')
        if kline["l_qualified"]:
            return kline["l_qualified"]
        elif kline.id > 58:
            diff = diff_two_value(ema9, ema60)
            diff_c_60 = diff_two_value(close, ema60)
            if ema22 < ema60:
                # 判断是否满足日线条件1
                if diff < 1 and close > ema60 and macd > 0:
                    logger.debug(log_str.format(
                        trade_time, 1, daily_K_time, ema9, ema22,
                        ema60, close, diff, diff_c_60, macd))
                    self.daily_klines.loc[self.daily_klines.id == kline.id,
                                          'l_qualified'] = 1
                    self.trade_status.set_daily_kline(kline, 1, 1)
                    return True
            elif ema22 > ema60:
                # 判断是否满足日线条件2
                if ema9 > ema22 > ema60 and diff < 1 and close > ema22:
                    logger.debug(log_str.format(
                        trade_time, 2, daily_K_time, ema9, ema22,
                        ema60, close, diff, diff_c_60, macd))
                    self.daily_klines.loc[self.daily_klines.id == kline.id,
                                          'l_qualified'] = 2
                    self.trade_status.set_daily_kline(kline, 1, 2)
                    return True
                # 判断是否满足日线条件3
                elif (1 < diff < 3 and ema9 > ema22 >
                      min(open_price, close) > ema60):
                    logger.debug(log_str.format(
                        trade_time, 3, daily_K_time, ema9, ema22,
                        ema60, close, diff, diff_c_60, macd))
                    self.daily_klines.loc[self.daily_klines.id == kline.id,
                                          'l_qualified'] = 3
                    self.trade_status.set_daily_kline(kline, 1, 3)
                    return True
                # 判断是否满足日线条件4
                elif 1 < diff < 3 and ema22 > close > ema60 and ema9 < ema22:
                    logger.debug(log_str.format(
                        trade_time, 4, daily_K_time, ema9, ema22,
                        ema60, close, diff, diff_c_60, macd))
                    self.daily_klines.loc[self.daily_klines.id == kline.id,
                                          'l_qualified'] = 4
                    self.trade_status.set_daily_kline(kline, 1, 4)
                    return True
                elif (diff > 3 and ema22 > close > ema60 and diff_c_60 < 2):
                    logger.debug(log_str.format(
                        trade_time, 5, daily_K_time, ema9, ema22,
                        ema60, close, diff, diff_c_60, macd))
                    self.daily_klines.loc[self.daily_klines.id == kline.id,
                                          'l_qualified'] = 5
                    self.trade_status.set_daily_kline(kline, 1, 5)
                    return True
        return False

    def __match_dk_cond_short(self):
        # 如果id不足59，说明合约成交日还未满60天，ema60均线还不准确
        # 故不能作为判断依据
        logger = get_logger()
        kline = self.daily_klines.iloc[-2]
        tick = self.ticks.iloc[-1]
        ema9 = kline.ema9
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        trade_time = get_date_str(tick.datetime)
        log_str = ('{} 满足<做空>日线条件{}:ema9:{},ema22:{},ema60:{},收盘:{},'
                   'diff:{},MACD:{}')
        if kline["s_qualified"]:
            return kline["s_qualified"]
        elif kline.id > 58:
            diff = diff_two_value(ema22, ema60)
            if ema22 > ema9 and macd < 0:
                if ema22 > ema60 > close and diff < 2:
                    logger.debug(log_str.format(
                        trade_time, 1, ema9, ema22, ema60,
                        close, diff, macd))
                    self.daily_klines.loc[self.daily_klines.id == kline.id,
                                          's_qualified'] = 1
                    self.trade_status.set_daily_kline(kline, -1, 1)
                    return 1
                elif ema22 > close > ema60:
                    if 2 < diff < 3:
                        logger.debug(log_str.format(
                            trade_time, 2, ema9, ema22, ema60,
                            close, diff, macd))
                        self.daily_klines.loc[self.daily_klines.id == kline.id,
                                              's_qualified'] = 2
                        self.trade_status.set_daily_kline(kline, -1, 2)
                        return 2
                    elif diff > 3:
                        logger.debug(log_str.format(
                            trade_time, 3, ema9, ema22, ema60,
                            close, diff, macd))
                        self.daily_klines.loc[self.daily_klines.id == kline.id,
                                              's_qualified'] = 3
                        self.trade_status.set_daily_kline(kline, -1, 3)
                        return 3
            elif ema60 > ema22:
                if diff < 1:
                    logger.debug(log_str.format(
                        trade_time, 4, ema9, ema22, ema60,
                        close, diff, macd))
                    self.daily_klines.loc[self.daily_klines.id == kline.id,
                                          's_qualified'] = 4
                    self.trade_status.set_daily_kline(kline, -1, 4)
                    return 4
        return 0

    def __calc_pos_by_price(self):
        tick = self.ticks.iloc[-1]
        available = self.account.balance * open_volumes_persent
        volumes = floor(available / tick.ask_price1)
        return volumes

    def __is_last_5_minitus(self, quote_time):
        time_num = int(quote_time.time().strftime("%H%M%S"))
        return 150000 > time_num > 145500

    def __long_stop_profit(self):
        logger = get_logger()
        ts = self.trade_status
        s_p_p = ts.l_stop_profit_point
        dk = self.daily_klines.iloc[-2]
        m30k = self.m30_klines.iloc[-2]
        tick = self.ticks.iloc[-1]
        log_str = "{} <做多>止赢{},现价:{},手数:{},剩余仓位:{},止赢起始价:{}"
        ts.update_l_profit_status(dk, m30k)
        if ts.check_profit_status(1):
            trade_time = get_date_str(tick.datetime)
            last_price = tick.last_price
            s_p_reason = '止盈条件:{},盈亏比达到{},售出{}仓位'

            # 其他止盈条件，达到1:3盈亏比，售出一半仓位
            if ts.l_profit_cond == 0 and ts.l_profit_stage == 1:
                sold_pos = int(self.position.pos_long / 2)
                rest_pos = self.__soldout(1, self.position.pos_long, sold_pos)
                logger.info(log_str.format(
                    trade_time, '0-1', last_price, sold_pos,
                    rest_pos, s_p_p))
                self.tb.r_l_sold_pos(self.underlying_symbol,
                                     ts.tb_count, trade_time,
                                     s_p_reason.format('其他', '1:3', '50%'),
                                     last_price, sold_pos)
            result = ts.should_closeout(dk, m30k, tick)
            if result == 8:
                sold_pos = int(self.position.pos_long * 0.8)
                rest_pos = self.__soldout(1, self.position.pos_long,
                                          sold_pos)
                ts.l_profit_stage = 3
                logger.info(log_str.format(
                    trade_time, '0-2', last_price, sold_pos,
                    rest_pos, s_p_p))
                self.tb.r_l_sold_pos(self.underlying_symbol,
                                     ts.tb_count, trade_time,
                                     s_p_reason.format('其他', '', '80%'),
                                     last_price, sold_pos)
            elif result:
                sold_pos = self.position.pos_long
                logger.info(log_str.format(
                    trade_time,
                    ts.l_profit_cond, last_price,
                    sold_pos, 0, s_p_p))
                self.tb.r_l_sold_pos(self.underlying_symbol,
                                     ts.tb_count, trade_time,
                                     s_p_reason.format(ts.l_profit_cond,
                                                       '', '全部'),
                                     last_price, sold_pos)
                self.__closeout(1)

    def __short_profit_closeout(self, kline):
        logger = get_logger()
        ema22 = kline.ema22
        ema60 = kline.ema60
        close = kline.close
        s_cond = self.trade_status.s_cond
        macd = kline['MACD.close']
        tick = self.ticks.iloc[-1]
        log_str = "{} <做空>止盈条件{} 最后5分钟平仓,现价:{},手数:{}"
        if (s_cond != 4 and close > ema60 and ema22 > ema60 and macd > 0):
            pos_short = self.position.pos_short
            price = tick.last_price
            self.__closeout(-1)
            logger.info(log_str.format(
               get_date_str(tick.datetime),
               s_cond, price, pos_short))

    def __short_stop_profit(self, pos_short):
        logger = get_logger()
        ts = self.trade_status
        tick = self.ticks.iloc[-1]
        price = tick.last_price
        h2k = self.h2_klines.iloc[-2]
        m30k = self.m30_klines.iloc[-2]
        m5k = self.m5_klines.iloc[-2]
        open_price = self.position.open_price_short
        s_cond = self.trade_status.s_cond
        trade_time = tafunc.time_to_datetime(tick.datetime)
        log_str = "{} <做空>止赢条件{},现价:{},手数:{},剩余仓位:{}"
        if pos_short > 0 and ts.check_profit_status(-1):
            if s_cond in [2, 3, 4]:
                if price <= calc_price_by_scale(open_price, s_base_persent,
                                                False, 2):
                    ts.s_stop_loss_price = open_price
                elif price <= calc_price_by_scale(open_price, s_base_persent,
                                                  False, 4):
                    sale_pos = ceil(pos_short / 3)
                    current_pos = self.__soldout(-1, pos_short, sale_pos)
                    logger.info(log_str.format(
                        trade_time, str(ts.s_cond) + '-2',
                        price, sale_pos, current_pos))
            elif s_cond == 1:
                if price <= calc_price_by_scale(open_price, s_base_persent,
                                                False, 3):
                    ts.s_stop_loss_price = open_price
                elif price <= calc_price_by_scale(open_price, s_base_persent,
                                                  False, 5):
                    ts.s_stop_loss_price = calc_price_by_scale(open_price,
                                                               s_base_persent,
                                                               False,
                                                               3)
                elif price <= calc_price_by_scale(open_price, s_base_persent,
                                                  False, 10):
                    sale_pos = ceil(pos_short / 3)
                    current_pos = self.__soldout(-1, pos_short, sale_pos)
                    logger.info(log_str.format(
                        trade_time, str(ts.s_cond) + '-3',
                        price, sale_pos, current_pos))

            if self.__is_last_5_minitus(trade_time):
                if s_cond == 1:
                    self.__short_profit_closeout(h2k)
                elif s_cond == 2:
                    self.__short_profit_closeout(m30k)
                elif s_cond == 3:
                    self.__short_profit_closeout(m5k)
                elif calc_date_delta(ts.trade_date, trade_time) >= 5:
                    self.__closeout(-1)
                    logger.info(log_str.format(
                        trade_time, str(ts.s_cond) + '-3',
                        price, pos_short, 0))

    def __soldout(self, s_or_l, total_vols, sold_volume):
        logger = get_logger()
        log_str = '{} 平仓,多空:{},价格:{},手数:{}'
        target_volume = total_vols - sold_volume
        tick = self.ticks.iloc[-1]
        trade_time = tafunc.time_to_datetime(tick.datetime)
        last_price = tick.last_price
        if target_volume < 0:
            target_volume = 0
        if s_or_l == -1:
            target_volume = - target_volume
        self.target_pos.set_target_volume(target_volume)
        while True:
            self.__api.wait_update()
            if s_or_l == 1:
                if self.position.pos_long == target_volume:
                    logger.debug(log_str.format(
                        trade_time, s_or_l, last_price, sold_volume))
                    break
            else:
                if self.position.pos_short == - target_volume:
                    logger.debug(log_str.format(
                        trade_time, s_or_l, last_price, sold_volume))
                    target_volume = - target_volume
                    break
        return target_volume

    def __closeout(self, s_or_l):
        if s_or_l == 1:
            self.__soldout(1, self.position.pos_long, self.position.pos_long)
            self.trade_status.reset_long()
        elif s_or_l == -1:
            self.__soldout(-1, self.position.pos_short,
                           self.position.pos_short)
            self.trade_status.reset_short()

    def __try_stop_profit(self):
        if self.trade_status.short_or_long == 1:
            self.__long_stop_profit()
        elif self.trade_status.short_or_long == -1:
            pos = self.position.pos_short
            self.__short_stop_profit(pos)

    def __try_stop_loss(self):
        logger = get_logger()
        ts = self.trade_status
        tb = self.tb
        tick = self.ticks.iloc[-1]
        trade_time = get_date_str(tick.datetime)
        last_price = tick.last_price
        if ts.check_stop_loss_status():
            stop_loss_price = 0
            if ts.short_or_long == 1:
                pos = self.position.pos_long
                stop_loss_price = ts.l_stop_loss_price
                tb.r_l_sold_pos(self.underlying_symbol,
                                ts.tb_count, trade_time,
                                f'止损平仓,止损价{stop_loss_price}',
                                last_price, pos)
                self.__closeout(1)
            elif ts.short_or_long == -1:
                pos = self.position.pos_short
                stop_loss_price = ts.s_stop_loss_price
                self.__closeout(-1)
            logger.info(f'{trade_time} 止损,现价:{last_price},'
                        f'止损价:{stop_loss_price}'
                        f'多空:{ts.short_or_long},手数:{pos}')

    def __open_pos(self, long=True, short=True):
        logger = get_logger()
        log_str = '{} 合约:{}开仓 开仓价:{} {}头{}手'
        tick = self.ticks.iloc[-1]
        trade_time = tafunc.time_to_datetime(tick.datetime)
        if long and self.__can_open_volumes_long():
            wanted_pos = self.__calc_pos_by_price()
            self.target_pos.set_target_volume(wanted_pos)
            while True:
                self.__api.wait_update()
                if self.position.pos_long == wanted_pos:
                    break
            logger.info(log_str.format(
                trade_time, self.underlying_symbol,
                self.position.open_price_long, '多', wanted_pos))
            self.trade_status.make_long_deal()
        elif short and self.__can_open_volumes_short():
            wanted_pos = self.__calc_pos_by_price() * -1
            self.target_pos.set_target_volume(wanted_pos)
            while True:
                self.__api.wait_update()
                if self.position.pos_short() == wanted_pos * -1:
                    break
            logger.info(log_str.format(trade_time, self.underlying_symbol,
                        self.position.open_price_short, '空', wanted_pos * -1))
            self.trade_status.make_short_deal()

    def __scan_order_status(self):
        self.__try_stop_loss()
        self.__try_stop_profit()

    def start_trade(self):
        self.__open_pos(short=False)
        self.__scan_order_status()
