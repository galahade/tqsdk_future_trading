from pymongo.database import Database
from dao.config_entity import FutureConfigInfo

db: Database = None


def store_future_config(future_config: FutureConfigInfo) -> None:
    future_config_info = {
        'symbol': future_config.symbol,
        'is_active': future_config.is_active,
        'contract_m': future_config.contract_m,
        'name': future_config.name,
        'switch_days': future_config.switch_days,
        'long.base_scale':
        future_config.long_config.profit_base_scale,
        'long.profit_start_scale_1':
        future_config.long_config.profit_start_scale_1,
        'long.profit_start_scale_2':
        future_config.long_config.profit_start_scale_2,
        'long.promote_scale_1':
        future_config.long_config.promote_scale_1,
        'long.promote_scale_2':
        future_config.long_config.promote_scale_2,
        'long.promote_target_1':
        future_config.long_config.promote_target_1,
        'long.promote_target_2':
        future_config.long_config.promote_target_2,
        'long.stop_loss_scale':
        future_config.long_config.stop_loss_scale,
        'short.base_scale':
        future_config.short_config.profit_base_scale,
        'short.profit_start_scale':
        future_config.short_config.profit_start_scale,
        'short.promote_scale':
        future_config.short_config.promote_scale,
        'short.promote_target':
        future_config.short_config.promote_target,
        'short.stop_loss_scale':
        future_config.short_config.stop_loss_scale,
    }
    db.future_config_infos.update_one(
        {'symbol': future_config.symbol},
        {'$set': future_config_info}, upsert=True)


def get_future_configs() -> list:
    future_configs = []
    for fci in db.future_config_infos.find({'is_active': 1}):
        fc = FutureConfigInfo(fci, 0.2)
        future_configs.append(fc)
    return future_configs
