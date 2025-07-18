
import os
from typing import List, Optional
import uuid

import requests
import src.llm as llm
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict

from src.modules.tools.data_objects import ProcessedCommand, ClassificationResult, InterpretationResult
from src.modules.tools.data_objects import InterpretationVerdict
from src.tools.db_servers_cmdb.app.db import Metadata
from src.tools.diagnostic.main import DiagnosticTool, ExecutionPlatformType
from src.tools.remediator.main import RemediatorTool

from src.tools.communication.app.slack import SlackFormatting


class DBIncidentAssistantInput(TypedDict):
    incident_id: str
    instance_id: str
    hostname: str
    incident_description: str
    host_description: str
    slack_thread_id: str

class DBIncidentAssistantOutput(TypedDict):
    output: str

class DBIncidentAssistantState(DBIncidentAssistantInput, DBIncidentAssistantOutput):
    metadata: Metadata
    metadata_error_code: str
    metadata_error_message: str
    diagnostic_commands: List[ProcessedCommand]
    classification_results: List[ClassificationResult]
    interpretation_results: List[InterpretationResult]
    remediation_commands: List[ProcessedCommand]


class OutboundCommunication():

    def __init__(self):
        self.db_assistant_response_endpoint = os.getenv("DB_INCIDENT_ASSISTANT_RESPONSE_ENDPOINT")
        self.cmd_exec_endpoint = os.getenv("CMD_EXEC_ENDPOINT")
        self.communication_endpoint = os.getenv("COMMUNICATION_ENDPOINT")
        self.manager_endpoint = os.getenv("MANAGER_ENDPOINT")

    def execute_commands(self, incident_id: str, instance_id: str, processed_commands: List[ProcessedCommand]):

        command_types=[]

        processed_commands_json=[]
        for command in processed_commands:
            processed_commands_json.append(command.model_dump())
            command_type="shell"
            if command.platform=="postgres":
                command_type="psql"
            command_types.append(command_type)
            
        json_data={"incident_id": incident_id, "instance_id": instance_id, "commands": processed_commands_json, "response_endpoint": self.db_assistant_response_endpoint,"command_types": command_types}
        print(f"Executing commands: {json_data}")
        response = requests.post(self.cmd_exec_endpoint+"/executions", json=json_data)
        if response.status_code == 200:
            return response.json()
        else:
            return None
        
    def send_question(self, question: str, slack_thread_id: str,command_id: str):
        print(f"[Outbound communication] Sending question for thread {slack_thread_id}: {question}")
        json_data={"question": question, "thread_id": slack_thread_id,"command_id": command_id}

        response = requests.post(self.communication_endpoint+"/questions", json=json_data)
        return response.json()
        
    def send_status_update(self, message: str, formatting: Optional[SlackFormatting] = None,  slack_thread_id: Optional[str]=None):
        print(f"[Outbound communication] Sending status update for thread {slack_thread_id}: {message}")
        json_data={"message": message}
        if formatting is not None:
            json_data["formatting"] = formatting.value
        if slack_thread_id is not None:
            json_data["thread_id"] = slack_thread_id
        response = requests.post(self.communication_endpoint+"/messages", json=json_data)
        thread_id=None
        try:
            print(f"Communication response: {response}")
            message=response.json()["message"]
            thread_id=response.json()["thread_id"]
        except Exception as e:
            print(f"Error sending status update: {e}")
            return None
        return thread_id
    
    def close_incident(self, incident_id: str):
        print(f"Closing incident: {incident_id}")
        print(f"URL: {self.manager_endpoint}/incidents/{incident_id}/status/closed")
        response = requests.put(f"{self.manager_endpoint}/incidents/{incident_id}/status/closed")
        print(f"Incident closed: {response}")


class DBIncidentAssistant:
    def __init__(self):
        self.graph = self._build()
        self.diagnostic_tool = DiagnosticTool(llm.llm)
        self.remediator_tool = RemediatorTool(llm.llm)
        self.outbound_communication = OutboundCommunication()

    def _build(self):
        checkpointer = MemorySaver()
        graph_builder = StateGraph(DBIncidentAssistantState, input=DBIncidentAssistantInput, output=DBIncidentAssistantOutput)


        #graph_builder.add_node("get_metadata", self._get_metadata)
        graph_builder.add_node("classify_incident", self._classify_incident)
        graph_builder.add_node("generate_diagnostic", self._generate_diagnostic)
        graph_builder.add_node("execute_diagnostic", self._execute_diagnostic)
        graph_builder.add_node("wait_for_diagnostic_execution", self._wait_for_diagnostic_execution)
        graph_builder.add_node("trigger_commands_interpretation", self._trigger_commands_interpretation)
        graph_builder.add_node("generate_recommendations", self._generate_recommendations)
        graph_builder.add_node("generate_remediation_commands", self._generate_remediation_commands)
        graph_builder.add_node("close_incident", self._close_incident)
        graph_builder.add_node("wait_for_remediation_command_execution", self._wait_for_remediation_command_execution)

        graph_builder.add_edge(START, "classify_incident")
        #graph_builder.add_edge(START, "generate_remediation_commands")
        #graph_builder.add_conditional_edges("get_metadata",self._check_metadata_error)
        graph_builder.add_edge("classify_incident", "generate_diagnostic")
        graph_builder.add_edge("generate_diagnostic", "execute_diagnostic")
        graph_builder.add_edge("execute_diagnostic", "wait_for_diagnostic_execution")
        graph_builder.add_edge("wait_for_diagnostic_execution", "trigger_commands_interpretation")
        graph_builder.add_conditional_edges("trigger_commands_interpretation", self._additional_diagnostic_needed)
        graph_builder.add_edge("generate_recommendations", "generate_remediation_commands")
        graph_builder.add_edge("generate_remediation_commands", "wait_for_remediation_command_execution")
        graph_builder.add_edge("wait_for_remediation_command_execution", "close_incident")
        graph_builder.add_edge("close_incident", END)  



        return graph_builder.compile(checkpointer=checkpointer)
    
    def _generate_remediation_commands(self, state: DBIncidentAssistantState):
        interpretation_results=state["interpretation_results"]
        interpretation_result=interpretation_results[-1]

        confirmed_commands = list(filter(lambda x: x.interpretation_verdict == InterpretationVerdict.CONFIRMED, state["diagnostic_commands"]))
        interpretation_result.commands=confirmed_commands

        remediation_commands = self.remediator_tool.generate_remediation_commands(state["incident_description"], "", interpretation_result)
        for command in remediation_commands:
            command.id=str(uuid.uuid4())
        state["remediation_commands"] = remediation_commands

        self.outbound_communication.send_status_update(f"Remediation commands:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
        for remediation in remediation_commands:
            correlation_id=f"{state['incident_id']}_id_{remediation.id}"
            self.outbound_communication.send_status_update(f"{remediation.command} ({remediation.platform})",formatting=SlackFormatting.CODE,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_question("Do you want to execute this command?",state["slack_thread_id"],correlation_id)
            self.outbound_communication.send_status_update(f"Interpretation: {remediation.interpretation}\n",slack_thread_id=state["slack_thread_id"])

        self.outbound_communication.send_status_update(f"\n\n\n",slack_thread_id=state["slack_thread_id"])
        return state
    
    def temp_generate_remediation_commands(self, state: DBIncidentAssistantState):
        slack_thread_id=self.outbound_communication.send_status_update(f"New incident")
        state["slack_thread_id"]=slack_thread_id
        remediation_commands =[ProcessedCommand(command="select 1", platform="postgres", interpretation="Positive interpretation", interpretation_verdict=InterpretationVerdict.CONFIRMED),ProcessedCommand(command="ls -l", platform="linux", interpretation="Positive interpretation", interpretation_verdict=InterpretationVerdict.CONFIRMED)]
        for command in remediation_commands:
            command.id=str(uuid.uuid4())
        state["remediation_commands"] = remediation_commands
        
        for remediation in remediation_commands:
            correlation_id=f"{state['incident_id']}_id_{remediation.id}"
            self.outbound_communication.send_status_update(f"{remediation.command} ({remediation.platform})",formatting=SlackFormatting.CODE,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_question("Do you want to execute this command?",state["slack_thread_id"],correlation_id)
            self.outbound_communication.send_status_update(f"Interpretation: {remediation.interpretation}\n",slack_thread_id=state["slack_thread_id"])

        return state
    
    def _wait_for_remediation_command_execution(self, state: DBIncidentAssistantState):
        print(f"Waiting for remediation command execution:")
        result=interrupt(state["remediation_commands"])
        for remediation in state["remediation_commands"]:
            for result_remediation in result:
                if remediation.id == result_remediation.id:
                    remediation.result = result_remediation.result
                    break   
                    
        print(f"Remediation command execution completed.")
        return state

    def commands_execuction_finished(self, incident_id: str, execution_results: dict):
        print(f"Command execution finished: {incident_id}")
        print(f"Execution results: {execution_results}")

        thread_config = {"configurable": {"thread_id": incident_id}}

        state=self.graph.get_state(thread_config)
        if state.created_at is None:
            print(f"State not found for incident: {incident_id}")
            return
        
        if "remediation_commands" in state[0]:
            print(f"Applying remedations commands state for incident: {incident_id}")
            remediation_commands=state[0]["remediation_commands"]
            self._apply_execution_results(remediation_commands, execution_results)
            print(f"Updating state with remediations...")
            self.graph.update_state(thread_config,{"remediation_commands": remediation_commands})
            self._check_remediation_finished(incident_id, remediation_commands,thread_config)

        else:
            print(f"Applying diagnostic commands state for incident: {incident_id}")
            self.graph.invoke(
                Command(resume=execution_results), config=thread_config
            )


    def remediation_command_execution_confirmed(self, correlation_id: str,approved: bool):

        incident_id=correlation_id.split("_id_")[0]
        remediation_command_id=correlation_id.split("_id_")[1]
        thread_config = {"configurable": {"thread_id": incident_id}}

        state=self.graph.get_state(thread_config)
        remediation_commands=state[0]["remediation_commands"]
        instance_id=state[0]["instance_id"]

        print(f"Remediation commands: {remediation_commands}")

        for remediation in remediation_commands:
            if remediation.id == remediation_command_id:
                print(f"Remediation command found: {remediation}")
                if remediation.result is not None:
                    print(f"Remediation command already executed: {remediation}")
                    return
                if not approved:
                    remediation.result="Rejected"
                    self.graph.update_state(thread_config,{"remediation_commands": remediation_commands})
                    self._check_remediation_finished(incident_id, remediation_commands,thread_config)
                else:
                    self.outbound_communication.execute_commands(incident_id, instance_id, [remediation])
                break

    def _check_remediation_finished(self, incident_id: str, remediation_commands: List[ProcessedCommand],thread_config: dict):
        all_commands_executed=True
        for remediation in remediation_commands:
            if remediation.result is None:
                all_commands_executed=False
                break
        if all_commands_executed:
            print(f"All remediation commands executed for incident: {incident_id}. Resuming state.")
            self.graph.invoke(
                Command(resume=remediation_commands), config=thread_config
            )


    def temp_generate_remediation_commands(self, state: DBIncidentAssistantState):
        interpretation_results=state["interpretation_results"]
        interpretation_result=interpretation_results[-1]

        confirmed_commands = list(filter(lambda x: x.interpretation_verdict == InterpretationVerdict.CONFIRMED, state["diagnostic_commands"]))
        interpretation_result.commands=confirmed_commands

        remediation_commands = self.remediator_tool.generate_remediation_commands(state["incident_description"], "", interpretation_result)
        self.outbound_communication.send_status_update(f"Remediation commands:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
        for remediation in remediation_commands:
            self.outbound_communication.send_status_update(f"{remediation.command} ({remediation.platform})",formatting=SlackFormatting.CODE,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_question("Do you want to execute this command?",state["slack_thread_id"],state["incident_id"],remediation.command,remediation.platform,state["instance_id"])
            self.outbound_communication.send_status_update(f"Interpretation: {remediation.interpretation}\n",slack_thread_id=state["slack_thread_id"])

        self.outbound_communication.send_status_update(f"\n\n\n",slack_thread_id=state["slack_thread_id"])
        return state
    
    def _generate_recommendations(self, state: DBIncidentAssistantState):
        interpretation_results=state["interpretation_results"]
        interpretation_result=interpretation_results[-1]

        confirmed_commands = list(filter(lambda x: x.interpretation_verdict == InterpretationVerdict.CONFIRMED, state["diagnostic_commands"]))
        interpretation_result.commands=confirmed_commands

        recommendations = self.remediator_tool.generate_recommendations(state["incident_description"], state["host_description"], interpretation_result)

        self.outbound_communication.send_status_update(f"Recommendations:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
        self.outbound_communication.send_status_update(f"{recommendations}\n",slack_thread_id=state["slack_thread_id"])

        self.outbound_communication.send_status_update(f"\n\n\n",slack_thread_id=state["slack_thread_id"])
        return state
    

    def _classify_incident(self, state: DBIncidentAssistantState):
        print(f"Classifying incident: {state['incident_description']}")

        if "diagnostic_commands" in state and "interpretation_results" in state:
            self.outbound_communication.send_status_update("Advanced incident classification:", formatting=SlackFormatting.BOLD, slack_thread_id=state["slack_thread_id"])
            commands=state["diagnostic_commands"]
            last_interpretation_result=state["interpretation_results"][-1]
            diagnostic_interpretation=f"Final interpretation verdict: {last_interpretation_result.final_interpretation_verdict}\nFinal interpretation: {last_interpretation_result.final_interpretation}\n"
        else:
            self.outbound_communication.send_status_update("Incident classification:", formatting=SlackFormatting.BOLD, slack_thread_id=state["slack_thread_id"])
            commands=[]
            diagnostic_interpretation=""

        classification_result = self.diagnostic_tool.classify_incident(state["incident_description"], state["host_description"], commands, diagnostic_interpretation)
        if "classification_results" not in state:
            state["classification_results"]=[]
        state["classification_results"].append(classification_result)
        print(f"Classification result: {classification_result}")
        self.outbound_communication.send_status_update(f"Based on the incident description and host description, the following execution platforms are considered:",slack_thread_id=state["slack_thread_id"])
        self.outbound_communication.send_status_update(f"{', '.join([elem.value for elem in classification_result.execution_platform_list])}",SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
        self.outbound_communication.send_status_update(f"The reason for the classification is:",slack_thread_id=state["slack_thread_id"])
        self.outbound_communication.send_status_update(f"{classification_result.reason}",SlackFormatting.ITALIC,slack_thread_id=state["slack_thread_id"])
        self.outbound_communication.send_status_update(f"Waiting for gathering diagnostic commands...",SlackFormatting.ITALIC,slack_thread_id=state["slack_thread_id"])
        return state
    
    def _close_incident(self, state: DBIncidentAssistantState):
        self.outbound_communication.close_incident(state["incident_id"])
        self.outbound_communication.send_status_update(f"Incident closed",formatting=SlackFormatting.ITALIC,slack_thread_id=state["slack_thread_id"])
        return state
    
    def _trigger_commands_interpretation(self, state: DBIncidentAssistantState):
        print(f"Triggering commands interpretation.")
        commands_to_interpret=[]
        for command in state["diagnostic_commands"]:
            if command.interpretation is None:
                commands_to_interpret.append(command)

        
        import time
        start_time = time.time()
        interpretation_result = self.diagnostic_tool.incident_interpretation(state["incident_description"], "", commands_to_interpret)
        execution_time = time.time() - start_time
        print(f"Interpretation execution time: {execution_time:.2f} seconds")

        self.outbound_communication.send_status_update(f"Interpretation results:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
        for interpreted_command in interpretation_result.commands:
            self.outbound_communication.send_status_update(f"Command:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_status_update(f"{interpreted_command.command} ({interpreted_command.platform})",formatting=SlackFormatting.CODE,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_status_update(f"Interpretation verdict: {interpreted_command.interpretation_verdict}",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_status_update(f"Interpretation:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_status_update(f"{interpreted_command.interpretation}\n",slack_thread_id=state["slack_thread_id"])
            for command_to_interpret in commands_to_interpret:
                if command_to_interpret.command == interpreted_command.command:
                    command_to_interpret.interpretation = interpreted_command.interpretation
                    command_to_interpret.interpretation_verdict = interpreted_command.interpretation_verdict
            
        self.outbound_communication.send_status_update(f"Final interpretation verdict: {interpretation_result.final_interpretation_verdict}",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
        self.outbound_communication.send_status_update(f"Final interpretation:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
        self.outbound_communication.send_status_update(f"{interpretation_result.final_interpretation}\n",slack_thread_id=state["slack_thread_id"])

        if "interpretation_results" not in state:
            state["interpretation_results"]=[]
        state["interpretation_results"].append(interpretation_result)
        self.outbound_communication.send_status_update(f"\n\n\n",slack_thread_id=state["slack_thread_id"])
        return state

    def _apply_execution_results(self,commands: List[ProcessedCommand], execution_results: dict):
        for command_body in execution_results.keys():
            for command in commands:
                if command.command == command_body:
                    command.result = execution_results[command_body]
                    if command.result is None:
                        command.result="No output"
                    command.interpretation=None
                    command.interpretation_verdict=None
                    
    def _wait_for_diagnostic_execution(self, state):
        if "diagnostic_commands" not in state:
            return state
        execution_results = interrupt(state["diagnostic_commands"])
        diagnostic_commands=state["diagnostic_commands"]
        self._apply_execution_results(diagnostic_commands, execution_results)


        self.outbound_communication.send_status_update(f"Command execution results:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
        for diagnostic_command in diagnostic_commands:
            self.outbound_communication.send_status_update(f"Command:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_status_update(f"{diagnostic_command.command} ({diagnostic_command.platform})",formatting=SlackFormatting.CODE,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_status_update(f"Output:",formatting=SlackFormatting.BOLD,slack_thread_id=state["slack_thread_id"])
            self.outbound_communication.send_status_update(f"{diagnostic_command.result}",formatting=SlackFormatting.CODE_BLOCK,slack_thread_id=state["slack_thread_id"])
                    
        self.outbound_communication.send_status_update(f"\n\n\n",slack_thread_id=state["slack_thread_id"])
        self.outbound_communication.send_status_update(f"Waiting for interpretation...",formatting=SlackFormatting.ITALIC,slack_thread_id=state["slack_thread_id"])  

        state["diagnostic_commands"] = diagnostic_commands
        return state
    
    def run(self, incident_id: str,instance_id: str,hostname: str,incident_description: str,host_description: str)->str:
        slack_thread_id=self.outbound_communication.send_status_update(f"New incident on {hostname}: {incident_description}")
        thread_config = {"configurable": {"thread_id": incident_id}}
        
        self.graph.invoke(
            {
                "incident_id": incident_id,
                "instance_id": instance_id,
                "hostname": hostname,
                "incident_description": incident_description,
                "host_description": host_description,
                "slack_thread_id": slack_thread_id
            },
            config=thread_config,
        ) 

        state=self.graph.get_state(thread_config)
        return "Run successfully"
    
    def _is_advanced_diagnostic_needed(self, state: DBIncidentAssistantState):
        if "interpretation_results" not in state:
            return False
        
        interpretation_results=state["interpretation_results"]
        if len(interpretation_results) == 1:
            last_interpretation_result=interpretation_results[-1]
            if last_interpretation_result.final_interpretation_verdict == InterpretationVerdict.INCONCLUSIVE or last_interpretation_result.final_interpretation_verdict == InterpretationVerdict.FALSE_POSITIVE:
                return True
        return False
    
    def _generate_diagnostic(self, state: DBIncidentAssistantState):

        use_advanced_diagnostic=self._is_advanced_diagnostic_needed(state)
        classification_results=state["classification_results"]
        last_classification_result=classification_results[-1]
        commands=[]
        for execution_platform in last_classification_result.execution_platform_list:
            if use_advanced_diagnostic:
                new_commands=self.diagnostic_tool.advanced_diagnose_incident(state["incident_description"], execution_platform.value)
            else:
                new_commands=self.diagnostic_tool.diagnose_incident(execution_platform,state["incident_description"], state["host_description"]).commands
                for command in new_commands:
                    command.platform=execution_platform.value
            commands.extend(new_commands)
   
        for command in commands:
            print(command)

        slack_thread_id=state["slack_thread_id"]
        if use_advanced_diagnostic:
            self.outbound_communication.send_status_update(f"Advanced diagnostic commands:",formatting=SlackFormatting.BOLD,slack_thread_id=slack_thread_id)
        else:
            self.outbound_communication.send_status_update(f"Diagnostic commands:",formatting=SlackFormatting.BOLD,slack_thread_id=slack_thread_id)
        for command in commands:
            self.outbound_communication.send_status_update(f"{command.command} ({command.platform})",formatting=SlackFormatting.CODE,slack_thread_id=slack_thread_id)

        self.outbound_communication.send_status_update(f"\n\n\n",slack_thread_id=slack_thread_id)
        self.outbound_communication.send_status_update(f"Waiting for execution...",formatting=SlackFormatting.ITALIC,slack_thread_id=slack_thread_id)
        state["diagnostic_commands"] = commands
        return state
    
    def _execute_diagnostic(self, state: DBIncidentAssistantState):
        print(f"Executing diagnostic commands:")
        commands_to_execute=[]
        for command in state["diagnostic_commands"]:
            if command.result is None:
                commands_to_execute.append(command)
        self.outbound_communication.execute_commands(state["incident_id"], state["instance_id"], commands_to_execute)
    
        return state
    
    def _additional_diagnostic_needed(self, state: DBIncidentAssistantState):
        if "interpretation_results" not in state:
            print("No interpretation results found. Closing incident.")
            return "close_incident"
        interpretation_results=state["interpretation_results"]
        if len(interpretation_results) == 1:
            last_interpretation_result=interpretation_results[-1]
            if last_interpretation_result.final_interpretation_verdict == InterpretationVerdict.INCONCLUSIVE or last_interpretation_result.final_interpretation_verdict == InterpretationVerdict.FALSE_POSITIVE:
                print(f"Additional diagnostic needed. Last interpretation result: {last_interpretation_result}")
                return "classify_incident"
        print("No additional diagnostic needed. Closing incident.")
        return "generate_recommendations"

    def _check_metadata_error(self, state: DBIncidentAssistantState):
        if 'metadata' in state:
            print("Metadata found")
            return "classify_incident"
        else:
            print("Metadata not found")
            if 'metadata_error_code' in state:
                print(f"Error code: {state['metadata_error_code']}")
            if 'metadata_error_message' in state:
                print(f"Error message: {state['metadata_error_message']}")
            return END

    def _get_metadata(self, state: DBIncidentAssistantState):
        server_id = state["hostname"]
        db_servers_cmdb_endpoint = os.getenv("DB_SERVERS_CMDB_ENDPOINT")
        response = requests.get(f"{db_servers_cmdb_endpoint}/metadata/{server_id}")
        if response.status_code == 200:
            metadata = Metadata(**response.json())
            state["metadata"] = metadata
        else:
            state["metadata_error_code"] = response.status_code
            state["metadata_error_message"] = response.text
        return state


