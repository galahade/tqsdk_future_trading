from math import floor, ceil
from tqsdk.objs import Quote, Position
from tqsdk import TqApi, TargetPosTask, tafunc
from utils.tools import Trade_Book, get_date_str, diff_two_value
from utils.common import LoggerGetter
# from utils.tools import calc_indicator, diff_two_value, get_date_str,\
# calc_date_delta, Trade_Book


class Trade_Status:
    logger = LoggerGetter()
    open_volumes_persent = 0.02

    def __init__(self, position: Position, quote: Quote, tb: Trade_Book)\
            -> None:
        self._pos = position
        self._quote = quote
        self.is_trading = False
        self._tb = tb
        self._symbol = quote.underlying_symbol

    def set_last_daily_kline(self, kline):
        self._daily_kline = kline

    def set_last_h2_kline(self, kline):
        self._h2_kline = kline

    def set_m30_kline(self, kline):
        self._m30_kline = kline

    def set_deal_info(self) -> None:
        logger = self.logger
        if self.is_trading:
            logger.warning("无法创建Trade_Status, 交易进行中。")
        self.is_trading = False
        self._set_sale_prices()
        self._set_stop_profit_values()
        self._record_to_excel()

    def get_stoplose_status(self) -> bool:
        pass

    def get_profit_status(self) -> bool:
        pass

    def get_current_price(self) -> float:
        return self._quote.last_price

    def get_current_date_str(self):
        return get_date_str(self._quote.datetime)

    def reset(self):
        self.is_trading = False

    @classmethod
    def calc_price(cls, price: float, is_add: bool, scale: int) -> float:
        if is_add:
            return round(price * (1 + cls.base_persent * scale), 2)
        else:
            return round(price * (1 - cls.base_persent * scale), 2)

    def _set_sale_prices(self) -> None:
        pass

    def _set_stop_profit_values(self) -> None:
        self._profit_stage = 0

    def _record_to_excel(self) -> None:
        pass

    def _is_last_5_m(self) -> bool:
        t_time = tafunc.time_to_datetime(self._quote.datetime)
        time_num = int(t_time.time().strftime("%H%M%S"))
        return 150000 > time_num > 145500


class Trade_Status_Long(Trade_Status):

    base_persent = 0.02

    def set_last_daily_kline(self, num, *args):
        '''重写父类方法。
        设置符合开仓条件的日线，并记录符合第几个日线条件
        '''
        super().set_last_daily_kline(*args)
        self._daily_cond = num

    def set_last_h2_kline(self, num, *args):
        '''重写父类方法。
        设置符合条件的两小时线，同时记录符合哪个两小时条件。
        '''
        super().set_last_h2_kline(*args)
        self._h2_cond = num

    def get_stoplose_status(self) -> bool:
        if self.is_trading:
            pos = self._pos.pos_long
            price = self.get_current_price()
            if pos > 0 and price <= self._stop_loss_price:
                return True
        return False

    def get_profit_status(self) -> bool:
        logger = self.logger
        if self.is_trading:
            price = self.get_current_price()
            log_str = '{} <做多>现价:{} 达到止盈价{}开始监控'
            if self._begin_stop_profit:
                return True
            elif price >= self._stop_profit_point:
                self._begin_stop_profit = True
                logger.info(log_str.format(
                    self.get_current_date_str(),
                    price,
                    self._stop_profit_point))
                return True
        return False

    def update_profit_stage(self, dk, m30k):
        '''当开仓后，使用该方法判断是否达到监控止盈条件，
        当开始监控止盈后，根据最新价格，更新止损价格和止盈阶段
        为止盈提供依据
        '''
        pos = self._pos.pos_long
        if pos > 0 and self.get_profit_status():
            if self._profit_stage == 0:
                self._profit_stage = 1
            elif self._profit_cond == 0:
                if self._profit_stage == 1:
                    self._profit_stage = 2

    def is_final5_closeout(self, dk, m30k):
        '''在当日交易结束前5分钟，判断是否应该清仓
        可返回3种状态：
        1. True 应该清仓
        2. False 不清仓
        3. 8 售出持有仓位的80%
        '''
        logger = self.logger
        log_str = '{} <做多>止盈条件:{},当前价:{},售出比例:{}日线EMA22:{},30mEMA60:{}'
        ema22 = dk.ema22
        price = self.get_current_price()
        current_date = self.get_current_date_str()
        if self._is_last_5_m():
            if (self._profit_cond == 1 and price < ema22):
                logger.debug(log_str.format(
                 current_date, 1, price, '100%', ema22, m30k.ema60))
                return True
            elif self._profit_cond == 0:
                if self._profit_stage == 2:
                    if price < m30k.ema60:
                        logger.debug(log_str.format(
                         current_date, 0, price, '80%', ema22, m30k.ema60))
                        return 8
                elif self._profit_stage == 3:
                    if price < ema22:
                        logger.debug(log_str.format(
                         current_date, 0, price, '100%', ema22, m30k.ema60))
                        return True
        return False

    def _set_sale_prices(self) -> None:
        open_pos_price = self._pos.open_price_long
        current_date = self.get_current_date_str()
        self._stop_loss_price = self.calc_price(open_pos_price, False, 1)
        self._stop_profit_point = self.calc_price(open_pos_price, True, 3)
        self.logger.info(f'{current_date}'
                         f'<做多>止损设为:{self._stop_loss_price}'
                         f'止盈起始价为:{self._stop_profit_point}')

    def _set_stop_profit_values(self):
        '''根据两小时线和日线的条件，设置止盈适用条件。
        默认为0:即达到止盈价格后卖出50%仓位，然后分阶段止盈。
        当止盈条件为1:每日收盘前5分钟判断是否平仓。
        '''
        super()._set_stop_profit_values()
        ema9 = self._h2_kline.ema9
        ema22 = self._h2_kline.ema22
        ema60 = self._h2_kline.ema60
        close = self._h2_kline.close
        macd = self._h2_kline['MACD.close']
        diff_22_60 = diff_two_value(ema22, ema60)
        diff_c_60 = diff_two_value(close, ema60)
        if (self._daily_cond in [1, 2, 3, 4] and close > ema22 > ema60
           and (diff_c_60 < 1.2 or diff_22_60 < 1)):
            self._profit_cond = 1
        elif (self._daily_cond == 5 and ema60 > ema22 > ema9 and macd > 0
              and close > ema9):
            self._profit_cond = 1

    def _record_to_excel(self):
        self.tb_count = self._tb.r_l_open_pos(
            self._symbol, self.get_current_date_str(),
            self._daily_cond, self._h2_cond,
            self._pos.open_price_long,
            self._pos.pos_long
        )
        pass

    def reset(self):
        super().reset()
        self._daily_cond = 0
        self._h2_cond = 0
        self._stop_loss_price = 0.0
        self._begin_stop_profit = False
        self._profit_cond = 0
        self._stop_profit_point = 0.0
        self._profit_stage = 0


class Future_Trade:
    ''' 期货交易基类，是多空交易类的父类。定义了一个期货交易对外开放的接口和内部
    主要方法。
    '''
    logger = LoggerGetter()

    def __init__(self, api: TqApi, symbol: str, trade_book: Trade_Book)\
            -> None:
        self._api = api
        self._symbol = symbol
        self._pos = api.get_position(symbol)
        self._trade_tool = TargetPosTask(api, symbol)
        self._account = api.get_account()
        self._daily_klines = api.get_kline_serial(symbol, 60*60*24)
        self._tb = trade_book
        self._ts = self.get_trade_status()

    def get_trade_status(self) -> Trade_Status:
        pass

    def get_quote(self) -> Quote:
        return self._api.get_quote(self._symbol)

    def _try_open_pos(self) -> None:
        '''
        尝试进行开仓，当没有任何持仓时进行。
        需要被具体的多空交易类重写。
        '''
        pass

    def _try_for_sale(self) -> None:
        '''
        尝试在开仓后，进行止损或止盈。
        需要被具体的多空交易类重写。
        '''
        pass

    def try_trade(self) -> None:
        '''
        交易类对外暴露的接口，每次行情更新时调用这个方法尝试交易
        '''
        self._try_open_pos()
        self._try_for_sale()
