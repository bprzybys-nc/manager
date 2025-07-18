import os
import sys
import unittest


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.llm import llm
from src.modules.tools.data_objects import InterpretationResult, ProcessedCommand, VerificationResult, Verdict, SourceIdentification
from src.tools.interpretation.main import InterpretationTool
from src.tools.source_identification.main import SourceIdentificationTool




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

class TestAPI(unittest.TestCase):
    def setUp(self):
        pass

    def test_source_identification_unix(self):
        runtime_description = f"OS: linux, Platform: ubuntu, Platform Family: debian, Platform Version: 24.04, Kernel Version: 6.8.0-1024-aws"
        incident_description = "Type: Type.HIGH_CPU_USAGE. Details: {'load': '100 10 10'}"

        verification_result = VerificationResult(verdict=Verdict.CONFIRMED, 
                                                 explanation="The problem stated in the incident description is not confirmed and the remediation might not be needed.",
                                                  detailed_explanation="The diagnostic results show that there is no high CPU usage occurring on the system. The `top` command output indicates a load average of 0.00, which is extremely low and suggests that the system is not under any load. The `ps aux --sort=-%cpu` command shows no processes with high CPU usage, with the 'systemd' process using 0.0% CPU. The `mpstat` command confirms that the CPU is almost entirely idle, with 99.99% idle time across multiple snapshots. Additionally, the system logs retrieved with `grep` show only routine entries with the CPU not exhibiting abnormal usage patterns. Given these results, the incident description indicating a load average of '100 10 10' is likely incorrect, hence the issue is marked as FALSE_POSITIVE.")
        source_identificationTool = SourceIdentificationTool(llm)
        source_identificationResult = source_identificationTool.run(
            incident_description, runtime_description, diagnostic_commands, verification_result
        )
        for source in source_identificationResult.sources:
            print(source)
        assert len(source_identificationResult.sources) == 4
        for source in source_identificationResult.sources:
            assert source.source_type == "postgres"

if __name__ == "__main__":
    unittest.main()