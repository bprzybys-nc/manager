from typing import List, Sequence, Optional
from enum import Enum
import os

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from src.modules.tools.data_objects import ProcessedCommand, ProcessedCommands, VerificationResult, ExecutionPlatformType
from src.tools.verification_tool.main import VerificationTool
from src.tools.source_identification.main import SourceIdentificationTool
from src.tools.interpretation.main import InterpretationTool
from src.tools.classifier.main import IncidentClassifier
from src.tools.web_extractor.main import WebExtractor
from src.llm import LLMUtils


class DiagnosticInputState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class DiagnosticOutputState(TypedDict):
    processed_commands: ProcessedCommands

class DiagnosticAgentState(DiagnosticInputState, DiagnosticOutputState):
    pass

class DiagnosticTool:

    def __init__(self, llm):
        self.llm = llm.with_structured_output(
            ProcessedCommands, method="function_calling"
        )
        self.llm_utils = LLMUtils(self.llm)
        self.verification_tool = VerificationTool(llm)
        self.source_identification_tool = SourceIdentificationTool(llm)
        self.interpretation_tool = InterpretationTool(llm)
        self.classifier = IncidentClassifier(llm)
        self.graph = self._build()
        self.web_extractor = WebExtractor(llm)
 
    def incident_source_identification(self, incident_description: str, environment_description: str, diagnostic_commands: List[ProcessedCommand], verification_result:VerificationResult):
        return self.source_identification_tool.run(incident_description, environment_description, diagnostic_commands, verification_result)
    
    def classify_incident(self, incident_description: str, environment_description: str, diagnostic_commands: List[ProcessedCommand], diagnostic_interpretation: str):
        return self.classifier.classify(incident_description, environment_description, diagnostic_commands, diagnostic_interpretation)

    def advanced_diagnose_incident(self, incident_description: str, environment_description: str):
        commands = self.web_extractor.find_commands(incident_description, environment_description)

        print(f"Web Extractor Commands:")
        for command in commands:
            print(f"  {command}")
        print("--------------------------------")
        return commands

    def diagnose_incident(
        self,
        execution_platform: ExecutionPlatformType,
        incident_description: str,
        environment_description: str,
        previously_processed_commands: List[ProcessedCommand] = []
    ):

        input_data = "Execute the diagnostics for the following incident:\n"
        input_data += (
            f"<incident_description>{incident_description}</incident_description>\n"
        )
        input_data += (
            f"<runtime_description>{environment_description}</runtime_description>\n"
        )
        input_data += (
            f"<previous_commands>{previously_processed_commands}</previous_commands>\n"
        )

        prompt = self._get_prompt(execution_platform) 
        inputs = {
            "messages": [
                SystemMessage(content=prompt),
                HumanMessage(content=input_data),
            ]
        }
        return self.graph.invoke(inputs)["processed_commands"]
    
    def judge_incident_validity(
        self,
        incident_description: str,
        environment_description: str,
        previously_processed_commands: List[ProcessedCommand] = []
    ):  
        return self.verification_tool.run(incident_description, environment_description, previously_processed_commands)
      
    def incident_interpretation(
        self,
        incident_description: str,
        environment_description: str,
        processed_commands: List[ProcessedCommand] = []
    ):
        return self.interpretation_tool.run(incident_description, environment_description, processed_commands)

    def _build(self):
        graph_builder = StateGraph(
            DiagnosticAgentState,
            input=DiagnosticInputState,
            output=DiagnosticOutputState,
        )

        def diagnostic(state):
            return {"processed_commands": self.llm_utils.secure_llm_call(state["messages"])}
        
        graph_builder.add_node("diagnostic", diagnostic)
        graph_builder.add_edge(START, "diagnostic")
        graph_builder.add_edge("diagnostic", END)

        return graph_builder.compile()
    
    def _get_prompt(self, execution_platform: ExecutionPlatformType):
        module_location=os.path.dirname(os.path.abspath(__file__))
        with open(f"{module_location}/prompts/main.txt") as f:
            prompt_body = f.read()
        with open(f"{module_location}/prompts/{execution_platform.value}_examples.txt") as f:
            prompt_examples = f.read()
        with open(f"{module_location}/prompts/{execution_platform.value}_role.txt") as f:
            prompt_role = f.read()

        return prompt_role + '\n' + prompt_body + '\n' + prompt_examples