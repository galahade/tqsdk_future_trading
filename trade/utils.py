import logging


def get_logger():
    return logging.getLogger(__name__)


class Future_Trade_Util:
    '''
    单个期货品种交易使用改类对象，包括多空两个方向，
    并且会在天勤切换该品种主力合约后跟踪新的主力合约，
    判断是否进行虚拟交易。如果符合交易规则，则会记录交易止盈止损条件。
    以便在换月后买入，并跟踪止盈止损。
    '''
    def __init__(self, long_ftu, short_ft):
        self._lftu = long_ftu
        self._sft = short_ft

    def try_trade(self):
        '''
        在交易时间内每次交易信息更新后调用该方法尝试进行交易。
        交易包括尝试开仓，如果已经开仓，则尝试止损止盈。
        '''
        # 如果不能做多，则尝试做空
        if not self._lftu.try_trade():
            self._sft.try_trade()

    def create_next_symbol_trade(self):
        '''
        为回测提供的方法，用来在天勤切换主力合约后创建一个虚拟交易，
        用来跟踪换月前，当前主力合约的交易情况。
        将来有可能会在正式交易版本上线时取消。
        '''
        self._lftu.create_next_symbol_trade()

    def switch_trade(self):
        '''
        当满足换月条件后，进行合约切换操作。
        多空交易同时进行。
        '''
        pass
