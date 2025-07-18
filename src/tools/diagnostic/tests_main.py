import os
import random
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.llm import llm
from src.modules.tools.data_objects import ProcessedCommand
from src.tools.diagnostic.main import DiagnosticTool, ExecutionPlatformType


previous_commands = [
    ProcessedCommand(
        command="top -b|head -n 10",
        result="""
            top - 19:07:13 up 1 day, 55 min,  2 users,  load average: 0.00, 0.00, 0.00
            Tasks: 138 total,   1 running, 137 sleeping,   0 stopped,   0 zombie
            %Cpu(s):  2.3 us,  0.0 sy,  0.0 ni, 95.3 id,  0.0 wa,  0.0 hi,  0.0 si,  2.3 st 
            MiB Mem :  15990.2 total,  12466.9 free,    708.9 used,   3160.1 buff/cache     
            MiB Swap:      0.0 total,      0.0 free,      0.0 used.  15281.3 avail Mem 
                PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
                1 root      20   0   22320  13236   9396 S   0.0   0.1   0:03.39 systemd
                2 root      20   0       0      0      0 S   0.0   0.0   0:00.02 kthreadd
                3 root      20   0       0      0      0 S   0.0   0.0   0:00.00 pool_wo+
""",
    ),
    ProcessedCommand(
        command="ps aux --sort=-%cpu | head -n 10",
        result="""
            USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
            root         1  0.0  0.1 22320 13236 ?        Ss   19:07   0:03.39 systemd
            root         2  0.0  0.0      0     0 ?        S    19:07   0:00.02 kthreadd
            root         3  0.0  0.0      0     0 ?        S    19:07   0:00.00 pool_wo+
""",
    ),
    ProcessedCommand(
        command="mpstat -P ALL 1 5 2>/dev/null",
        result="""
    Linux 6.8.0-1024-aws (ip-10-0-0-100)   03/27/25  _x86_64_    (1 CPU)    
    11:55:55 AM  CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
    11:55:56 AM  all   0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00   99.99
    11:55:57 AM  all   0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00   99.99
    11:55:58 AM  all   0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00   99.99
    11:55:59 AM  all   0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00   99.99
""",
    ),
    ProcessedCommand(
        command="grep -i 'cpu' /var/log/syslog | tail -50",
        result="""
            Mar 27 11:55:55 ip-10-0-0-100 kernel: [115555.000000] CPU: 0 PID: 1 Comm: systemd Tainted: G        W       4.15.0-204.el7.x86_64 #1        
            Mar 27 11:55:56 ip-10-0-0-100 kernel: [115556.000000] CPU: 0 PID: 1 Comm: systemd Tainted: G        W       4.15.0-204.el7.x86_64 #1        
            Mar 27 11:55:57 ip-10-0-0-100 kernel: [115557.000000] CPU: 0 PID: 1 Comm: systemd Tainted: G        W       4.15.0-204.el7.x86_64 #1        
            Mar 27 11:55:58 ip-10-0-0-100 kernel: [115558.000000] CPU: 0 PID: 1 Comm: systemd Tainted: G        W       4.15.0-204.el7.x86_64 #1        
            Mar 27 11:55:59 ip-10-0-0-100 kernel: [115559.000000] CPU: 0 PID: 1 Comm: systemd Tainted: G        W       4.15.0-204.el7.x86_64 #1  
""",
    ),
]

diagnosticTool = DiagnosticTool(llm.llm)

unix_runtime_description = f"OS: linux, Platform: ubuntu, Platform Family: debian, Platform Version: 24.04, Kernel Version: 6.8.0-1024-aws"
unix_incident_description = "- Type: Type.HIGH_CPU_USAGE\n- Details: {'load': '100 10 10'}"

postgres_runtime_description = f"Database: PostgreSQL"
postgres_incident_description = "- Type: Type.HIGH_CPU_USAGE\n- Details: {'load': '100 10 10'}"



class TestAPI(unittest.TestCase):
    def setUp(self):
        pass

    def test_diagnostic_unix(self):
        commands = diagnosticTool.run(
            ExecutionPlatformType.LINUX, unix_incident_description, unix_runtime_description
        )
        print("Unix commands:")
        for command in commands.commands:
            print(command.command)
        assert len(commands.commands) > 0
        assert len(commands.commands[0].command) > 0

    def test_diagnostic_postgres(self):
        commands = diagnosticTool.run(
            ExecutionPlatformType.POSTGRES, postgres_incident_description, postgres_runtime_description
        )
        print("Postgres commands:")
        for command in commands.commands:
            print(command.command)
        assert len(commands.commands) > 0
        assert len(commands.commands[0].command) > 0

    
    

if __name__ == "__main__":
    unittest.main()