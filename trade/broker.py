from utils.tools import get_date_str, examine_symbol
from utils.common import LoggerGetter
from datetime import datetime
from tqsdk.objs import Quote
from tqsdk import TqApi, tafunc
from trade.trades import Future_Trade, Future_Trade_Long,\
        Future_Trade_Short
from entity.status import Trade_Status
from dao.dao_service import init_trade_status_info, update_tsi_next_symbol


class Future_Trade_Broker:
    logger = LoggerGetter()

    def __init__(self,  api: TqApi, symbol_config: dict, trade_type=2) -> None:
        ''' trade_type:代表要执行的策略类型
        0: short，1: long，2: all
        '''
        self._api = api
        symbol = symbol_config['symbol']
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

    def try_trade(self) -> None:
        for trade_util in self._ftu_list:
            trade_util.try_trade()

    def ready_for_switch(self) -> None:
        '''当天勤主力合约切换后，在交易状态信息中记录下一个主力合约。
        当满足换月条件后使用该合约作为下一个主力合约。
        '''
        for trade_util in self._ftu_list:
            trade_util.ready_for_switch()

    def switch_trade(self):
        '''在主连合约更换主力合约后调用，
        如果满足换月条件，则进行换月操作。
        '''
        for ftu in self._ftu_list:
            if ftu._need_switch_contract():
                ftu.switch_trade()

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
        if self._api.is_changing(self._zl_quote, "underlying_symbol"):
            # self.create_next_trade()
            self.ready_for_switch()
        # 当天交易结束时即17:59:59，会触发以下条件，
        if self.is_changing(1):
            self.close_operation()
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

    def close_operation(self):
        logger = self.logger
        log_str = '{} {}'
        logger.debug(log_str.format(
            get_date_str(self._zl_quote.datetime),
            self._get_trading_symbol(),
        ))
        self.calc_indicators(1)
        self.switch_trade()
        # print(self._short_ftu._current_trade._pos)
        # self.trading_close_operation()

    def trading_close_operation(self) -> None:
        for ftu in self._ftu_list:
            ftu.trading_close_operation()

    def get_next_symbol(self) -> str:
        quote = self._long_ftu._current_trade._quote
        symbol = self._long_ftu._current_trade._symbol
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
            return ftu._current_trade._symbol


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
        self._current_trade = self._init_trade(symbol, trade_time)

    def _init_trade(self, symbol, trade_time) -> Future_Trade:
        tsi = init_trade_status_info(self._zl_symbol,
                                     symbol, False, trade_time)
        return Future_Trade_Short(tsi, self._api, symbol, self._config)

    def _create_trade(self, symbol, trade_time) -> Future_Trade:
        tsi = self._current_trade._tsi
        return Future_Trade_Short(tsi, self._api, symbol, self._config)

    def ready_for_switch(self) -> None:
        ''' 平台主力合约更换时调用，将换月时需要的下一个合约记录到存储引擎
        '''
        logger = self.logger
        symbol = self._zl_quote.underlying_symbol
        ts = self._current_trade._ts
        trade_time = ts.get_current_date()
        tsi = self._current_trade._tsi
        tsi.last_modified = trade_time
        update_tsi_next_symbol(tsi, symbol)
        logger.debug(f'{ts.get_current_date_str()} 天勤主力合约已更换,'
                     f'原合约 {self._current_trade._symbol},'
                     f'新合约 {symbol},开始准备切换合约')

    def create_next_trade(self) -> None:
        '''将被替换 创建下一个合约的虚拟交易，跟踪其行情
        '''
        logger = self.logger
        symbol = self._zl_quote.underlying_symbol
        trade_time = self._current_trade._ts.get_current_date_str()
        logger.debug(f'{trade_time} 天勤主力合约已更换,'
                     f'原合约 {self._current_trade._symbol},'
                     f'新合约 {symbol},开始准备切换合约')
        self._next_trade = True

    def try_trade(self) -> None:
        self._current_trade.try_trade()

    def switch_trade(self):
        logger = self.logger
        ts = self._current_trade._ts
        old_symbol = self._current_trade._symbol
        new_symbol = self._zl_quote.underlying_symbol
        trade_time = ts.get_current_date()
        self._current_trade.finish()
        self._current_trade = self._create_trade(new_symbol, trade_time)
        logger.info(f'{trade_time} <做空>换月完成:原合约 {old_symbol},'
                    f'新合约 {self._current_trade._symbol}')

    def calc_indicators(self, k_type: int):
        '''计算当前交易工具中所有交易的某个周期的技术指标
        k_type 用来表示具体周期：
        1:日线，2:2小时线，3:30分钟线，4:5分钟线
        '''
        self._current_trade.calc_criteria(k_type)

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
        return self._current_trade.is_changing(k_type)

    def _need_switch_contract(self):
        '''判断是否需要换月
        规则是：如果原合约有持仓，则在合约交割月之前10天换月
        否则，在交割月之前一个月月初换月。
        '''
        trade = self._current_trade
        if trade._tsi.next_symbol is not None:
            return self._is_time_to_switch_month(trade._quote, trade._ts)
        return False

    def trading_close_operation(self) -> None:
        self._current_trade.trading_close_operation()

    def _is_time_to_switch_month(self, quote: Quote, ts: Trade_Status) -> bool:
        trade_time = get_date_str(quote.datetime)
        self.logger.debug(f'{trade_time} {ts._symbol} '
                          f'距原合约截止日{quote.expire_rest_days}天')
        if (ts._get_pos_number() > 0 and
           quote.expire_rest_days <= self._switch_days[0]):
            return True
        elif (ts._get_pos_number() == 0
              and quote.expire_rest_days <= self._switch_days[1]):
            return True
        return False


class Long_Future_Trade_Broker(Short_Future_Trade_Broker):
    logger = LoggerGetter()

    def __init__(self, zl_symbol: str, zl_quote: Quote, api: TqApi,
                 symbol_config: dict,) -> None:
        super().__init__(zl_symbol, zl_quote, api, symbol_config)

    def _init_trade(self, symbol, trade_time) -> Future_Trade:
        tsi = init_trade_status_info(self._zl_symbol,
                                     symbol, True, trade_time)
        return Future_Trade_Long(tsi, self._api, symbol, self._config)

    def _create_trade(self, symbol, trade_time) -> Future_Trade:
        tsi = self._current_trade._tsi
        return Future_Trade_Long(tsi, self._api, symbol, self._config)

    def trading_close_operation(self) -> None:
        pass
