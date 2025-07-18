import os
from typing import Dict, List, Optional

import certifi
from pydantic import BaseModel
from pymongo import MongoClient

from src.modules.tools.data_objects import Metadata


class MetadataDB:
    def __init__(self):
        connection_string = os.environ.get('MONGODB_URI')
        self.client = MongoClient(connection_string, tlsCAFile=certifi.where())

        self.db = self.client['tools']

        self.metadata_collection = self.db['db_servers_cmdb']

    def get_metadata(self, server_id)->Metadata:
        document = self.metadata_collection.find_one({"server_id": server_id})
        if document:
            metadata=Metadata(**document)
            return metadata
        else:
            return None
    
    def clear_metadata(self):
        self.metadata_collection.delete_many({})
    
    def get_all_metadata(self)->List[Metadata]:
        documents = self.metadata_collection.find()
        metadata_list = []
        for document in documents:
            metadata_list.append(Metadata(**document))
        return metadata_list
    
    def _remove_none_values(self, data:Dict):
        data_dump= {k: v for k, v in data.items() if v is not None}
        return data_dump

    def add_metadata(self, server_id, metadata:Metadata):
        document = self.metadata_collection.find_one({"server_id": server_id})
        if document:
            metadata_dump=self._remove_none_values(metadata.model_dump())
            metadata_dump.update(self._remove_none_values(document))
            print(f"updating metadata: {metadata_dump}")
            result = self.metadata_collection.update_one({"server_id": server_id}, {"$set": metadata_dump})
        else:
            metadata.server_id = server_id
            result = self.metadata_collection.insert_one({"server_id": server_id, **metadata.model_dump()})