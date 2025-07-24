import unittest
import json
import os
import sys
import certifi

from pymongo import MongoClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from sysaidmin.manager.src.usecases.db_incident_assistant.app.main import DBIncidentAssistant
from src.modules.inventory.db import InventoryDB, InstanceStatus



class TestDBIncidentAssistantMain(unittest.TestCase):
    def setUp(self):
        self.db_incident_assistant = DBIncidentAssistant()

        connection_string = os.environ.get('MONGODB_URI')
        self.db_client = MongoClient(connection_string, tlsCAFile=certifi.where())
        self.inventory_db = InventoryDB(self.db_client)
        instances = self.inventory_db.get_instances()
        
        # Find the instance with the specified ID
        self.instance = None
        for instance in instances:
            if str(instance.id) == "66f7c2d7-536e-439f-9f9c-394357c91248" and instance.status == InstanceStatus.ACTIVE:
                self.instance = instance
                break

    def tearDown(self):
        self.db_client.close()
    
    @unittest.skip("Temporarily turned off")
    def test_db_incident_assistant(self):
        result = self.db_incident_assistant.run("123", "456", "789", "test")
        self.assertEqual(result, "No metadata found for server_id")

    def test_db_incident_assistant_with_metadata(self):

        incident_id = "66f7c2d7-536e-439f-9f9c-394357c91248"
        hostname = "db-incident-sandbox"
        instance_id = self.instance.id
        incident_description = "%%%\nCPU usage reached a ceiling.\n\nTriggered for:\n- Host: db-incident-sandbox\n- Value: 63.002 (Threshold: 60.0)\n\n@webhook-ovora-incident-assistant\n\n\n[![Metric Graph](https://p.datadoghq.com/snapshot/view/dd-snapshots-prod/org_1325540/2025-04-30/969acb70593fa0738f73c95a8e006f7b9d1d083f.png)](https://app.datadoghq.com/monitors/170773010?group=host%3Adb-incident-sandbox&from_ts=1746012650000&to_ts=1746013850000&event_id=8082436309665268856&link_source=monitor_notif)\n\n**system.cpu.user** over **host:db-incident-sandbox** was **> 60.0** on average during the **last 5m**.\n\nThe monitor was last triggered at Wed Apr 30 2025 11:45:50 UTC.\n\n- - -\n\n[[Monitor Status](https://app.datadoghq.com/monitors/170773010?group=host%3Adb-incident-sandbox&from_ts=1746012650000&to_ts=1746013850000&event_id=8082436309665268856&link_source=monitor_notif)] · [[Edit Monitor](https://app.datadoghq.com/monitors/170773010/edit?link_source=monitor_notif)] · [[View db-incident-sandbox](https://app.datadoghq.com/infrastructure?filter=db-incident-sandbox&link_source=monitor_notif)] · [[Show Processes](https://app.datadoghq.com/process?from_ts=1746013250000&to_ts=1746013670000&live=false&showSummaryGraphs=true&sort=cpu%2CDESC&query=host%3Adb-incident-sandbox&link_source=monitor_notif)]\n%%%"
        host_description=', '.join(f"{k.replace('_', ' ').title()}: {getattr(self.instance.metadata.host_info, k)}" for k in vars(self.instance.metadata.host_info))

        result = self.db_incident_assistant.run(incident_id, instance_id, hostname, incident_description,host_description)
        self.assertEqual(result, "Fine")

if __name__ == "__main__":
    unittest.main()