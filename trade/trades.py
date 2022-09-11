from math import floor
from tqsdk import TqApi, TargetPosTask, tafunc
from utils.tools import get_date_str, get_date_str_short, diff_two_value,\
    calc_indicator, is_nline
from utils.common import LoggerGetter
from datetime import datetime
from trade.utils import TradeUtilsLong, TradeUtilsShort,\
        Trade_Status_Virtual, TradeUtils
from dao.entity import TradeStatusInfo


class FutureTrade:
    '''期货交易基类，是多空交易类的父类。定义了一个期货交易对外开放的接口和内部
    主要方法。
    '''
    logger = LoggerGetter()

    def __init__(self, tsi: TradeStatusInfo, api: TqApi, trade_config: dict):
        self._api = api
        account = api.get_account()
        symbol = tsi.current_symbol
        quote = self._api.get_quote(symbol)
        position = api.get_position(symbol)
        self._trade_tool = TargetPosTask(api, symbol)
        self._daily_klines = api.get_kline_serial(symbol, 60*60*24)
        self._h3_klines = api.get_kline_serial(symbol, 60*60*3)
        self._m30_klines = api.get_kline_serial(symbol, 60*30)
        self._m5_klines = api.get_kline_serial(symbol, 60*5)
        self._utils: TradeUtils = self._create_utils(
            account, position, tsi, quote, trade_config)
        self.calc_criteria(0)

    def _calc_open_pos_number(self) -> bool:
        utils = self._utils
        available = utils.account.balance * utils.buy_pos_scale
        pos = floor(available / utils.quote.bid_price1)
        return pos

    def _can_open_ops(self):
        utils = self._utils
        if utils.get_pos() == 0:
            if self._match_dk_cond():
                if self._match_3hk_cond():
                    if self._match_30mk_cond():
                        if self._match_5mk_cond():
                            return True

    def _trade_pos(self, total_pos, sale_pos) -> int:
        '''final 方法，进行期货交易。开仓平仓，多空都适用。
        '''
        logger = self.logger
        utils = self._utils
        log_str = '{}交易,价格:{}手数:{}'
        quote = utils.quote
        ts = self._utils
        target_pos = total_pos - sale_pos
        trade_time = ts.get_current_date_str()
        price = quote.last_price
        if target_pos <= 0:
            target_pos = 0
        self._trade_tool.set_target_volume(self._sale_target_pos(target_pos))
        while True:
            self._api.wait_update()
            if ts._get_pos_number() == target_pos:
                if sale_pos == 0:
                    logger.debug(log_str.format(
                        trade_time, price, total_pos))
                else:
                    logger.debug(log_str.format(
                        trade_time, price, sale_pos))
                break
        return target_pos

    def _closeout(self, sale_reason: str, is_switch=False) -> None:
        pos_number = self._utils._get_pos_number()
        self._sell_and_record_pos(pos_number, sale_reason, is_switch)

    def _sell_and_record_pos(self, sale_pos: int, sale_reason: str,
                             is_switch: bool) -> int:
        utils = self._utils
        price = utils.get_current_price()
        total_pos = utils._get_pos_number()
        rest_pos = self._trade_pos(total_pos, sale_pos)
        utils.set_close_info(price, sale_pos, sale_reason, is_switch)
        return rest_pos

    def _try_stop_loss(self) -> None:
        logger = self.logger
        utils = self._utils
        td = utils.tsi.trade_data
        trade_time = utils.get_current_date_str()
        price = utils.get_current_price()
        log_str = '{} {} <多空> {},现价:{},止损价:{},手数:{}'
        if utils.get_stoplose_status():
            pos = self._utils._get_pos_number()
            logger.info(log_str.format(
                trade_time, utils.tsi.current_symbol, td.slr,
                price, td.slp, pos))
            self._closeout(utils.sl_message)

    def _try_open_pos(self) -> bool:
        ''' 开仓,当没有任何持仓并满足开仓条件时买入。
        子类可以利用该方法加入日志等逻辑
        '''
        utils = self._utils
        td = utils.tsi.trade_data
        jd = utils.tsi.judge_data
        if utils._get_pos_number():
            return True
        if self._can_open_ops() and jd.d_cond != 0:
            logger = self.logger
            log_str = '{}合约:{}<多空>开仓,开仓价:{},{}手'
            open_pos = self._calc_open_pos_number()
            self._trade_pos(open_pos, 0)
            utils.set_open_info(open_pos)
            trade_time = utils.get_current_date_str()
            open_pos = utils._get_pos_number()
            logger.info(log_str.format(
                trade_time, utils.tsi.current_symbol, td.price, open_pos))
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
        if self._try_open_pos():
            self._try_sell_pos()

    def _get_last_dk_line(self):
        return self._daily_klines.iloc[-2]

    def _get_last_h3_kline(self):
        return self._h3_klines.iloc[-2]

    def _get_last_m30_kline(self):
        return self._m30_klines.iloc[-2]

    def get_Kline_values(self, kline) -> tuple:
        ema9 = kline.ema9
        ema22 = kline.ema22
        ema60 = kline.ema60
        macd = kline['MACD.close']
        close = kline.close
        open_p = kline.open
        trade_time = self._utils.get_current_date_str()
        return (ema9, ema22, ema60, macd, close, open_p, trade_time)

    def calc_criteria(self, k_type: int):
        '''计算某个周期的技术指标
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        if k_type == 1:
            calc_indicator(self._daily_klines)
        elif k_type == 2:
            calc_indicator(self._h3_klines)
        elif k_type == 3:
            calc_indicator(self._m30_klines)
        elif k_type == 4:
            calc_indicator(self._m5_klines)
        else:
            calc_indicator(self._daily_klines)
            calc_indicator(self._h3_klines)
            calc_indicator(self._m30_klines)
            calc_indicator(self._m5_klines)

    def is_changing(self, k_type: int) -> bool:
        '''当某种K线生成新的记录时返回True
        k_type 代表K线类型
        0:代表当日交易结束的时刻
        1:生成新日线
        2:生成新3小时线
        3:生成新30分钟线
        4:生成新5分钟线
        '''
        if k_type == 1:
            return self._api.is_changing(
                self._daily_klines.iloc[-1], "datetime")
        elif k_type == 2:
            return self._api.is_changing(
                self._h3_klines.iloc[-1], "datetime")
        elif k_type == 3:
            return self._api.is_changing(
                self._m30_klines.iloc[-1], "datetime")
        elif k_type == 4:
            return self._api.is_changing(
                self._m5_klines.iloc[-1], "datetime")
        elif k_type == 0:
            return self._api.is_changing(
                self._daily_klines.iloc[-1], "close")

    def finish(self) -> None:
        '''换月操作，代表当前交易已完成。
        如果当前合约交易有持仓，则全部平仓，
        并将tsi状态设置成下一个合约的初始状态
        '''
        logger = self.logger
        utils = self._utils
        tsi = utils.tsi
        logger.debug(tsi)
        if tsi.is_trading:
            hold_pos = tsi.trade_data.pos
            log_str = '换月清仓,售出数量{}'
            price = utils.quote.last_price
            self._trade_tool.set_target_volume(
                self._sale_target_pos(0))
            logger.info(log_str.format(hold_pos))
            utils.set_close_info(price, hold_pos, '换月平仓', True)
        else:
            tsi.switch_symbol(utils.get_current_date())
            utils.update_tsi()


class FutureTradeShort(FutureTrade):
    '''做空交易类
    '''
    def _create_utils(self, account, position, tsi, quote,
                      trade_config) -> TradeUtilsShort:
        rules = trade_config['short']
        return TradeUtilsShort(account, position, tsi, quote, rules)

    def _not_match_dk_cond(self) -> bool:
        # logger = self.logger
        # t_time = self._ts.get_current_date_str()
        # log_str = ('{} Last is N:{},Last2 is N:{},'
        #            'Last decline more then 2%:{},'
        #            'Last2 decline more than 2%:{}')
        # log_str2 = ('{} diff9_60:{},ema9:{},ema60:{},close:{}')
        l_kline = self._get_last_dk_line()
        # l2_kline = self._daily_klines.iloc[-3]
        # l3_kline = self._daily_klines.iloc[-4]
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(l_kline)
        diff9_60 = diff_two_value(e9, e60)
        diff22_60 = diff_two_value(e22, e60)
        if diff9_60 < 2 or diff22_60 < 2:
            if e60 < close:
                # logger.debug(log_str2.format(
                #     t_time, diff9_60, e9, e60, close))
                return True
        # if diff9_60 < 3:
        #     l_n = is_nline(l_kline)
        #     l2_n = is_nline(l2_kline)
        #     l_d2 = is_decline_2p(l_kline, l2_kline)
        #     l2_d2 = is_decline_2p(l2_kline, l3_kline)
        #     if (l_n and l2_n) or (l_d2 or l2_d2):
        #         logger.debug(log_str.format(t_time, l_n, l2_n, l_d2, l2_d2))
        #         return True
        return False

    def _match_dk_cond(self) -> bool:
        '''做空日线条件检测
        合约交易日必须大于等于60天
        '''
        logger = self.logger
        kline = self._get_last_dk_line()
        utils = self._utils
        symbol = utils.tsi.current_symbol
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        daily_k_time = get_date_str_short(kline.datetime)
        log_str = ('{}<做空>{}日线条件:{} K线时间:{},ema9:{},ema22:{},'
                   'ema60:{},收盘:{},MACD:{}')
        if kline['s_qualified']:
            return kline['s_qualified']
        elif kline.get('s_match', default=1) == 0:
            return False
        elif kline.id > 58:
            # 日线条件1
            if e22 > e60 and macd < 0 and e22 > close:
                # logger.debug(f'kline column:{kline}')
                is_match = not self._not_match_dk_cond()
                if is_match:
                    logger.debug(log_str.format(
                        trade_time, symbol, 1, daily_k_time,
                        e9, e22, e60, close, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           's_qualified'] = 1
                    utils.set_last_daily_kline(1, kline)
                else:
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           's_match'] = 0
                return is_match
        return False

    def _match_3hk_cond(self) -> bool:
        '''做空3小时线检测
        '''
        logger = self.logger
        utils = self._utils
        kline = self._get_last_h3_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        diff9_60 = diff_two_value(e9, e60)
        diff22_60 = diff_two_value(e22, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} {} 满足<做空>3小时条件:K线生成时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},开盘{}'
                   'diffc_60:{},diff9_60:{},diff22_60{},MACD:{}')
        if kline["s_qualified"]:
            return True
        if (e22 > e60 and
            (e22 > e9 or (e22 < e9 and close < e60 and open_p > e60))
           and diff9_60 < 3 and diff22_60 < 3 and diffc_60 < 3 and macd < 0):
            logger.debug(log_str.format(
                trade_time, utils.tsi.current_symbol, kline_time, e9, e22,
                e60, close, open_p, diffc_60, diff9_60, diff22_60, macd))
            self._h3_klines.loc[self._h3_klines.id == kline.id,
                                's_qualified'] = 1
            utils.set_last_h3_kline(kline)
            return True
        return False

    def _match_30mk_cond(self) -> bool:
        '''做空30分钟线检测
        '''
        logger = self.logger
        utils = self._utils
        kline = self._get_last_m30_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diff22_60 = diff_two_value(e22, e60)
        diff9_60 = diff_two_value(e9, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{}<做空>30分钟条件:K线时间:{},ema9:{},'
                   'ema22:{},ema60:{},收盘:{},diff22_60:{},deff9_60:{},MACD:{}')
        # logger.debug(log_str.format(
        #     trade_time, kline_time, e9, e22, e60, close,
        #     diff22_60, diff9_60, macd))
        if kline["s_qualified"]:
            return True
        if ((e60 > e22 > e9 or e22 > e60 > e9) and diff9_60 < 2
           and diff22_60 < 1 and macd < 0 and e60 > close
           and self.is_within_2days()):
            logger.debug(log_str.format(
                trade_time, kline_time, e9, e22, e60, close,
                diff22_60, diff9_60, macd))
            self._m30_klines.loc[self._m30_klines.id == kline.id,
                                 's_qualified'] = 1
            utils.set_last_m30_kline(kline)
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
        utils = self._utils
        symbol = utils.tsi.current_symbol
        td = utils.tsi.trade_data
        dk = self._get_last_dk_line()
        dks = []
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(dk)
        diff22_60 = diff_two_value(e22, e60)
        log_str = ('{}<做空>{}全部止赢,现价:{},手数:{},diff22_60:{},'
                   'close:{},macd:{}.之前符合条件K线日期{},macd{},'
                   'close:{},open:{}')
        utils.try_improve_sl_price()
        if utils.get_profit_status(dk):
            trade_time = utils.get_current_date_str()
            price = utils.get_current_price()
            if close > e9 and macd > 0:
                dks.append(self._daily_klines.iloc[-3])
                dks.append(self._daily_klines.iloc[-4])
                for t_dk in dks:
                    t_macd = t_dk['MACD.close']
                    if not is_nline(t_dk) and t_macd > 0:
                        sold_pos = td.pos
                        self._closeout('趋势止盈')
                        logger.info(log_str.format(
                            trade_time, symbol, price, sold_pos,
                            diff22_60, close, macd, get_date_str_short(
                                t_dk.datetime),
                            t_macd, t_dk.close, t_dk.open
                        ))
                        return
                td.stp = True
                utils.update_tsi()

    def trading_close_operation(self) -> None:
        '''弃用，主要进行收盘后的操作
        '''
        logger = self.logger
        utils = self._utils
        trade_time = utils.get_current_date_str()
        log_str = '{}<做空>{}开仓当天收盘价:{}大于EMA60:{},启动盈亏比止盈策略'
        if utils.tsi.is_trading:
            kline = self._daily_klines.iloc[-1]
            if self._pos.pos_short_today != 0:
                e9, e22, e60, macd, close, open_p, trade_time =\
                    self.get_Kline_values(kline)
                if close > e60:
                    utils.use_ps_ratio = True
                    utils.update_tsi()
                    logger.debug(
                        log_str.format(
                            trade_time,
                            self._symbol,
                            close,
                            e60))

    def is_within_2days(self) -> bool:
        # logger = self.logger
        utils = self._utils
        trade_time = utils.get_current_date_str()
        # log_str = ('{}<做空>{}当日K线生成时间{},最近一次30分钟收盘价与EMA60'
        #            '交叉时间{},ema60:{},close:{},距离在2天内,满足开仓条件')
        d_klines = self._daily_klines
        kline = d_klines.iloc[-1]
        last_dkline = self._get_last_dk_line()
        l30m_kline = d_klines.iloc[-9]
        # c_date = tafunc.time_to_datetime(kline.datetime)
        temp_df = self._m30_klines.iloc[::-1]
        e60, close = 0, 0
        for i, temp_kline in temp_df.iterrows():
            _, _, e60, _, close, open_p, trade_time =\
                self.get_Kline_values(temp_kline)
            if close >= e60:
                t30m_kline = self._m30_klines.iloc[i-1]
                _, et22, et60, _, _, _, t_time =\
                    self.get_Kline_values(t30m_kline)
                if et22 > et60:
                    l30m_kline = t30m_kline
                    break
        temp_date = tafunc.time_to_datetime(l30m_kline.datetime)
        l_date = tafunc.time_to_ns_timestamp(
            datetime(temp_date.year, temp_date.month, temp_date.day))

        l_kline = d_klines[d_klines.datetime == l_date].iloc[0]
        # logger.debug(f'当前日线id:{kline.id},最近一次交叉K线id:{l_kline.id},')
        # logger.debug(log_str.format(
        #     trade_time, self._symbol,
        #     get_date(c_date), temp_date,
        #     e60, close
        # ))
        limite_day = 2
        el9, el22, el60, _, cloes_l, _, _ =\
            self.get_Kline_values(last_dkline)
        if (diff_two_value(el22, el60) and cloes_l < el60
           or diff_two_value(el22, el60) > 5):
            limite_day = 3
        if kline.id - l_kline.id <= limite_day:
            # logger.debug(log_str.format(
            #     trade_time, self._symbol,
            #     get_date(c_date), get_date(l_date),
            #     e60, close
            # ))
            return True
        return False


class FutureTradeLong(FutureTrade):
    '''做多交易类
    '''
    def _create_utils(self, account, position, tsi, quote,
                      trade_config) -> TradeUtilsLong:
        rules = trade_config['long']
        return TradeUtilsLong(account, position, tsi, quote, rules)

    def _match_dk_cond(self) -> bool:
        '''做多日线条件检测
        合约交易日必须大于等于60天
        '''
        logger = self.logger
        kline = self._get_last_dk_line()
        utils = self._utils
        s = utils.tsi.current_symbol
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        daily_k_time = get_date_str_short(kline.datetime)
        log_str = ('{} {} <做多>日线{}:K线时间:{},ema9:{},ema22:{},'
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
                        trade_time, s, 1, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 1
                    utils.set_last_daily_kline(1, kline)
                    return True
            elif e22 > e60:
                # 日线条件2
                if diff22_60 < 1 and close > e60:
                    logger.debug(log_str.format(
                        trade_time, s, 2, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 2
                    utils.set_last_daily_kline(2, kline)
                    return True
                # 日线条件3
                elif (1 < diff9_60 < 3 and e9 > e22 and
                      e22 > min(open_p, close) > e60):
                    logger.debug(log_str.format(
                        trade_time, s, 3, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 3
                    utils.set_last_daily_kline(3, kline)
                    return True
                # 日线条件4
                elif (1 < diff22_60 < 3 and diff9_60 < 2 and e22 > close > e60
                      and e22 > e9 > e60):
                    logger.debug(log_str.format(
                        trade_time, s, 4, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 4
                    utils.set_last_daily_kline(4, kline)
                    return True
                # 日线条件5
                elif (diff22_60 > 3 and diffc_60 < 3 and
                      e22 > close > e60 and e22 > open_p > e60):
                    logger.debug(log_str.format(
                        trade_time, s, 5, daily_k_time, e9, e22, e60, close,
                        diff9_60, diffc_60, diff22_60, macd))
                    self._daily_klines.loc[self._daily_klines.id == kline.id,
                                           'l_qualified'] = 5
                    utils.set_last_daily_kline(5, kline)
                    return True
        return False

    def _match_3hk_cond(self) -> bool:
        '''做多2小时线检测
        '''
        logger = self.logger
        utils = self._utils
        jd = utils.tsi.judge_data
        s = utils.tsi.current_symbol
        kline = self._get_last_h3_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        diffo_60 = diff_two_value(open_p, e60)
        diff22_60 = diff_two_value(e22, e60)
        diff9_60 = diff_two_value(e9, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} {} <做多>2小时{}: K线时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},开盘:{},'
                   'diffc_60:{},diffo_60:{},diff22_60{},MACD:{}')
        if kline["l_qualified"]:
            return True
        if diffc_60 < 3 or diffo_60 < 3:
            if jd.d_cond in [1, 2]:
                if (e22 < e60 and e9 < e60 and
                    (diff22_60 < 1 or
                     (1 < diff22_60 < 2 and (macd > 0 or close > e60)))):
                    logger.debug(log_str.format(
                        trade_time, s, 1, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self._h3_klines.loc[self._h3_klines.id == kline.id,
                                        'l_qualified'] = 1
                    utils.set_last_h3_kline(1, kline)
                    return True
                elif close > e9 > e22 > e60:
                    if self._match_3hk_c2_distance():
                        logger.debug(log_str.format(
                            trade_time, s, 2, kline_time, e9, e22, e60, close,
                            open_p, diffc_60, diffo_60, diff22_60, macd))
                        self._h3_klines.loc[self._h3_klines.id == kline.id,
                                            'l_qualified'] = 2
                        utils.set_last_h3_kline(2, kline)
                        return True
                    if diff9_60 < 1 and diff22_60 < 1 and macd > 0:
                        logger.debug(log_str.format(
                            trade_time, s, 5, kline_time, e9, e22, e60, close,
                            open_p, diffc_60, diffo_60, diff22_60, macd))
                        self._h3_klines.loc[self._h3_klines.id == kline.id,
                                            'l_qualified'] = 5
                        utils.set_last_h3_kline(5, kline)
                        return True
            elif jd.d_cond in [3, 4]:
                if (close > e60 > e22 and macd > 0 and diff22_60 < 1 and e9 <
                   e60):
                    logger.debug(log_str.format(
                        trade_time, s, 3, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self._h3_klines.loc[self._h3_klines.id == kline.id,
                                        'l_qualified'] = 3
                    utils.set_last_h3_kline(3, kline)
                    return True
                elif jd.d_cond == 3 and diff9_60 < 1 and diff22_60 < 1:
                    logger.debug(log_str.format(
                        trade_time, s, 6, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self._h3_klines.loc[self._h3_klines.id == kline.id,
                                        'l_qualified'] = 6
                    utils.set_last_h3_kline(6, kline)
                    return True
            elif jd.d_cond == 5:
                if (e60 > e22 > e9):
                    logger.debug(log_str.format(
                        trade_time, s, 4, kline_time, e9, e22, e60, close,
                        open_p, diffc_60, diffo_60, diff22_60, macd))
                    self._h3_klines.loc[self._h3_klines.id == kline.id,
                                        'l_qualified'] = 4
                    utils.set_last_h3_kline(4, kline)
                    return True
        return False

    def _match_3hk_c2_distance(self) -> bool:
        # logger = self.logger
        klines = self._h3_klines.iloc[::-1]
        # log_str = 'k2:{},e9:{},e60:{},date:{}/k1:{},e22:{},e60:{},date:{}'
        k1, k2 = 0, 0
        is_done_1 = False
        for _, kline in klines.iterrows():
            # logger.debug(f'kline:{kline}')
            e9 = kline.ema9
            e22 = kline.ema22
            e60 = kline.ema60
            if not is_done_1 and e22 <= e60:
                k1 = kline.id
                # date1 = get_date_str(kline.datetime)
                # ema22 = e22
                # ema60_1 = e60
                is_done_1 = True
                # logger.debug(log_debug_1.format(
                #    k1, e9, e22, e60, date1
                # ))
            if e9 <= e60:
                k2 = kline.id
                # date2 = get_date_str(kline.datetime)
                # ema9 = e9
                # ema60_2 = e60
                # logger.debug(log_debug_2.format(
                #    k2, e9, e22, e60, date2
                # ))
                break
        if 0 <= k1 - k2 <= 5:
            # logger.debug(log_str.format(
            # k2, ema9, ema60_2, date2, k1, ema22, ema60_1, date1))
            # logger.debug('两个交点距离小于等于5,符合条件')
            return True
        return False

    def _match_30mk_cond(self) -> bool:
        '''做多30分钟线检测
        '''
        logger = self.logger
        utils = self._utils
        s = utils.tsi.current_symbol
        kline = self._get_last_m30_kline()
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} {} <做多>30分钟条件:K线时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},diffc_60:{},MACD:{}')
        if kline["l_qualified"]:
            return True
        if close > e60 and macd > 0 and diffc_60 < 1.2:
            logger.debug(log_str.format(
                trade_time, s, kline_time, e9, e22, e60,
                close, diffc_60, macd))
            self._m30_klines.loc[self._m30_klines.id == kline.id,
                                 'l_qualified'] = 1
            utils.set_last_m30_kline(kline)
            return True
        return False

    def _match_5mk_cond(self) -> bool:
        '''做多5分钟线检测
        '''
        logger = self.logger
        utils = self._utils
        s = utils.tsi.current_symbol
        kline = self._m5_klines.iloc[-2]
        e9, e22, e60, macd, close, open_p, trade_time =\
            self.get_Kline_values(kline)
        diffc_60 = diff_two_value(close, e60)
        kline_time = get_date_str(kline.datetime)
        log_str = ('{} {} <做多>5分钟条件:K线时间:{},'
                   'ema9:{},ema22:{},ema60:{},收盘:{},diffc_60:{},MACD:{}')
        if close > e60 and macd > 0 and diffc_60 < 1.2:
            logger.debug(log_str.format(
                trade_time, s, kline_time, e9, e22, e60,
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
        utils = self._utils
        td = utils.tsi.trade_data
        s = utils.tsi.current_symbol
        dk = self._get_last_dk_line()
        log_str = "{} {} <做多>止赢{},现价:{},手数:{},剩余仓位:{},止赢起始价:{}"
        sp_log = '止盈{}-售出{}'
        trade_time = utils.get_current_date_str()
        price = utils.get_current_price()
        # ts.update_profit_stage(dk, m30k)
        if utils.get_profit_status() in [1, 2, 3]:
            utils.try_improve_sl_price()
            result = utils.is_final5_closeout(dk)
            if result:
                sold_pos = utils._get_pos_number()
                self._closeout(sp_log.format(td.p_cond, '100%'))
                logger.info(log_str.format(
                    trade_time, s, td.p_cond, price,
                    sold_pos, 0, td.spp))
        elif utils.get_profit_status() in [4]:
            if td.p_stage == 1:
                td.p_stage = 2
                sold_pos = utils._get_pos_number()//2
                rest_pos = self._sell_and_record_pos(
                    sold_pos, sp_log.format(td.p_cond, '50%'), False)
                logger.info(log_str.format(
                    trade_time, s, td.p_cond, price,
                    sold_pos, rest_pos, td.spp))
                utils.update_tsi()
            elif td.p_stage == 2:
                if (utils.get_current_price() >=
                   utils.calc_price(td.price, True, 3)):
                    sold_pos = utils._get_pos_number()
                    self._closeout(sp_log.format(td.p_cond, '剩余全部'))
                    logger.info(log_str.format(
                        trade_time, s,
                        td.p_cond, price, sold_pos, 0, td.spp))

    def buy_pos(self, tsv: Trade_Status_Virtual) -> None:
        '''弃用，暂时不使用虚拟开仓逻辑换月时，如果虚拟交易有持仓，则直接现价买入
        '''
        logger = self.logger
        log_str = '{} {} <做多>换月开仓,开仓价:{},数量{}'
        utils = self._utils
        trade_time = utils.get_current_date_str()
        price = utils.get_current_price()
        if tsv.is_trading:
            logger = self.logger
            self._trade_pos(tsv._pos_quantity, 0)
            logger.info(log_str.format(
                trade_time, self._symbol, price, tsv._pos_quantity))
            self._ts = tsv.create_tsl()
            self._ts._record_to_excel()


class Future_Trade_Long_Virtual(FutureTradeLong):
    '''弃用虚拟开仓方法。虚拟做多交易类,用于跟踪期货下一个合约的交易状态。
    如果符合交易条件，则记录当时的止盈止损价格，并在之后跟踪调整止盈点位。
    当换月时，根据该对象的状态决定是否买入换月后的合约。
    '''
    def __init__(self, tsi: TradeStatusInfo, api: TqApi, symbol: str,
                 symbol_config: dict) -> None:
        super().__init__(tsi, api, symbol, symbol_config)
        self._ts = Trade_Status_Virtual(
            self._account, self._pos, symbol,
            self._quote, self._ts.rules)

    def _sell_and_record_pos(self, sale_pos: int, sale_reason: str) -> int:
        logger = self.logger
        logger.debug('虚拟交易清仓')
        ts = self._ts
        price = ts.get_current_price()
        total_pos = ts._get_pos_number()
        rest_pos = total_pos - sale_pos
        ts.set_close_info(price, sale_pos, sale_reason)
        return rest_pos

    def _trade_pos(self, total_pos, sale_pos):
        logger = self.logger
        target_pos = total_pos - sale_pos
        logger.debug(f'虚拟交易,目标仓位{target_pos}')
        return target_pos

    def get_trade_status(self) -> Trade_Status_Virtual:
        return self._ts
