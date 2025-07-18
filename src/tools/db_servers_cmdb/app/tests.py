import random
import unittest
import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from src.tools.db_servers_cmdb.app.api import app
from src.modules.tools.data_objects import Metadata
from src.tools.db_servers_cmdb.app.keyvault import AzureKeyVaultSecretManager


client = TestClient(app)
keyvault = AzureKeyVaultSecretManager()

class TestAPI(unittest.TestCase):

    #not used till test temporary db will be provided
    def setUp(self):
        self.clear_metadata()
        self.server_id = str(random.randint(1, 1000000))
        self.create_metadata()


    def clear_metadata(self):
        client.delete("/metadata")

    def create_metadata(self):
        payload = {
            "database_uri": "mongodb://localhost:27017",
        }
        response = client.post(f"/metadata/{self.server_id}", json=payload)
        self.assertEqual(response.status_code, 200)

    def create_other_metadata(self):
        payload = {
            "other": {
                "key": "mytestkey"
            }
        }
        response = client.post(f"/metadata/{self.server_id}", json=payload)
        self.assertEqual(response.status_code, 200)
        persisted_metadata=self.get_metadata()
        self.assertEqual(persisted_metadata["other"]["key"], "mytestkey")

    def test_get_metadata(self):
        metadata=self.get_metadata()
        self.assertEqual(metadata["server_id"], self.server_id)

    def test_get_all_metadata(self):
        metadata=self.get_all_metadata()
        self.assertEqual(len(metadata), 1)
        metadata=Metadata(**metadata[0])
        self.assertEqual(metadata.server_id, self.server_id)

    def test_get_wrong_metadata(self):
        response = client.get(f"/metadata/wrong_server_id")
        self.assertEqual(response.status_code, 404)

    def get_metadata(self):
        response = client.get(f"/metadata/{self.server_id}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def get_all_metadata(self):
        response = client.get("/metadata")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_create_secret(self):
        idx=random.randint(1, 1000000)
        payload = {
            "credentials_store_type": "azure_keyvault",
            "credentials": {
                "username_secret_name": f"username{idx}",
                "password_secret_name": f"password{idx}",
                "username_secret_value": f"username{idx}",
                "password_secret_value": f"password{idx}"
            }
        }
        response = client.post(f"/public/metadata/{self.server_id}", json=payload)
        self.assertEqual(response.status_code, 200)

        metadata=Metadata(**self.get_metadata())
        self.assertEqual(metadata.database_uri, "mongodb://localhost:27017")
        self.assertEqual(metadata.server_id, self.server_id)
        self.assertEqual(metadata.credentials_store_type, "azure_keyvault")
        self.assertEqual(metadata.credentials["username_secret_name"], f"username{idx}")
        self.assertEqual(metadata.credentials["password_secret_name"], f"password{idx}")
        self.assertEqual(metadata.credentials["username_secret_value"], f"username{idx}")
        self.assertEqual(metadata.credentials["password_secret_value"], f"password{idx}")

        keyvault.delete_secret(keyvault.get_vault_name(metadata.credentials_store_type), metadata.credentials["username_secret_name"])
        keyvault.delete_secret(keyvault.get_vault_name(metadata.credentials_store_type), metadata.credentials["password_secret_name"])

if __name__ == '__main__':
    unittest.main()