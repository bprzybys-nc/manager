
import os
from typing import List

from tavily import TavilyClient

from src.modules.tools.data_objects import ProcessedCommand, ProcessedCommands, ExecutionPlatformType
from pydantic import BaseModel
#tavily-python 0.7.2


QUERY_SUGGESTION_PROMPT = """
Given the following incident description in tag <incident_description> and runtime environment in tag <runtime_environment>, generate one concise and specific sentence question for diagnostic queries that could help identify the root cause or contributing factors of the incident. 

Follow the objectives defined in tag <objectives>.

Do not rush with a solution. Take your time and think step by step.

<objectives>
1. Generate a concise and specific sentence question for diagnostic queries that could help identify the root cause or contributing factors of the incident.
2. The question should be specific to the incident and the runtime environment and it is short with maximum 20 words.
3. Follow the examples provided in tag <examples>.
4. The question should be general not specific to the incident and runtime environment. It should not contain any specific names or values.
5. use incident description in the tag <incident_description> and runtime environment in the tag <runtime_environment> to generate the question.
</objectives>

<incident_description>
{incident_description}
</incident_description>

<runtime_environment>
{runtime_environment}
</runtime_environment>

<examples>
    <example>
    What diagnostic queries would help identify which transactions or queries are causing high CPU usage ubuntu server?
    </example>
    <example>
    What diagnostic queries would help identify which transactions or queries are causing lock contention on the PostgreSQL server?
    </example>
    <example>
    What diagnostic queries would help identify which transactions or queries are causing slow queries on the PostgreSQL server?
    </example>
    <example>
    What diagnostic queries would help identify which transactions or queries are causing high CPU usage on the PostgreSQL server?
    </example>
</examples>
"""

COMMAND_GENERATION_PROMPT = """
Given the raw web page content inside the <web_content> tag, generate a list of useful and logically inferred commands a technical user might want to run based on the content.

Follow the objectives outlined in the <objectives> tag.

<objectives>
1. Your main goal is to generate commands that can be run in a terminal, database, or system console.
2. The command should be used to diagnose the incident described in the <incident_description> tag.
3. The command should not modify or damage the system. 
4. The command should be safe to run.
5. No command should be destructive or delete data.
6. The command should be able to run in the runtime environment described in the <runtime_environment> tag.
7. Output only a JSON list in the format: {{"commands": [{{"command": "command1"}}, {{"command": "command2"}}]}}
8. Avoid redundant or ambiguous commands. Only include well-formed, actionable commands.
9. Do not include commentary or explanations outside the JSON list.
10. Focus on the commands which can solve the incident described in the <incident_description> tag.
11. Use the incident description in the <incident_description> tag and runtime environment in the <runtime_environment> tag to generate the commands.
</objectives>

<web_content>
{web_content}
</web_content>

<incident_description>
{incident_description}
</incident_description>

<runtime_environment>
{runtime_environment}
</runtime_environment>

<examples>
    <example>
    {{"commands": [
        {{"command": "top -b|head -n 10"}}, 
        {{"command": "ps aux --sort=-%cpu | head -n 10"}}
    ]}}
    </example>
    <example>
    {{"commands": [
        {{"command": "SELECT relname, n_dead_tup FROM pg_stat_user_tables WHERE n_dead_tup > 1000 ORDER BY n_dead_tup DESC LIMIT 5"}}, 
        {{"command": "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total_size FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 5;"}}
    ]}}
    </example>
</examples>
"""

TOP_COMMANDS_PROMPT = """
Given the <incident_description>, <runtime_environment>, and the list of diagnostic <candidate_commands>, select the {max_results} most relevant and safe-to-run commands that are most likely to help identify the root cause or contributing factors of the incident.

Follow the objectives defined in the <objectives> tag.

<objectives>
1. Select the {max_results} most relevant diagnostic commands that align with the given incident description and runtime environment.
2. Use your reasoning to carefully consider which commands provide the most insight. Consider how well each command aligns with the type of incident and the characteristics of the runtime environment.
3. Output only a JSON object in the format: {{"commands": [{{"command": "command1"}}, {{"command": "command2"}}, {{"command": "command3"}}, {{"command": "command4"}}, {{"command": "command5"}}]}}
4. Do not provide explanations, justifications, or any additional commentary outside the JSON object.
5. Use the incident description in the <incident_description> tag and runtime environment in the <runtime_environment> tag to generate the commands.
</objectives>

<incident_description>
{incident_description}
</incident_description>

<runtime_environment>
{runtime_environment}
</runtime_environment>

<candidate_commands>
{candidate_commands}
</candidate_commands>
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

class WebExtractor:
    def __init__(self,llm):
        tavily_token = os.getenv("TAVILY_TOKEN")
        self.client = TavilyClient(tavily_token)
        self.llm = llm
        self.llm_command_generator = llm.with_structured_output(ProcessedCommands)
        self.llm_platform_selection = llm.with_structured_output(PlatformSelection)


    def find_commands(self, incident_description: str, runtime_description: str,max_results:int=5):
        web_search_query = self._create_web_search_query(incident_description, runtime_description)
        response = self.client.search(
            query=web_search_query,
            max_results=3,
            include_raw_content=True
        )
        commands=[]
        for result in response["results"]:
            content=result["raw_content"]
            formatted_prompt = COMMAND_GENERATION_PROMPT.format(web_content=content, incident_description=incident_description, runtime_environment=runtime_description)
            new_commands = self.llm_command_generator.invoke(formatted_prompt)
            commands.extend(new_commands.commands)

        top_commands = self._select_top_commands(incident_description, runtime_description, commands, max_results)
        for command in top_commands:
            self._select_platform(command)
    
        resetted_commands = []
        for command in top_commands:
            resetted_commands.append(ProcessedCommand(command=command.command, platform=command.platform))
        return resetted_commands
    
    def _select_platform(self, command: ProcessedCommand):
        formatted_prompt = PLATFORM_SELECTION_PROMPT.format(command=command.command, platforms=", ".join([c.value for c in ExecutionPlatformType]))
        platform_selection = self.llm_platform_selection.invoke(formatted_prompt)
        command.platform = platform_selection.platform.value
       
    def _select_top_commands(self, incident_description: str, runtime_description: str, candidate_commands: List[ProcessedCommand], max_results: int=5):
        formatted_prompt = TOP_COMMANDS_PROMPT.format(incident_description=incident_description, runtime_environment=runtime_description, candidate_commands=candidate_commands, max_results=max_results)
        response = self.llm_command_generator.invoke(formatted_prompt)
        return response.commands

    def _create_web_search_query(self, incident_description: str, runtime_description: str):
        formatted_prompt = QUERY_SUGGESTION_PROMPT.format(incident_description=incident_description, runtime_environment=runtime_description)
        response = self.llm.invoke(formatted_prompt)
        return response.content

    


 