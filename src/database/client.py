from pymongo import MongoClient
from pymongo.errors import PyMongoError


class DatabaseClient:
    def __init__(self, config):
        self.client = MongoClient(config['uri'])
        try:
            self.client.is_mongos
        except PyMongoError as e:
            raise Exception(f"Could not connect to MongoDB: {e}")
