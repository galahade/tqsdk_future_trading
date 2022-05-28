import re
from tqsdk.ta import EMA, MACD
from tqsdk import tafunc, TargetPosTask
from datetime import datetime
from math import floor


class Underlying_symbol_trade:

    '主连合约交易类'
    def __init__(self, api, zhulian_symbol):
        self.api = api
        self.quote = api.get_quote(zhulian_symbol)
        self.underlying_symbol = self.quote.underlying_symbol
        self.last_symbol = self.underlying_symbol

        self.position = api.get_position(self.underlying_symbol)
        self.target_pos = TargetPosTask(api, self.underlying_symbol)

        self.base_persent = 0.02
        self.stop_loss_price = 0.0
        self.has_upgrade_stop_loss_price = False
        self.volumes = 0

    def __need_switch_contract(self):
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
        print(f"{tafunc.time_to_datetime(self.quote.datetime)},\
              旧合约:{self.last_symbol},新合约:{self.underlying_symbol}")
        return True

    def switch_contract(self):
        if self.__need_switch_contract():
            last_position = self.position
            current_position = self.api.get_position(self.underlying_symbol)
            last_pos_long = last_position.pos_long
            last_target_pos = self.target_pos
            current_target_pos = TargetPosTask(self.api,
                                               self.underlying_symbol)
            if last_pos_long > 0:
                last_target_pos.set_target_volume(0)
                current_target_pos.set_target_volume(last_pos_long)
                while True:
                    self.api.wait_update()
                    if last_position.pos_long == 0\
                       and current_position.pos_long == last_pos_long:
                        break
                print(f"{tafunc.time_to_datetime(self.quote.datetime)}-\
                      换月完成:旧合约{self.last_symbol},新合约{self.underlying_symbol},\
                      换月前，多头{last_pos_long}手。换月后,多头{last_pos_long}手")
            self.target_pos = current_target_pos
            self.last_symbol = self.underlying_symbol
            self.position = current_position
            self.__set_stop_loss_price()

    # 根据均线条件和是否有持仓判断是否可以开仓
    def __can_open_volumes(self, daily_klines, m30_klines):
        # 如果前一天日k线符合条件
        if(is_match_daily_kline_condition(daily_klines.iloc[-1])):
            if self.api.is_changing(m30_klines.iloc[-1], "datetime"):
                calc_indicator(m30_klines)
            last_30m_kline = m30_klines.iloc[-1]
            if(is_match_30m_kline_condition(last_30m_kline)):
                if self.position.pos_long == 0:
                    # print(f"符合条件,准备下单\
                    # {get_date_from_kline(m30_klines.iloc[-1])}")
                    #    print(daily_klines.iloc[-1])
                    #    print(last_30m_kline)
                    return True
        return False

    def calc_volume_by_price(self, account):
        available = account.balance*0.02
        volumes = floor(available / self.quote.ask_price1)
        # print(f'总资金：{account.balance}, 可用资金：{available}, 预计购入手数:{volumes}')
        self.volumes = volumes
        return volumes

    # 挂止损单
    def try_stop_loss(self):
        if self.stop_loss_price \
           and self.quote.last_price <= self.stop_loss_price\
           and self.position.pos_long > 0:
            self.target_pos.set_target_volume(0)
            while True:
                self.api.wait_update()
                if self.position.pos_long == 0:
                    break
            print(f"{tafunc.time_to_datetime(self.quote.datetime)}-\
                止损，现价:{self.quote.last_price}, 止损价:{self.stop_loss_price},\
                手数:{self.position.pos_long}")
            self.stop_loss_price = 0.0
            self.has_upgrade_stop_loss_price = False

    def open_volumes(self, daily_klines, m30_klines, account):
        if self.__can_open_volumes(daily_klines, m30_klines):
            wanted_volume = self.calc_volume_by_price(account)
            self.target_pos.set_target_volume(wanted_volume)
            while True:
                self.api.wait_update()
                if self.position.pos_long == wanted_volume:
                    break
            print(f"{tafunc.time_to_datetime(self.quote.datetime)}-\
                  主力合约:{self.underlying_symbol},开仓价格{self.position.open_price_long},\
                  多头{wanted_volume}手", end="-")
            self.__set_stop_loss_price()
            print(f"止损价格为:{self.stop_loss_price}")

    def __set_stop_loss_price(self):
        self.stop_loss_price = self.position.open_price_long\
            * (1 - self.base_persent)
        self.has_upgrade_stop_loss_price = False

    def upgrade_stop_loss_price(self):
        if (not self.has_upgrade_stop_loss_price
            and self.quote.last_price >=
                self.position.open_price_long * (1 + self.base_persent * 3)):
            self.stop_loss_price = self.position.open_price_long \
                * (1 + self.base_persent)
            self.has_upgrade_stop_loss_price = True
            print(f"{tafunc.time_to_datetime(self.quote.datetime)}-\
                  主力合约:{self.underlying_symbol},现价{self.quote.last_price},\
                  达到1:3盈亏比，止损提高至{self.stop_loss_price}")


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
