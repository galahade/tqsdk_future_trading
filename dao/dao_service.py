from dao.entity import OpenPosInfo, ClosePosInfo, TradeStatusInfo
import dao.excel_dao as edao
import dao.mongo_dao as mdao
from datetime import datetime


def store_open_record(opi: OpenPosInfo) -> None:
    edao.store_open_record(opi)
    mdao.store_open_record(opi)


def store_close_record(cpi: ClosePosInfo) -> None:
    edao.store_close_record(cpi)
    mdao.store_close_record(cpi)


def init_trade_status_info(zl_symbol: str, current_symbol: str, l_or_s: bool,
                           trade_time: datetime) -> TradeStatusInfo:
    tsi = mdao.init_trade_status_info(zl_symbol, current_symbol,
                                      l_or_s, trade_time)
    return tsi


def update_tsi_next_symbol(tsi: TradeStatusInfo, next_symbol: str) -> None:
    tsi.next_symbol = next_symbol
    mdao.update_tsi(tsi)


def update_tsi_for_next_trade(tsi: TradeStatusInfo,
                              trade_time: datetime) -> None:
    tsi.switch_symbol(trade_time)
    mdao.update_tsi(tsi)


def update_tsi(tsi: TradeStatusInfo) -> None:
    mdao.update_tsi(tsi)
