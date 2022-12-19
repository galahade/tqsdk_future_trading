from tqsdk import tafunc, TqApi
# from tqsdk2 import tafunc
from utils.tools import get_date_str
from utils.common import LoggerGetter
from dao.entity import OpenPosInfo, ClosePosInfo
from dao.config_entity import FutureConfigInfo
from dao.dao_service import DBService
from datetime import datetime


class TradeUtils:
    logger = LoggerGetter()

    def __init__(self, account, position, tsi, quote, tud) -> None:
        self.account = account
        self.position = position
        self.quote = quote
        self.tsi = tsi
        self.tud = tud
        self.open_pos_scale = (
            tud.future_config.open_pos_scale/tud.future_config.contract_m)
        self.dbservice = tud.dbservice
        self.sl_message = '止损'
        self.use_ps_ratio = False

    def _store_close_pos_info(self, sold_reason: str, sold_price: float,
                              sold_pos: int) -> None:
        self.tsi.last_modified = self.get_current_date()
        cpi = self._create_ClosePosInfo(sold_price, sold_pos, sold_reason)
        self.dbservice.store_close_record(cpi)

    def _set_sale_prices(self, pos: int) -> None:
        '''抽象方法，设置止盈止损价格
        当买入成交后，按成交价格设置目标止损价和止盈起始价
        '''
        td = self.tsi.trade_data
        if self.tud.just_check:
            td.price = self.get_current_price()
        else:
            td.price = self._get_open_price()
        td.pos = pos

    def _set_stop_profit_values(self) -> None:
        '''抽象方法，设置止盈类型和止盈阶段
        '''
        self.tsi.trade_data.p_stage = 0

    def _store_open_pos_info(self) -> None:
        '''将开仓记录和当前交易状态存储到硬盘中
        '''
        self.tsi.last_modified = self.get_current_date()
        opi = self._create_OpenPosInfo()
        self.dbservice.store_open_record(opi)
        self.tsi.trade_data.open_pos_id = opi._id
        self.dbservice.update_tsi(self.tsi, self.get_current_date())

    def _is_last_5_m(self) -> bool:
        '''判断交易时间是否为当日最后5分钟
        '''
        t_time = tafunc.time_to_datetime(self.quote.datetime)
        time_num = int(t_time.time().strftime("%H%M%S"))
        return 150000 > time_num > 145500

    def set_last_h3_kline(self, kline):
        self.tsi.judge_data.h3_kline = kline

    def set_last_m30_kline(self, kline):
        self.tsi.judge_data.m30_kline = kline

    def set_open_info(self, pos: int):
        logger = self.logger
        if self.tsi.is_trading:
            logger.warning("无法更新tsi状态, 交易进行中。")
            logger.warning(self.tsi.__dict__)
        self.tsi.is_trading = True
        self.tsi.trade_data.trade_date = self.get_current_date()
        self._set_stop_profit_values()
        self._set_sale_prices(pos)
        self._store_open_pos_info()

    def get_stoplose_status(self) -> bool:
        '''返回是否需要止损
        '''
        td = self.tsi.trade_data
        if self.tsi.is_trading:
            if td.pos > 0 and self._is_get_slp():
                return True
        return False

    def get_pos(self) -> int:
        return self.tsi.trade_data.pos

    def reset(self):
        '''接口，需要进一步修改需要子类增加逻辑，重置内部变量状态
        '''
        self.p_l_ratio = self.fc.profit_base_scale
        self.use_ps_ratio = False

    def get_current_price(self) -> float:
        '''接口，返回当前交易价格
        '''
        return self.quote.last_price

    def get_current_date_str(self) -> str:
        '''接口,返回当前交易时间
        '''
        return get_date_str(self.quote.datetime)

    def get_current_date(self) -> datetime:
        '''接口,返回当前交易时间
        '''
        return tafunc.time_to_datetime(self.quote.datetime)

    def calc_price(self, price: float, is_add: bool, scale: float) -> float:
        '''类方法，按盈亏比计算目标价格
        '''
        if is_add:
            return round(price * (1 + self.p_l_ratio * scale), 2)
        else:
            return round(price * (1 - self.p_l_ratio * scale), 2)

    def set_close_info(self, c_price: float, c_pos: int, c_reason: str,
                       is_switch: bool):
        tsi = self.tsi
        self._store_close_pos_info(c_reason, c_price, c_pos)
        t_time = self.get_current_date()
        if is_switch:
            tsi.switch_symbol(t_time)
        elif tsi.is_closing_out(c_pos):
            tsi.close_out()
        else:
            tsi.trade_data.pos = tsi.trade_data.pos - c_pos
        self.dbservice.update_tsi(tsi, t_time)

    def get_Kline_values(self, kline) -> tuple:
        ema9 = kline.ema9
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        open_p = kline.open
        trade_time = self.get_current_date_str()
        return (ema9, ema22, ema60, macd, close, open_p, trade_time)

    def update_tsi(self) -> None:
        self.dbservice.update_tsi(self.tsi, self.get_current_date())

    def set_last_daily_kline(self, cond_num, kline):
        '''设置符合开仓条件的日线，并记录符合第几个日线条件
        '''
        self.tsi.judge_data.d_kline = kline
        self.tsi.judge_data.d_cond = cond_num


class TradeUtilsShort(TradeUtils):
    logger = LoggerGetter()

    def __init__(self, account, position, tsi, quote, tud) -> None:
        super().__init__(account, position, tsi, quote, tud)
        self.trade_config = tud.future_config.short_config
        self.p_l_ratio = self.trade_config.profit_base_scale

    def _is_get_slp(self) -> bool:
        price = self.get_current_price()
        td = self.tsi.trade_data
        return price >= td.slp

    def try_improve_sl_price(self) -> None:
        '''尝试提高止损价
        当盈亏比达到1:10后将止损价格提升至1:5
        '''
        td = self.tsi.trade_data
        logger = self.logger
        price = self.get_current_price()
        trade_time = self.get_current_date_str()
        log_str = '{}<做空>现价{}达到1:{}盈亏比,将止损价提高至{}'
        calc_price = self.calc_price
        promote_price = calc_price(td.price, False,
                                   self.trade_config.promote_scale)
        if td.has_islp:
            return
        else:
            if (td.p_stage == 0 and price <= promote_price):
                td.slp = calc_price(td.price, False,
                                    self.trade_config.promote_target)
                td.p_stage = 1
                td.slr = '跟踪止盈'
                td.has_islp = True
                self.dbservice.update_tsi(self.tsi, self.get_current_date())
                logger.debug(log_str.format(
                    trade_time, price,
                    self.trade_config.promote_scale, td.slp))

    def get_profit_status(self, dk) -> bool:
        '''返回是否满足止盈条件。当第一次符合止盈条件时，设置相关止盈参数
        '''
        td = self.tsi.trade_data
        if self.tsi.is_trading:
            e9, e22, e60, macd, close, open_p, trade_time =\
                self.get_Kline_values(dk)
            # if (diff_two_value(e22, e60) > 3 and e60 > e22 > e9
            if (e60 > e22 > e9 and not td.stp):
                return True
            elif td.stp:
                if close < e9:
                    td.stp = False
                    self.dbservice.update_tsi(self.tsi,
                                              self.get_current_date())
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
            if (macd > 0 and price > ema9):
                logger.debug(log_str.format(
                    trade_time, price, ema9, ema22, macd))
                return True
        return False

    def _set_sale_prices(self, pos: int) -> None:
        super()._set_sale_prices(pos)
        td = self.tsi.trade_data
        td.slp = self.calc_price(td.price, True,
                                 self.trade_config.stop_loss_scale)
        td.spp = self.calc_price(td.price, False,
                                 self.trade_config.profit_start_scale)
        self.logger.info(f'{self.get_current_date_str()}'
                         f'<做空>止损设为:{td.slp}'
                         f'止盈起始价为:{td.spp}')

    def _create_OpenPosInfo(self) -> OpenPosInfo:
        return OpenPosInfo(self.tsi, False, self.account.commission,
                           self.account.balance)

    def _create_ClosePosInfo(self, sold_price: float, sold_pos: int,
                             sold_reason: str) -> ClosePosInfo:
        return ClosePosInfo(self.tsi, False, self.account.commission,
                            self.account.balance, self.get_float_profit(),
                            sold_price, sold_pos, sold_reason)

    def reset(self):
        super().reset()

    def get_float_profit(self) -> float:
        return self.position.float_profit

    def _get_open_price(self) -> float:
        return self.position.open_price_short

    def _get_tq_pos_number(self) -> int:
        '''返回当前合约持仓量
        '''
        return self.position.pos_short

    def is_2days_later(self, kline):
        log_str = '{}<做空>距离交易时间{}达到{}'
        # trade_time = self.get_current_date_str()
        today = tafunc.time_to_datetime(kline.datetime)
        timedelta = today - self.open_pos_date
        if timedelta.days >= 4 and (not hasattr(self, 'has_2_days') or
                                    not self.has_2_days):
            self.has_2_days = True
            self.logger.debug(
                log_str.format(
                    today,
                    self.open_pos_date,
                    timedelta.days
                ))
            self.logger.debug(timedelta)
            return True
        return False


class TradeUtilsLong(TradeUtils):
    logger = LoggerGetter()

    def __init__(self, account, position, tsi, quote, tud) -> None:
        super().__init__(account, position, tsi, quote, tud)
        self.trade_config = tud.future_config.long_config
        self.p_l_ratio = self.trade_config.profit_base_scale

    def set_last_h3_kline(self, cond_num, *args):
        '''重写父类方法。
        设置符合条件的两小时线，同时记录符合哪个两小时条件。
        '''
        super().set_last_h3_kline(*args)
        self.tsi.judge_data.h3_cond = cond_num

    def _is_get_slp(self) -> bool:
        price = self.get_current_price()
        td = self.tsi.trade_data
        return price <= td.slp

    def try_improve_sl_price(self) -> bool:
        td = self.tsi.trade_data
        logger = self.logger
        price = self.get_current_price()
        trade_time = self.get_current_date_str()
        log_str = '{}<做多>止盈条件{}现价{}达到1:{}盈亏比,将止损价提高至{}'
        calc_price = self.calc_price
        if td.has_islp:
            return
        else:
            if td.p_cond in [1, 2, 3]:
                standard_price = calc_price(td.price, True,
                                            self.trade_config.promote_scale_1)
                if price >= standard_price:
                    td.slp = calc_price(td.price, True,
                                        self.trade_config.promote_target_1)
                    td.slr = '跟踪止盈'
                    td.has_islp = True
                    self.dbservice.update_tsi(self.tsi,
                                              self.get_current_date())
                    logger.debug(log_str.format(
                        trade_time, 1, price,
                        self.trade_config.promote_scale_1, td.slp))

    def get_profit_status(self) -> int:
        '''返回满足止盈条件的序号，并设置相关止盈参数
        0:不满足止盈条件
        1:止盈条件1
        2:止盈条件2
        3:止盈条件3
        4:止盈条件4
        '''
        td = self.tsi.trade_data
        logger = self.logger
        if self.tsi.is_trading:
            log_str = ('{}<做多>现价:{} 达到止盈价{}开始监控,'
                       '止损价提高到:{}')
            price = self.get_current_price()
            if td.bsp:
                return td.p_cond
            if price >= td.spp:
                td.bsp = True
                if td.p_cond == 4:
                    td.slp = td.price
                    td.p_stage = 1
                self.dbservice.update_tsi(self.tsi, self.get_current_date())
                logger.info(log_str.format(
                    self.get_current_date_str(),
                    price, td.spp, td.slp
                ))
                return td.p_cond
        return 0

    def update_profit_stage(self, dk, m30k):
        '''暂时弃用-当开仓后，使用该方法判断是否达到监控止盈条件，
        当开始监控止盈后，根据最新价格，更新止损价格和止盈阶段
        为止盈提供依据
        '''
        pos = self.get_pos_number()
        if pos > 0 and self.get_profit_status():
            if self.tsi.trade_data.p_stage == 0:
                self.tsi.trade_data.p_stage = 1
            elif self.tsi.trade_data.p_cond == 0:
                if self.tsi.trade_data.p_stage == 1:
                    self.tsi.trade_data.p_stage = 2

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
            if (self.tsi.trade_data.p_cond == 1 and price < ema60 and
               ema9 < ema22):
                logger.debug(log_str.format(
                    trade_time, 1, price, ema9, ema22, ema60))
                return True
            elif (self.tsi.trade_data.p_cond in [2, 3] and price < ema22
                  and ema9 < ema22):
                logger.debug(log_str.format(
                    trade_time, 2, price, ema9, ema22, ema60))
                return True
        return False

    def _set_sale_prices(self, pos: int) -> None:
        super()._set_sale_prices(pos)
        td = self.tsi.trade_data
        td.slp = self.calc_price(td.price, False,
                                 self.trade_config.stop_loss_scale)
        if td.p_cond in [1, 2, 3]:
            td.spp = self.calc_price(
                td.price, True, self.trade_config.profit_start_scale_1)
        if td.p_cond in [4]:
            td.spp = self.calc_price(
                td.price, True, self.trade_config.profit_start_scale_2)
        self.logger.info(f'{self.get_current_date_str()}'
                         f'<做多>开仓价:{td.price}'
                         f'止损设为:{td.slp}'
                         f'止盈起始价为:{td.spp}')

    def _set_stop_profit_values(self):
        '''设置止盈操作的种类
        止盈操作分为两种，每种对应不同的止盈策略
        '''
        td = self.tsi.trade_data
        jd = self.tsi.judge_data
        super()._set_stop_profit_values()
        if (jd.d_cond in [1, 2]):
            td.p_cond = 1
        elif (jd.d_cond in [5]):
            td.p_cond = 2
        elif (jd.d_cond in [3] and
              jd.h3_cond == 6):
            td.p_cond = 3
        elif (jd.d_cond in [3, 4] and
              jd.h3_cond == 3):
            td.p_cond = 4

    def _create_OpenPosInfo(self) -> OpenPosInfo:
        return OpenPosInfo(self.tsi, True, self.account.commission,
                           self.account.balance,)

    def _create_ClosePosInfo(self, sold_price: float, sold_pos: int,
                             sold_reason: str) -> ClosePosInfo:
        return ClosePosInfo(self.tsi, True, self.account.commission,
                            self.account.balance, self.get_float_profit(),
                            sold_price, sold_pos, sold_reason)

    def get_float_profit(self) -> float:
        return self.position.float_profit

    def _get_open_price(self) -> float:
        return self.position.open_price_long

    def _get_tq_pos_number(self) -> int:
        '''返回当前合约持仓量
        '''
        return self.position.pos_long

    def reset(self):
        super().reset()


class TradeUtilsData:
    def __init__(self, api: TqApi, future_config: FutureConfigInfo, dbservice:
                 DBService,  direction: int,
                 just_check, is_backtest):
        self.api = api
        self.future_config = future_config
        self.dbservice = dbservice
        self.direction = direction
        self.just_check = just_check
        self.is_backtest = is_backtest
