


import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.llm import llm
from src.modules.tools.data_objects import ProcessedCommand
from src.tools.classifier.main import IncidentClassifier, ExecutionPlatformType

import json
# Sample incident descriptions for testing
import unittest

incident_descriptions = [
    # 1) High CPU incident
    {
        "id": "8082436309665268856",
        "source": "datadog",
        "last_updated": "1746013550000",
        "event_type": "query_alert_monitor",
        "title": "[Triggered on {host:db-incident-sandbox}] DB Host is near the max CPU usage limit",
        "date": "1746013550000",
        "org": {
            "id": "1325540",
            "name": "IBM Ovora"
        },
        "body": "%%%\n## CPU usage reached a ceiling\nTriggered for:\n- Host: db-incident-sandbox\n- Value: 93.002 (Threshold: 90.0)\n\n@webhook-ovora-incident-assistant\n\n\n",
        "hostname": "db-incident-sandbox"
    },
    
    # 2) Lock Contention Critical incident
    {
        "id": "8082436309665268856",
        "source": "datadog",
        "last_updated": "1746013550000",
        "event_type": "query_alert_monitor",
        "title": "[Triggered on {host:db-incident-sandbox}] PostgreSQL Lock Contention Critical",
        "date": "1746013550000",
        "org": {
            "id": "1325540",
            "name": "IBM Ovora"
        },
        "body": "%%%\n## Lock Contention Alert\nDetected 11.0 blocked transactions on PostgreSQL server.\n\nService Impact\n* Transaction queuing\n* Increased response times\n* Potential application timeouts\n\n@webhook-ovora-incident-assistant",
        "hostname": "db-incident-sandbox"
    },
    
    # 3) Slow Query Detection incident
    {
        "id": "8082436309665268856",
        "source": "datadog",
        "last_updated": "1746013550000",
        "event_type": "query_alert_monitor",
        "title": "[Triggered on {host:db-incident-sandbox}] PostgreSQL Slow Query Detection",
        "date": "1746013550000",
        "org": {
            "id": "1325540",
            "name": "IBM Ovora"
        },
        "body": "%%%\n## PostgreSQL Slow Query Alert\nThe average query time on has increased by 84551.093ms in the last 5 minutes.\n\nImpact\n * Increased application response times\n *Possible timeout errors\n * Database connection saturation\n\n@webhook-ovora-incident-assistant",
        "hostname": "db-incident-sandbox"
    },
    
    # 4) Connection pool exhausted incident
    {
        "id": "8082436309665268856",
        "source": "datadog",
        "last_updated": "1746013550000",
        "event_type": "query_alert_monitor",
        "title": "[Triggered on {host:db-incident-sandbox}] PostgreSQL Connection Pool Near Saturation",
        "date": "1746013550000",
        "org": {
            "id": "1325540",
            "name": "IBM Ovora"
        },
        "body": "%%%\n## PostgreSQL Connection Pool Alert\nConnection pool on db-incident-sandbox is at 0.924 capacity (threshold: 0.8).\n\nImpact\n* New connections will be rejected once the pool is exhausted, causing application errors.\n\n@webhook-ovora-incident-assistant",
        "hostname": "db-incident-sandbox"
    },
    
    # 5) Unexpected Database shutdown incident
    {
        "id": "8082436309665268856",
        "source": "datadog",
        "last_updated": "1746013550000",
        "event_type": "query_alert_monitor",
        "title": "[Triggered on {host:db-incident-sandbox}] Unexpected showdown PostgreSQL DB",
        "date": "1746013550000",
        "org": {
            "id": "1325540",
            "name": "IBM Ovora"
        },
        "body": "%%%\n## Detected unexpected shutdown of the PostgreSQL DB.\n\nMetric: postgresql.heartbeat\n\nTriggered for:\n\nHost: db-incident-sandbox\nValue: 0.0 (Threshold: 0.5)\nDB hostname: db-incident-sandbox\nPostgreSQL version: 14.17_ubuntu_14.17-0ubuntu0.22.04.1\n\n@webhook-ovora-incident-assistant",
        "hostname": "db-incident-sandbox"
    }
]


class TestIncidentClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = IncidentClassifier(llm)
        self.host_description = "OS: linux, Platform: ubuntu, Platform Family: debian, Platform Version: 24.04, Kernel Version: 6.8.0-1024-aws"
    
    def test_basic_classification(self):
        """Test basic classification with no previous commands"""
        results = []
        for incident_description in incident_descriptions:
            incident_description_str = json.dumps(incident_description)
            result = self.classifier.classify(
                incident_description=incident_description_str,
                runtime_description=self.host_description,
                previously_processed_commands=None,
                diagnostic_interpretation=None
            )
            results.append(result)

        self.assertEqual(sorted(results[0].execution_platform_list), [ExecutionPlatformType.LINUX])     
        self.assertEqual(sorted(results[1].execution_platform_list), [ExecutionPlatformType.LINUX, ExecutionPlatformType.POSTGRES])
        self.assertEqual(sorted(results[2].execution_platform_list), [ExecutionPlatformType.LINUX, ExecutionPlatformType.POSTGRES])
        self.assertEqual(sorted(results[3].execution_platform_list), [ExecutionPlatformType.LINUX, ExecutionPlatformType.POSTGRES])
        self.assertEqual(sorted(results[4].execution_platform_list), [ExecutionPlatformType.LINUX, ExecutionPlatformType.POSTGRES])
        
    
    def test_classification_with_previously_processed_commands(self):
        """Test classification with previously processed commands"""
        postgres_incident = incident_descriptions[1]
        postgres_incident_str = json.dumps(postgres_incident)
        
        result = self.classifier.classify(
            incident_description=postgres_incident_str,
            runtime_description=self.host_description,
            previously_processed_commands=[{
                "command": "SELECT * FROM users",
                "platform": "postgres",
                "result": "user1, user2, user3",
                "interpretation": "Users were found in the database."
            }],
            diagnostic_interpretation="Missing credentials"
        )

        print(f"Classification result: {result}")
        
        self.assertEqual(sorted(result.execution_platform_list), [ExecutionPlatformType.LINUX, ExecutionPlatformType.POSTGRES])    

    def test_classification_with_previously_processed_commands_with_execution_failure(self):
        """Test classification with previously processed commands"""
        postgres_incident = incident_descriptions[1]
        postgres_incident_str = json.dumps(postgres_incident)
        
        result = self.classifier.classify(
            incident_description=postgres_incident_str,
            runtime_description=self.host_description,
            previously_processed_commands=[{
                "command": "SELECT * FROM users",
                "platform": "postgres",
                "result": "Error: Access denied for user 'root'@'localhost'",
                "interpretation": "The user 'root' does not have access to the 'users' table."
            }],
            diagnostic_interpretation="Missing credentials"
        )

        print(f"Classification result: {result}")
        
        self.assertEqual(sorted(result.execution_platform_list), [ExecutionPlatformType.LINUX])   


if __name__ == "__main__":
    unittest.main()
