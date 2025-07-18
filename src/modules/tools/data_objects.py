from typing import Optional, List, Dict
from enum import Enum

from pydantic import BaseModel

class Verdict(Enum):
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INCONCLUSIVE = "INCONCLUSIVE"

class CredentialsStoreType(str,Enum):
    AZURE_KEYVAULT = "azure_keyvault"
    AWS_SECRET_MANAGER = "aws_secret_manager"

class DatabaseType(str,Enum):
    COSMOS_MONGO = "cosmos_mongo"
    MONGODB = "mongodb"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    REDSHIFT = "redshift"
    ORACLE = "oracle"
    SQL_SERVER = "sql_server"
    DYNAMO_DB = "dynamo_db"

class SourceType(str,Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    REDSHIFT = "redshift"
    ORACLE = "oracle"
    SQL_SERVER = "sql_server"
    DYNAMO_DB = "dynamo_db"
    JAVA = "java"
    OTHER = "other"

class ExecutionPlatformType(str,Enum):
    LINUX = "linux"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    REDSHIFT = "redshift"
    ORACLE = "oracle"
    SQL_SERVER = "sql_server"
    DYNAMO_DB = "dynamo_db"
    JAVA = "java"
    OTHER = "other"

class InterpretationVerdict(str,Enum):
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INCONCLUSIVE = "INCONCLUSIVE"

class ClassificationResult(BaseModel):
    execution_platform_list: List[ExecutionPlatformType]
    reason: str

class Metadata(BaseModel):
    server_id: Optional[str] = None
    database_uri: Optional[str] = None
    database_type: Optional[DatabaseType] = None
    credentials_store_type: Optional[CredentialsStoreType] = None
    credentials: Optional[Dict] = None
    other: Optional[Dict] = None

class SourceIdentification(BaseModel):
    source_type: SourceType
    source_description: str
    source_id: str

class SourceIdentificationResult(BaseModel):
    sources: List[SourceIdentification]


class VerificationResult(BaseModel):
    """
    A formatter for the response from the agent.
    """

    verdict: Verdict
    explanation: str
    detailed_explanation: str



class ProcessedCommand(BaseModel):
    """
    A processed command with its result, risk, and human confirmation.
    """

    command: str
    result: Optional[str] = None
    platform: Optional[str] = None
    risk: Optional[str] = None
    risk_justification: Optional[str] = None
    human_confirmation: Optional[str] = None
    interpretation: Optional[str] = None
    interpretation_verdict: Optional[InterpretationVerdict] = None
    id: Optional[str] = None

    

class ProcessedCommands(BaseModel):
    """
    A formatter for the response from the agent.
    """

    commands: List[ProcessedCommand]


class InterpretationResult(BaseModel):
    """
    A formatter for the response from the agent.
    """
    commands: List[ProcessedCommand]
    final_interpretation: str
    final_interpretation_verdict: InterpretationVerdict