from pymongo import MongoClient
from dao.dao_service import DBService
from dao.excel_entity import Trade_Book
import logging


def get_logger():
    return logging.getLogger(__name__)


def load_open_pos_infos(name='future_trade', mongo_user='root',
                        mongo_pasw='example', mongo_host='localhost',
                        mongo_port=27016):
    # logger = get_logger()
    mongo_url = (f'mongodb://{mongo_user}:{mongo_pasw}'
                 f'@{mongo_host}:{mongo_port}/')
    service = DBService(MongoClient(mongo_url).get_database(name))
    opis = service.get_all_open_pos_infos()
    future_config = service.get_future_configs()
    trade_book = Trade_Book(name, future_config)
    for opi in opis:
        trade_book.sheet.record_line(opi)
    trade_book.finish()
