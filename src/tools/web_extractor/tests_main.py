import unittest
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.llm import llm
from src.tools.web_extractor.main import WebExtractor
from src.modules.tools.data_objects import InterpretationResult, ProcessedCommand
from src.tools.interpretation.main import InterpretationTool

high_cpu_usage_incident = """
'{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-sandbox}] High CPU Usage",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## High CPU Usage Alert\nDetected high CPU usage on the server.\n\nService Impact\n* Increased response times\n* Potential application timeouts\n\n@webhook-ovora-incident-assistant",
   "hostname":"db-incident-sandbox"
}'
"""


postgres_lock_contention_incident = """
'{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-sandbox}] PostgreSQL Lock Contention Critical",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## Lock Contention Alert\nDetected 11.0 blocked transactions on PostgreSQL server.\n\nService Impact\n* Transaction queuing\n* Increased response times\n* Potential application timeouts\n\n@webhook-ovora-incident-assistant",
   "hostname":"db-incident-sandbox"
}'
"""

postgres_unexpected_shutdown_incident = """
'{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-sandbox}] Unexpected showdown PostgreSQL DB",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## Detected unexpected shutdown of the PostgreSQL DB.\n\nMetric: postgresql.heartbeat\n\nTriggered for:\n\nHost: db-incident-sandbox\nValue: 0.0 (Threshold: 0.5)\nDB hostname: db-incident-sandbox\nPostgreSQL version: 14.17_ubuntu_14.17-0ubuntu0.22.04.1\n\n@webhook-ovora-incident-assistant",
   "hostname":"db-incident-sandbox"
}'
"""

postgres_connection_pool_near_saturation_incident = """
'{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-sandbox}] PostgreSQL Connection Pool Near Saturation",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## PostgreSQL Connection Pool Alert\nConnection pool on db-incident-sandbox is at 0.924 capacity (threshold: 0.8).\n\nImpact\n* New connections will be rejected once the pool is exhausted, causing application errors.\n\n@webhook-ovora-incident-assistant",
   "hostname":"db-incident-sandbox"
}'
"""

# Define sample PostgreSQL diagnostic commands for lock contention
postgres_lock_contention_commands = [
    ProcessedCommand(
        command="SELECT blocking_locks.pid AS blocking_pid, blocked_locks.pid AS blocked_pid FROM pg_catalog.pg_locks blocked_locks JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid AND blocking_locks.pid != blocked_locks.pid JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid WHERE NOT blocked_locks.granted ORDER BY blocked_activity.query_start DESC LIMIT 5;"
    ),
    ProcessedCommand(
        command="SELECT pid, usename, client_addr, state, query, EXTRACT(EPOCH FROM (now() - query_start)) AS query_duration_secs FROM pg_stat_activity WHERE state = 'active' ORDER BY query_duration_secs DESC LIMIT 10;"
    ),
    ProcessedCommand(
        command="SELECT datname, usename, wait_event_type, wait_event, pid, pg_blocking_pids(pid) AS blocked_by, backend_type, query FROM pg_stat_activity WHERE wait_event_type IS NOT NULL AND wait_event_type NOT IN ('Activity', 'Client');"
    ),
    ProcessedCommand(
        command="SELECT activity.pid, activity.usename, activity.query, blocking.pid AS blocking_id, blocking.query AS blocking_query FROM pg_stat_activity AS activity JOIN pg_stat_activity AS blocking ON blocking.pid = ANY(pg_blocking_pids(activity.pid));"
    ),
    ProcessedCommand(
        command="SELECT relation_name, query, pg_locks.* FROM pg_locks JOIN pg_class ON pg_locks.relation = pg_class.oid JOIN pg_stat_activity ON pg_locks.pid = pg_stat_activity.pid;"
    )
]

class TestWebExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = WebExtractor(llm)

    def test_command_classification(self):
        for command in postgres_lock_contention_commands:
            self.extractor._select_platform(command)
            print(f"{command.platform}: {command.command}")


    def test_build_query(self):
        incident = postgres_lock_contention_incident
        runtime = "PostgreSQL"
        commands = self.extractor.find_commands(incident, runtime)
        print("Lock Contention")
        for command in commands:
            print(f"  {command}")
        print("--------------------------------")

        incident = high_cpu_usage_incident
        runtime = "linux"
        commands = self.extractor.find_commands(incident, runtime)

        print("High CPU Usage")
        for command in commands:
            print(f"  {command}")
        print("--------------------------------")
        """
        incident = postgres_unexpected_shutdown_incident
        runtime = "PostgreSQL"
        result = self.extractor.search(incident, runtime)
        print("Unexpected Shutdown")
        print(result)
        print("--------------------------------")
        incident = postgres_connection_pool_near_saturation_incident
        runtime = "PostgreSQL"
        result = self.extractor.search(incident, runtime)
        print("Connection Pool Near Saturation")
        print(result)
        print("--------------------------------")
        """

        
    
if __name__ == "__main__":
    unittest.main()
