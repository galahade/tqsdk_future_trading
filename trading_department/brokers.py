from utils.tools import get_date_str
from utils.common import LoggerGetter
# from tqsdk2 import TqApi, tafunc
from tqsdk import TqApi, tafunc
from trade.trades import FutureTrade, FutureTradeLong,\
        FutureTradeShort
from trade.utils import TradeUtilsData


class LongTermTradeBrokerManager:
    logger = LoggerGetter()

    def __init__(self,  api: TqApi, fc, direction,
                 just_check, dbservice, is_backtest):
        '''direction:代表交易方向
        0: short，1: long，2: all
        '''
        self._api = api
        self.tud = TradeUtilsData(api, fc, dbservice, direction, just_check,
                                  is_backtest)
        self._zl_symbol = fc.symbol.strip()
        self._zl_quote = api.get_quote(self._zl_symbol)
        self._long_ftu = None
        self._short_ftu = None
        if direction:
            self._long_ftu = LongTermTradeLongBroker(self.tud)
            if direction == 2:
                self._short_ftu = LongTermTradeShortBroker(self.tud)
        else:
            self._short_ftu = LongTermTradeShortBroker(self.tud)

    def _try_trade(self) -> None:
        '''调用多空broker进行交易
        '''
        if self._long_ftu:
            self._long_ftu.try_trade()
        if self._short_ftu:
            self._short_ftu.try_trade()

    def _calc_indicators(self, k_type):
        '''计算当前交易工具中所有交易的某个周期的技术指标
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        if self._long_ftu:
            self._long_ftu.trade.calc_criteria(k_type)
        if self._short_ftu:
            self._short_ftu.trade.calc_criteria(k_type)

    def _is_changing(self, k_type) -> bool:
        '''判断交易工具类种的合约中某种K线是否发生变化
        由于合约交易时间相同，只需判断一个合约即可
        当该K线发生变化时，则调用相关方法进行进一步操作
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        if self._long_ftu:
            return self._long_ftu.trade.is_changing(k_type)
        else:
            return self._short_ftu.trade.is_changing(k_type)

    def _trade(self) -> None:
        '''根据交易数据的推进进行相应的操作。
        * 1: 生成新的日K线，在回测中需要相应的收盘操作
            而在实盘交易中由于每天重启系统，则不需要进行相关操作。
        * 2: 生成新的3小时线，需要根据新生成的K线产生相关交易指标。
        * 3: 生成新的30分钟线，需要根据新生成的K线产生相关交易指标。
        * 4: 生成新的5分钟线，需要根据新生成的K线产生相关交易指标。
        * 如果在交易时间内quote被更新，则尝试进行交易判断。
        '''
        if self.tud.is_backtest:
            # 只有在回测中需要用到以下逻辑
            # 当天交易结束时即17:59:59，会触发以下条件，
            if self._is_changing(1):
                self._close_operation()
        if self._is_changing(2):
            self._calc_indicators(2)
        if self._is_changing(3):
            self._calc_indicators(3)
        if self._is_changing(4):
            self._calc_indicators(4)
        if self._api.is_changing(self._zl_quote, "datetime"):
            self._try_trade()

    def _close_operation(self):
        '''收盘后将必要的数据重置，
        仅回测需要使用，实盘交易每日需重启服务，故不需要使用该方法重置数据
        '''
        logger = self.logger
        log_str = '{} {} 交易结束'
        self._calc_indicators(1)
        if self._long_ftu:
            self._long_ftu.trading_close_operation()
        if self._short_ftu:
            self._short_ftu.trading_close_operation()
        logger.info(log_str.format(
            get_date_str(self._zl_quote.datetime),
            self._zl_symbol))

    def _daily_check_task(self) -> None:
        '''每日交易前对期货合约进行检查，判断是否需要进行换月
        '''
        if self._long_ftu:
            self._long_ftu.daily_check_task()
        if self._short_ftu:
            self._short_ftu.daily_check_task()

    def daily_opration(self) -> None:
        '''期货交易操作对外接口。
        交易时间内循环调用该方法,实现期货交易逻辑，包括两部分：
        * 开始交易前检查期货是否需要换月
        * 跟踪交易信号，当满足条件时进行交易
        '''
        self._daily_check_task()
        self._trade()


class LongTermTradeShortBroker:
    logger = LoggerGetter()

    def __init__(self, tud: TradeUtilsData) -> None:
        self.tud = tud
        self._api = tud.api
        self._zl_symbol = tud.future_config.symbol
        self._zl_quote = tud.api.get_quote(self._zl_symbol)
        self.trade = self._init_trade()
        self._daily_checked = False
        self._trade_checked = False

    def _init_trade(self) -> FutureTrade:
        '''运行时执行一次，创建期货交易对象进行交易
        '''
        trade_time = tafunc.time_to_datetime(self._zl_quote.datetime)
        tsi = self.tud.dbservice.init_trade_status_info(
            self._zl_symbol, self._zl_quote, False, trade_time)
        return FutureTradeShort(tsi, self.tud)

    def _get_symbol(self) -> str:
        return self.trade._utils.tsi.current_symbol

    def _need_switch_contract(self):
        '''判断是否需要换月,规则是：
        * 如果原合约有持仓，则在合约交日之前20天换月
        * 否则，在交割日之前45天换月。
        '''
        trade = self.trade
        if trade._utils.tsi.next_symbol is not None:
            return self._is_time_to_switch_month()
        return False

    def _is_time_to_switch_month(self) -> bool:
        trade = self.trade
        utils = trade._utils
        config = self.tud.future_config
        trade_time = utils.get_current_date_str()
        quote = utils.quote
        self.logger.info(f'{trade_time} {utils.tsi.current_symbol} '
                         f'距原合约截止日{quote.expire_rest_days}天')
        if (utils.get_pos() > 0 and
           quote.expire_rest_days <= config.switch_days[0]):
            return True
        elif (utils.get_pos() == 0
              and quote.expire_rest_days <= config.switch_days[1]):
            return True
        return False

    def _check_record_nsymbol(self) -> None:
        '''检查服务端是否已经更换主力合约，
        如果已更换，则将新的主力合约保持至数据库中，
        以备换月时使用。
        '''
        logger = self.logger
        utils = self.trade._utils
        tsi = utils.tsi
        n_symbol = self._zl_quote.underlying_symbol
        if tsi.has_change_symbol(n_symbol):
            tsi.last_modified = utils.get_current_date()
            self.tud.dbservice.update_tsi_next_symbol(tsi, n_symbol)
            logger.info(f'{utils.get_current_date_str()}'
                        f'{self.trade._utils.tsi.custom_symbol} 天勤主力合约已更换,'
                        f'原合约 {tsi.current_symbol},'
                        f'新合约 {n_symbol},开始准备切换合约')

    def try_trade(self) -> None:
        '''尝试进行交易。
        实盘交易时，根据交易状态判断是否处于交易时间，并在每日第一次尝试交易时
        输出开始交易信息。
        回测时，无法使用交易状态对象。需要使用其他方法确定交易时间。
        '''
        logger = self.logger
        log_str = '{} {} {} 交易开始'
        symbol = self._get_symbol()
        if not self.tud.is_backtest:
            ts = self._api.get_trading_status(symbol)
            if not self._trade_checked and ts.trade_status == "CONTINOUS":
                self._trade_checked = True
                logger.info(log_str.format(
                    get_date_str(self._zl_quote.datetime),
                    self._get_symbol(),
                    self.trade._utils.tsi.custom_symbol
                ))
            if ts.trade_status == "CONTINOUS":
                self.trade.try_trade()
        else:
            if not self._trade_checked:
                self._trade_checked = True
                logger.info(log_str.format(
                    get_date_str(self._zl_quote.datetime),
                    self._get_symbol(),
                    self.trade._utils.tsi.custom_symbol
                ))
            self.trade.try_trade()

    def switch_trade(self):
        '''符合换月条件后，执行换月操作，生成新的交易对象进行交易。
        '''
        logger = self.logger
        utils = self.trade._utils
        trade_time = utils.get_current_date()
        o_symbol = utils.tsi.current_symbol
        self.trade = self.trade.finish()
        logger.info(f'{trade_time} {self.trade._utils.tsi.custom_symbol}换月完成:'
                    f'原合约 {o_symbol},'
                    f'新合约 {utils.tsi.current_symbol}')

    def daily_check_task(self) -> None:
        '''开盘前对期货合约进行检查，查看是否符合换月条件。
        如满足则进行换月
        '''
        logger = self.logger
        symbol = self._get_symbol()
        log_str = '{} {} {} 交易日检查任务结束'
        # 只有实盘交易支持查看交易状态的操作
        if not self.tud.is_backtest:
            ts = self._api.get_trading_status(symbol)
            if ((ts.trade_status == "AUCTIONORDERING" or
                 ts.trade_status == "CONTINOUS") and not self._daily_checked):
                self._check_record_nsymbol()
                if self._need_switch_contract():
                    self.switch_trade()
                self._daily_checked = True
                logger.info(log_str.format(
                    get_date_str(self._zl_quote.datetime),
                    self._get_symbol(),
                    self.trade._utils.tsi.custom_symbol
                ))
        else:
            if not self._daily_checked:
                self._check_record_nsymbol()
                if self._need_switch_contract():
                    self.switch_trade()
                self._daily_checked = True
                logger.info(log_str.format(
                    get_date_str(self._zl_quote.datetime),
                    self._get_symbol(),
                    self.trade._utils.tsi.custom_symbol
                ))

    def trading_close_operation(self) -> None:
        self._daily_checked = False
        self._trade_checked = False


class LongTermTradeLongBroker(LongTermTradeShortBroker):
    logger = LoggerGetter()

    def _init_trade(self) -> FutureTrade:
        trade_time = tafunc.time_to_datetime(self._zl_quote.datetime)
        tsi = self.tud.dbservice.init_trade_status_info(
            self._zl_symbol, self._zl_quote, True, trade_time)
        return FutureTradeLong(tsi, self.tud)
