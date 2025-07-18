
import os
import sys

from typing import Optional, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.modules.tools.data_objects import ProcessedCommand, ClassificationResult, ExecutionPlatformType

from pydantic import BaseModel

from enum import Enum, auto

class IncidentClassifier:

    CLASSIFICATION_PROMPT = """
    You are a helpful assistant that classifies incidents into one of the following categories provided in <classification_categories>.

    Follow the following objectives provided in <objectives>.

    <objectives>
    - You task is to classify the incident into one or many of the categories based on the incident description, runtime description, previously processed commands, and diagnostic interpretation.
    - The incident description is tag <incident_description>.
    - The runtime description is tag <runtime_description>.
    - The previously processed commands are tag <previously_processed_commands>.
    - The diagnostic interpretation is tag <diagnostic_interpretation>.
    - The reason should be a short explanation of why the incident was classified into the given categories.
    - The reason should be no more than 100 characters.
    - The output should be a JSON object with the following fields: execution_platform_list: List[ExecutionPlatformType], reason: str
    - The examples of the output are provided in <examples>.
    - If previously processed commands defined in <previously_processed_commands> had the results and the interpretation which were incidating execution failure, then you should not again classify the incident into the same category and explain the reason in the reason field.
    </objectives>

    <examples>
    <example>
    {{
        "execution_platform_list": ["linux","postgres"],
        "reason": "The incident description mentions a Postgres database running on a Linux system."
    }}
    </example>
    <example>
    {{
        "execution_platform_list": ["linux"],
        "reason": "The incident description mentions a Linux system."
    }}
    </example>
    </examples>

    <classification_categories>
    {classification_categories}
    </classification_categories>

    <incident_description>
    {incident_description}
    </incident_description>

    <runtime_description>
    {runtime_description}
    </runtime_description>

    <previously_processed_commands>
    {previously_processed_commands}
    </previously_processed_commands>

    <diagnostic_interpretation>
    {diagnostic_interpretation}
    </diagnostic_interpretation>
    """

  
    def __init__(self, llm, prompt=CLASSIFICATION_PROMPT):
        self.llm = llm.with_structured_output(
            ClassificationResult, method="function_calling"
        )
        self.prompt = prompt


  
    def classify(self, incident_description: str, runtime_description: str, previously_processed_commands: List[ProcessedCommand], diagnostic_interpretation: str) -> str:
        formatted=self.prompt.format(incident_description=incident_description, 
                                     runtime_description=runtime_description,
                                     previously_processed_commands=previously_processed_commands, 
                                     diagnostic_interpretation=diagnostic_interpretation,
                                     classification_categories= ", ".join([c.value for c in ExecutionPlatformType]))


        response = self.llm.invoke(formatted)


        return response
    
      

