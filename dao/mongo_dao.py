from dao.entity import OpenPosInfo, ClosePosInfo, TradeStatusInfo
from pymongo.database import Database
from utils.common_tools import get_custom_symbol
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
        'h3_cond': opi.h3_cond,
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
        'open_pos_id': cpi.open_pos_id
    }
    result = db.close_pos_infos.insert_one(close_pos_info)
    cpi._id = result.inserted_id


def init_trade_status_info(zl_symbol: str, zl_quote, l_or_s: bool,
                           trade_time: datetime) -> TradeStatusInfo:
    tsi = _get_trade_status_info(zl_symbol, l_or_s)
    if tsi is None:
        tsi = _create_trade_status_info(
            zl_symbol, zl_quote.underlying_symbol, l_or_s, trade_time)
    return tsi


def _create_trade_status_info(
     zl_symbol: str, current_symbol: str, l_or_s: bool,
     trade_time: datetime) -> TradeStatusInfo:
    tsi = TradeStatusInfo(zl_symbol, trade_time, current_symbol, l_or_s)
    result = db.trade_status_infos.insert_one(_get_tsi_dict(tsi))
    tsi._id = result.inserted_id
    return tsi


def _get_trade_status_info(zl_symbol: str, l_or_s: bool) -> TradeStatusInfo:
    custom_symbol = get_custom_symbol(zl_symbol, l_or_s)
    db_data = db.trade_status_infos.find_one(
        {'custom_symbol': custom_symbol})
    if db_data is not None:
        tsi = TradeStatusInfo(zl_symbol)
        tsi._id = db_data.get('_id')
        tsi.custom_symbol = db_data.get('custom_symbol')
        tsi.current_symbol = db_data.get('current_symbol')
        tsi.next_symbol = db_data.get('next_symbol')
        tsi.is_trading = db_data.get('is_trading')
        tsi.last_modified = db_data.get('last_modified')
        trade_data = db_data.get('trade_data')
        tsi.trade_data.open_pos_id = trade_data['open_pos_id']
        tsi.trade_data.price = trade_data['price']
        tsi.trade_data.pos = trade_data['pos']
        tsi.trade_data.trade_date = trade_data['trade_date']
        tsi.trade_data.p_stage = trade_data['p_stage']
        tsi.trade_data.p_cond = trade_data['p_cond']
        tsi.trade_data.has_islp = trade_data['has_islp']
        tsi.trade_data.slp = trade_data['slp']
        tsi.trade_data.slr = trade_data['slr']
        tsi.trade_data.spp = trade_data['spp']
        tsi.trade_data.bsp = trade_data['bsp']
        tsi.trade_data.stp = trade_data['stp']
        judge_data = db_data.get('judge_data')
        tsi.judge_data.d_cond = judge_data['d_cond']
        # tsi.judge_data.d_kline = judge_data['d_kline']
        tsi.judge_data.h3_cond = judge_data['h3_cond']
        # tsi.judge_data.h3_kline = judge_data['h3_kline']
        # tsi.judge_data.m30_kline = judge_data['m30_kline']

        return tsi
    return None


def update_tsi(tsi: TradeStatusInfo) -> None:
    db.trade_status_infos.update_one(
        {'_id': tsi._id},
        {'$set': _get_tsi_dict(tsi)})


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


def _get_tsi_dict(tsi: TradeStatusInfo) -> dict:
    trade_data = tsi.trade_data
    judge_data = tsi.judge_data
    return {
        'custom_symbol': tsi.custom_symbol,
        'current_symbol': tsi.current_symbol,
        'next_symbol': tsi.next_symbol,
        'is_trading': tsi.is_trading,
        'last_modified': tsi.last_modified,
        'trade_data': {
            'open_pos_id': trade_data.open_pos_id,
            'price': trade_data.price,
            'pos': trade_data.pos,
            'trade_date': trade_data.trade_date,
            'p_stage': trade_data.p_stage,
            'p_cond': trade_data.p_cond,
            'has_islp': trade_data.has_islp,
            'slp': trade_data.slp,
            'slr': trade_data.slr,
            'spp': trade_data.spp,
            'bsp': trade_data.bsp,
            'stp': trade_data.stp
        },
        'judge_data': {
            'd_cond': judge_data.d_cond,
            'h3_cond': judge_data.h3_cond,
        }
    }


def get_open_pos_infos() -> list:
    all_data = db.open_pos_infos.find()
    results = []
    for data in all_data:
        opi = OpenPosInfo()
        opi.symbol = data.get('symbol')
        opi.l_or_s = data.get('l_or_s')
        opi.commission = data.get('commission')
        opi.current_balance = data.get('current_balance')
        opi.trade_date = data.get('trade_date')
        opi.trade_price = data.get('trade_price')
        opi.trade_number = data.get('trade_number')
        opi.daily_cond = data.get('daily_cond')
        opi.h3_cond = data.get('h3_cond')
        opi.stop_loss_price = data.get('stop_loss_price')
        opi.stop_profit_point = data.get('stop_profit_point')
        opi.close_pos_infos = []
        close_infos = db.close_pos_infos.find(
            {'open_pos_id': data.get('_id')})
        for c_data in close_infos:
            cpi = ClosePosInfo()
            cpi.symbol = c_data.get('symbol')
            cpi.l_or_s = c_data.get('l_or_s')
            cpi.commission = c_data.get('commission')
            cpi.current_balance = c_data.get('current_balance')
            cpi.trade_date = c_data.get('trade_date')
            cpi.open_pos_id = c_data.get('open_pos_id')
            cpi.trade_price = c_data.get('trade_price')
            cpi.trade_number = c_data.get('trade_number')
            cpi.float_profit = c_data.get('float_profit')
            cpi.close_reason = c_data.get('close_reason')
            opi.close_pos_infos.append(cpi)
        results.append(opi)
    return results
