from datetime import datetime
from tools import examine_symbol
from tqsdk2 import tafunc


def __get_date_from_symbol(symbol_last_part):
    temp = int(symbol_last_part)
    year = int(temp / 100) + 2000
    month = temp % 100
    day = 1
    return datetime(year, month, day, 15, 0, 0)


def __need_switch_contract(last_symbol, underlying_symbol, quote):
    last_symbol_list = examine_symbol(last_symbol)
    today_symbol_list = examine_symbol(underlying_symbol)
    if not last_symbol_list or not today_symbol_list:
        return False
    if today_symbol_list[0] != last_symbol_list[0] or \
            today_symbol_list[1] != last_symbol_list[1]:
        return False
    if underlying_symbol <= last_symbol:
        return False
    last_date = __get_date_from_symbol(last_symbol_list[2])
    current_date = tafunc.time_to_datetime(quote.datetime)
    print(f"last_date:{last_date}, current_date:{current_date}")
    timedelta = last_date - current_date
    if timedelta.days <= 5:
        return True
    return False


def test_need_switch_contract():
    quote = type('', (), {})()
    quote.datetime = datetime.strptime("27/09/18 14:30", "%d/%m/%y\
                                       %H:%M").timestamp()
    assert __need_switch_contract("SHFE.rb1810", "SHFE.rb1901", quote)
