import re
from tqsdk.ta import EMA, MACD
from tqsdk import tafunc, TargetPosTask
from datetime import datetime
from math import floor


class Underlying_symbol_trade:
    base_persent = 0.02
    # base_persent = 0.002
    stop_loss_price = 0.0
    upgrade_stop_loss_price = False

    '主连合约交易类'
    def __init__(self, api, zhulian_symbol):
        self.api = api
        self.quote = api.get_quote(zhulian_symbol)
        self.underlying_symbol = self.quote.underlying_symbol
        self.last_symbol = self.underlying_symbol

        self.position = api.get_position(self.underlying_symbol)
        self.target_pos = TargetPosTask(api, self.underlying_symbol)

    def need_switch_contract(self):
        self.underlying_symbol = self.quote.underlying_symbol
        last_symbol_list = examine_symbol(self.last_symbol)
        today_symbol_list = examine_symbol(self.underlying_symbol)
        if not last_symbol_list or not today_symbol_list:
            print('新/旧合约代码有误，请检验')
            return False
        if today_symbol_list[0] != last_symbol_list[0] or \
                today_symbol_list[1] != last_symbol_list[1]:
            print('新/旧合约品种不一，请检验')
            return False
        if self.underlying_symbol <= self.last_symbol:
            print('新合约非远月合约，不换月')
            return False
        print(f"{tafunc.time_to_datetime(self.quote.datetime)},旧合约:{self.last_symbol},新合约:{self.underlying_symbol}")
        return True

    def switch_contract(self):
        if self.need_switch_contract():
            last_position = self.api.get_position(self.last_symbol)
            current_position = self.api.get_position(self.underlying_symbol)
            if last_position.pos_long > 0:
                last_target_pos = TargetPosTask(self.api, self.last_symbol)
                current_target_pos = TargetPosTask(self.api,
                                                   self.underlying_symbol)
                last_target_pos.set_target_volume(0)
                current_target_pos.set_target_volume(last_position.pos_long)
                print("换月完成:旧合约{
            self.last_symbol = self.underlying_symbol
            return False




def is_zhulian_symbol(_symbol):
    pattern = re.compile(r'^(KQ.m@)(CFFEX|CZCE|DCE|INE|SHFE).(\w{1,2})$')
    return pattern.match(_symbol)


def examine_symbol(_symbol):
    pattern_dict_normal = {
        'CFFEX': re.compile(r'^(CFFEX).([A-Z]{1,2})(\d{4})$'),
        'CZCE': re.compile(r'^(CZCE).([A-Z]{2})(\d{3})$'),
        'DCE': re.compile(r'^(DCE).([a-z]{1,2})(\d{4})$'),
        'INE': re.compile(r'^(INE).([a-z]{2})(\d{4})$'),
        'SHFE': re.compile(r'^(SHFE).([a-z]{2})(\d{4})$'),
        # 'KQ.m': re.compile(r'^(KQ.m@)(CFFEX|CZCE|DCE|INE|SHFE).(\w{1,2})$')
        }

    for k, ipattern in pattern_dict_normal.items():
        matchsymbol = ipattern.match(_symbol)
        if matchsymbol:
            exchange, variety, expiry_month = \
                matchsymbol.group(1), matchsymbol.group(2), \
                matchsymbol.group(3)
            return [exchange, variety, expiry_month]
    return False


def get_date_from_kline(kline):
    return datetime.fromtimestamp(kline.datetime/1e9)


def calc_ema22(klines):
    ema22 = EMA(klines, 22)
    klines["ema22"] = ema22.ema


def calc_ema60(klines):
    ema60 = EMA(klines, 60)
    klines["ema60"] = ema60.ema


def calc_macd(klines):
    macd = MACD(klines, 12, 24, 4)
    # 用 K 线图模拟 MACD 指标柱状图
    klines["MACD.open"] = 0.0
    klines["MACD.close"] = macd["bar"]
    klines["MACD.high"] = klines["MACD.close"].where(
        klines["MACD.close"] > 0, 0)
    klines["MACD.low"] = klines["MACD.close"].where(
        klines["MACD.close"] < 0, 0)
    klines["diff"] = macd["diff"]
    klines["dea"] = macd["dea"]


def calc_indicator(klines):
    calc_macd(klines)
    calc_ema22(klines)
    calc_ema60(klines)
    klines["ema22.board"] = "MAIN"
    klines["ema22.color"] = "red"
    klines["ema60.board"] = "MAIN"
    klines["ema60.color"] = "green"
    klines["MACD.board"] = "MACD"
    # 在 board=MACD 上添加 diff、dea 线
    klines["diff.board"] = "MACD"
    klines["diff.color"] = "gray"
    klines["dea.board"] = "MACD"
    klines["dea.color"] = "rgb(255,128,0)"


def diff_two_value(first, second):
    return abs(first - second)/second


def is_match_daily_kline_condition(kline):
    # 如果id不足59，说明合约成交日还未满60天，ema60均线还不准确
    # 故不能作为判断依据
    if kline.id > 58:
        diff1 = diff_two_value(kline.ema60, kline.ema22)
        diff2 = diff_two_value(kline.ema22, kline.ema60)
        # EMA22 < EMA60， 且偏离度小于2时
        if kline["ema22"] < kline["ema60"] and diff1 < 0.02:
            # 收盘价格在EMA60均线上方
            if kline["close"] > kline["ema60"] and kline["MACD.close"] > 0:
                return True
        elif kline["ema22"] > kline["ema60"]:
            if diff2 < 0.02 and kline["close"] > kline["ema60"]:
                return True
            elif (diff2 > 0.03 and
                    ((kline["close"] > kline["ema60"] and
                        kline["close"] < kline["ema22"]) and
                        (kline["open"] > kline["ema60"] and
                            kline["open"] < kline["ema22"]) and
                        (diff_two_value(kline.close, kline.ema60) < 0.02))):
                return True
    else:
        return False


def is_match_30m_kline_condition(kline):
    if kline["close"] > kline["ema60"] and kline["MACD.close"] > 0:
        if kline["ema22"] < kline["ema60"]:
            diff_persent = abs(kline.close - kline.ema22)/kline.ema22
            if diff_persent <= 0.02:
                return True
        elif kline["ema22"] > kline["ema60"]:
            diff_persent = abs(kline.close - kline.ema60)/kline.ema60
            if diff_persent <= 0.02:
                return True
    return False


def calc_volume_by_price(quote, account):
    available = account.balance*0.02
    volume = floor(available / quote.ask_price1)
    print(f'总资金：{account.balance}, 可用资金：{available}, 预计购入手数:{volume}')
    return volume


def get_total_pos(position):
    return position.pos_long_his + position.pos_log_today


# 根据均线条件和是否有持仓判断是否可以开仓
def can_open_volumes(api, daily_klines, m30_klines, position):
    # 如果前一天日k线符合条件
    if(is_match_daily_kline_condition(daily_klines.iloc[-1])):
        if api.is_changing(m30_klines.iloc[-1], "datetime"):
            calc_indicator(m30_klines)
        last_30m_kline = m30_klines.iloc[-1]
        if(is_match_30m_kline_condition(last_30m_kline)):
            if position.pos_long == 0:
                print(f"符合开仓条件，准备下单,时间{get_date_from_kline(m30_klines.iloc[-1])}")
                print(daily_klines.iloc[-1])
                print(last_30m_kline)
                return True
    return False


# _api: tqsdk api, _last_symbol: 上一个主力合约代码, _today_symbol: 主连合约代码
def need_switch_contract(_last_symbol, _today_symbol):
    last_symbol_list = examine_symbol(_last_symbol)
    today_symbol_list = examine_symbol(_today_symbol)
    if not last_symbol_list or not today_symbol_list:
        print('新/旧合约代码有误，请检验')
        return False
    if today_symbol_list[0] != last_symbol_list[0] or \
            today_symbol_list[1] != last_symbol_list[1]:
        print('新/旧合约品种不一，请检验')
        return False
    if _today_symbol <= _last_symbol:
        print('新合约非远月合约，不换月')
        return False
    return True


# _api: tqsdk api, _last_symbol: 上一个主力合约代码, _zhulian_symbol: 主连合约代码
def switch_contract(_api, _last_symbol, _zhulian_symbol, _quote, _position):
    _today_symbol = quote.underlying_symbol

    if need_switch_contract(_last_symbol, _today_symbol):
        return False
