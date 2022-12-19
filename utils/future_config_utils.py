from pymongo import MongoClient
from dao.config_entity import FutureConfigInfo
import dao.future_config_dao as dao
import yaml
import logging


def get_logger():
    return logging.getLogger(__name__)


def get_trade_config_from_file(file_name='trade_config.yaml') -> dict:
    with open(f'conf/{file_name}', 'r') as f:
        return yaml.safe_load(f.read())


def store_future_config_to_db(mongo_user='root', mongo_pasw='example',
                              mongo_host='localhost', mongo_port=27019,
                              name='future_trade'):
    # logger = get_logger()
    mongo_url = (f'mongodb://{mongo_user}:{mongo_pasw}'
                 f'@{mongo_host}:{mongo_port}/')
    prepare_future_configs('trade_config.yaml',
                           MongoClient(mongo_url).get_database(name))


def prepare_future_configs(config_file, db):
    dao.db = db
    logger = get_logger()
    logger.debug(db.name)
    trade_configs = get_trade_config_from_file(config_file)
    future_configs = trade_configs['futures']
    for future_config in future_configs:
        fci = FutureConfigInfo(future_config, trade_configs['open_pos_scale'])
        dao.store_future_config(fci)
