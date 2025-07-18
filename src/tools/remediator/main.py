


from src.modules.tools.data_objects import ProcessedCommands, InterpretationResult, ProcessedCommand
from src.modules.tools.data_objects import ExecutionPlatformType
from pydantic import BaseModel


RECOMMENDATION_PROMPT = """
    You are a remediation expert. Your main goal is to propose recommendations that will fix the issue described in the <incident_description>.

    You are given the following input tags:
    <objectives>: Describe your main goals during generating recommendations.
    <incident_description>: Describes the reported issues or symptoms observed.
    <runtime_description>: Describes the current runtime environment or context.
    <diagnostic_commands>: Diagnostic commands used to diagnose the issue.
    <final_interpretation_verdict>: Verdict of the final interpretation.
    <final_interpretation>: Final interpretation of the diagnostic commands.

    <objectives>
    1. Based on diagnostic commands execution results, verification explanation, verification detailed explanation, propose recommendations that will fix the issue.
    2. Suggest recommendations which will solve the issue described in the <incident_description>.
    3. The recommendations need to be executable on the system described in the <runtime_description>.
    4. Target only the root cause of the issue mentioned in <diagnostic_commands> and <verification_detailed_explanation>.
    5. Be very specific about the recommendations you propose and do not propose recommendations that are not related to the incident.
    6. The recommendations need to be concise and to the point.
    7. The recommendations can be in the form of a command, a configuration change, a policy, a procedure, or a documentation change.
    8. The recommendations need to be actionable.
    9. The recommendations need to be verifiable.
    10. The recommendations need to be secure.
    11. The recommendations need to be efficient.
    12. The recommendations need to be easy to understand.
    </objectives>

    <final_interpretation_verdict>
    {final_interpretation_verdict}
    </final_interpretation_verdict>
    <final_interpretation>
    {final_interpretation}
    </final_interpretation>
    <diagnostic_commands>
    {diagnostic_commands}
    </diagnostic_commands>
    <incident_description>
    {incident_description}
    </incident_description>
    <runtime_description>
    {runtime_description}
    </runtime_description>
    """

REMEDIATION_PROMPT = """
    Your purpose is to propose remediation commands that will fix the issue described in the <incident_description>.

    You are given the following input tags:
    <objectives>: Describe your main goals during remediation.
    <output_format>: Describe the format of the output.
    <incident_description>: Describes the reported issues or symptoms observed.
    <runtime_description>: Describes the current runtime environment or context.
    <diagnostic_commands>: Diagnostic commands used to diagnose the issue.
    <final_interpretation_verdict>: Verdict of the final interpretation.
    <final_interpretation>: Final interpretation of the diagnostic commands.
    <remediation_instructions>: Specific rules and constraints for proposing valid remediation commands.

    <objectives>
    1. Based on diagnostic commands execution results, verification explanation, verification detailed explanation, propose remediation commands that will fix the issue.
    2. Suggest commands which will solve the issue described in the <incident_description>. 
    3. The commands need to be executable on the system described in the <runtime_description>.
    4. Follow the instructions in <remediation_instructions> for specific rules and constraints for proposing valid remediation commands.
    5. Target only the root cause of the issue mentioned in <diagnostic_commands> and <verification_detailed_explanation>.
    6. Be very specific about the commands you propose and do not propose commands that are not related to the incident.
    7. Use examples in <examples> to understand how to propose commands.
    </objectives>

    <output_format>
    {{
        "commands": [
            {{
                "command": "command to execute",
                "interpretation": "the purpose of the command, how the command will fix the incident"
            }}
        ]
    }}
    </output_format>

    <remediation_instructions>
    1. When proposing make sure you are very specific and target strictly the root cause of the issue. Using unique identifiers like pid, query id, etc.
    2. Use only unique identifiers to make sure not to harm other processes, services, queries, functions, procedures, etc.
    3. If the solution requires multiple commands, propose a sequence of commands that will fix the issue, connect with separator valid for execution platform. 
    4. It is especially important for databases as they are very sensitive to the commands executed on them. Don't use selects with where clause with too wide range of possible results, use only specific identifiers.
    5. You might be forced to kill a process with kill, pkill, killall, or similar commands. Be very specific about the process you want to kill. Use process name, pid, or other unique identifiers.
    5. You might be forced to stop a service with systemctl stop, service stop, or similar commands. Be very specific about the service you want to stop. Use service name, pid, or other unique identifiers.
    6. You might be forced to limit the CPU usage of a specific process with cpulimit, or similar commands. Be very specific about the process you want to limit the CPU usage. Use process name, pid, or other unique identifiers.
    7. You might be forced to delete old logs with rm, or similar commands. Be very specific about the logs you want to delete. Use log file name, log file path, or other unique identifiers.
    8. You might be forced to remove unused Docker data with docker system prune, or similar commands. Be very specific about the Docker data you want to delete. Use Docker container name, Docker container id, or other unique identifiers.
    9. Stop the database queries, functions, procedures, etc. that are causing the issue on the database. Be very specific about the queries, functions, procedures, etc. you want to stop. Use query id, pid or other unique identifiers.
    10. Propose commands that are safe and will not harm the system.
    11. Do not propose commands that are not related to the incident.
    12. Do not propose destructive actions unless absolutely necessary and justified.
    13. Focus on minimal impact and maximum recoverability.
    14. Make sure the selected command matches the platform. Meaning the command can be directly executed on the platform.
    </remediation_instructions>

    <final_interpretation_verdict>
    {final_interpretation_verdict}
    </final_interpretation_verdict>
    <final_interpretation>
    {final_interpretation}
    </final_interpretation>
    <diagnostic_commands>
    {diagnostic_commands}
    </diagnostic_commands>
    <incident_description>
    {incident_description}
    </incident_description>
    <runtime_description>
    {runtime_description}
    </runtime_description>

    <examples>
    {{
        "commands": [
            {{
                "command": "SELECT pg_cancel_backend(113024); SELECT pg_cancel_backend(113029); SELECT pg_cancel_backend(113032); SELECT pg_cancel_backend(113035)",
                "interpretation": "These commands will cancel the currently active and resource-intensive queries identified by their process IDs, thereby reducing the high CPU usage caused by the queries."
            }},
            {{
                "command": "kill -9 1234",
                "interpretation": "This command will kill the process with the given process ID, thereby stopping the resource-intensive process."
            }}
        ]
    }}
    </examples>
    """

PLATFORM_SELECTION_PROMPT = """

    Given the command in the <command> tag, select the most appropriate platform from the list of platforms in the <platforms> tag.

    <objectives>
    1. Select the most appropriate platform from the list of platforms in the <platforms> tag.
    2. Use your reasoning to carefully consider which platform is most appropriate for the command.
    3. Output only a JSON object in the format: {{"platform": "platform1"}}
    4. Do not provide explanations, justifications, or any additional commentary outside the JSON object.
    5. Use the command in the <command> tag to generate the platform.
    6. Database commands like select, update, delete, insert, alter etc. are run on a database server like PostgreSQL, MySQL, etc.
    </objectives>

    <command>
    {command}
    </command>

    <platforms>
    {platforms}
    </platforms>
    """

class PlatformSelection(BaseModel):
    platform: ExecutionPlatformType

class RemediatorTool:


    def __init__(self, llm, recommendation_prompt=RECOMMENDATION_PROMPT, remediation_prompt=REMEDIATION_PROMPT):
        self.llm = llm
        self.llm_with_processed_commands = self.llm.with_structured_output(
            ProcessedCommands, method="function_calling"
        )
        self.recommendation_prompt = recommendation_prompt
        self.remediation_prompt = remediation_prompt
        self.llm_platform_selection = llm.with_structured_output(PlatformSelection)


    def generate_recommendations(self, incident_description: str, environment_description: str, interpretation_result: InterpretationResult):
        formatted_prompt=self.recommendation_prompt.format(
            final_interpretation_verdict=interpretation_result.final_interpretation_verdict,
            final_interpretation=interpretation_result.final_interpretation,
            diagnostic_commands=interpretation_result.commands,
            incident_description=incident_description,
            runtime_description=environment_description
        )

        return self.llm.invoke(formatted_prompt).content
    
    def generate_remediation_commands(self, incident_description: str, environment_description: str, interpretation_result: InterpretationResult):
        formatted_prompt=self.remediation_prompt.format(
            final_interpretation_verdict=interpretation_result.final_interpretation_verdict,
            final_interpretation=interpretation_result.final_interpretation,
            diagnostic_commands=interpretation_result.commands,
            incident_description=incident_description,
            runtime_description=environment_description
        )

        processed_commands = self.llm_with_processed_commands.invoke(formatted_prompt).commands
        for command in processed_commands:
            command.platform = self.llm_platform_selection.invoke(PLATFORM_SELECTION_PROMPT.format(command=command.command, platforms=", ".join([c.value for c in ExecutionPlatformType]))).platform

        resetted_commands = []
        for command in processed_commands:
            resetted_commands.append(ProcessedCommand(command=command.command, platform=command.platform, interpretation=command.interpretation))
        return resetted_commands
