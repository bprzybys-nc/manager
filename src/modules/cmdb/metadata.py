import requests


class CMDBMetadata:
    """
    CMDBMetadata is a class that handles the metadata of the CMDB (Configuration Management Database).
    It provides methods to fetch and update metadata from a CMDB API.
    """

    def __init__(self, cmdb_api_url: str):
        self.cmdb_api_url = cmdb_api_url

    def get_metadata(self, server_id: str) -> dict:
        """
        Fetches metadata from the CMDB API.
        """
        response = requests.get(f"{self.cmdb_api_url}/metadata/{server_id}")
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch metadata: {response.status_code}")
