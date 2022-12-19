class LongConfig:
    def __init__(self, long_config: dict):
        # 止盈止损基础比例
        self.profit_base_scale = long_config['base_scale']
        # 止损倍数
        self.stop_loss_scale = long_config['stop_loss_scale']
        # 开始止盈倍数
        self.profit_start_scale_1 = long_config['profit_start_scale_1']
        # 开始止盈2倍数
        self.profit_start_scale_2 = long_config['profit_start_scale_2']
        # 提高止损需达到的倍数
        self.promote_scale_1 = long_config['promote_scale_1']
        # 提高止损需达到的倍数2
        self.promote_scale_2 = long_config['promote_scale_2']
        # 将止损提高的倍数
        self.promote_target_1 = long_config['promote_target_1']
        # 将止损提高的倍数2
        self.promote_target_2 = long_config['promote_target_2']


class ShortConfig:
    def __init__(self, short_config: dict):
        # 止盈止损基础比例
        self.profit_base_scale = short_config['base_scale']
        # 止损倍数
        self.stop_loss_scale = short_config['stop_loss_scale']
        # 开始止盈倍数
        self.profit_start_scale = short_config['profit_start_scale']
        # 提高止损需达到的倍数
        self.promote_scale = short_config['promote_scale']
        # 将止损提高的倍数
        self.promote_target = short_config['promote_target']


class FutureConfigInfo:
    def __init__(self, future_config: dict, open_pos_scale: int):
        # 期货合约加交易所的表示方法
        self.symbol = future_config['symbol']
        # 是否对该品种进行监控
        self.is_active = future_config['is_active']
        # 合约中文名称
        self.name = future_config['name']
        # 合约乘数
        self.contract_m = future_config['contract_m']
        # 开仓金额占粽资金的比例
        self.open_pos_scale = open_pos_scale
        self.switch_days = future_config['switch_days']
        self.long_config = LongConfig(future_config['long'])
        self.short_config = ShortConfig(future_config['short'])
