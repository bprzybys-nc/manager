

from typing import  Sequence, List

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from src.modules.tools.data_objects import ProcessedCommand, SourceIdentificationResult, VerificationResult


class SourceIdentificationInputState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


class SourceIdentificationOutputState(TypedDict):
    source_identification_result: SourceIdentificationResult


class SourceIdentificationAgentState(SourceIdentificationInputState, SourceIdentificationOutputState):
    pass


class SourceIdentificationTool:

    SOURCE_IDENTIFICATION_PROMPT = """
    You are a incident source identification engine. Your task is to analyze the incident description, runtime environment, and diagnostic commands and determine the sources of the incident.

    You are given four input tags:
    <objectives>: Describe your main goals.
    <incident_description>: Describes the reported issues or symptoms observed.
    <runtime_description>: Describes the current runtime environment or context.
    <diagnostic_commands>: A list of diagnostic commands that were executed to diagnose the incident.
    <verification_result>: A list of verification results from the diagnostic commands.
    <output_format>: Instructions or constraints that must be followed when identifying the sources.
    <examples>: Some examples of how the output of your work should look like.

    <objectives>
    1. Don't question the incident validity or the correctness of the diagnosis results. Focus on identifying the sources of the incident.
    2. Based on the diagnosis results, extract and list all relevant sources contributing to the incident. For each source, provide:
        - A classification into one of the predefined source types: "postgres", "mysql", "redshift", "oracle", "sql_server", "dynamo_db", "java", or "other".
        - A short description of the source that clearly explains its role in the incident.
        - The unique identifier (e.g., PID, connection ID, etc.) for traceability.

    3. When identifying sources:
        - Process-based sources: Capture process name, PID, resource usage, and the user.
        - Service-based sources: Capture service name, version if available, and behavior.
        - Query-based sources: Capture database name, user, and operation (e.g., SELECT, INSERT).
        - Hardware-related processes: Capture associated device/process/resource.

    4. If no relevant sources can be extracted from the available data, the list of sources should be empty.
    5. Avoid speculation. Only include sources that can be *directly* inferred from the provided command outputs.
    6. Be comprehensive: if multiple sources are present, list *all* of them individually. Do not group multiple processes under a single entry unless they are identical in behavior and characteristics.
    7. Descriptions should be precise, technically accurate, and use clear terminology, avoiding vague terms like "something wrong" or "some process".
    8. You should take into account the incident description in the tag <incident_description>, the runtime description in the tag <runtime_description>, the diagnostic commands in the tag <diagnostic_commands> and the verification result in the tag <verification_result>.
    9. Focus strictly on the true sources of the incident. Do not include any other sources that are not directly related to the incident, but are listed in the <diagnostic_commands> or <verification_result>.
    </objectives>

    <output_format>
    {
        "sources":[
            {
                "source_type": "postgres" | "mysql" | "redshift" | "oracle" | "sql_server" | "dynamo_db" | "java" | "other",
                "source_description": "Short description of the source",
                "source_id": "Unique identifier for the source"
            }
        ]
    }
    </output_format>

    <examples>
    Example 1:
    {
        "sources": [
            {
                "source_type": "postgres",
                "source_description": "PostgreSQL 14 process running SELECT query on database 'mydbname'",
                "source_id": "1030224"
            },
            {
                "source_type": "postgres",
                "source_description": "PostgreSQL 14 process running SELECT query on database 'mydbname'",
                "source_id": "1030228"
            },
            {
                "source_type": "postgres",
                "source_description": "PostgreSQL 14 process running SELECT query on database 'mydbname'",
                "source_id": "1030230"
            },
            {
                "source_type": "postgres",
                "source_description": "PostgreSQL 14 process running SELECT query on database 'mydbname'",
                "source_id": "1030229"
            }
        ]
    }
    Example 2:
    {
        "sources": [
            {
                "source_type": "other",
                "source_description": "Simulation process started by stress-ng.",
                "source_id": "78786"
            }
        ]
    }
    </examples>

    Do not rush with a solution. Take your time and think step by step.
    """

    def __init__(self, llm, prompt=SOURCE_IDENTIFICATION_PROMPT):
        self.llm = llm.with_structured_output(
            SourceIdentificationResult, method="function_calling"
        )
        self.prompt = prompt
        self.graph = self._build()

    def _build(self):
        graph_builder = StateGraph(
            SourceIdentificationAgentState,
            input=SourceIdentificationInputState,
            output=SourceIdentificationOutputState,
        )

        def source_identification(state):
            return {"source_identification_result": self.llm.invoke(state["messages"])}

        graph_builder.add_node("source_identification", source_identification)
        graph_builder.add_edge(START, "source_identification")
        graph_builder.add_edge("source_identification", END)

        return graph_builder.compile()

    def run(
        self,
        incident_description: str,
        environment_description: str,
        diagnostic_commands: List[ProcessedCommand],
        verification_result: VerificationResult,
    ):

        input_data = "Identify the source of the following incident:\n"
        input_data += (
            f"<incident_description>{incident_description}</incident_description>\n"
        )
        input_data += (
            f"<runtime_description>{environment_description}</runtime_description>\n"
        )
        input_data += (
            f"<diagnostic_commands>{diagnostic_commands}</diagnostic_commands>"
        )
        input_data += (
            f"<verification_result>{verification_result}</verification_result>"
        )

        inputs = {
            "messages": [
                SystemMessage(content=self.prompt),
                HumanMessage(content=input_data),
            ]
        }
        output = self.graph.invoke(inputs)["source_identification_result"]
        return output