from dao.entity import OpenPosInfo, ClosePosInfo, TradeStatusInfo
from pymongo.database import Database
from utils.tools import get_custom_symbol
from datetime import datetime

db: Database = None


def store_open_record(opi: OpenPosInfo) -> None:
    open_pos_info = {
        'symbol': opi.symbol,
        'l_or_s': opi.l_or_s,
        'trade_date': opi.trade_date,
        'trade_price': opi.trade_price,
        'trade_number': opi.trade_number,
        'commission': opi.commission,
        'current_balance': opi.current_balance,
        'daily_cond': opi.daily_cond,
        'h2_cond': opi.h2_cond,
        'stop_loss_price': opi.stop_loss_price,
        'stop_profit_point': opi.stop_profit_point
    }
    result = db.open_pos_infos.insert_one(open_pos_info)
    opi._id = result.inserted_id


def store_close_record(cpi: ClosePosInfo) -> None:
    close_pos_info = {
        'symbol': cpi.symbol,
        'l_or_s': cpi.l_or_s,
        'trade_date': cpi.trade_date,
        'trade_price': cpi.trade_price,
        'trade_number': cpi.trade_number,
        'commission': cpi.commission,
        'current_balance': cpi.current_balance,
        'float_profit': cpi.float_profit,
        'close_reason': cpi.close_reason,
        'open_pos_id': cpi.open_ops_id
    }
    result = db.close_pos_infos.insert_one(close_pos_info)
    cpi._id = result.inserted_id


def init_trade_status_info(zl_symbol: str, current_symbol: str, l_or_s: bool,
                           trade_time: datetime) -> TradeStatusInfo:
    tsi = _get_trade_status_info(zl_symbol, l_or_s)
    if tsi is None:
        tsi = _create_trade_status_info(zl_symbol, current_symbol,
                                        l_or_s, trade_time)
    return tsi


def _create_trade_status_info(
     zl_symbol: str, current_symbol: str, l_or_s: bool,
     trade_time: datetime) -> TradeStatusInfo:
    tsi = TradeStatusInfo(zl_symbol, trade_time, current_symbol, l_or_s)
    trade_status_info = {
        'custom_symbol': tsi.custom_symbol,
        'current_symbol': tsi.current_symbol,
        'next_symbol': tsi.next_symbol,
        'is_trading': tsi.is_trading,
        'last_modified': tsi.last_modified,
        'trade_data': None,
        'judge_data': None
    }
    result = db.trade_status_infos.insert_one(trade_status_info)
    tsi._id = result.inserted_id
    return tsi


def _get_trade_status_info(zl_symbol: str, l_or_s: bool) -> TradeStatusInfo:
    custom_symbol = get_custom_symbol(zl_symbol, l_or_s)
    trade_status_info = db.trade_status_infos.find_one(
        {'custom_symbol': custom_symbol})
    if trade_status_info is not None:
        tsi = TradeStatusInfo(zl_symbol)
        tsi._id = trade_status_info.get('_id')
        tsi.current_symbol = trade_status_info.get('current_symbol')
        tsi.next_symbol = trade_status_info.get('next_symbol')
        tsi.is_trading = trade_status_info.get('is_trading')
        tsi.open_pos_id = trade_status_info.get('open_pos_id')
        print(f'mongo tsi is {tsi}')
        return tsi
    return None


def update_tsi(tsi: TradeStatusInfo) -> None:
    db.trade_status_infos.update_one(
        {'_id': tsi._id},
        {'$set': {'current_symbol': tsi.current_symbol,
                  'next_symbol': tsi.next_symbol,
                  'is_trading': tsi.is_trading,
                  'last_modified': tsi.last_modified,
                  'trade_data.open_ops_id': tsi.trade_data.open_pos_id,
                  'trade_data.price': tsi.trade_data.price,
                  'trade_data.pos': tsi.trade_data.pos,
                  'trade_data.p_stage': tsi.trade_data.p_stage,
                  'trade_data.p_cond': tsi.trade_data.p_cond,
                  'trade_data.has_islp': tsi.trade_data.has_islp,
                  'trade_data.slp': tsi.trade_data.slp,
                  'trade_data.spp': tsi.trade_data.spp,
                  'trade_data.bsp': tsi.trade_data.bsp,
                  'trade_data.stp': tsi.trade_data.stp,
                  'judge_data.d_cond': tsi.judge_data.d_cond,
                  'judge_data.h3_cond': tsi.judge_data.h3_cond,
                  }})


def update_reset_tsi(tsi: TradeStatusInfo) -> None:
    db.trade_status_infos.update_one(
        {'_id': tsi._id},
        {'$set': {'current_symbol': tsi.current_symbol,
                  'next_symbol': tsi.next_symbol,
                  'is_trading': tsi.is_trading,
                  'last_modified': tsi.last_modified,
                  'trade_data': None,
                  'judge_data': None
                  }})
