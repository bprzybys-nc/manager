import os
import sys
from typing import Dict, List
from typing import Callable

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from src.modules.tools.data_objects import ProcessedCommand
from src.tools.cmd_exec.app.cmd_exec import Platform, CommandExecutorTool


class TestPlatform(Platform):
    def execute_commands(self, incident_id: str, instance_id: str, commands: List[str], command_types: List[str]):
        print(f"Executing commands: {incident_id} | {instance_id} | {commands} | {command_types}")

    def commands_executed(self, incident_id: str, execution_results: Dict[str, str]):
        print(f"Commands executed: {execution_results}")
    
    def add_commands_executed_callback(self, callback: Callable):
        pass


test_platform = TestPlatform()


def execution_finished_callback(result):
    print(f"Execution finished: {result}")


commandExecutorTool = CommandExecutorTool(test_platform, execution_finished_callback)

commandExecutorTool.run(
    "123",
    "128374837",
    [
        ProcessedCommand(command="top -b|head -n 10"),
        ProcessedCommand(command="ps aux --sort=-%cpu | head -n 10"),
    ],
    ["shell", "shell"]
)
test_platform.commands_executed(
    "123",
    {
        "top -b|head -n 10": "Command top -b|head -n 10 executed successfully 10",
        "ps aux --sort=-%cpu | head -n 10": "Command ps aux --sort=-%cpu | head -n 10 executed successfully 10",
    }
)