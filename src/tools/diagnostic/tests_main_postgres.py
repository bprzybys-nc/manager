import os
import json
import sys
import unittest
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.llm import llm
from src.modules.tools.data_objects import ProcessedCommand, Verdict, VerificationResult, SourceType
from src.tools.diagnostic.main import DiagnosticTool, ExecutionPlatformType


diagnostic_commands = [
    ProcessedCommand(
        command="top -b|head -n 10",
        result="""
top - 10:05:29 up 3 days, 14:36,  2 users,  load average: 0.62, 0.16, 0.04
Tasks: 185 total,   6 running, 179 sleeping,   0 stopped,   0 zombie
%Cpu(s): 91.3 us,  8.7 sy,  0.0 ni,  0.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :  15989.3 total,  11910.4 free,   1576.8 used,   2502.1 buff/cache
MiB Swap:      0.0 total,      0.0 free,      0.0 used.  14073.4 avail Mem 

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
1030144 postgres  20   0  336028  77408  60160 R 100.0   0.5   0:00.27 postgres
1030142 postgres  20   0  336028  77408  60032 R  94.1   0.5   0:00.31 postgres
1030143 postgres  20   0  336028  77536  60160 R  94.1   0.5   0:00.32 postgres
""",
    ),
    ProcessedCommand(
        command="ps aux --sort=-%cpu | head -n 10",
        result="""
USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
postgres 1030224  108  0.4 336028 77280 ?        Rs   10:05   0:01 postgres: 14/main: admin mydbname 127.0.0.1(60926) SELECT
postgres 1030228 99.0  0.4 336028 77280 ?        Rs   10:05   0:00 postgres: 14/main: admin mydbname 127.0.0.1(60936) SELECT
postgres 1030230 98.0  0.4 336028 77408 ?        Rs   10:05   0:00 postgres: 14/main: admin mydbname 127.0.0.1(60956) SELECT
postgres 1030229 95.0  0.4 336028 77408 ?        Rs   10:05   0:00 postgres: 14/main: admin mydbname 127.0.0.1(60952) SELECT
azureus+ 1030225  8.0  0.0  23200 12928 pts/1    S+   10:05   0:00 /usr/lib/postgresql/14/bin/psql -h localhost -p 5432 -U admin -d mydbname -c SELECT count(*) FROM generate_series(1, 10000000) s;
azureus+ 1030226  8.0  0.0  23200 12800 pts/1    S+   10:05   0:00 /usr/lib/postgresql/14/bin/psql -h localhost -p 5432 -U admin -d mydbname -c SELECT count(*) FROM generate_series(1, 10000000) s;
azureus+ 1030227  8.0  0.0  23200 12672 pts/1    S+   10:05   0:00 /usr/lib/postgresql/14/bin/psql -h localhost -p 5432 -U admin -d mydbname -c SELECT count(*) FROM generate_series(1, 10000000) s;
azureus+ 1030223  7.0  0.0  23200 12672 pts/1    S+   10:05   0:00 /usr/lib/postgresql/14/bin/psql -h localhost -p 5432 -U admin -d mydbname -c SELECT count(*) FROM generate_series(1, 10000000) s;
dd-agent     641  2.3  1.4 2747620 239516 ?      Ssl  Apr30 124:29 /opt/datadog-agent/bin/agent/agent run -p /opt/datadog-agent/run/agent.pid
""",
    ),
    ProcessedCommand(
        command="mpstat -P ALL 1 5 2>/dev/null",
        result="""
Linux 6.8.0-1027-azure (db-incident-sandbox)    05/04/25        _x86_64_        (4 CPU)
10:06:03     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
10:06:04     all   93.94    0.00    6.06    0.00    0.00    0.00    0.00    0.00    0.00    0.00
10:06:04       0   93.88    0.00    6.12    0.00    0.00    0.00    0.00    0.00    0.00    0.00
10:06:04       1   95.92    0.00    4.08    0.00    0.00    0.00    0.00    0.00    0.00    0.00
10:06:04       2   93.00    0.00    7.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00
10:06:04       3   93.00    0.00    7.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00
""",
    ),
    ProcessedCommand(
        command="grep -i 'cpu' /var/log/syslog | tail -50",
        result="""
May  4 00:33:47 db-incident-sandbox agent[641]: 2025-05-04 00:33:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:40 in CheckStarted) | check:cpu | Running check...
May  4 00:33:47 db-incident-sandbox agent[641]: 2025-05-04 00:33:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:59 in CheckFinished) | check:cpu | Done running check
May  4 02:38:47 db-incident-sandbox agent[641]: 2025-05-04 02:38:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:40 in CheckStarted) | check:cpu | Running check...
May  4 02:38:47 db-incident-sandbox agent[641]: 2025-05-04 02:38:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:59 in CheckFinished) | check:cpu | Done running check
May  4 04:43:47 db-incident-sandbox agent[641]: 2025-05-04 04:43:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:40 in CheckStarted) | check:cpu | Running check...
May  4 04:43:47 db-incident-sandbox agent[641]: 2025-05-04 04:43:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:59 in CheckFinished) | check:cpu | Done running check
May  4 06:48:47 db-incident-sandbox agent[641]: 2025-05-04 06:48:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:40 in CheckStarted) | check:cpu | Running check...
May  4 06:48:47 db-incident-sandbox agent[641]: 2025-05-04 06:48:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:59 in CheckFinished) | check:cpu | Done running check
May  4 08:53:47 db-incident-sandbox agent[641]: 2025-05-04 08:53:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:40 in CheckStarted) | check:cpu | Running check...
May  4 08:53:47 db-incident-sandbox agent[641]: 2025-05-04 08:53:47 UTC | CORE | INFO | (pkg/collector/worker/check_logger.go:59 in CheckFinished) | check:cpu | Done running check
""",
    ),
]

postgres_diagnostic_commands = [
    ProcessedCommand(
        command="SELECT pid, usename, now() - query_start AS duration, state, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 5;",
        result="""
   pid   | usename |    duration     | state  |                                                                      query                                                                      
---------+---------+-----------------+--------+-------------------------------------------------------------------------------------------------------------------------------------------------
 1051331 | admin   | 00:00:01.924259 | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 1051333 | admin   | 00:00:01.819413 | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 1051335 | admin   | 00:00:01.69282  | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 1051337 | admin   | 00:00:01.601366 | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 1051343 | admin   | 00:00:00        | active | SELECT pid, usename, now() - query_start AS duration, state, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 5;
(5 rows)
""",
    ),
    ProcessedCommand(
        command="SELECT * FROM pg_stat_database WHERE deadlocks > 0;",
        result="""
""",
    ),
    ProcessedCommand(
        command="SELECT relname, n_dead_tup FROM pg_stat_user_tables WHERE n_dead_tup > 1000 ORDER BY n_dead_tup DESC LIMIT 5;",
        result="""
relname | n_dead_tup 
---------+------------
(0 rows)
""",
    ),
    ProcessedCommand(
        command="SELECT relname, seq_scan, idx_scan, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables ORDER BY n_tup_upd + n_tup_del DESC LIMIT 5;",
        result="""
 relname | seq_scan | idx_scan | n_tup_ins | n_tup_upd | n_tup_del 
---------+----------+----------+-----------+-----------+-----------
(0 rows)
""",
    ),
       ProcessedCommand(
        command="SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total_size FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 5;",
        result="""
 relname | total_size 
---------+------------
(0 rows)
""",
    )
]

diagnosticTool = DiagnosticTool(llm)

unix_runtime_description = f"OS: linux, Platform: ubuntu, Platform Family: debian, Platform Version: 24.04, Kernel Version: 6.8.0-1024-aws"
#unix_incident_description = "- Type: Type.HIGH_CPU_USAGE\n- Details: {'load': '100 10 10'}"


class TestDiagnosticTool(unittest.TestCase):
    def setUp(self):
        with open("sample_alert.json", "r") as f:
            self.unix_incident_description = json.load(f)

    def test_diagnose_incident_unix(self):
        commands = diagnosticTool.diagnose_incident(
            ExecutionPlatformType.LINUX, self.unix_incident_description, unix_runtime_description
        )
        print("Unix commands:")
        for command in commands.commands:
            print(command.command)
        assert len(commands.commands) > 0
        assert len(commands.commands[0].command) > 0
    
    def test_judge_incident_validity(self):
        verification_result = self.get_verification_result(
            self.unix_incident_description, unix_runtime_description, diagnostic_commands
        )
        print(verification_result)
        assert verification_result.verdict == Verdict.CONFIRMED

    def test_incident_source_identification(self):
        verification_result = self.get_verification_result(
            self.unix_incident_description, unix_runtime_description, diagnostic_commands
        )
        source_identification_result = self.get_source_identification_result(
            self.unix_incident_description, unix_runtime_description, diagnostic_commands, verification_result
        )
        print("Source identification result:")
        print(source_identification_result)
        assert len(source_identification_result.sources) > 0
        assert source_identification_result.sources[0].source_type == SourceType.POSTGRES

    def test_diagnose_incident_postgres(self):
        commands = diagnosticTool.diagnose_incident(
            ExecutionPlatformType.POSTGRES, self.unix_incident_description, "Postgres"
        )
        print("Postgres commands:")
        for command in commands.commands:
            print(command.command)

    def test_incident_interpretation(self):
        commands= diagnostic_commands+postgres_diagnostic_commands
        interpretation_result = diagnosticTool.incident_interpretation(
            self.unix_incident_description, "Postgres", commands
        )
        print("Interpretation result:")
        for command in interpretation_result.commands:
            print(command.command)
            print(command.interpretation)
            print(f"--------------------------------")
        print(f"Summary: {interpretation_result.summary}")
        assert len(interpretation_result.commands) > 0
        assert len(interpretation_result.commands[0].interpretation) > 0

    def get_verification_result(self, incident_description: str, environment_description: str, diagnostic_commands: List[ProcessedCommand]):
        return diagnosticTool.judge_incident_validity(incident_description, environment_description, diagnostic_commands)
    
    def get_source_identification_result(self, incident_description: str, environment_description: str, diagnostic_commands: List[ProcessedCommand], verification_result: VerificationResult):
        return diagnosticTool.incident_source_identification(incident_description, environment_description, diagnostic_commands, verification_result)

if __name__ == "__main__":
    unittest.main()