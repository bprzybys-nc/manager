import os
import requests

from src.modules.tools.data_objects import CredentialsStoreType

class AzureKeyVaultSecretManager:
    def __init__(self):
        self.tenant_id = os.environ.get('SPN_TENANT_ID')
        self.client_id = os.environ.get('SPN_CLIENT_ID')
        self.client_secret = os.environ.get('SPN_PSWD')

    def get_vault_name(self, keystore_type):
        if keystore_type == CredentialsStoreType.AZURE_KEYVAULT:
            return "kyeyvault-ovora"
        else:
            raise ValueError(f"Invalid keystore type: {keystore_type}")

    def _get_token(self):
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        token_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://vault.azure.net/.default"
        }

        response = requests.post(token_url, data=token_data)
        return response.json()["access_token"]
    
    def delete_secret(self, vault_name, secret_name):
        token = self._get_token()
        api_version = "7.4"
        url = f"https://{vault_name}.vault.azure.net/secrets/{secret_name}?api-version={api_version}"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = requests.delete(url, headers=headers)
        return response.json()
    
    def create_secret(self, vault_name, secret_name, secret_value):
        token = self._get_token()
        api_version = "7.4"
        url = f"https://{vault_name}.vault.azure.net/secrets/{secret_name}?api-version={api_version}"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = requests.put(url, headers=headers, json={"value": secret_value})
        return response.json()
    
    def get_secret(self, secret_name, vault_name):
        token = self._get_token()
        api_version = "7.4"
        url = f"https://{vault_name}.vault.azure.net/secrets/{secret_name}?api-version={api_version}"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = requests.get(url, headers=headers)
        return response.json()["value"]
