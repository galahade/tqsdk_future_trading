from utils.tools import get_custom_symbol
# from bson.objectid import ObjectId


class Trade_Data:
    pass


class Judge_Data:
    pass


class TradeStatusInfo:
    def __init__(self, zl_symbol: str, trade_time=None,
                 current_symbol='', l_or_s=True):
        self.custom_symbol = get_custom_symbol(zl_symbol, l_or_s)
        self.current_symbol = current_symbol
        self.last_modified = trade_time
        self.next_symbol = None
        self.is_trading = False
        self._id = None
        self.trade_data = Trade_Data()
        self.judge_data = Judge_Data()
        self._init_trade_data()
        self._init_judge_data()

    def _init_trade_data(self):
        self.trade_data.open_pos_id = None
        self.trade_data.price = 0
        self.trade_data.pos = 0
        self.trade_data.trade_date = None
        # 该属性表示止盈阶段
        self.trade_data.p_stage = 0
        # 该属性表示该交易适用的止盈条件
        self.trade_data.p_cond = 0
        # 该属性表示是否已经提高止损价
        self.trade_data.has_islp = False
        # 该属性表示止损价格
        self.trade_data.slp = 0.0
        # 该属性表示止损原因
        self.trade_data.slr = '止损'
        # 该属性表示止盈监控开始价格
        self.trade_data.spp = 0.0
        # 该属性表示进入止盈阶段
        self.trade_data.bsp = False
        # 该属性表示停止跟踪止盈
        self.trade_data.stp = False

    def _init_judge_data(self):
        # 该属性表示当前状态满足的日线条件
        self.judge_data.d_cond = 0
        self.judge_data.d_kline = None
        # 该属性表示当前状态满足的3小时线条件
        self.judge_data.h3_cond = 0
        self.judge_data.h3_kline = None
        self.judge_data.m30_kline = None

    def close_out(self) -> None:
        self.is_trading = False
        self._init_judge_data()
        self._init_trade_data()

    def switch_symbol(self, trade_time) -> None:
        self.last_modified = trade_time
        self.close_out()
        self.current_symbol = self.next_symbol
        self.next_symbol = None

    def is_closing_out(self, close_pos: int) -> bool:
        if self.trade_data.pos <= close_pos:
            return True
        else:
            return False


class TradePosInfo:
    def __init__(self, tsi: TradeStatusInfo, l_or_s: bool,  commission: float,
                 balance: float) -> None:
        self.symbol = tsi.current_symbol
        self.l_or_s = l_or_s
        self.commission = commission
        self.current_balance = balance
        self.trade_date = tsi.last_modified


class OpenPosInfo(TradePosInfo):
    def __init__(self, tsi: TradeStatusInfo, l_or_s: bool, commission: float,
                 balance: float) -> None:
        super().__init__(tsi, l_or_s, commission, balance)
        self.trade_price = tsi.trade_data.price
        self.trade_number = tsi.trade_data.pos
        self.daily_cond = tsi.judge_data.d_cond
        self.h3_cond = tsi.judge_data.h3_cond
        self.stop_loss_price = tsi.trade_data.slp
        self.stop_profit_point = tsi.trade_data.spp
        self.close_pos_ids: list(str) = []

    def add_close_info(self, close_pos_id) -> None:
        self.close_pos_ids.append(close_pos_id)


class ClosePosInfo(TradePosInfo):
    def __init__(self, tsi: TradeStatusInfo, l_or_s: bool, commission: float,
                 balance: float, float_profit: float, close_price: float,
                 close_pos: int, close_reason: str) -> None:
        super().__init__(tsi, l_or_s, commission, balance)
        self.trade_price = close_price
        self.trade_number = close_pos
        self.open_ops_id = tsi.trade_data.open_pos_id
        self.float_profit = float_profit
        self.close_reason = close_reason
