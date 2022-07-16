from math import floor
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
        self.tb_count = 0

    def set_last_daily_kline(self, kline):
        self._daily_kline = kline

    def set_last_h2_kline(self, kline):
        self._h2_kline = kline

    def set_last_m30_kline(self, kline):
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
    logger = LoggerGetter()
    base_persent = 0.02

    def set_last_daily_kline(self, cond_num, *args):
        '''重写父类方法。
        设置符合开仓条件的日线，并记录符合第几个日线条件
        '''
        super().set_last_daily_kline(*args)
        self._daily_cond = cond_num

    def set_last_h2_kline(self, cond_num, *args):
        '''重写父类方法。
        设置符合条件的两小时线，同时记录符合哪个两小时条件。
        '''
        super().set_last_h2_kline(*args)
        self._h2_cond = cond_num

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
        self._h2_klines = api.get_kline_serial(symbol, 60*60*2)
        self._m30_klines = api.get_kline_serial(symbol, 60*30)
        self._tb = trade_book
        self._ts: Trade_Status

    def _get_pos_number(self) -> int:
        '''返回当前合约持仓量
        需要多空合约交易类重写该方法
        '''
        pass

    def _match_dk_cond(self) -> bool:
        pass

    def _match_2hk_cond(self) -> bool:
        pass

    def _match_30mk_cond(self) -> bool:
        pass

    def _match_5mk_cond(self) -> bool:
        pass

    def _calc_open_pos_number(self) -> bool:
        available = self.account.balance * Trade_Status.open_volumes_persent
        pos = floor(available / self.get_quote().bid_price1)
        return pos

    def _can_open_ops(self):
        if self._get_pos_number() == 0:
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

    def _sell_pos(self, total_pos, sale_pos):
        '''final 方法，售出仓位。多空适用。
        '''
        logger = self.logger
        log_str = '{} 平仓,excel序号:{}价格:{}手数:{}'
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

    def _closeout(self):
        '''清仓，多空子类需要重写该方法
        '''
        pass

    def get_quote(self) -> Quote:
        return self._quote

    def _try_stop_loss(self) -> None:
        ''' 止损抽象方法，需要多空子类重写
        '''
        pass

    def _try_stop_profit(self) -> None:
        ''' 止盈抽象方法，需要多空子类重写
        '''
        pass

    def _try_open_pos(self) -> None:
        ''' 开仓抽象类，当没有任何持仓时进行。
        需要被具体的多空交易类重写。
        '''
        pass

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


class Future_Trade_Long(Future_Trade):
    '''做多交易类
    '''
    def __init__(self, api: TqApi, symbol: str, trade_book: Trade_Book)\
            -> None:
        super().__init__(api, symbol, trade_book)
        self._m5_klines = api.get_kline_serial(symbol, 60*5)
        self._ts = Trade_Status_Long(self._pos, self._quote, trade_book)

    def _get_pos_number(self) -> int:
        '''返回当前合约持仓量
        '''
        return self._pos.pos_long

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
        log_str = ('{} 满足<做多>日线条件{}: K线生成时间:{},ema9:{},'
                   'ema22:{},ema60:{},收盘:{},diff9_60:{},diffc_60:{},MACD:{}')
        if kline['l_qualified']:
            return kline['l_qualified']
        elif kline.id > 58:
            diff9_60 = diff_two_value(e9, e60)
            diffc_60 = diff_two_value(close, e60)
            if e22 < e60:
                # 日线条件1
                if diff9_60 < 1 and close > e60 and macd > 0:
                    logger.debug(log_str.format(
                        trade_time, 1, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 1
                    ts.set_last_daily_kline(1, kline)
                    return True
            elif e22 > e60:
                # 日线条件2
                if e9 > e22 > e60 and diff9_60 < 1 and close > e22:
                    logger.debug(log_str.format(
                        trade_time, 2, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 2
                    ts.set_last_daily_kline(2, kline)
                    return True
                # 日线条件3
                elif (1 < diff9_60 < 3 and e9 > e22 >
                      min(open_p, close) > e60):
                    logger.debug(log_str.format(
                        trade_time, 3, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 3
                    ts.set_last_daily_kline(3, kline)
                    return True
                # 日线条件4
                elif 1 < diff9_60 < 3 and e22 > close > e60 and e9 < e22:
                    logger.debug(log_str.format(
                        trade_time, 4, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 4
                    ts.set_last_daily_kline(4, kline)
                    return True
                # 日线条件5
                elif (diff9_60 > 3 and e22 > close > e60 and diffc_60 < 2):
                    logger.debug(log_str.format(
                        trade_time, 5, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 5
                    ts.set_last_daily_kline(5, kline)
                    return True
        return False

    def _match_2hk_cond(self):
        logger = self.logger
        ts = self._ts
        kline = self._get_last_h2_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        diffo_60 = diff_two_value(open_p, e60)
        diff22_60 = diff_two_value(e22, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做多>2小时条件{}: K线生成时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},开盘:{},'
                   'diffc_60:{},diffo_60:{},diff22_60{},MACD:{}')
        if kline["l_qualified"]:
            return True
        if diffc_60 < 3 or diffo_60 < 3:
            if ts._daily_cond in [1, 2]:
                if (e22 < e60 and e9 < e60 and macd > 0):
                    logger.debug(log_str.format(
                        trade_time, 1, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self.h2_klines.loc[self.h2_klines.id == kline.id,
                                       'l_qualified'] = 1
                    ts.set_last_h2_kline(1, kline)
                    return True
                elif close > e9 > e22 > e60:
                    logger.debug(log_str.format(
                        trade_time, 2, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self.h2_klines.loc[self.h2_klines.id == kline.id,
                                       'l_qualified'] = 2
                    ts.set_last_h2_kline(2, kline)
                    return True
            elif ts._daily_cond in [3]:
                if (close > e60 > e22 and macd > 0):
                    logger.debug(log_str.format(
                        trade_time, 3, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self.h2_klines.loc[self.h2_klines.id == kline.id,
                                       'l_qualified'] = 3
                    ts.set_last_h2_kline(3, kline)
                    return True
            elif ts._daily_cond == 5:
                if (e60 > e22 > e9):
                    logger.debug(log_str.format(
                        trade_time, 4, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self.h2_klines.loc[self.h2_klines.id == kline.id,
                                       'l_qualified'] = 4
                    ts.set_last_h2_kline(4, kline)
                    return True
        return False

    def _match_30mk_cond(self):
        logger = self.logger
        ts = self._ts
        kline = self._get_last_m30_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} 满足<做多>30分钟条件{}: K线生成时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},diffc_60:{},MACD:{}')
        if kline["l_qualified"]:
            return True
        if close > e60 and macd > 0 and diffc_60 < 1.2:
            logger.debug(log_str.format(trade_time, kline_time, e9, e22, e60,
                                        close, diffc_60, macd))
            self.m30_klines.loc[self.m30_klines.id == kline.id,
                                'l_qualified'] = 1
            ts.set_last_m30_kline(kline)
            return True
        return False

    def _match_5mk_cond(self):
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

    def _closeout(self):
        '''重写父类方法，提供做多版本
        '''
        self._sell_pos(self._pos.pos_long, self._pos.pos_long)
        self._ts.reset()

    def _try_open_pos(self) -> None:
        '''重写父类抽象方法
        提供做多版本逻辑
        '''
        logger = self.logger
        log_str = '{} 合约:{}<多头>开仓 开仓价:{} {}手'
        ts = self._ts
        trade_time = ts.get_current_date_str()
        if self._can_open_ops():
            open_pos = self._calc_open_pos_number()
            self.target_pos.set_target_volume(open_pos)
            while True:
                self._api.wait_update()
                if self._pos.pos_long == open_pos:
                    break
            logger.info(log_str.format(
                trade_time, self._symbol, self._pos.open_price_long,
                open_pos))
            ts.set_deal_info()

    def _try_stop_loss(self) -> None:
        logger = self.logger
        ts = self._ts
        tb = self.tb
        trade_time = ts.get_current_date_str()
        price = ts.get_current_price()
        if ts.get_stoplose_status():
            stop_loss_price = 0
            pos = self.position.pos_long
            stop_loss_price = ts._stop_loss_price
            tb.r_l_sold_pos(self._symbol,
                            ts.tb_count, trade_time,
                            f'止损平仓,止损价{stop_loss_price}',
                            price, pos)
            logger.info(f'{trade_time} <做多>止损,现价:{price},'
                        f'止损价:{stop_loss_price},手数:{pos}')
            self._closeout()

    def _try_stop_profit(self) -> None:
        logger = self.logger
        ts = self._ts
        stop_profit_profit = ts._stop_profit_point
        dk = self._get_last_dk_line()
        m30k = self._get_last_m30_kline()
        log_str = "{} <做多>止赢{},现价:{},手数:{},剩余仓位:{},止赢起始价:{}"
        ts.update_profit_stage(dk, m30k)
        if ts.get_profit_status():
            trade_time = ts.get_current_date_str()
            price = ts.get_current_price()
            stopprofit_log = '止盈条件:{},盈亏比达到{},售出{}手'

            # 其他止盈条件，达到1:3盈亏比，售出一半仓位
            if ts._profit_cond == 0 and ts._profit_cond == 1:
                sold_pos = int(self._pos.pos_long / 2)
                rest_pos = self._sell_pos(self._pos.pos_long, sold_pos)
                logger.info(log_str.format(
                    trade_time, '0-1', price, sold_pos, rest_pos,
                    stop_profit_profit))
                self.tb.r_l_sold_pos(self._symbol,
                                     ts.tb_count, trade_time,
                                     stopprofit_log.format('其他', '1:3', '50%'),
                                     price, sold_pos)
            result = ts.is_final5_closeout(dk, m30k)
            if result == 8:
                sold_pos = int(self._pos.pos_long * 0.8)
                rest_pos = self._sell_pos(self._pos.pos_long, sold_pos)
                ts._profit_stage = 3
                logger.info(log_str.format(
                    trade_time, '0-2', price, sold_pos,
                    rest_pos, stop_profit_profit))
                self.tb.r_l_sold_pos(self.underlying_symbol,
                                     ts.tb_count, trade_time,
                                     stopprofit_log.format('其他', '', '80%'),
                                     price, sold_pos)
            elif result:
                sold_pos = self._pos.pos_long
                logger.info(log_str.format(
                    trade_time,
                    ts._profit_cond, price,
                    sold_pos, 0, stop_profit_profit))
                self.tb.r_l_sold_pos(self._symbol,
                                     ts.tb_count, trade_time,
                                     stopprofit_log.format(ts._profit_cond,
                                                           '', '全部'),
                                     price, sold_pos)


class Future_Trade_Long_Virtual(Future_Trade_Long):
    '''虚拟做多交易类,用于跟踪期货下一个合约的交易状态。
    如果符合交易条件，则记录当时的止盈止损价格，并在之后跟踪调整止盈点位。
    当换月时，根据该对象的状态决定是否买入换月后的合约。
    '''

    def _closeout(self):
        '''重写父类方法，不进行实际交易，只重置交易状态。
        '''
        self._ts.reset()

    def _sell_pos(self, total_pos, sale_pos):
        target_pos = total_pos - sale_pos
        return target_pos


class Future_Trade_Short(Future_Trade):
    pass


class Future_Trade_Util:
    def __init__(self,  api: TqApi, zl_symbol: str, trade_book: Trade_Book)\
            -> None:
        self._long_ftu = Long_Future_Trade_Util(api, zl_symbol, trade_book)
        self._ftu_list: list(Future_Trade_Util) = []
        self._ftu_list.append()

    def try_trade(self) -> None:
        for trade_util in self._ftu_list:
            trade_util.try_trade()

    def create_next_trade(self) -> None:
        '''创建下一个合约的虚拟交易对象
        做多交易需要重写该方法，当天勤切换主力合约时，使用该方法创建新合约
        的新合约虚拟交易对象，用来跟踪该合约的交易情况，为换月时是否买入该
        合约提供依据
        '''
        for trade_util in self._ftu_list:
            trade_util.create_next_trade()

    def switch_trade(self):
        for trade_util in self._ftu_list:
            trade_util.switch_trade()


class Long_Future_Trade_Util(Future_Trade_Util):
    def __init__(self,  api: TqApi, zl_symbol: str, trade_book: Trade_Book)\
            -> None:
        self._api = api
        self._tb = trade_book
        self.zl_quote = api.get_quote(zl_symbol)
        symbol = self.zl_quote.underlying_symbol
        self._current_trade = Future_Trade_Long(api, symbol, trade_book)
        self._future_trade_list = []
        self._future_trade_list.append(self.current_trade)

    def create_next_trade(self):
        ''' 该方法应在天勤切换主力合约后调用
        '''
        symbol = self.zl_quote.underlying_symbol()
        self._next_trade = Future_Trade_Long_Virtual(
            self._api, symbol, self.tb_tb)
        self._future_trade_list.append(self._next_trade)

    def try_trade(self) -> None:
        for trade in self._future_trade_list:
            trade.try_trade()

    def switch_trade(self):
        self._current_trade = Future_Trade_Long(
            self._api, self._next_trade._symbol, self._tb
        )
        self._next_trade = None
        self._future_trade_list.clear()
        self._future_trade_list.append(self._current_trade)

