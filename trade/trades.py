from math import floor
from tqsdk.objs import Quote, Position
from tqsdk import TqApi, TargetPosTask, tafunc
from utils.tools import Trade_Book, get_date_str, get_date, diff_two_value,\
    calc_indicator, examine_symbol
from utils.common import LoggerGetter
from datetime import datetime


class Trade_Status:
    logger = LoggerGetter()
    open_volumes_persent = 0.02

    def __init__(self, position: Position, symbol: str, quote: Quote,
                 tb: Trade_Book) -> None:
        self._pos = position
        self._quote = quote
        self.is_trading = False
        self._tb = tb
        self._symbol = symbol
        self.tb_count = 0

    def set_last_daily_kline(self, cond_num, kline):
        ''' 设置符合开仓条件的日线，并记录符合第几个日线条件
        '''
        self._daily_kline = kline
        self._daily_cond = cond_num

    def set_last_h2_kline(self, kline):
        self._h2_kline = kline

    def set_last_m30_kline(self, kline):
        self._m30_kline = kline

    def set_deal_info(self, pos: int) -> None:
        logger = self.logger
        if self.is_trading:
            logger.warning("无法创建Trade_Status, 交易进行中。")
        self.is_trading = True
        self._set_stop_profit_values()
        self._set_sale_prices(pos)
        self._record_to_excel()

    def get_stoplose_status(self) -> bool:
        '''抽象方法，返回是否需要止损
        '''
        pass

    def get_profit_status(self) -> bool:
        '''抽象方法，返回是否需要止盈
        '''
        pass

    def get_current_price(self) -> float:
        '''接口，返回当前交易价格
        '''
        return self._quote.last_price

    def get_current_date_str(self):
        '''接口,返回当前交易时间
        '''
        return get_date_str(self._quote.datetime)

    def reset(self):
        '''接口，需要子类增加逻辑，重置内部变量状态
        '''
        self.is_trading = False
        self._has_improved_sl_price = False
        self._stop_loss_price = 0.0
        self._begin_stop_profit = False
        self._stop_profit_point = 0.0
        self._profit_stage = 0
        self._t_price = 0.0
        self._pos_quantity = 0

    @classmethod
    def calc_price(cls, price: float, is_add: bool, scale: float) -> float:
        '''类方法，按盈亏比计算目标价格
        '''
        if is_add:
            return round(price * (1 + cls.base_persent * scale), 2)
        else:
            return round(price * (1 - cls.base_persent * scale), 2)

    def _set_sale_prices(self, pos: int) -> None:
        '''抽象方法，设置止盈止损价格
        当买入成交后，按成交价格设置目标止损价和止盈起始价
        '''
        pass

    def _set_stop_profit_values(self) -> None:
        '''抽象方法，设置止盈类型和止盈阶段
        '''
        self._profit_stage = 0

    def _record_to_excel(self) -> None:
        '''抽象方法，将开仓记录保存到excel中
        '''
        pass

    def _is_last_5_m(self) -> bool:
        '''判断交易时间是否为当日最后5分钟
        '''
        t_time = tafunc.time_to_datetime(self._quote.datetime)
        time_num = int(t_time.time().strftime("%H%M%S"))
        return 150000 > time_num > 145500

    def record_sell_to_excel(self, t_time: str, sold_reason: str,
                             price: float, pos: int) -> None:
        '''抽象方法，在excel中插入卖出记录
        '''
        pass

    def _get_pos_number(self) -> int:
        '''抽象方法,返回当前合约持仓量
        '''
        pass


class Trade_Status_Short(Trade_Status):
    logger = LoggerGetter()
    base_persent = 0.03

    def get_stoplose_status(self) -> bool:
        if self.is_trading:
            pos = self._pos.pos_short
            price = self.get_current_price()
            if pos > 0 and price >= self._stop_loss_price:
                return True
        return False

    def try_improve_sl_price(self) -> None:
        '''尝试提高止损价
        当盈亏比达到1:10后将止损价格提升至1:5
        '''
        logger = self.logger
        price = self.get_current_price()
        trade_time = self.get_current_date_str()
        log_str = '{}<做空>现价{}达到1:{}盈亏比,将止损价提高至{}'
        o_price = self._pos.open_price_short
        calc_price = self.calc_price
        if hasattr(self, "_has_improved_sl_price"):
            if self._has_improved_sl_price:
                return
        else:
            if price <= calc_price(o_price, False, 10):
                self._stop_loss_price = calc_price(o_price, False, 5)
                logger.debug(log_str.format(
                    trade_time, price, 10, self._stop_loss_price))
                self._has_improved_sl_price = True

    def get_profit_status(self) -> bool:
        '''返回是否满足止盈条件。当第一次符合止盈条件时，设置相关止盈参数
        '''
        logger = self.logger
        if self.is_trading:
            price = self.get_current_price()
            log_str = ('{} <做空>现价:{} 达到止盈价{}开始监控,'
                       '止损价提高到:{}')
            if hasattr(self, "_begin_stop_profit"):
                if self._begin_stop_profit:
                    return True
            elif price <= self._stop_profit_point:
                self._begin_stop_profit = True
                self._stop_loss_price = self._pos.open_price_short
                logger.info(log_str.format(
                    self.get_current_date_str(),
                    price, self._stop_profit_point,
                    self._stop_loss_price
                ))
                return True
        return False

    def is_final5_closeout(self, dk):
        '''在当日交易结束前5分钟，判断是否应该清仓
        可返回2种状态：
        1. True 应该清仓
        2. False 不清仓
        '''
        logger = self.logger
        log_str = ('{}<做空>满足最后5分钟止盈,当前价:{},'
                   '日线EMA9:{},日线EMA22:{},MACD:{}')
        ema9 = dk.ema9
        ema22 = dk.ema22
        macd = dk['MACD.close']
        price = self.get_current_price()
        trade_time = self.get_current_date_str()
        if self._is_last_5_m():
            if (macd > 0 and ema9 > ema22):
                logger.debug(log_str.format(
                    trade_time, price, ema9, ema22, macd))
                return True
        return False

    def _set_sale_prices(self, pos: int) -> None:
        open_pos_price = self._pos.open_price_short
        trade_time = self.get_current_date_str()
        self._t_price = open_pos_price
        self._pos_quantity = self._pos.pos_short
        self._stop_loss_price = self.calc_price(open_pos_price, True, 1)
        self._stop_profit_point = self.calc_price(open_pos_price, False, 3)
        self.logger.info(f'{trade_time}'
                         f'<做空>止损设为:{self._stop_loss_price}'
                         f'止盈起始价为:{self._stop_profit_point}')

    def _record_to_excel(self) -> None:
        self.tb_count = self._tb.r_s_open_pos(
            self._symbol, self.get_current_date_str(),
            self._pos.open_price_short,
            self._pos.pos_short
        )

    def record_sell_to_excel(self, t_time: str, sold_reason: str,
                             price: float, pos: int) -> None:
        self._tb.r_sold_pos(self._symbol, self.tb_count, t_time, sold_reason,
                            price, pos, False)

    def reset(self):
        super().reset()

    def _get_pos_number(self) -> int:
        '''返回当前合约持仓量
        '''
        return self._pos.pos_short


class Trade_Status_Long(Trade_Status):
    logger = LoggerGetter()
    base_persent = 0.02

    def set_last_h2_kline(self, cond_num, *args):
        '''重写父类方法。
        设置符合条件的两小时线，同时记录符合哪个两小时条件。
        '''
        super().set_last_h2_kline(*args)
        self._h2_cond = cond_num

    def get_stoplose_status(self) -> bool:
        if self.is_trading:
            pos = self._get_pos_number()
            price = self.get_current_price()
            if pos > 0 and price <= self._stop_loss_price:
                return True
        return False

    def try_improve_sl_price(self) -> bool:
        logger = self.logger
        price = self.get_current_price()
        trade_time = self.get_current_date_str()
        log_str = '{}<做多>止盈条件{}现价{}达到1:{}盈亏比,将止损价提高至{}'
        o_price = self._t_price
        calc_price = self.calc_price
        if hasattr(self, "_has_improved_sl_price"):
            if self._has_improved_sl_price:
                return
        else:
            if self._profit_cond in [1, 2, 3]:
                standard_price = calc_price(o_price, True, 6)
                if price >= standard_price:
                    self._stop_loss_price = calc_price(o_price, True, 3)
                    logger.debug(log_str.format(
                        trade_time, 1, price, 6, self._stop_loss_price))
                    self._has_improved_sl_price = True

    def get_profit_status(self) -> int:
        '''返回满足止盈条件的序号，并设置相关止盈参数
        0:不满足止盈条件
        1:止盈条件1
        2:止盈条件2
        3:止盈条件3
        4:止盈条件4
        '''
        logger = self.logger
        if self.is_trading:
            price = self.get_current_price()
            log_str = ('{} <做多>现价:{} 达到止盈价{}开始监控,'
                       '止损价提高到:{}')
            # if price >= 3892:
            #     logger.debug(f"{self.get_current_date_str()},price:{price}")
            #     logger.debug(self.__dict__)
            if hasattr(self, "_begin_stop_profit"):
                if self._begin_stop_profit:
                    return self._profit_cond
            if price >= self._stop_profit_point:
                self._begin_stop_profit = True
                if self._profit_cond == 4:
                    self._stop_loss_price = self._t_price
                    self._profit_stage = 1
                logger.info(log_str.format(
                    self.get_current_date_str(),
                    price, self._stop_profit_point,
                    self._stop_loss_price
                ))
                return self._profit_cond
        return 0

    def update_profit_stage(self, dk, m30k):
        '''暂时弃用-当开仓后，使用该方法判断是否达到监控止盈条件，
        当开始监控止盈后，根据最新价格，更新止损价格和止盈阶段
        为止盈提供依据
        '''
        pos = self._get_pos_number()
        if pos > 0 and self.get_profit_status():
            if self._profit_stage == 0:
                self._profit_stage = 1
            elif self._profit_cond == 0:
                if self._profit_stage == 1:
                    self._profit_stage = 2

    def is_final5_closeout(self, dk):
        '''在当日交易结束前5分钟，判断是否应该清仓
        可返回2种状态：
        1. True 应该清仓
        2. False 不清仓
        '''
        logger = self.logger
        log_str = ('{}<做多>满足最后5分钟止盈,止盈条件:{},当前价:{},'
                   '日线EMA9:{},日线EMA22:{},EMA60:{}')
        ema9 = dk.ema9
        ema22 = dk.ema22
        ema60 = dk.ema60
        price = self.get_current_price()
        trade_time = self.get_current_date_str()
        if self._is_last_5_m():
            if (self._profit_cond == 1 and price < ema60 and
               ema9 < ema22):
                logger.debug(log_str.format(
                    trade_time, 1, price, ema9, ema22, ema60))
                return True
            elif (self._profit_cond in [2, 3] and price < ema22
                  and ema9 < ema22):
                logger.debug(log_str.format(
                    trade_time, 2, price, ema9, ema22, ema60))
                return True
        return False

    def _set_sale_prices(self, pos: int) -> None:
        open_pos_price = self._get_open_price()
        current_date = self.get_current_date_str()
        self._t_price = open_pos_price
        self._pos_quantity = self._get_pos_number()
        self._stop_loss_price = self.calc_price(open_pos_price, False, 1)
        if self._profit_cond in [1, 2, 3]:
            self._stop_profit_point = self.calc_price(open_pos_price, True, 3)
        if self._profit_cond in [4]:
            self._stop_profit_point = self.calc_price(
                open_pos_price, True, 1.5)
        self.logger.info(f'{current_date}'
                         f'<做多>开仓价:{open_pos_price}'
                         f'止损设为:{self._stop_loss_price}'
                         f'止盈起始价为:{self._stop_profit_point}')

    def _set_stop_profit_values(self):
        '''设置止盈操作的种类
        止盈操作分为两种，每种对应不同的止盈策略
        '''
        super()._set_stop_profit_values()
        if (self._daily_cond in [1, 2]):
            self._profit_cond = 1
        elif (self._daily_cond in [5]):
            self._profit_cond = 2
        elif (self._daily_cond in [3] and self._h2_cond == 6):
            self._profit_cond = 3
        elif (self._daily_cond in [3, 4] and self._h2_cond == 3):
            self._profit_cond = 4

    def _record_to_excel(self):
        self.tb_count = self._tb.r_l_open_pos(
            self._symbol, self.get_current_date_str(),
            self._daily_cond, self._h2_cond,
            self._pos.open_price_long,
            self._get_pos_number()
        )

    def reset(self):
        super().reset()
        self._daily_cond = 0
        self._h2_cond = 0
        self._profit_cond = 0

    def record_sell_to_excel(self, t_time: str, sold_reason: str,
                             price: float, pos: int) -> None:
        self._tb.r_sold_pos(self._symbol, self.tb_count, t_time, sold_reason,
                            price, pos, True)

    def _get_pos_number(self) -> int:
        '''返回当前合约持仓量
        '''
        return self._pos.pos_long

    def _get_open_price(self) -> float:
        return self._pos.open_price_long


class Trade_Status_Virtual(Trade_Status_Long):
    logger = LoggerGetter()
    base_persent = 0.02

    def _get_pos_number(self) -> int:
        '''返回当前合约持仓量
        '''
        if hasattr(self, '_pos_quantity'):
            return self._pos_quantity
        else:
            return 0

    def _get_open_price(self) -> float:
        return self.get_current_price()

    def _set_sale_prices(self, pos: int) -> None:
        self._pos_quantity = pos
        super()._set_sale_prices(pos)

    def _record_to_excel(self):
        self.tb_count = self._tb.r_lv_open_pos(
            self._symbol, self.get_current_date_str(),
            self._daily_cond, self._h2_cond,
            self._t_price,
            self._get_pos_number()
        )

    def record_sell_to_excel(self, t_time: str, sold_reason: str,
                             price: float, pos: int) -> None:
        sold_reason = str(sold_reason) + '虚拟售出'
        self._tb.r_sold_pos(self._symbol, self.tb_count, t_time, sold_reason,
                            price, pos, True)

    def create_tsl(self) -> Trade_Status_Long:
        # logger = self.logger
        # logger.debug(self.__dict__)
        tsl = Trade_Status_Long(self._pos, self._symbol, self._quote,
                                self._tb)
        tsl.is_trading = self.is_trading
        tsl.tb_count = self.tb_count
        if hasattr(self, "_has_improved_sl_price"):
            tsl._has_improved_sl_price = self._has_improved_sl_price
        if hasattr(self, "_begin_stop_profit"):
            tsl._begin_stop_profit = self._begin_stop_profit
        tsl._stop_loss_price = self._stop_loss_price
        tsl._stop_profit_point = self._stop_profit_point
        tsl._profit_stage = self._profit_stage
        tsl._t_price = self._t_price
        tsl._pos_quantity = self._pos_quantity
        tsl._daily_cond = self._daily_cond
        tsl._h2_cond = self._h2_cond
        tsl._profit_cond = self._profit_cond
        return tsl


class Future_Trade:
    '''期货交易基类，是多空交易类的父类。定义了一个期货交易对外开放的接口和内部
    主要方法。
    '''
    logger = LoggerGetter()

    def __init__(self, api: TqApi, symbol: str, trade_book: Trade_Book)\
            -> None:
        self._api = api
        self._symbol = symbol
        self._pos = api.get_position(symbol)
        self._quote = self._api.get_quote(self._symbol)
        self._trade_tool = TargetPosTask(api, symbol)
        self._account = api.get_account()
        self._daily_klines = api.get_kline_serial(symbol, 60*60*24)
        self._h2_klines = api.get_kline_serial(symbol, 60*60*3)
        self._m30_klines = api.get_kline_serial(symbol, 60*30)
        self._m5_klines = api.get_kline_serial(symbol, 60*5)
        self._tb = trade_book
        self._ts: Trade_Status
        self.calc_criteria(0)

    def _match_dk_cond(self) -> bool:
        pass

    def _match_2hk_cond(self) -> bool:
        pass

    def _match_30mk_cond(self) -> bool:
        pass

    def _match_5mk_cond(self) -> bool:
        pass

    def _calc_open_pos_number(self) -> bool:
        available = self._account.balance * Trade_Status.open_volumes_persent
        pos = floor(available / self.get_quote().bid_price1)
        return pos

    def _can_open_ops(self):
        if self._ts._get_pos_number() == 0:
            if self._match_dk_cond():
                if self._match_2hk_cond():
                    if self._match_30mk_cond():
                        if self._match_5mk_cond():
                            return True

    def _stop_profit(self) -> None:
        '''当满足止盈操作时，按止盈不同阶段操作。
        需要被多空交易子类重写
        '''
        pass

    def _sale_target_pos(self, target_pos) -> int:
        '''交易工具类需要的目标仓位，需要子类重写
        做多返回正数，做空返回负数
        '''
        pass

    def _trade_pos(self, total_pos, sale_pos) -> int:
        '''final 方法，进行期货交易。开仓平仓，多空都适用。
        '''
        logger = self.logger
        log_str = '{} 交易,excel序号:{}价格:{}手数:{}'
        quote = self.get_quote()
        ts = self._ts
        target_pos = total_pos - sale_pos
        trade_time = ts.get_current_date_str()
        price = quote.last_price
        if target_pos <= 0:
            target_pos = 0
        self._trade_tool.set_target_volume(self._sale_target_pos(target_pos))
        while True:
            self._api.wait_update()
            # 假设多空不同时开仓，如多空同时开仓，需修改以下逻辑
            if self._pos.pos == target_pos:
                logger.debug(log_str.format(
                    trade_time, ts.tb_count, price, sale_pos))
                break
        return target_pos

    def _closeout(self) -> None:
        pos_number = self._ts._get_pos_number()
        self._trade_pos(pos_number, pos_number)
        self._ts.reset()

    def get_quote(self) -> Quote:
        return self._quote

    def _try_stop_loss(self) -> None:
        logger = self.logger
        ts = self._ts
        trade_time = ts.get_current_date_str()
        price = ts.get_current_price()
        if ts.get_stoplose_status():
            stop_loss_price = 0
            pos = self._ts._get_pos_number()
            stop_loss_price = ts._stop_loss_price
            message = '止损'
            if hasattr(self._ts, "_has_improved_sl_price"):
                if self._ts._has_improved_sl_price:
                    message = '跟踪止盈'
            ts.record_sell_to_excel(trade_time, message, price, pos)
            logger.info(f'{trade_time} <多空>{message},现价:{price},'
                        f'止损价:{stop_loss_price},手数:{pos},'
                        f'止盈开始价:{ts._stop_profit_point}')
            self._closeout()

    def _try_stop_profit(self) -> None:
        ''' 止盈抽象方法，需要多_空子类重写
        '''
        pass

    def _try_open_pos(self) -> bool:
        ''' 开仓,当没有任何持仓并满足开仓条件时买入。
        子类可以利用该方法加入日志等逻辑
        '''
        if self._can_open_ops():
            ts = self._ts
            logger = self.logger
            log_str = '{}合约:{}<多空>开仓,开仓价:{},{}手'
            open_pos = self._calc_open_pos_number()
            self._trade_pos(open_pos, 0)
            ts.set_deal_info(open_pos)
            trade_time = self._ts.get_current_date_str()
            open_pos = self._ts._pos_quantity
            logger.info(log_str.format(
                trade_time, self._symbol, ts._t_price,
                open_pos))
            return True
        return False

    def _try_sell_pos(self) -> None:
        ''' final 方法，尝试在开仓后进行止损或止盈。
        '''
        self._try_stop_loss()
        self._try_stop_profit()

    def try_trade(self) -> None:
        ''' final 方法，交易类对外接口，
        每次行情更新时调用这个方法尝试交易
        '''
        self._try_open_pos()
        self._try_sell_pos()

    def _get_last_dk_line(self):
        return self._daily_klines.iloc[-2]

    def _get_last_h2_kline(self):
        return self._h2_klines.iloc[-2]

    def _get_last_m30_kline(self):
        return self._m30_klines.iloc[-2]

    def get_Kline_values(self, kline) -> tuple:
        ema9 = kline.ema9
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        open_p = kline.open
        trade_time = self._ts.get_current_date_str()
        return (ema9, ema22, ema60, macd, close, open_p, trade_time)

    def calc_criteria(self, k_type: int):
        '''计算某个周期的技术指标
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        if k_type == 1:
            calc_indicator(self._daily_klines)
        elif k_type == 2:
            calc_indicator(self._h2_klines)
        elif k_type == 3:
            calc_indicator(self._m30_klines)
        elif k_type == 4:
            calc_indicator(self._m5_klines)
        else:
            calc_indicator(self._daily_klines)
            calc_indicator(self._h2_klines)
            calc_indicator(self._m30_klines)
            calc_indicator(self._m5_klines)

    def is_changing(self, k_type: int) -> bool:
        '''当某种K线生成新的记录时返回True
        k_type 代表K线类型
        '''
        if k_type == 1:
            return self._api.is_changing(
                self._daily_klines.iloc[-1], "datetime")
        elif k_type == 2:
            return self._api.is_changing(
                self._h2_klines.iloc[-1], "datetime")
        elif k_type == 3:
            return self._api.is_changing(
                self._m30_klines.iloc[-1], "datetime")
        elif k_type == 4:
            return self._api.is_changing(
                self._m5_klines.iloc[-1], "datetime")

    def buy_pos(self, tsl: Trade_Status_Long) -> None:
        '''换月时，如果虚拟交易有持仓，则直接现价买入
        '''

    def closeout_pos(self) -> None:
        '''换月平仓
        '''
        logger = self.logger
        if self._ts.is_trading:
            ts = self._ts
            hold_pos = self._pos.pos_long
            logger = self.logger
            log_str = '换月清仓,售出数量{}'
            self._closeout()
            trade_time = ts.get_current_date_str()
            price = ts.get_current_price()
            logger.info(log_str.format(hold_pos))
            ts.record_sell_to_excel(trade_time, '换月平仓', price, hold_pos)


class Future_Trade_Short(Future_Trade):
    '''做空交易类
    '''
    def __init__(self, api: TqApi, symbol: str, trade_book: Trade_Book)\
            -> None:
        super().__init__(api, symbol, trade_book)
        self._ts = Trade_Status_Short(self._pos, symbol,
                                      self._quote, trade_book)

    def _match_dk_cond(self) -> bool:
        '''做空日线条件检测
        合约交易日必须大于等于60天
        '''
        logger = self.logger
        kline = self._get_last_dk_line()
        ts = self._ts
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        daily_k_time = get_date_str(kline.datetime)
        log_str = ('{}满足<做空>日线条件{}:K线生成时间:{},ema9:{},ema22:{},'
                   'ema60:{},收盘:{},MACD:{}')
        if kline['l_qualified']:
            return kline['l_qualified']
        elif kline.id > 58:
            # 日线条件1
            if e22 > e60 and macd < 0 and e22 > close:
                logger.debug(log_str.format(
                    trade_time, 1, daily_k_time, e9, e22, e60, close, macd))
                self._daily_klines.loc[self._daily_klines.id == kline.id,
                                       's_qualified'] = 1
                ts.set_last_daily_kline(1, kline)
                return True
            # 日线条件2
            elif e60 > e9 > e22 and e60 > close:
                logger.debug(log_str.format(
                    trade_time, 2, daily_k_time, e9, e22, e60, close, macd))
                self._daily_klines.loc[self._daily_klines.id == kline.id,
                                       's_qualified'] = 2
                ts.set_last_daily_kline(2, kline)
                return True
        return False

    def _match_2hk_cond(self) -> bool:
        '''做空2小时线检测
        '''
        logger = self.logger
        ts = self._ts
        kline = self._get_last_h2_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        diff9_60 = diff_two_value(e9, e60)
        diff22_60 = diff_two_value(e22, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{}满足<做空>2小时条件:K线生成时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},'
                   'diffc_60:{},diff9_60:{},diff22_60{},MACD:{}')
        if kline["l_qualified"]:
            return True
        if (e22 > e60 and diff9_60 < 3 and diff22_60 < 3 and diffc_60 < 3 and
           macd < 0):
            logger.debug(log_str.format(
                trade_time, kline_time, e9, e22, e60, close,
                diffc_60, diff9_60, diff22_60, macd))
            self._h2_klines.loc[self._h2_klines.id == kline.id,
                                's_qualified'] = 1
            ts.set_last_h2_kline(kline)
            return True
        return False

    def _match_30mk_cond(self) -> bool:
        '''做空30分钟线检测
        '''
        logger = self.logger
        ts = self._ts
        kline = self._get_last_m30_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diff22_60 = diff_two_value(e22, e60)
        diff9_60 = diff_two_value(e9, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做空>30分钟条件: K线生成时间:{},ema9:{},'
                   'ema22:{},ema60:{},收盘:{},diff22_60:{},deff9_60:{},MACD:{}')
        if kline["l_qualified"]:
            return True
        if ((e60 > e22 > e9 or e22 > e60 > e9) and diff9_60 < 2
           and diff22_60 < 1 and macd < 0):
            logger.debug(log_str.format(
                trade_time, kline_time, e9, e22, e60, close,
                diff22_60, diff9_60, macd))
            self._m30_klines.loc[self._m30_klines.id == kline.id,
                                 's_qualified'] = 1
            ts.set_last_m30_kline(kline)
            return True
        return False

    def _match_5mk_cond(self) -> bool:
        '''做空5分钟线检测
        '''
        return True

    def _sale_target_pos(self, target_pos) -> int:
        '''交易工具类需要的目标仓位，需要子类重写
        做多返回正数，做空返回负数
        '''
        return -target_pos

    def _try_stop_profit(self) -> None:
        logger = self.logger
        ts = self._ts
        dk = self._get_last_dk_line()
        log_str = "{}<做空>止赢,现价:{},手数:{},剩余仓位:{},止赢起始价:{}"
        if ts.get_profit_status():
            spp = ts._stop_profit_point
            trade_time = ts.get_current_date_str()
            price = ts.get_current_price()
            ts.try_improve_sl_price()
            result = ts.is_final5_closeout(dk)
            if result:
                sold_pos = ts._get_pos_number()
                logger.info(log_str.format(
                    trade_time, price, sold_pos, 0, spp))
                ts.record_sell_to_excel(trade_time, price, '收盘止盈', sold_pos)
                self._closeout()


class Future_Trade_Long(Future_Trade):
    '''做多交易类
    '''
    def __init__(self, api: TqApi, symbol: str, trade_book: Trade_Book)\
            -> None:
        self.logger.debug(f'Create a new Long Trade, symbol:{symbol}')
        super().__init__(api, symbol, trade_book)
        self._ts = Trade_Status_Long(self._pos, symbol,
                                     self._quote, trade_book)

    def _match_dk_cond(self) -> bool:
        '''做多日线条件检测
        合约交易日必须大于等于60天
        '''
        logger = self.logger
        kline = self._get_last_dk_line()
        ts = self._ts
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        daily_k_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做多>日线条件{}: K线生成时间:{},ema9:{},ema22:{},'
                   'ema60:{},收盘:{},diff9_60:{},diffc_60:{},diff22_60:{},'
                   'MACD:{}')
        if kline['l_qualified']:
            return kline['l_qualified']
        elif kline.id > 58:
            diff9_60 = diff_two_value(e9, e60)
            diffc_60 = diff_two_value(close, e60)
            diff22_60 = diff_two_value(e22, e60)
            if e22 < e60:
                # 日线条件1
                if ((diff9_60 < 1 or diff22_60 < 1) and close > e60 and
                   macd > 0 and (e9 > e22 or macd > 0)):
                    logger.debug(log_str.format(
                        trade_time, 1, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 1
                    ts.set_last_daily_kline(1, kline)
                    return True
            elif e22 > e60:
                # 日线条件2
                if 0 < diff22_60 < 2 and 0 < diff9_60 < 2 and close > e60:
                    logger.debug(log_str.format(
                        trade_time, 2, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 2
                    ts.set_last_daily_kline(2, kline)
                    return True
                # 日线条件3
                elif (1 < diff9_60 < 3 and e9 > e22 and
                      e22 > min(open_p, close) > e60):
                    logger.debug(log_str.format(
                        trade_time, 3, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 3
                    ts.set_last_daily_kline(3, kline)
                    return True
                # 日线条件4
                elif (1 < diff22_60 < 3 and diff9_60 < 2 and e22 > close > e60
                      and e22 > e9 > e60):
                    logger.debug(log_str.format(
                        trade_time, 4, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 4
                    ts.set_last_daily_kline(4, kline)
                    return True
                # 日线条件5
                elif (diff22_60 > 3 and diff9_60 > 3 and diffc_60 < 3 and
                      e22 > close > e60 and e22 > open_p > e60):
                    logger.debug(log_str.format(
                        trade_time, 5, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 5
                    ts.set_last_daily_kline(5, kline)
                    return True
        return False

    def _match_2hk_cond(self) -> bool:
        '''做多2小时线检测
        '''
        logger = self.logger
        ts = self._ts
        kline = self._get_last_h2_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        diffo_60 = diff_two_value(open_p, e60)
        diff22_60 = diff_two_value(e22, e60)
        diff9_60 = diff_two_value(e9, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做多>2小时条件{}: K线生成时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},开盘:{},'
                   'diffc_60:{},diffo_60:{},diff22_60{},MACD:{}')
        if kline["l_qualified"]:
            return True
        if diffc_60 < 3 or diffo_60 < 3:
            if ts._daily_cond in [1, 2]:
                if (e22 < e60 and diff22_60 < 1 and e9 < e60 and
                   (macd > 0 or close > e60)):
                    logger.debug(log_str.format(
                        trade_time, 1, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self._h2_klines.loc[self._h2_klines.id == kline.id,
                                        'l_qualified'] = 1
                    ts.set_last_h2_kline(1, kline)
                    return True
                elif close > e9 > e22 > e60:
                    if self._match_2hk_c2_distance():
                        logger.debug(log_str.format(
                            trade_time, 2, kline_time, e9, e22, e60, close,
                            open_p, diffc_60, diffo_60, diff22_60, macd))
                        self._h2_klines.loc[self._h2_klines.id == kline.id,
                                            'l_qualified'] = 2
                        ts.set_last_h2_kline(2, kline)
                        return True
                    if diff9_60 < 1 and diff22_60 < 1 and macd > 0:
                        logger.debug(log_str.format(
                            trade_time, 5, kline_time, e9, e22, e60, close,
                            open_p, diffc_60, diffo_60, diff22_60, macd))
                        self._h2_klines.loc[self._h2_klines.id == kline.id,
                                            'l_qualified'] = 5
                        ts.set_last_h2_kline(5, kline)
                        return True
            elif ts._daily_cond in [3, 4]:
                if (close > e60 > e22 and macd > 0 and diff22_60 < 1 and e9 <
                   e60):
                    logger.debug(log_str.format(
                        trade_time, 3, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self._h2_klines.loc[self._h2_klines.id == kline.id,
                                        'l_qualified'] = 3
                    ts.set_last_h2_kline(3, kline)
                    return True
            elif ts._daily_cond == 3:
                if diff9_60 < 1 and diff22_60 < 1:
                    logger.debug(log_str.format(
                        trade_time, 6, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self._h2_klines.loc[self._h2_klines.id == kline.id,
                                        'l_qualified'] = 6
                    ts.set_last_h2_kline(6, kline)
                    return True
            elif ts._daily_cond == 5:
                if (e60 > e22 > e9):
                    logger.debug(log_str.format(
                        trade_time, 4, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self._h2_klines.loc[self._h2_klines.id == kline.id,
                                        'l_qualified'] = 4
                    ts.set_last_h2_kline(4, kline)
                    return True
        return False

    def _match_2hk_c2_distance(self) -> bool:
        logger = self.logger
        klines = self._h2_klines.iloc[::-1]
        log_str = 'k2:{},e9:{},e60:{},date:{}/k1:{},e22:{},e60:{},date:{}'
        # log_debug_1 = '22<60:k:{},e9:{},e22:{},e60:{},date:{}'
        # log_debug_2 = '9<60:k:{},e9:{},e22:{},e60:{},date:{}'
        k1 = 0
        k2 = 0
        date1 = 0
        date2 = 0
        ema9 = 0
        ema22 = 0
        ema60_1 = 0
        ema60_2 = 0
        is_done_1 = False
        for _, kline in klines.iterrows():
            # logger.debug(f'kline:{kline}')
            e9 = kline.ema9
            e22 = kline.ema22
            e60 = kline.ema60
            if not is_done_1 and e22 <= e60:
                k1 = kline.id
                date1 = get_date_str(kline.datetime)
                ema22 = e22
                ema60_1 = e60
                is_done_1 = True
                # logger.debug(log_debug_1.format(
                #    k1, e9, e22, e60, date1
                # ))
            if e9 <= e60:
                k2 = kline.id
                date2 = get_date_str(kline.datetime)
                ema9 = e9
                ema60_2 = e60
                # logger.debug(log_debug_2.format(
                #    k2, e9, e22, e60, date2
                # ))
                break
        if 0 <= k1 - k2 <= 5:
            logger.debug(log_str.format(
                k2, ema9, ema60_2, date2, k1, ema22, ema60_1, date1))
            logger.debug('两个交点距离小于等于5,符合条件')
            return True
        return False

    def _match_30mk_cond(self) -> bool:
        '''做多30分钟线检测
        '''
        logger = self.logger
        ts = self._ts
        kline = self._get_last_m30_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做多>30分钟条件: K线生成时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},diffc_60:{},MACD:{}')
        if kline["l_qualified"]:
            return True
        if close > e60 and macd > 0 and diffc_60 < 1.2:
            logger.debug(log_str.format(trade_time, kline_time, e9, e22, e60,
                                        close, diffc_60, macd))
            self._m30_klines.loc[self._m30_klines.id == kline.id,
                                 'l_qualified'] = 1
            ts.set_last_m30_kline(kline)
            return True
        return False

    def _match_5mk_cond(self) -> bool:
        '''做多5分钟线检测
        '''
        logger = self.logger
        kline = self._m5_klines.iloc[-2]
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做多>5分钟条件: K线生成时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},diffc_60:{},MACD:{}')
        if close > e60 and macd > 0 and diffc_60 < 1.2:
            logger.debug(log_str.format(trade_time, kline_time, e9, e22, e60,
                                        close, diffc_60, macd))
            return True
        return False

    def _sale_target_pos(self, target_pos) -> int:
        '''交易工具类需要的目标仓位，需要子类重写
        做多返回正数，做空返回负数
        '''
        return target_pos

    def _try_stop_profit(self) -> None:
        logger = self.logger
        ts = self._ts
        dk = self._get_last_dk_line()
        log_str = "{}<做多>止赢{},现价:{},手数:{},剩余仓位:{},止赢起始价:{}"
        sp_log = '止盈{}, 售出{}'
        trade_time = ts.get_current_date_str()
        price = ts.get_current_price()
        # ts.update_profit_stage(dk, m30k)
        if ts.get_profit_status() in [1, 2, 3]:
            ts.try_improve_sl_price()
            spp = ts._stop_profit_point
            result = ts.is_final5_closeout(dk)
            if result:
                sold_pos = ts._get_pos_number()
                logger.info(log_str.format(
                    trade_time,
                    ts._profit_cond, price,
                    sold_pos, 0, spp))
                ts.record_sell_to_excel(
                    trade_time, sp_log.format(ts._profit_cond, '100%'),
                    price, sold_pos)
                self._closeout()
        elif ts.get_profit_status() in [4]:
            spp = ts._stop_profit_point
            if ts._profit_stage == 1:
                sold_pos = ts._get_pos_number()//2
                rest_pos = self._trade_pos(ts._get_pos_number(), sold_pos)
                ts._profit_stage = 2
                logger.info(log_str.format(
                    trade_time,
                    ts._profit_cond, price,
                    sold_pos, rest_pos, spp))
                ts.record_sell_to_excel(
                    trade_time, sp_log.format(ts._profit_cond, '50%'),
                    price, sold_pos)
            elif ts._profit_stage == 2:
                if (ts.get_current_price() >=
                   ts.calc_price(ts._t_price, True, 3)):
                    sold_pos = ts._get_pos_number()
                    logger.info(log_str.format(
                        trade_time,
                        ts._profit_cond, price,
                        sold_pos, 0, spp))
                    ts.record_sell_to_excel(
                        trade_time, sp_log.format(ts._profit_cond, '剩余全部'),
                        price, sold_pos)
                    self._closeout()

    def buy_pos(self, tsv: Trade_Status_Virtual) -> None:
        '''换月时，如果虚拟交易有持仓，则直接现价买入
        '''
        logger = self.logger
        log_str = '{}合约:{}<做多>换月开仓,开仓价:{},数量{}'
        ts = self._ts
        trade_time = ts.get_current_date_str()
        price = ts.get_current_price()
        if tsv.is_trading:
            logger = self.logger
            self._trade_pos(tsv._pos_quantity, 0)
            logger.info(log_str.format(
                trade_time, self._symbol, price, tsv._pos_quantity))
            self._ts = tsv.create_tsl()
            self._ts._record_to_excel()


class Future_Trade_Long_Virtual(Future_Trade_Long):
    '''虚拟做多交易类,用于跟踪期货下一个合约的交易状态。
    如果符合交易条件，则记录当时的止盈止损价格，并在之后跟踪调整止盈点位。
    当换月时，根据该对象的状态决定是否买入换月后的合约。
    '''
    def __init__(self, api: TqApi, symbol: str, trade_book: Trade_Book)\
            -> None:
        super().__init__(api, symbol, trade_book)
        self._ts = Trade_Status_Virtual(self._pos, symbol,
                                        self._quote, trade_book)

    def _closeout(self):
        '''重写父类方法，不进行实际交易，只重置交易状态。
        '''
        logger = self.logger
        logger.debug('虚拟交易清仓')
        self._ts.reset()

    def _trade_pos(self, total_pos, sale_pos):
        logger = self.logger
        target_pos = total_pos - sale_pos
        logger.debug(f'虚拟交易,目标仓位{target_pos}')
        return target_pos

    def get_trade_status(self) -> Trade_Status_Virtual:
        return self._ts


class Future_Trade_Util:
    logger = LoggerGetter()

    def __init__(self,  api: TqApi, zl_symbol: str, trade_book: Trade_Book)\
            -> None:
        self._api = api
        self._zl_quote = api.get_quote(zl_symbol)
        self._long_ftu = Long_Future_Trade_Util(
            self._zl_quote, api, zl_symbol, trade_book)
        self._ftu_list: list(Future_Trade_Util) = []
        self._ftu_list.append(self._long_ftu)

    def _get_date_from_symbol(self, symbol_last_part):
        temp = int(symbol_last_part)
        year = int(temp / 100) + 2000
        month = temp % 100
        day = 1
        return datetime(year, month, day, 0, 0, 0)

    def _need_switch_contract(self):
        '''判断是否需要换月
        规则是：如果原合约有持仓，则在合约交割月之前10天换月
        否则，在交割月之前一个月月初换月。
        '''
        logger = self.logger
        if (hasattr(self._long_ftu, '_next_trade') and
           self._long_ftu._next_trade):
            c_symbol = self._long_ftu._current_trade._symbol
            n_symbol = self._long_ftu._next_trade._symbol
            position = self._long_ftu._current_trade._pos
            last_symbol_list = examine_symbol(c_symbol)
            today_symbol_list = examine_symbol(n_symbol)
            if not last_symbol_list or not today_symbol_list:
                logger.warning('新/旧合约代码有误，请检验')
                return False
            if today_symbol_list[0] != last_symbol_list[0] or \
                    today_symbol_list[1] != last_symbol_list[1]:
                logger.warning('新/旧合约品种不一，请检验')
                return False
            if n_symbol <= c_symbol:
                logger.warning('新合约非远月合约，不换月')
                return False
            last_date = self._get_date_from_symbol(last_symbol_list[2])
            current_date = tafunc.time_to_datetime(self._zl_quote.datetime)
            timedelta = last_date - current_date
            logger.debug(f'原合约{c_symbol},下一个合约{n_symbol}'
                         f'当前时间与原合约交易截止月相差{timedelta.days}天')
            if position.pos != 0 and timedelta.days <= 11:
                return True
            elif position.pos == 0 and timedelta.days <= 31:
                return True
        return False

    def try_trade(self) -> None:
        for trade_util in self._ftu_list:
            trade_util.try_trade()

    def create_next_trade(self) -> None:
        '''创建下一个合约的虚拟交易对象
        当前只需要做多提供实现逻辑，做空提供空方法即可。
        当天勤切换主力合约时，使用该方法为新的主力合约创建虚拟交易对象
        用来跟踪该合约的交易情况，为换月时是否买入该合约提供依据
        '''
        for trade_util in self._ftu_list:
            trade_util.create_next_trade()

    def switch_trade(self):
        '''在主连合约更换主力合约后调用，
        如果满足换月条件，则进行换月操作。
        '''
        if self._need_switch_contract():
            for trade_util in self._ftu_list:
                trade_util.switch_trade()

    def calc_indicators(self, k_type):
        '''计算当前交易工具中所有交易的某个周期的技术指标
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        for trade_util in self._ftu_list:
            trade_util.calc_indicators(k_type)

    def is_changing(self, k_type) -> bool:
        '''判断交易工具类种的合约中某种K线是否发生变化
        由于合约交易时间相同，只需判断一个合约即可
        当该K线发生变化时，则调用相关方法进行进一步操作
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        return self._long_ftu.is_changing(k_type)

    def start_trading(self) -> None:
        '''期货交易工具对外接口。交易时间内不断循环调用该接口
        实现期货交易逻辑，包括：
        * 尝试开仓
        * 开仓后尝试止盈止损
        * 天勤更换主力合约后，做多交易开始跟踪新主力交易状态
        * 符合换月条件后，切换实际交易对象
        '''
        logger = self.logger
        if self._api.is_changing(self._zl_quote, "underlying_symbol"):
            self.create_next_trade()
        # 当天交易结束时即14:59:59，会触发以下条件，
        if self.is_changing(1):
            log_str = '合约:{},当日最高价:{},日期:{}'
            logger.debug(log_str.format(
                self._long_ftu._current_trade._symbol,
                self._long_ftu._current_trade._get_last_dk_line().high,
                get_date(self._zl_quote.datetime)
            ))
            self.calc_indicators(1)
            self.switch_trade()
        if self.is_changing(2):
            self.calc_indicators(2)
        if self.is_changing(3):
            self.calc_indicators(3)
        if self.is_changing(4):
            self.calc_indicators(4)
        if self._api.is_changing(self._zl_quote, "datetime"):
            t_time = tafunc.time_to_datetime(self._zl_quote.datetime)
            # 为避免交易开始之前做出错误判断，需在交易时间进行交易
            if t_time.hour > 8:
                self.try_trade()


class Long_Future_Trade_Util(Future_Trade_Util):
    logger = LoggerGetter()

    def __init__(self, zl_quote: Quote, api: TqApi, zl_symbol: str,
                 trade_book: Trade_Book) -> None:
        self._api = api
        self._tb = trade_book
        self._zl_quote = zl_quote
        symbol = self._zl_quote.underlying_symbol
        self._current_trade: Future_Trade_Long = Future_Trade_Long(
            api, symbol, trade_book
        )
        self._future_trade_list: list(Future_Trade_Long) = []
        self._future_trade_list.append(self._current_trade)

    def create_next_trade(self):
        ''' 创建下一个合约的虚拟交易，跟踪其行情
        '''
        logger = self.logger
        symbol = self._zl_quote.underlying_symbol
        trade_time = self._current_trade._ts.get_current_date_str()
        logger.debug(f'{trade_time}平台主力合约已更换,'
                     f'原合约{self._current_trade._symbol},'
                     f'新合约{symbol},开始准备切换合约')
        self._next_trade: Future_Trade_Long_Virtual =\
            Future_Trade_Long_Virtual(self._api, symbol, self._tb)
        self._future_trade_list.append(self._next_trade)

    def try_trade(self) -> None:
        for trade in self._future_trade_list:
            trade.try_trade()

    def switch_trade(self):
        logger = self.logger
        old_symbol = self._current_trade._symbol
        trade_time = self._current_trade._ts.get_current_date_str()
        self._current_trade.closeout_pos()
        self._current_trade = Future_Trade_Long(
            self._api, self._next_trade._symbol, self._tb
        )
        self._current_trade.buy_pos(self._next_trade.get_trade_status())
        self._next_trade = None
        self._future_trade_list.clear()
        self._future_trade_list.append(self._current_trade)

        logger.info(f'{trade_time}换月完成:旧合约{old_symbol},'
                    f'新合约{self._current_trade._symbol}')

    def calc_indicators(self, k_type: int):
        '''计算当前交易工具中所有交易的某个周期的技术指标
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        for trade in self._future_trade_list:
            trade.calc_criteria(k_type)

    def is_changing(self, k_type) -> bool:
        '''判断交易工具类种的合约中某种K线是否发生变化
        由于合约交易时间相同，只需判断一个合约即可
        当该K线发生变化时，则调用相关方法进行进一步操作
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        return self._current_trade.is_changing(k_type)
