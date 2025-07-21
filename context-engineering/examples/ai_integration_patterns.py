"""
AI Integration Patterns - Manager Component Examples

This file demonstrates patterns for integrating AI capabilities within the
Ovora Manager component, focusing on Azure OpenAI, LangChain, and intelligent
automation patterns used throughout the Manager codebase.
"""

from typing import Dict, Any, List, Optional, Union, AsyncGenerator
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json
import os
from contextlib import asynccontextmanager

# LangChain and OpenAI imports
try:
    from langchain_openai import AzureChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
    from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
    from langchain.schema import BaseOutputParser
    from pydantic import BaseModel, Field, validator
except ImportError:
    # Fallback for when dependencies are not available
    class BaseModel:
        pass
    def Field(*args, **kwargs):
        pass

# Configure logging
logger = logging.getLogger(__name__)

class AITaskType(Enum):
    """Types of AI tasks in Manager component."""
    INCIDENT_ANALYSIS = "incident_analysis"
    CODE_ANALYSIS = "code_analysis"
    DECISION_SUPPORT = "decision_support"
    AUTOMATION = "automation"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"

@dataclass
class AIResponse:
    """Standard AI response structure."""
    success: bool
    content: str
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tokens_used: Optional[int] = None
    duration_ms: Optional[int] = None

# Azure OpenAI Configuration Pattern
class AzureOpenAIConfig:
    """
    Configuration pattern for Azure OpenAI integration.
    
    Based on patterns from:
    - src/llm/llm.py
    - Incident assistant implementations
    - Database workflow AI components
    """
    
    def __init__(
        self,
        api_key: str = None,
        api_version: str = "2024-02-15-preview",
        azure_endpoint: str = None,
        deployment_name: str = "gpt-4",
        temperature: float = 0.1,
        max_tokens: int = 2000,
        timeout: int = 30
    ):
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = api_version
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = deployment_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        if not self.api_key or not self.azure_endpoint:
            raise ValueError("Azure OpenAI API key and endpoint must be provided")
    
    def create_client(self) -> AzureChatOpenAI:
        """Create Azure OpenAI client with standard configuration."""
        return AzureChatOpenAI(
            azure_endpoint=self.azure_endpoint,
            azure_deployment=self.deployment_name,
            api_version=self.api_version,
            api_key=self.api_key,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout
        )

# Structured Output Patterns
class IncidentAnalysisOutput(BaseModel):
    """Structured output for incident analysis AI tasks."""
    severity: str = Field(..., description="Incident severity: low, medium, high, critical")
    category: str = Field(..., description="Incident category")
    root_cause: str = Field(..., description="Likely root cause analysis")
    recommended_actions: List[str] = Field(..., description="Recommended remediation actions")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    requires_human_review: bool = Field(..., description="Whether human review is needed")
    
    @validator('severity')
    def validate_severity(cls, v):
        valid_severities = ['low', 'medium', 'high', 'critical']
        if v.lower() not in valid_severities:
            raise ValueError(f"Severity must be one of {valid_severities}")
        return v.lower()

class CodeAnalysisOutput(BaseModel):
    """Structured output for code analysis AI tasks."""
    language_detected: str = Field(..., description="Programming language detected")
    code_quality_score: float = Field(..., ge=0.0, le=10.0, description="Code quality score")
    issues_found: List[str] = Field(default=[], description="List of issues found")
    suggestions: List[str] = Field(default=[], description="Improvement suggestions")
    security_concerns: List[str] = Field(default=[], description="Security concerns identified")
    complexity_assessment: str = Field(..., description="Complexity assessment: low, medium, high")

class DecisionSupportOutput(BaseModel):
    """Structured output for decision support AI tasks."""
    recommendation: str = Field(..., description="Primary recommendation")
    alternatives: List[str] = Field(default=[], description="Alternative options")
    pros_and_cons: Dict[str, List[str]] = Field(..., description="Pros and cons analysis")
    risk_assessment: str = Field(..., description="Risk level: low, medium, high")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence")
    required_resources: List[str] = Field(default=[], description="Resources needed for implementation")

# Base AI Service Pattern
class BaseAIService:
    """
    Base pattern for AI services in Manager component.
    
    Provides common functionality for:
    - Azure OpenAI client management
    - Prompt template handling
    - Response parsing and validation
    - Error handling and retries
    - Token usage tracking
    """
    
    def __init__(self, config: AzureOpenAIConfig, service_name: str):
        self.config = config
        self.service_name = service_name
        self.client = None
        self.token_usage = 0
        
    async def __aenter__(self):
        """Async context manager for resource management."""
        self.client = self.config.create_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources."""
        self.client = None
    
    async def _invoke_with_retry(
        self, 
        messages: List[Union[HumanMessage, SystemMessage]],
        max_retries: int = 3
    ) -> AIMessage:
        """Invoke AI with retry logic for resilience."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                start_time = datetime.now()
                
                response = await self.client.ainvoke(messages)
                
                # Track performance metrics
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self.token_usage += getattr(response, 'usage', {}).get('total_tokens', 0)
                
                logger.info(
                    f"{self.service_name} AI call succeeded",
                    extra={
                        "duration_ms": duration,
                        "attempt": attempt + 1,
                        "tokens": getattr(response, 'usage', {}).get('total_tokens', 0)
                    }
                )
                
                return response
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"{self.service_name} AI call failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise last_exception
    
    def create_system_prompt(self, role: str, context: str = None) -> SystemMessage:
        """Create standardized system prompt."""
        base_prompt = f"""You are an expert {role} working in the Ovora Manager system.
        
Your responsibilities:
- Provide accurate, actionable analysis
- Use structured output formats when specified
- Consider the context of the Manager component and its integration with Agent and UI components
- Prioritize reliability and safety in recommendations

Context: {context or 'General Manager system operations'}

Always provide clear reasoning for your conclusions and indicate your confidence level."""
        
        return SystemMessage(content=base_prompt)

# Incident Analysis Service
class IncidentAnalysisService(BaseAIService):
    """
    AI service for incident analysis and response recommendations.
    
    Based on patterns from:
    - src/modules/incident/assistant.py
    - Database incident workflows
    - Alert processing and classification
    """
    
    def __init__(self, config: AzureOpenAIConfig):
        super().__init__(config, "IncidentAnalysis")
        self.output_parser = PydanticOutputParser(pydantic_object=IncidentAnalysisOutput)
    
    async def analyze_incident(
        self,
        incident_data: Dict[str, Any],
        historical_context: List[Dict[str, Any]] = None
    ) -> AIResponse:
        """Analyze incident and provide structured recommendations."""
        
        # Prepare context
        context = f"""
        Current incident data:
        - Title: {incident_data.get('title', 'Unknown')}
        - Description: {incident_data.get('description', 'No description')}
        - Source: {incident_data.get('source', 'Unknown')}
        - Metrics: {json.dumps(incident_data.get('metrics', {}), indent=2)}
        - Timestamp: {incident_data.get('timestamp', 'Unknown')}
        """
        
        if historical_context:
            context += f"\n\nHistorical similar incidents:\n"
            for idx, hist in enumerate(historical_context[:3]):
                context += f"{idx + 1}. {hist.get('title', 'Unknown')}: {hist.get('resolution', 'No resolution')}\n"
        
        # Create messages
        system_message = self.create_system_prompt(
            "incident response specialist",
            "Analyzing system incidents and providing remediation guidance"
        )
        
        human_message = HumanMessage(content=f"""
        Analyze the following incident and provide structured analysis:
        
        {context}
        
        {self.output_parser.get_format_instructions()}
        
        Focus on:
        1. Accurate severity assessment
        2. Root cause identification
        3. Actionable remediation steps
        4. Risk assessment for similar future incidents
        """)
        
        try:
            # Get AI response
            response = await self._invoke_with_retry([system_message, human_message])
            
            # Parse structured output
            parsed_output = self.output_parser.parse(response.content)
            
            return AIResponse(
                success=True,
                content=json.dumps(parsed_output.dict(), indent=2),
                confidence=parsed_output.confidence_score,
                reasoning="AI analysis of incident data with historical context",
                metadata={
                    "incident_id": incident_data.get('id'),
                    "severity": parsed_output.severity,
                    "category": parsed_output.category,
                    "requires_review": parsed_output.requires_human_review
                }
            )
            
        except Exception as e:
            logger.error(f"Incident analysis failed: {e}")
            return AIResponse(
                success=False,
                content=f"Analysis failed: {str(e)}",
                metadata={"error": str(e)}
            )

# Code Analysis Service
class CodeAnalysisService(BaseAIService):
    """
    AI service for code analysis and quality assessment.
    
    Used in:
    - GraphMCP workflow code analysis
    - Database decommissioning code review
    - Pattern discovery in repositories
    """
    
    def __init__(self, config: AzureOpenAIConfig):
        super().__init__(config, "CodeAnalysis")
        self.output_parser = PydanticOutputParser(pydantic_object=CodeAnalysisOutput)
    
    async def analyze_code(
        self,
        code_content: str,
        file_path: str = None,
        context: str = None
    ) -> AIResponse:
        """Analyze code for quality, security, and maintainability."""
        
        system_message = self.create_system_prompt(
            "senior software engineer and code reviewer",
            f"Analyzing code from {file_path or 'unknown file'} in Manager component context"
        )
        
        human_message = HumanMessage(content=f"""
        Analyze the following code for quality, security, and maintainability:
        
        File: {file_path or 'Unknown'}
        Context: {context or 'General code analysis'}
        
        Code:
        ```
        {code_content}
        ```
        
        {self.output_parser.get_format_instructions()}
        
        Focus on:
        1. Code quality and maintainability
        2. Security vulnerabilities
        3. Performance considerations
        4. Adherence to Python/Manager component best practices
        """)
        
        try:
            response = await self._invoke_with_retry([system_message, human_message])
            parsed_output = self.output_parser.parse(response.content)
            
            return AIResponse(
                success=True,
                content=json.dumps(parsed_output.dict(), indent=2),
                confidence=parsed_output.code_quality_score / 10.0,
                reasoning="AI code analysis with quality and security assessment",
                metadata={
                    "file_path": file_path,
                    "language": parsed_output.language_detected,
                    "quality_score": parsed_output.code_quality_score,
                    "complexity": parsed_output.complexity_assessment
                }
            )
            
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return AIResponse(
                success=False,
                content=f"Code analysis failed: {str(e)}",
                metadata={"error": str(e)}
            )

# Decision Support Service
class DecisionSupportService(BaseAIService):
    """
    AI service for decision support and recommendation generation.
    
    Used in:
    - Database decommissioning decisions
    - Architecture choice recommendations
    - Workflow optimization suggestions
    """
    
    def __init__(self, config: AzureOpenAIConfig):
        super().__init__(config, "DecisionSupport")
        self.output_parser = PydanticOutputParser(pydantic_object=DecisionSupportOutput)
    
    async def get_recommendation(
        self,
        decision_context: str,
        options: List[str] = None,
        constraints: List[str] = None,
        success_criteria: List[str] = None
    ) -> AIResponse:
        """Provide structured decision support and recommendations."""
        
        context_info = f"""
        Decision Context: {decision_context}
        
        Available Options: {', '.join(options or ['Not specified'])}
        
        Constraints: {', '.join(constraints or ['None specified'])}
        
        Success Criteria: {', '.join(success_criteria or ['Not specified'])}
        """
        
        system_message = self.create_system_prompt(
            "senior technical architect and decision analyst",
            "Providing technical decision support for Manager component operations"
        )
        
        human_message = HumanMessage(content=f"""
        Provide decision support analysis for the following scenario:
        
        {context_info}
        
        {self.output_parser.get_format_instructions()}
        
        Consider:
        1. Technical feasibility and complexity
        2. Resource requirements and timeline
        3. Risk assessment and mitigation strategies
        4. Long-term maintainability and scalability
        5. Integration with existing Manager/Agent/UI components
        """)
        
        try:
            response = await self._invoke_with_retry([system_message, human_message])
            parsed_output = self.output_parser.parse(response.content)
            
            return AIResponse(
                success=True,
                content=json.dumps(parsed_output.dict(), indent=2),
                confidence=parsed_output.confidence,
                reasoning="AI decision support analysis with pros/cons evaluation",
                metadata={
                    "recommendation": parsed_output.recommendation,
                    "risk_level": parsed_output.risk_assessment,
                    "alternatives_count": len(parsed_output.alternatives)
                }
            )
            
        except Exception as e:
            logger.error(f"Decision support failed: {e}")
            return AIResponse(
                success=False,
                content=f"Decision support failed: {str(e)}",
                metadata={"error": str(e)}
            )

# Streaming AI Service Pattern
class StreamingAIService(BaseAIService):
    """
    Pattern for streaming AI responses for real-time feedback.
    
    Used in:
    - Interactive incident analysis
    - Real-time workflow guidance
    - Progressive code analysis
    """
    
    def __init__(self, config: AzureOpenAIConfig):
        super().__init__(config, "StreamingAI")
    
    async def stream_analysis(
        self,
        prompt: str,
        context: str = None
    ) -> AsyncGenerator[str, None]:
        """Stream AI analysis results in real-time."""
        
        system_message = self.create_system_prompt(
            "analytical assistant",
            context or "Real-time analysis and guidance"
        )
        
        human_message = HumanMessage(content=prompt)
        
        try:
            # Note: Streaming implementation depends on LangChain version
            # This is a simplified example
            response = await self._invoke_with_retry([system_message, human_message])
            
            # Simulate streaming by yielding chunks
            content = response.content
            chunk_size = 50
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.1)  # Simulate streaming delay
                
        except Exception as e:
            yield f"Error in streaming analysis: {str(e)}"

# AI Service Factory Pattern
class AIServiceFactory:
    """
    Factory pattern for creating AI services with shared configuration.
    
    Provides centralized configuration and service instantiation
    following Manager component patterns.
    """
    
    def __init__(self, config: AzureOpenAIConfig):
        self.config = config
        self._services: Dict[str, BaseAIService] = {}
    
    def get_incident_analysis_service(self) -> IncidentAnalysisService:
        """Get or create incident analysis service."""
        if "incident" not in self._services:
            self._services["incident"] = IncidentAnalysisService(self.config)
        return self._services["incident"]
    
    def get_code_analysis_service(self) -> CodeAnalysisService:
        """Get or create code analysis service."""
        if "code" not in self._services:
            self._services["code"] = CodeAnalysisService(self.config)
        return self._services["code"]
    
    def get_decision_support_service(self) -> DecisionSupportService:
        """Get or create decision support service."""
        if "decision" not in self._services:
            self._services["decision"] = DecisionSupportService(self.config)
        return self._services["decision"]
    
    def get_streaming_service(self) -> StreamingAIService:
        """Get or create streaming AI service."""
        if "streaming" not in self._services:
            self._services["streaming"] = StreamingAIService(self.config)
        return self._services["streaming"]
    
    async def close_all_services(self):
        """Close all active services."""
        for service in self._services.values():
            if hasattr(service, 'close'):
                await service.close()
        self._services.clear()

# Prompt Engineering Patterns
class PromptTemplates:
    """
    Collection of prompt templates used throughout Manager component.
    
    Based on proven patterns from:
    - Incident analysis workflows
    - Database decommissioning automation
    - Code review and analysis tasks
    """
    
    INCIDENT_ANALYSIS_SYSTEM = """
    You are an expert Site Reliability Engineer analyzing system incidents.
    
    Your expertise includes:
    - Root cause analysis for complex distributed systems
    - Incident severity assessment and escalation procedures
    - Post-incident review and prevention strategies
    - Integration with monitoring and alerting systems
    
    Always provide:
    - Clear severity assessment with justification
    - Actionable remediation steps
    - Risk assessment for similar incidents
    - Confidence level in your analysis
    """
    
    CODE_ANALYSIS_SYSTEM = """
    You are a senior software engineer specializing in Python and distributed systems.
    
    Your expertise covers:
    - Python best practices and design patterns
    - FastAPI and async programming patterns
    - Database integration and ORM patterns
    - Security vulnerability assessment
    - Performance optimization strategies
    
    Focus on:
    - Maintainability and readability
    - Security considerations
    - Performance implications
    - Integration compatibility
    """
    
    DECISION_SUPPORT_SYSTEM = """
    You are a senior technical architect providing decision support.
    
    Your approach:
    - Systematic analysis of options and trade-offs
    - Risk assessment and mitigation strategies
    - Resource and timeline estimation
    - Long-term architectural impact assessment
    
    Always provide:
    - Clear recommendation with reasoning
    - Alternative options with pros/cons
    - Implementation roadmap
    - Success criteria and metrics
    """
    
    @classmethod
    def format_incident_prompt(cls, incident_data: Dict[str, Any]) -> str:
        """Format incident analysis prompt with data."""
        return f"""
        Analyze this system incident:
        
        Incident Details:
        {json.dumps(incident_data, indent=2)}
        
        Provide structured analysis including:
        1. Severity assessment (critical/high/medium/low)
        2. Root cause analysis
        3. Immediate remediation steps
        4. Prevention strategies
        5. Confidence level (0.0-1.0)
        """
    
    @classmethod
    def format_code_analysis_prompt(cls, code: str, context: str = None) -> str:
        """Format code analysis prompt."""
        return f"""
        Analyze this code for quality, security, and maintainability:
        
        Context: {context or 'General code review'}
        
        Code:
        ```python
        {code}
        ```
        
        Provide analysis covering:
        1. Code quality score (0-10)
        2. Security vulnerabilities
        3. Performance considerations
        4. Maintainability issues
        5. Improvement recommendations
        """

# Context-Aware AI Integration Pattern
class ContextAwareAIService:
    """
    Advanced pattern for context-aware AI integration.
    
    Maintains conversation context and adapts responses based on:
    - Previous interactions
    - System state
    - User preferences
    - Performance feedback
    """
    
    def __init__(self, config: AzureOpenAIConfig, context_window: int = 10):
        self.config = config
        self.context_window = context_window
        self.conversation_history: List[Dict[str, Any]] = []
        self.system_context: Dict[str, Any] = {}
        self.factory = AIServiceFactory(config)
    
    async def analyze_with_context(
        self,
        task_type: AITaskType,
        input_data: Dict[str, Any],
        user_context: Dict[str, Any] = None
    ) -> AIResponse:
        """Perform AI analysis with full context awareness."""
        
        # Build context from history and current state
        context = self._build_context(task_type, user_context)
        
        # Select appropriate service
        service = await self._get_service_for_task(task_type)
        
        # Perform analysis with context
        if task_type == AITaskType.INCIDENT_ANALYSIS:
            response = await service.analyze_incident(input_data, context.get("historical_incidents"))
        elif task_type == AITaskType.CODE_ANALYSIS:
            response = await service.analyze_code(
                input_data.get("code", ""),
                input_data.get("file_path"),
                context.get("code_context")
            )
        elif task_type == AITaskType.DECISION_SUPPORT:
            response = await service.get_recommendation(
                input_data.get("decision_context", ""),
                input_data.get("options"),
                input_data.get("constraints"),
                context.get("success_criteria")
            )
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
        
        # Update conversation history
        self._update_history(task_type, input_data, response)
        
        return response
    
    def _build_context(self, task_type: AITaskType, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build comprehensive context for AI task."""
        context = {
            "system_context": self.system_context,
            "recent_history": self.conversation_history[-self.context_window:],
            "task_type": task_type.value,
            "user_context": user_context or {}
        }
        
        # Add task-specific context
        if task_type == AITaskType.INCIDENT_ANALYSIS:
            context["historical_incidents"] = [
                h for h in self.conversation_history 
                if h.get("task_type") == AITaskType.INCIDENT_ANALYSIS.value
            ][-5:]  # Last 5 incidents
        
        elif task_type == AITaskType.CODE_ANALYSIS:
            context["code_context"] = {
                "recent_files": [h.get("file_path") for h in self.conversation_history 
                               if h.get("file_path")][-10:],
                "common_patterns": self._extract_common_patterns()
            }
        
        return context
    
    def _extract_common_patterns(self) -> List[str]:
        """Extract common patterns from code analysis history."""
        patterns = []
        for entry in self.conversation_history:
            if entry.get("task_type") == AITaskType.CODE_ANALYSIS.value:
                if entry.get("response", {}).get("metadata", {}).get("language"):
                    patterns.append(entry["response"]["metadata"]["language"])
        return list(set(patterns))
    
    async def _get_service_for_task(self, task_type: AITaskType):
        """Get appropriate AI service for task type."""
        if task_type == AITaskType.INCIDENT_ANALYSIS:
            return self.factory.get_incident_analysis_service()
        elif task_type == AITaskType.CODE_ANALYSIS:
            return self.factory.get_code_analysis_service()
        elif task_type == AITaskType.DECISION_SUPPORT:
            return self.factory.get_decision_support_service()
        else:
            raise ValueError(f"No service available for task type: {task_type}")
    
    def _update_history(self, task_type: AITaskType, input_data: Dict[str, Any], response: AIResponse):
        """Update conversation history with task results."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type.value,
            "input_data": input_data,
            "response": {
                "success": response.success,
                "confidence": response.confidence,
                "metadata": response.metadata
            }
        }
        
        self.conversation_history.append(entry)
        
        # Keep history within window size
        if len(self.conversation_history) > self.context_window * 2:
            self.conversation_history = self.conversation_history[-self.context_window:]
    
    def update_system_context(self, context_update: Dict[str, Any]):
        """Update system context for future AI interactions."""
        self.system_context.update(context_update)
    
    async def close(self):
        """Close all services."""
        await self.factory.close_all_services()

# Example Usage Patterns
async def example_incident_analysis():
    """Example of incident analysis using AI integration patterns."""
    
    # Configure AI service
    config = AzureOpenAIConfig(
        deployment_name="gpt-4",
        temperature=0.1
    )
    
    # Create incident data
    incident_data = {
        "id": "INC-2024-001",
        "title": "Database Connection Pool Exhausted",
        "description": "Application unable to connect to database, connection pool showing 100% utilization",
        "source": "monitoring_alert",
        "timestamp": "2024-01-15T10:30:00Z",
        "metrics": {
            "connection_pool_size": 100,
            "active_connections": 100,
            "queue_length": 45,
            "response_time_p95": 5000
        }
    }
    
    # Analyze incident
    async with IncidentAnalysisService(config) as service:
        response = await service.analyze_incident(incident_data)
        
        if response.success:
            print(f"Incident Analysis Results:")
            print(f"Content: {response.content}")
            print(f"Confidence: {response.confidence}")
        else:
            print(f"Analysis failed: {response.content}")

async def example_context_aware_analysis():
    """Example of context-aware AI analysis."""
    
    config = AzureOpenAIConfig()
    context_service = ContextAwareAIService(config)
    
    # Set system context
    context_service.update_system_context({
        "environment": "production",
        "component": "manager",
        "team": "sre"
    })
    
    # Perform incident analysis with context
    incident_data = {
        "title": "High Memory Usage Alert",
        "description": "Manager service showing 85% memory utilization",
        "metrics": {"memory_usage": 0.85, "cpu_usage": 0.45}
    }
    
    response = await context_service.analyze_with_context(
        AITaskType.INCIDENT_ANALYSIS,
        incident_data,
        user_context={"urgency": "medium", "business_hours": True}
    )
    
    print(f"Context-Aware Analysis: {response.content}")
    
    await context_service.close()

if __name__ == "__main__":
    # Example usage
    asyncio.run(example_incident_analysis())