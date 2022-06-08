import logging
from tqsdk import TargetPosTask
from math import floor
from utils.tools import calc_indicator, diff_two_value, get_date_str

base_persent = 0.02


def get_logger():
    return logging.getLogger(__name__)


class Trade_status:

    def __init__(self, api, position, quote):
        self.is_trading = False
        self.api = api
        self.daily_condition = 0
        self.quote = quote
        self.open_price_long = position.open_price_long
        self.open_long = position.pos_long
        self.stop_loss_price = 0.0
        self.has_upgrade_stop_loss_price = False
        self.has_begin_sale_for_profit = False
        # 1:实时跟踪止盈，2:收盘前5分钟判断止盈
        self.profit_condition = 0
        self.stop_profit_point = 0.0
        # 以下属性只有在 profit_condition = 3 时使用
        # 1:出售剩余仓位的80%，2:平仓
        self.profit_stage = 0

    def set_daily_kline(self, kline, num):
        self.__daily_kline = kline
        self.__daily_condition = num

    def set_h2_kline(self, kline):
        self.__h2_kline = kline

    def set_m30_kline(self, kline):
        self.__m30_kline = kline

    def make_a_deal(self):
        logger = get_logger()
        if self.is_trading:
            logger.debug("无法创建新交易状态，交易进行中")
            return False
        if (not self.daily_condition or not self.__daily_kline or
           not self.__h2_kline or not self.__m30_kline):
            logger.debug("创建交易状态失败, 日线条件或K线没有正确设置")
            return False
        self.is_trading = True
        ema9 = self.__h2_kline.ema9
        ema22 = self.__h2_kline.ema22
        ema60 = self.__h2_kline.ema60
        close = self.__h2_kline.close
        macd = self.__h2_kline["MACD.close"]
        self.stop_loss_price = self.open_price_long * (1 - base_persent)
        self.stop_profit_point = self.open_price_long * (1 + base_persent * 3)
        logger.info(f"{get_date_str(self.quote.datetime)}\
止损为:{self.stop_loss_price}")
        logger.info(f"{get_date_str(self.quote.datetime)}\
止赢起始价为:{self.stop_loss_price}")
        if (ema22 > ema60 and close > ema22 and diff_two_value(ema22, ema60) <
           1.2 and self.__daily_condition in [1, 2, 3, 4]):
            self.profit_condition = 1
        elif (ema60 > ema22 and ema22 > close and close > ema9 and macd > 0 and
              self.__daily_condition == 5):
            self.profit_condition = 1
        else:
            self.profit_condition = 2

    def check_profit_status(self):
        self.api.wait_update()
        price = self.open_price_long
        current_price = self.quote.last_price
        if current_price >= price * (1 + base_persent * 3):
            self.has_begin_sale_for_profit = True


class Underlying_symbol_trade:

    '主连合约交易类'
    def __init__(self, api, symbol, account):
        self.api = api
        self.quote = api.get_quote(symbol)
        self.underlying_symbol = self.quote.underlying_symbol
        self.symbol = symbol
        self.position = api.get_position(self.underlying_symbol)
        self.target_pos = TargetPosTask(api, self.underlying_symbol)
        self.account = account
        self.trade_status = Trade_status(api, self.position, self.quote)
        self.daily_klines = api.get_kline_serial(self.underlying_symbol,
                                                 60*60*24)
        self.h2_klines = api.get_kline_serial(self.underlying_symbol, 60*60*2)
        self.m30_klines = api.get_kline_serial(self.underlying_symbol, 60*30)
        self.m5_klines = api.get_kline_serial(self.underlying_symbol, 60*5)

        calc_indicator(self.daily_klines, is_daily_kline=True)
        calc_indicator(self.m30_klines)
        calc_indicator(self.h2_klines)
        calc_indicator(self.m5_klines)

    # 根据均线条件和是否有持仓判断是否可以开仓
    def __can_open_volumes(self):
        if self.position.pos_long == 0:
            result = self.__is_match_daily_kline_condition()
            if result:
                if self.__is_match_2h_kline_condition(result):
                    if(self.__is_match_30m_kline_condition()):
                        if self.__is_match_5m_kline_condition():
                            if self.position.pos_long == 0:
                                return True
        return False

    def __is_match_5m_kline_condition(self):
        logger = get_logger()
        kline = self.m5_klines.iloc[-2]
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        diff = diff_two_value(close, ema60)
        if close > ema60 and macd > 0 and diff < 1.2:
            logger.debug(f"{get_date_str(self.quote.datetime)}\
满足5分钟线条件,ema60:{ema60},收盘:{close}, MACD:{macd},diff:{diff}")
            return True
        return False

    # 判断是否满足30分钟线条件
    def __is_match_30m_kline_condition(self):
        logger = get_logger()
        kline = self.m30_klines.iloc[-2]
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        diff = diff_two_value(close, ema60)
        if kline["qualified"]:
            return True
        if close > ema60 and macd > 0 and diff < 1.2:
            logger.debug(f"{get_date_str(self.quote.datetime)}\
满足30分钟线条件,ema60:{ema60},收盘:{close}, MACD:{macd}, diff:{diff}")
            self.m30_klines.loc[self.m30_klines.id == kline.id,
                                'qualified'] = 1
            self.trade_status.set_m30_kline(kline)
            return True
        return False

    def __is_match_2h_kline_condition(self, num):
        logger = get_logger()
        kline = self.h2_klines.iloc[-2]
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        if kline["qualified"]:
            return True
        if (close > ema22 and close > ema60 and diff_two_value(ema22, ema60) >
           3):
            return False
        if num in [1, 2, 5]:
            if close > ema60 or macd > 0:
                logger.debug(f"{get_date_str(self.quote.datetime)}\
满足两小时线条件1,ema22:{ema22},ema60:{ema60},收盘:{close},MACD:{macd}")
                self.h2_klines.loc[self.h2_klines.id == kline.id,
                                   'qualified'] = 1
                self.trade_status.set_h2_kline(kline)
                return True
        elif num in [3, 4]:
            if (macd > 0 or close > ema60) and ema22 > ema60:
                logger.debug(f"{get_date_str(self.quote.datetime)}\
满足两小时线条件2,ema22:{ema22},ema60:{ema60},收盘:{close},MACD:{macd}")
                self.h2_klines.loc[self.h2_klines.id == kline.id,
                                   'qualified'] = 1
                self.trade_status.set_h2_kline(kline)
                return True
        return False

    # 判断是否满足日K线条件
    def __is_match_daily_kline_condition(self):
        # 如果id不足59，说明合约成交日还未满60天，ema60均线还不准确
        # 故不能作为判断依据
        logger = get_logger()
        kline = self.daily_klines.iloc[-2]
        ema9 = kline.ema9
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        # logger.info(kline)
        if kline["qualified"]:
            return kline["qualified"]
        elif kline.id > 58:
            diff = diff_two_value(ema9, ema60)
            if ema22 < ema60:
                if diff < 1 and close > ema60 and macd > 0:
                    logger.debug(f"{get_date_str(self.quote.datetime)}\
满足日线条件1,ema9:{ema9},ema22:{ema22},ema60:{ema60},\
收盘:{close},diff:{diff},MACD:{macd}")
                    self.daily_klines.loc[self.daily_klines.id == kline.id,
                                          'qualified'] = 1
                    self.trade_status.set_daily_kline(kline, 1)
                    return 1
            elif ema22 > ema60:
                if ema9 > ema22:
                    if diff < 1 and close > ema22:
                        logger.debug(f"{get_date_str(self.quote.datetime)}\
满足日线条件2,ema9:{ema9},ema22:{ema22},ema60:{ema60},\
收盘:{close},diff:{diff}")
                        self.daily_klines.loc[self.daily_klines.id == kline.id,
                                              'qualified'] = 2
                        self.trade_status.set_daily_kline(kline, 2)
                        return 2
                    elif diff > 1 and diff < 3 and close > ema60:
                        logger.debug(f"{get_date_str(self.quote.datetime)}\
满足日线条件3,ema9:{ema9},ema22:{ema22},ema60:{ema60},\
收盘:{close},diff:{diff}")
                        self.trade_status.set_daily_kline(kline, 3)
                        return 3
                elif ema9 < ema22:
                    if (diff > 1 and diff < 3 and (close > ema60
                                                   and close < ema22)):
                        logger.debug(f"{get_date_str(self.quote.datetime)}\
满足日线条件4,ema9:{ema9},ema22:{ema22},ema60:{ema60},\
收盘:{close},diff:{diff}")
                        self.daily_klines.loc[self.daily_klines.id == kline.id,
                                              'qualified'] = 4
                        self.trade_status.set_daily_kline(kline, 4)
                        return 4
                else:
                    if diff > 3 and (close > ema60 and close < ema22):
                        logger.debug(f"{get_date_str(self.quote.datetime)}\
满足日线条件4,ema9:{ema9},ema22:{ema22},ema60:{ema60},\
收盘:{close},diff:{diff}")
                        self.daily_klines.loc[self.daily_klines.id == kline.id,
                                              'qualified'] = 5
                        self.trade_status.set_daily_kline(kline, 5)
                        return 5

    def calc_volume_by_price(self):
        available = self.account.balance*0.02
        volumes = floor(available / self.quote.ask_price1)
        self.volumes = volumes
        return volumes

    def scan_order_status(self):
        logger = get_logger()
        self.__try_stop_loss()

    def __try_stop_profit(self):
        logger = get_logger()

    def __try_stop_loss(self):
        logger = get_logger()
        position_log = self.position.pos_long
        if position_log > 0\
           and self.quote.last_price <= self.stop_loss_price:
            self.target_pos.set_target_volume(0)
            while True:
                self.api.wait_update()
                if self.position.pos_long == 0:
                    break
            logger.info(f"{get_date_str(self.quote.datetime)}止损,\
现价:{self.quote.last_price}, 止损价:{self.stop_loss_price} \
手数:{position_log}")
            self.stop_loss_price = 0.0
            self.has_upgrade_stop_loss_price = False

    def open_volumes(self):
        logger = get_logger()
        if self.__can_open_volumes():
            wanted_volume = self.calc_volume_by_price()
            self.target_pos.set_target_volume(wanted_volume)
            while True:
                self.api.wait_update()
                if self.position.pos_long == wanted_volume:
                    break
            logger.info(f"{get_date_str(self.quote.datetime)}\
合约:{self.underlying_symbol} 开仓价{self.position.open_price_long}\
多头{wanted_volume}手")
            self.trade_status.make_a_deal()

    def upgrade_stop_loss_price(self):
        logger = get_logger()
        if (not self.has_upgrade_stop_loss_price
            and self.position.pos_long > 0
            and self.quote.last_price >=
                self.position.open_price_long * (1 + self.base_persent * 2)):
            self.stop_loss_price = self.position.open_price_long \
                * (1 + self.base_persent)
            self.has_upgrade_stop_loss_price = True
            logger.info(f"{get_date_str(self.quote.datetime)} \
合约:{self.underlying_symbol},现价{self.quote.last_price}\
达到1:2盈亏比，止损提高至{self.stop_loss_price}")
