from utils.tools import get_date_str, examine_symbol
from utils.common import LoggerGetter
from datetime import datetime
from tqsdk.objs import Quote
from tqsdk import TqApi, tafunc
from trade.trades import FutureTrade, FutureTradeLong,\
        FutureTradeShort
from dao.dao_service import init_trade_status_info, update_tsi_next_symbol


class Future_Trade_Broker:
    logger = LoggerGetter()

    def __init__(self,  api: TqApi, symbol_config: dict, trade_type=2) -> None:
        ''' trade_type:代表要执行的策略类型
        0: short，1: long，2: all
        '''
        self._api = api
        symbol = symbol_config['symbol']
        self._zl_symbol = symbol
        self._mains = symbol_config['main_list']
        self._zl_quote = api.get_quote(symbol)
        self._ftu_list: list(Future_Trade_Broker) = []
        if trade_type:
            if trade_type == 1:
                self._long_ftu = Long_Future_Trade_Broker(
                    symbol, self._zl_quote, api, symbol_config)
                self._ftu_list.append(self._long_ftu)
            else:
                self._long_ftu = Long_Future_Trade_Broker(
                    symbol, self._zl_quote, api, symbol_config)
                self._short_ftu = Short_Future_Trade_Broker(
                    symbol, self._zl_quote, api, symbol_config)
                self._ftu_list.append(self._long_ftu)
                self._ftu_list.append(self._short_ftu)
        else:
            self._short_ftu = Short_Future_Trade_Broker(
                symbol, self._zl_quote, api, symbol_config)
            self._ftu_list.append(self._short_ftu)

    def _get_date_from_symbol(self, symbol_last_part):
        temp = int(symbol_last_part)
        year = int(temp / 100) + 2000
        month = temp % 100
        day = 1
        return datetime(year, month, day, 0, 0, 0)

    def _try_trade(self) -> None:
        for trade_util in self._ftu_list:
            trade_util.try_trade()

    def _calc_indicators(self, k_type):
        '''计算当前交易工具中所有交易的某个周期的技术指标
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        for trade_util in self._ftu_list:
            trade_util.calc_indicators(k_type)

    def _is_changing(self, k_type) -> bool:
        '''判断交易工具类种的合约中某种K线是否发生变化
        由于合约交易时间相同，只需判断一个合约即可
        当该K线发生变化时，则调用相关方法进行进一步操作
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        for ftu in self._ftu_list:
            return ftu.is_changing(k_type)

    def start_trading(self) -> None:
        '''期货交易工具对外接口。交易时间内不断循环调用该接口
        实现期货交易逻辑，包括：
        * 尝试开仓
        * 开仓后尝试止盈止损
        * 天勤更换主力合约后，做多交易开始跟踪新主力交易状态
        * 符合换月条件后，切换实际交易对象
        '''
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
            t_time = tafunc.time_to_datetime(self._zl_quote.datetime)
            # 为避免交易开始之前做出错误判断，需在交易时间进行交易
            if t_time.hour > 8:
                self._try_trade()

    def _close_operation(self):
        logger = self.logger
        log_str = '{} {}'
        logger.debug(log_str.format(
            get_date_str(self._zl_quote.datetime),
            self._get_trading_symbol(),
        ))
        self._calc_indicators(1)
        # print(self._short_ftu._current_trade._pos)
        # self.trading_close_operation()

    def _trading_close_operation(self) -> None:
        for ftu in self._ftu_list:
            ftu.trading_close_operation()

    def _get_next_symbol(self) -> str:
        quote = self._long_ftu._trade._quote
        utils = self._long_ftu._trade._utils
        symbol = utils.tsi.current_symbol
        next_index = self._mains.index(quote.delivery_month) + 1
        symbol_list = examine_symbol(symbol)
        symbol_year = quote.delivery_year
        if next_index >= len(self._mains):
            next_index = 0
        if next_index == 0:
            symbol_year += 1
        symbol_month = self._mains[next_index]
        next_symbol = (f'{symbol_list[0]}.{symbol_list[1]}'
                       f'{symbol_year}{symbol_month:02}')
        self.logger.debug(f'next symbol is {next_symbol}')
        return next_symbol

    def _get_trading_symbol(self) -> str:
        for ftu in self._ftu_list:
            return ftu._trade._utils.tsi.current_symbol

    def daily_check_task(self) -> None:
        logger = self.logger
        # ts = self._api.get_trading_status(self._zl_symbol)
        # if ts.trade_status == "AUCTIONORDERING":
        if self._api.is_changing(
           self._short_ftu._trade._daily_klines.iloc[-1], "open_oi"):
            log_str = '{}-{}'
            logger.debug(log_str.format(
                get_date_str(self._zl_quote.datetime),
                self._get_trading_symbol(),
            ))
            self._check_record_nsymbol()
            self._check_switch_trade()

    def _check_record_nsymbol(self) -> None:
        '''当天勤主力合约切换后，在交易状态信息中记录下一个主力合约。
        当满足换月条件后使用该合约作为下一个主力合约。
        '''
        for trade_util in self._ftu_list:
            trade_util.check_record_nsymbol()

    def _check_switch_trade(self) -> None:
        '''在主连合约更换主力合约后调用，
        如果满足换月条件，则进行换月操作。
        '''
        for ftu in self._ftu_list:
            if ftu._need_switch_contract():
                ftu.switch_trade()


class Short_Future_Trade_Broker:
    logger = LoggerGetter()

    def __init__(self, zl_symbol: str, zl_quote: Quote, api: TqApi,
                 symbol_config: dict) -> None:
        self._api = api
        self._zl_symbol = zl_symbol
        self._zl_quote = zl_quote
        self._config = symbol_config
        self._switch_days = symbol_config['switch_days']
        symbol = self._zl_quote.underlying_symbol
        trade_time = tafunc.time_to_datetime(zl_quote.datetime)
        self._trade = self._init_trade(symbol, trade_time)

    def _init_trade(self, symbol, trade_time) -> FutureTrade:
        tsi = init_trade_status_info(self._zl_symbol,
                                     symbol, False, trade_time)
        return FutureTradeShort(tsi, self._api, self._config)

    def _create_trade(self, symbol, trade_time) -> FutureTrade:
        tsi = self._trade._utils.tsi
        return FutureTradeShort(tsi, self._api, self._config)

    def create_next_trade(self) -> None:
        '''将被替换 创建下一个合约的虚拟交易，跟踪其行情
        '''
        logger = self.logger
        tsi = self._trade._utils.tsi
        o_symbol = tsi.current_symbol
        symbol = self._zl_quote.underlying_symbol
        trade_time = self._trade._utils.get_current_date_str()
        logger.debug(f'{trade_time} 天勤主力合约已更换,'
                     f'原合约 {o_symbol},'
                     f'新合约 {symbol},开始准备切换合约')
        self._next_trade = True

    def try_trade(self) -> None:
        self._trade.try_trade()

    def switch_trade(self):
        logger = self.logger
        utils = self._trade._utils
        old_symbol = utils.tsi.current_symbol
        new_symbol = utils.tsi.next_symbol
        trade_time = utils.get_current_date()
        self._trade.finish()
        self._trade = self._create_trade(new_symbol, trade_time)
        logger.info(f'{trade_time} 换月完成:原合约 {old_symbol},'
                    f'新合约 {new_symbol}')

    def calc_indicators(self, k_type: int):
        '''计算当前交易工具中所有交易的某个周期的技术指标
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        self._trade.calc_criteria(k_type)

    def is_changing(self, k_type) -> bool:
        '''判断交易工具类种的合约中某种K线是否发生变化
        由于合约交易时间相同，只需判断一个合约即可
        当该K线发生变化时，则调用相关方法进行进一步操作
        k_type 用来表示具体周期：
        0:代表当日交易结束的时刻
        1:生成新日线
        2:生成新3小时线
        3:生成新30分钟线
        4:生成新5分钟线
        '''
        return self._trade.is_changing(k_type)

    def _need_switch_contract(self):
        '''判断是否需要换月
        规则是：如果原合约有持仓，则在合约交割月之前10天换月
        否则，在交割月之前一个月月初换月。
        '''
        trade = self._trade
        if trade._utils.tsi.next_symbol is not None:
            return self._is_time_to_switch_month()
        return False

    def trading_close_operation(self) -> None:
        self._trade.trading_close_operation()

    def _is_time_to_switch_month(self) -> bool:
        trade = self._trade
        utils = trade._utils
        # trade_time = utils.get_current_date_str()
        quote = utils.quote
        # self.logger.debug(f'{trade_time} {utils.tsi.current_symbol} '
        # f'距原合约截止日{quote.expire_rest_days}天')
        if (utils._get_pos_number() > 0 and
           quote.expire_rest_days <= self._switch_days[0]):
            return True
        elif (utils._get_pos_number() == 0
              and quote.expire_rest_days <= self._switch_days[1]):
            return True
        return False

    def check_record_nsymbol(self) -> None:
        '''检查是否需要记录主力合约的更换,
        如需更换，将换月时需要的下一个合约记录到存储引擎
        '''
        logger = self.logger
        utils = self._trade._utils
        tsi = utils.tsi
        symbol = self._zl_quote.underlying_symbol
        c_symbol = tsi.current_symbol
        if (symbol != c_symbol and
           (tsi.next_symbol is None or tsi.next_symbol != symbol)):
            tsi.last_modified = utils.get_current_date()
            update_tsi_next_symbol(tsi, symbol)
            logger.debug(f'{utils.get_current_date_str()} 天勤主力合约已更换,'
                         f'原合约 {c_symbol},'
                         f'新合约 {symbol},开始准备切换合约')


class Long_Future_Trade_Broker(Short_Future_Trade_Broker):
    logger = LoggerGetter()

    def __init__(self, zl_symbol: str, zl_quote: Quote, api: TqApi,
                 symbol_config: dict,) -> None:
        super().__init__(zl_symbol, zl_quote, api, symbol_config)

    def _init_trade(self, symbol, trade_time) -> FutureTrade:
        tsi = init_trade_status_info(self._zl_symbol,
                                     symbol, True, trade_time)
        return FutureTradeLong(tsi, self._api, self._config)

    def _create_trade(self, symbol, trade_time) -> FutureTrade:
        tsi = self._trade._utils.tsi
        return FutureTradeLong(tsi, self._api, self._config)

    def trading_close_operation(self) -> None:
        pass
