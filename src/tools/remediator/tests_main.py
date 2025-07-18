



import os
import sys
import unittest
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.llm import llm
from src.tools.remediator.main import RemediatorTool
from src.modules.tools.data_objects import ProcessedCommand, Verdict, InterpretationVerdict
from src.tools.interpretation.main import InterpretationResult



commands = [
        ProcessedCommand(
        command="top -b -n 1 | grep postgres",
        result="""
112953 postgres  20   0  336032  77284  59904 R  50.0   1.0   0:01.69 postgres
 112956 postgres  20   0  336032  77284  59904 R  50.0   1.0   0:01.04 postgres
 112959 postgres  20   0  336032  77284  59904 R  43.8   1.0   0:00.47 postgres
 112962 postgres  20   0  336032  77284  59904 R  43.8   1.0   0:00.22 postgres
   8631 postgres  20   0  220740  32000  29440 S   0.0   0.4   0:01.83 postgres
   8633 postgres  20   0  220856  10340   7552 S   0.0   0.1   0:00.01 postgres
   8634 postgres  20   0  220740   9060   6272 S   0.0   0.1   0:00.25 postgres
   8635 postgres  20   0  220740  11620   8832 S   0.0   0.1   0:00.24 postgres
   8636 postgres  20   0  221420  10468   7424 S   0.0   0.1   0:00.43 postgres
   8637 postgres  20   0   73560   7140   4352 S   0.0   0.1   0:02.56 postgres
   8638 postgres  20   0  221164   9444   6400 S   0.0   0.1   0:00.01 postgres
   9906 postgres  20   0  224956  23192  16640 S   0.0   0.3   0:46.02 postgres
   9909 postgres  20   0  224916  21408  15232 S   0.0   0.3   0:56.76 postgres
""",
    interpretation="The postgres process is running with high CPU usage.",
    interpretation_verdict=InterpretationVerdict.CONFIRMED,
    ),
    ProcessedCommand(
        command="ps aux --sort=-%cpu | head -10",
        result="""
USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
postgres  112953 59.6  0.9 336032 77284 ?        Rs   19:12   0:01 postgres: 14/main: admin mydbname 127.0.0.1(56718) SELECT
postgres  112956 57.5  0.9 336032 77284 ?        Rs   19:12   0:01 postgres: 14/main: admin mydbname 127.0.0.1(56720) SELECT
postgres  112959 57.0  0.9 336032 77284 ?        Rs   19:12   0:00 postgres: 14/main: admin mydbname 127.0.0.1(56724) SELECT
azureus+  112958  7.0  0.1  23200 12672 pts/0    S+   19:12   0:00 /usr/lib/postgresql/14/bin/psql -h localhost -p 5432 -U admin -d mydbname -c SELECT count(*) FROM generate_series(1, 10000000) s;
azureus+  112961  7.0  0.1  23200 12800 pts/0    S+   19:12   0:00 /usr/lib/postgresql/14/bin/psql -h localhost -p 5432 -U admin -d mydbname -c SELECT count(*) FROM generate_series(1, 10000000) s;
azureus+  112955  4.0  0.1  23200 12928 pts/0    S+   19:12   0:00 /usr/lib/postgresql/14/bin/psql -h localhost -p 5432 -U admin -d mydbname -c SELECT count(*) FROM generate_series(1, 10000000) s;
azureus+  112952  2.3  0.1  23200 12800 pts/0    S+   19:12   0:00 /usr/lib/postgresql/14/bin/psql -h localhost -p 5432 -U admin -d mydbname -c SELECT count(*) FROM generate_series(1, 10000000) s;
dd-agent    9874  1.6  2.6 2587556 212384 ?      Ssl  09:36   9:22 /opt/datadog-agent/bin/agent/agent run -p /opt/datadog-agent/run/agent.pid
root        2003  0.7  0.1 1231948 13292 ?       Ssl  08:41   4:46 /opt/sysaidmin/sysaidmin-agent -config /opt/sysaidmin/config.json
""",
  interpretation="The output confirms multiple postgres processes consuming high CPU, with 'SELECT count(*) FROM generate_series(1, 10000000) s;' being a likely culprit for high usage, verified by postgres connections and query details. This matches known usage patterns of resource-intensive queries, confirming their impact.",
    interpretation_verdict=InterpretationVerdict.CONFIRMED
    ),
        ProcessedCommand(
        command="grep -i 'erro' /var/log/postgresql/postgresql-14-main.log | tail -100",
        result="""
""",
 interpretation="No errors were found in the recent logs, indicating the excessive CPU usage might not be caused by any apparent errors or faults in PostgreSQL operations, but rather by high-load queries or typical application behavior.",
    interpretation_verdict= InterpretationVerdict.FALSE_POSITIVE
    ),
        ProcessedCommand(
        command="sudo journalctl -u postgresql --since '1 hour ago'",
        result="""
-- No entries --
""",
 interpretation="No recent logs are available, confirming the absence of system-level issues or failures within the PostgreSQL service itself that coincide with the timing of the high CPU usage incident.",
    interpretation_verdict=InterpretationVerdict.FALSE_POSITIVE
    ),
        ProcessedCommand(
        command="vmstat 1 5",
        result="""
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 5  0      0 4820460  97500 2644032    0    0    10    86  315  513  4  1 95  0  0
 5  0      0 4714120  97500 2742648    0    0     0     0 2594 2599 93  7  0  0  0
 4  0      0 4637764  97500 2814584    0    0     0     0 2447 1991 94  6  0  0  0
 4  0      0 4605764  97500 2858260    0    0     0     8 2378 1781 96  4  0  0  0
 4  0      0 4652748  97504 2735052    0    0     0    68 2769 3206 91 10  0  0  0
""",
 interpretation="The vmstat output indicates that the system has ample memory and swap space. The CPU utilization reflects the current load issue, with high user mode CPU percentages, consistent with the postgres processes taxing the system.",
    interpretation_verdict=InterpretationVerdict.CONFIRMED
    ),
        ProcessedCommand(
        command="systemctl status postgresql",
        result="""
● postgresql.service - PostgreSQL RDBMS
     Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
     Active: active (exited) since Mon 2025-05-12 09:29:42 UTC; 9h ago
   Main PID: 8649 (code=exited, status=0/SUCCESS)
        CPU: 1ms
May 12 09:29:42 db-incident-demo systemd[1]: Starting PostgreSQL RDBMS...
May 12 09:29:42 db-incident-demo systemd[1]: Finished PostgreSQL RDBMS.
""",
 interpretation="PostgreSQL service is active, showing no issues or unexpected behavior. The service status does not relate directly to the CPU load, suggesting the postgres queries themselves are the primary contributors to system strain.",
    interpretation_verdict=InterpretationVerdict.INCONCLUSIVE
    ),
        ProcessedCommand(
        command="SELECT pid, usename, now() - query_start AS duration, state, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 5;",
        result="""
pid   | usename |    duration     | state  |                                                                      query                                                                     
--------+---------+-----------------+--------+-------------------------------------------------------------------------------------------------------------------------------------------------
 113024 | admin   | 00:00:06.30676  | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 113029 | admin   | 00:00:04.663852 | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 113032 | admin   | 00:00:03.477784 | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 113035 | admin   | 00:00:03.252479 | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 113041 | admin   | 00:00:00        | active | SELECT pid, usename, now() - query_start AS duration, state, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 5;
(5 rows)
""",
 interpretation="The active postgres queries are performing SELECTs on large series, identified as the primary source of CPU usage. The queries are ongoing with notable durations, aligning with the high CPU incident and confirming resource-heavy operations.",
    interpretation_verdict=InterpretationVerdict.CONFIRMED
    ),
        ProcessedCommand(
        command="SELECT * FROM pg_stat_database WHERE deadlocks > 0;",
        result="""
datid | datname | numbackends | xact_commit | xact_rollback | blks_read | blks_hit | tup_returned | tup_fetched | tup_inserted | tup_updated | tup_deleted | conflicts | temp_files | temp_bytes | deadlocks | checksum_failures | checksum_last_failure | blk_read_time | blk_write_time | session_time | active_time | idle_in_transaction_time | sessions | sessions_abandoned | sessions_fatal | sessions_killed | stats_reset
-------+---------+-------------+-------------+---------------+-----------+----------+--------------+-------------+--------------+-------------+-------------+-----------+------------+------------+-----------+-------------------+-----------------------+---------------+----------------+--------------+-------------+--------------------------+----------+--------------------+----------------+-----------------+-------------
(0 rows)
""",
 interpretation="No deadlocks are present, confirming that CPU spikes are not due to transaction issues. This absence suggests isolated query resource usage as the load source, rather than database contention problems.",
    interpretation_verdict= InterpretationVerdict.FALSE_POSITIVE
    ),
        ProcessedCommand(
        command="SELECT relname, seq_scan, idx_scan, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables ORDER BY n_tup_upd + n_tup_del DESC LIMIT 5; ",
        result="""
relname | seq_scan | idx_scan | n_tup_ins | n_tup_upd | n_tup_del
---------+----------+----------+-----------+-----------+-----------
(0 rows)
""",
 interpretation="No significant updates or deletions are showing in user tables, supporting the theory that current CPU usage is driven by read operations rather than write-heavy transactions. This suggests intensive querying activity without data change impact.",
    interpretation_verdict=InterpretationVerdict.FALSE_POSITIVE
    ),
        ProcessedCommand(
        command="SELECT relname, n_dead_tup FROM pg_stat_user_tables WHERE n_dead_tup > 1000 ORDER BY n_dead_tup DESC LIMIT 5;",
        result="""
 relname | n_dead_tup
---------+------------
(0 rows)
""",
 interpretation="No high number of dead tuples indicates well-performing tables with respect to space compaction. The cause of high CPU use lies in the active SELECT queries rather than inefficient table scans or dead tuples management.",
    interpretation_verdict=InterpretationVerdict.FALSE_POSITIVE
    )
]


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.remediator_tool = RemediatorTool(llm)

    def test_recommendation_tool(self):
        runtime_description = f"Postgres"
        incident_description = {
            "id":"8082436309665268856",
            "source":"datadog",
            "last_updated":"1746013550000",
            "event_type":"query_alert_monitor",
            "title":"[Triggered on {host:db-incident-demo}] Postgres is near the max CPU usage limit",
            "date":"1746013550000",
            "org":{
                "id":"1325540",
                "name":"IBM Ovora"
            },
            "body":"%%%\n## CPU usage reached a ceiling for postgres\nTriggered for:\n- Host: db-incident-demo\n- Value: 93.002 (Threshold: 90.0)\n\n@webhook-ovora-incident-assistant\n\n\n",
            "hostname":"db-incident-demo"
            }
        incident_description = json.dumps(incident_description)

        confirmed_commands = list(filter(lambda x: x.interpretation_verdict == InterpretationVerdict.CONFIRMED, commands))
        final_interpretation = InterpretationResult(
            commands=confirmed_commands,
            final_interpretation="The persistent high CPU usage is attributed to concurrent heavy SQL SELECT queries, specifically using 'generate_series' causing processor load peaks. Postgres settings may require optimization to handle such load, but no logged errors or system service failures contribute directly to the load increases observed.",
            final_interpretation_verdict=InterpretationVerdict.CONFIRMED
        )

        recommendations = self.remediator_tool.generate_recommendations(incident_description, runtime_description, final_interpretation)
        print("recommendations:", recommendations)

    def test_remediation_tool(self):
        runtime_description = f""
        incident_description = {
            "id":"8082436309665268856",
            "source":"datadog",
            "last_updated":"1746013550000",
            "event_type":"query_alert_monitor",
            "title":"[Triggered on {host:db-incident-demo}] Postgres is near the max CPU usage limit",
            "date":"1746013550000",
            "org":{
                "id":"1325540",
                "name":"IBM Ovora"
            },
            "body":"%%%\n## CPU usage reached a ceiling for postgres\nTriggered for:\n- Host: db-incident-demo\n- Value: 93.002 (Threshold: 90.0)\n\n@webhook-ovora-incident-assistant\n\n\n",
            "hostname":"db-incident-demo"
            }
        incident_description = json.dumps(incident_description)

        confirmed_commands = list(filter(lambda x: x.interpretation_verdict == InterpretationVerdict.CONFIRMED, commands))
        final_interpretation = InterpretationResult(
            commands=confirmed_commands,
            final_interpretation="The persistent high CPU usage is attributed to concurrent heavy SQL SELECT queries, specifically using 'generate_series' causing processor load peaks. Postgres settings may require optimization to handle such load, but no logged errors or system service failures contribute directly to the load increases observed.",
            final_interpretation_verdict=InterpretationVerdict.CONFIRMED
        )

        remediation_list = self.remediator_tool.generate_remediation_commands(incident_description, runtime_description, final_interpretation)
        index=1
        for remediation in remediation_list:
            print(f"{index}. {remediation.command} ({remediation.platform}) - {remediation.interpretation}")
            index+=1



    

if __name__ == "__main__":
    unittest.main()