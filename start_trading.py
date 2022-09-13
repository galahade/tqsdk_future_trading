from tqsdk import TqApi, TqAuth, TqSim
from utils.trade_utils import wait_to_trade
from pymongo import MongoClient
import os


acc = TqSim()
mongo_host = os.environ['MONGO_HOST']
mongo_user = os.environ['MONGO_ADMINUSERNAME']
mongo_pasw = os.environ['MONGO_ADMINPASSWORD']
mongo_port = os.environ['MONGO_PORT']


def trade(trade_type: int):
    mongo_url = (f'mongodb://{mongo_user}:{mongo_pasw}'
                 f'@{mongo_host}:{mongo_port}/')
    api = TqApi(acc, auth=TqAuth("galahade", "211212"))
    client = MongoClient(mongo_url)
    db = client.get_database('future_trade')
    wait_to_trade(api, trade_type, db)
