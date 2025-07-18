
from typing import Sequence
import sys
from typing import List

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from typing_extensions import Annotated, TypedDict

from src.modules.tools.data_objects import InterpretationResult, ProcessedCommand

class InterpretationInputState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


class InterpretationOutputState(TypedDict):
    interpretation_result: InterpretationResult


class InterpretationAgentState(InterpretationInputState, InterpretationOutputState):
    pass


class InterpretationTool:

    INTERPRETATION_PROMPT = """
    You are given input tags:
    <objectives>: Describe your main goals.
    <incident_description>: Describes the reported issues or symptoms observed.
    <runtime_description>: Describes the current runtime environment or context.
    <commands>: A history of commands run, including execution result.
    <examples>: Some examples of how the output of your work should look like.

    You need to interpret the result of the command and provide a detailed explanation of the command.

    Do not rush with a solution. Take your time and think step by step.

    Return your response in the following json format:
    {
        "commands": [
            {
                "command": "command to execute",
                "interpretation": "interpretation of the result of the command",
                "interpretation_verdict": "interpretation verdict of the command: CONFIRMED, FALSE_POSITIVE, INCONCLUSIVE",
                "risk": "risk of the command",
                "risk_justification": "justification of the risk of the command",
            }
        ],
        "final_interpretation": "summary of the interpretation",
        "final_interpretation_verdict": "interpretation verdict of the final interpretation: CONFIRMED, FALSE_POSITIVE, INCONCLUSIVE"
    }

    <objectives>
    1. Your main goal is to interpret the result of each command. 
    2. Don't miss any command. Each command is important and has to have an interpretation.
    2. State whether the result has an answer to the cause of the incident or not, if it has, describe it in a focused way, so that the remediation step can understand it and come up with a fix of a problem.
    3. If the result does not have an answer to the cause of the incident or any leads, state it in the interpretation.
    4. If the human did not wish the command to be executed, state it in the interpretation which matters only for high risk commands.
    5. Set interpretation verdict to CONFIRMED if the command has an answer to the cause of the incident.
    6. Set interpretation verdict to FALSE_POSITIVE if the command could confirm the incident but does not have an answer to the cause of the incident.
    7. Set interpretation verdict to INCONCLUSIVE if the command has an answer to the cause of the incident but it is not the root cause or it is not related to the incident or not enough information is provided or the command's execution failed.
    5. You should take into account the incident description in the tag <incident_description>, the runtime description in the tag <runtime_description>.
    6. You should take into account the output of the command in the tag <result>.
    7. You should take into account the examples in the tag <examples>.
    8. The interpretation should have maximum 100 words.
    9. When all the commands are interpreted, provide a final summary of the interpretation, if possible with pinpointing the root cause of the incident.
    10. The final interpretation summary should done based on the interpretation of all the commands.
    11. The final interpretation summary should have maximum 100 words.
    12. The final interpretation summary should provide all the information like process id or file system location etc. that is needed to fix the incident.
    13. The final interpretation verdict should be based on the interpretation of all the commands.
    </objectives>

    <examples>
        <command>
            <command>df -h; du -sh /* 2>/dev/null | sort -hr | head -10</command>
            <result>
            Filesystem      Size  Used Avail Use% Mounted on
            /dev/root        29G   17G   12G  58% /
            tmpfs           7.9G   84K  7.9G   1% /dev/shm
            tmpfs           3.2G  888K  3.2G   1% /run
            tmpfs           5.0M     0  5.0M   0% /run/lock
            /dev/xvda16     881M  137M  683M  17% /boot
            /dev/xvda15     105M  6.1M   99M   6% /boot/efi
            tmpfs           1.6G   12K  1.6G   1% /run/user/1000
            </result>
            <interpretation>
            The df -h output shows that the root filesystem (/dev/root) has 12GB of available space out of 29GB, with 58% of the space used, which is not critical. 
            The issue may relate to other filesystems or partitions, but no immediate low disk space issues are visible in the provided output. 
            The reported problem of low disk space (10%) could be related to a specific directory or mount point not covered in this snapshot. 
            Further investigation is needed to pinpoint any specific volume or directory causing the low disk space issue.
            </interpretation>
            <interpretation_verdict>INCONCLUSIVE</interpretation_verdict>
         </command>
        <command>
            <command>top -b -n 1</command>
            <result>
            top - 19:55:45 up 0 min,  2 users,  load average: 0.18, 0.07, 0.02
            Tasks: 141 total,   1 running, 140 sleeping,   0 stopped,   0 zombie
            %Cpu(s):  0.0 us,  2.2 sy,  0.0 ni, 93.5 id,  0.0 wa,  0.0 hi,  0.0 si,  4.3 st 
            MiB Mem :  15990.2 total,  15325.4 free,    497.4 used,    441.3 buff/cache     
            MiB Swap:      0.0 total,      0.0 free,      0.0 used.  15492.8 avail Mem 

                PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
                1 root      20   0   22148  12924   9340 S   0.0   0.1   0:01.41 systemd
                2 root      20   0       0      0      0 S   0.0   0.0   0:00.00 kthreadd
                3 root      20   0       0      0      0 S   0.0   0.0   0:00.00 pool_workqueue_release
                4 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker/R-rcu_g
                5 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker/R-rcu_p
                6 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker/R-slub_
                7 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker/R-netns
                8 root      20   0       0      0      0 I   0.0   0.0   0:00.00 kworker/0:0-events
            </result>
            <interpretation>
            The top command output indicates that the CPU is mostly idle, with 93.5% of the CPU time spent in the idle state (id). 
            The system has 141 tasks, with one running and the rest sleeping. 
            Memory usage is low, with 15,325.4 MiB free out of 15,990.2 MiB total, and no swap usage. 
            However, the issue of high CPU load (100 10 10) isn't reflected in this specific snapshot, suggesting the high load might be intermittent or was observed after this command output. 
            </interpretation>
            <interpretation_verdict>FALSE_POSITIVE</interpretation_verdict>
        </command>
        <command>
            <command>top -b -n 1</command>
            <result>
            top - 20:00:42 up 5 min,  2 users,  load average: 0.28, 0.08, 0.02
            Tasks: 137 total,   2 running, 135 sleeping,   0 stopped,   0 zombie
            %Cpu(s): 26.8 us,  0.0 sy,  0.0 ni, 73.2 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st 
            MiB Mem :  15990.2 total,  15188.2 free,    568.0 used,    553.2 buff/cache     
            MiB Swap:      0.0 total,      0.0 free,      0.0 used.  15422.2 avail Mem 

            PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
            1233 root      20   0  293112  13084   2432 R 100.0   0.1   0:20.64 stress-ng-cpu
                1 root      20   0   22148  12924   9340 S   0.0   0.1   0:01.43 systemd
                2 root      20   0       0      0      0 S   0.0   0.0   0:00.00 kthreadd
                3 root      20   0       0      0      0 S   0.0   0.0   0:00.00 pool_workqueue_release
                4 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker/R-rcu_g
                5 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker/R-rcu_p
                6 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker/R-slub_
                7 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker/R-netns
            </result>
            <interpretation>
            The top command output shows that the system's CPU is experiencing high usage, with 26.8% of the CPU time spent on user processes (us). 
            The stress-ng-cpu process (PID 1233) is consuming 100% of the CPU, which is likely the cause of the high CPU load mentioned in the problem. 
            Memory usage is low, and no swap is being used. 
            The issue seems to be directly linked to the stress-ng-cpu process, which is likely used for CPU stress testing. 
            </interpretation>
            <interpretation_verdict>CONFIRMED</interpretation_verdict>
        </command>
        <command>
            <command>ps aux --sort=-%cpu</command>
            <result>
            USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
            root        1233 99.9  0.0 293112 13084 pts/2    R    20:00   3:07 stress-ng-cpu [run]
            root        1247  0.5  0.2 577340 39988 ?        Ssl  20:00   0:00 /usr/libexec/fwupd/fwupd
            root         585  0.2  0.1 1469164 32216 ?       Ssl  19:54   0:01 /usr/lib/snapd/snapd
            root           1  0.2  0.0  22148 12924 ?        Ss   19:54   0:01 /sbin/init
            root         583  0.2  0.1 1833616 19532 ?       Ssl  19:54   0:01 /snap/amazon-ssm-agent/9881/amazon-ssm-agent
            root         156  0.0  0.1  66816 19268 ?        S<s  19:54   0:00 /usr/lib/systemd/systemd-journald
            root          28  0.0  0.0      0     0 ?        S    19:54   0:00 [migration/2]
            root          34  0.0  0.0      0     0 ?        S    19:54   0:00 [migration/3]
            root        1232  0.0  0.6 293112 103040 pts/2   SL   20:00   0:00 stress-ng --cpu 1 --timeout 10000 --metrics-brief
            root          22  0.0  0.0      0     0 ?        S    19:54   0:00 [migration/1]
            root         222  0.0  0.0  26476  8064 ?        Ss   19:54   0:00 /usr/lib/systemd/systemd-udevd
            ubuntu      1197  0.0  0.0  14996  6820 ?        S    19:55   0:00 sshd: ubuntu@pts/1
            ubuntu      1038  0.0  0.0  14992  6944 ?        S    19:54   0:00 sshd: ubuntu@pts/0
            root         575  0.0  0.1  32456 20480 ?        Ss   19:54   0:00 /usr/bin/python3 /usr/bin/networkd-dispatcher --run-startup-triggers
            systemd+     362  0.0  0.0  21584 12544 ?        Ss   19:54   0:00 /usr/lib/systemd/systemd-resolved
            </result>
            <interpretation>
            The ps aux output shows that the stress-ng-cpu process (PID 1233) is consuming 99.9% of the CPU, which is directly causing the high CPU load mentioned in the problem (100 10 10). 
            This process is designed for stress testing the CPU, explaining the high usage. No other processes are contributing significantly to the CPU load. 
            The system's memory usage appears normal. To resolve the high CPU usage, consider stopping or adjusting the stress-ng-cpu process if it's not needed for testing.
            </interpretation>
            <interpretation_verdict>CONFIRMED</interpretation_verdict>
        </command>
    </examples>
    """

    def __init__(self, llm, prompt=INTERPRETATION_PROMPT):
        self.llm = llm.with_structured_output(
            InterpretationResult, method="function_calling"
        )
        self.prompt = prompt
        self.graph = self._build()

    def _build(self):
        graph_builder = StateGraph(
            InterpretationAgentState,
            input=InterpretationInputState,
            output=InterpretationOutputState,
        )

        def interpretation(state):
            return {"interpretation_result": self.llm.invoke(state["messages"])}

        graph_builder.add_node("interpretation", interpretation)
        graph_builder.add_edge(START, "interpretation")
        graph_builder.add_edge("interpretation", END)

        return graph_builder.compile()

    def run(
        self,
        incident_description: str,
        environment_description: str,
        commands: List[ProcessedCommand] = [],
    ):

        input_data = "Execute the interpretation for the following commands:\n"
        input_data += (
            f"<incident_description>{incident_description}</incident_description>\n"
        )
        input_data += (
            f"<runtime_description>{environment_description}</runtime_description>\n"
        )
        input_data += f"<commands>{commands}</commands>\n"

        inputs = {
            "messages": [
                SystemMessage(content=self.prompt),
                HumanMessage(content=input_data),
            ]
        }
        output = self.graph.invoke(inputs)["interpretation_result"]
        return output