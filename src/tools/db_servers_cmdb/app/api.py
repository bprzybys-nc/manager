from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.modules.tools.data_objects import Metadata, CredentialsStoreType
from src.tools.db_servers_cmdb.app.db import MetadataDB
from src.tools.db_servers_cmdb.app.keyvault import AzureKeyVaultSecretManager

app = FastAPI()
db_servers_cmdb = MetadataDB()
keyvault = AzureKeyVaultSecretManager()

@app.get("/metadata/{server_id}")
def get_metadata(server_id: str):
    metadata = db_servers_cmdb.get_metadata(server_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Metadata for server_id {server_id} not found")
    
    if metadata.credentials_store_type == CredentialsStoreType.AZURE_KEYVAULT:
        vault_name = keyvault.get_vault_name(metadata.credentials_store_type)
        print(f"Loading secrets from vault {vault_name}")
        metadata.credentials["username_secret_value"] = keyvault.get_secret(metadata.credentials["username_secret_name"],vault_name)
        metadata.credentials["password_secret_value"] = keyvault.get_secret(metadata.credentials["password_secret_name"],vault_name)
    else:
        print(f"No vault name found for {metadata.credentials_store_type}")

    return metadata

@app.post("/public/metadata/{server_id}")
def create_secret(server_id: str, metadata: Metadata):
    vault_name = keyvault.get_vault_name(metadata.credentials_store_type)
    result=keyvault.create_secret(vault_name, metadata.credentials["username_secret_name"], metadata.credentials["username_secret_value"])
    result=keyvault.create_secret(vault_name, metadata.credentials["password_secret_name"], metadata.credentials["password_secret_value"])
    del metadata.credentials["username_secret_value"]
    del metadata.credentials["password_secret_value"]
    db_servers_cmdb.add_metadata(server_id, metadata)
    return {"message": "Secret created successfully", "result": result}

@app.delete("/metadata")
def clear_metadata():
    return db_servers_cmdb.clear_metadata()

@app.get("/metadata")
def get_all_metadata():
    metadata_list = db_servers_cmdb.get_all_metadata()
    for metadata in metadata_list:
        if metadata.credentials_store_type == CredentialsStoreType.AZURE_KEYVAULT:
            vault_name = keyvault.get_vault_name(metadata.credentials_store_type)
            metadata.credentials["username_secret_value"] = keyvault.get_secret(metadata.credentials["username_secret_name"],vault_name)
            metadata.credentials["password_secret_value"] = keyvault.get_secret(metadata.credentials["password_secret_name"],vault_name)
    return metadata_list

@app.post("/metadata/{server_id}")
def create_item(server_id: str, metadata: Metadata):
    return db_servers_cmdb.add_metadata(server_id, metadata)