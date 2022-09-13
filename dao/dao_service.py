from dao.entity import OpenPosInfo, ClosePosInfo, TradeStatusInfo
import dao.mongo_dao as mdao
from datetime import datetime


def store_open_record(opi: OpenPosInfo) -> None:
    mdao.store_open_record(opi)


def store_close_record(cpi: ClosePosInfo) -> None:
    mdao.store_close_record(cpi)


def init_trade_status_info(zl_symbol: str, current_symbol: str, l_or_s: bool,
                           trade_time: datetime) -> TradeStatusInfo:
    tsi = mdao.init_trade_status_info(zl_symbol, current_symbol,
                                      l_or_s, trade_time)
    return tsi


def update_tsi_next_symbol(tsi: TradeStatusInfo, next_symbol: str) -> None:
    tsi.next_symbol = next_symbol
    mdao.update_tsi(tsi)


def update_tsi(tsi: TradeStatusInfo, t_time: datetime) -> None:
    tsi.last_modified = t_time
    mdao.update_tsi(tsi)
