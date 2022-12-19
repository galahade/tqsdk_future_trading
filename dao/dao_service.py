from dao.entity import OpenPosInfo, ClosePosInfo, TradeStatusInfo
import dao.mongo_dao as mdao
import dao.future_config_dao as fc_dao
from datetime import datetime


class DBService:
    def __init__(self, db):
        mdao.db = db
        fc_dao.db = db

    @staticmethod
    def store_open_record(opi: OpenPosInfo) -> None:
        mdao.store_open_record(opi)

    @staticmethod
    def store_close_record(cpi: ClosePosInfo) -> None:
        mdao.store_close_record(cpi)

    @staticmethod
    def init_trade_status_info(zl_symbol: str, zl_quote, l_or_s: bool,
                               trade_time: datetime) -> TradeStatusInfo:
        tsi = mdao.init_trade_status_info(zl_symbol, zl_quote,
                                          l_or_s, trade_time)
        return tsi

    @staticmethod
    def update_tsi_next_symbol(tsi: TradeStatusInfo, next_symbol: str) -> None:
        tsi.next_symbol = next_symbol
        mdao.update_tsi(tsi)

    @staticmethod
    def update_tsi(tsi: TradeStatusInfo, t_time: datetime) -> None:
        tsi.last_modified = t_time
        mdao.update_tsi(tsi)

    @staticmethod
    def get_future_configs() -> list:
        return fc_dao.get_future_configs()

    @staticmethod
    def get_all_open_pos_infos() -> list:
        return mdao.get_open_pos_infos()
