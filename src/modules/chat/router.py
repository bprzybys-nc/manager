import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from langgraph.checkpoint.mongodb import MongoDBSaver
from langchain.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from src.database.client import DatabaseClient
from src.llm import llm
from src.modules.incident.db import IncidentDB, Status, Type
from src.modules.inventory.db import InventoryDB
from src.modules.metrics.prometheus import Prometheus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PROMPT = f"""You are a chat agent. Your task is to chat with users and provide responses based on the conversation.

# GENERAL INSTRUCTIONS

IMPORTANT: The chat is in request-response format, where the user sends a message, and you respond accordingly. This is
not stream-based chat, so you should respond to each message from the user with complete information.

CRITICAL INSTRUCTION: NEVER use phrases that suggest you're retrieving data in real-time. Users expect complete answers
immediately. DO NOT send messages containing any of these phrases or similar ones:
- "Fetching details..."
- "Please wait..."
- "Let me check..."
- "I'm looking into it..."
- "Let me fetch..."
- "I'll check"
- "One moment"
- "Just a second"
- "Getting that information for you"
- "Checking the status"
- "Looking into any issues"
- "Searching for"
- "Retrieving"
- "Finding"
- "Will provide"

Instead, when you need data, directly use the appropriate tool and immediately provide the complete response without
mentioning the retrieval process at all. Never announce that you will check something - just check it and provide the
results directly.

Be talkative, friendly, and informal in your responses. Show some personality! Here are some tips:

- Use conversational language and occasional exclamations like "Hey there!" or "Great question!"
- Feel free to use some humor when appropriate
- Address the user directly and maintain a friendly tone
- Express enthusiasm when sharing information ("I'd be happy to help with that!")
- Use follow-up questions to clarify needs when appropriate
- Occasionally add personal touches like "I find this interesting" or "Let me dig into that for you"
- Fit in 180 lines of response text in a single message to avoid splitting the response into multiple messages.

Remember that while you should be friendly and personable, your primary goal is still to provide accurate and helpful
information about the system.

# WHEN THIS IS A WELCOME MESSAGE, FOLLOW THESE STEPS:

1. **Greet the User**: Start with a friendly greeting, e.g., "Hey there! How can I help you today?"
2. **Introduce Yourself**: Briefly introduce yourself and your role, e.g., "I'm a chat agent here to assist you."
3. **Offer Assistance**: Let the user know you're available to help with any questions or issues.
4. **Set the Tone**: Keep the tone friendly and professional, and encourage the user to ask questions.
5. **Status Update**: If there are any ongoing issues or maintenance, inform the user. Immediately use tools to gather incidents
   (get_incidents), check instances (get_instances), or query metrics and present this information directly without mentioning
   the process of gathering this information. Only mention actual issues, not closed incidents, resolved alerts, or healthy instances.
6. **Ask for More Information**: If the user hasn't provided a specific request, ask for more details to better assist them.

# WHEN ASKED ABOUT INSTANCES, INCIDENTS, FOLLOW THESE STEPS:

1. **Fetch Instances**: Use the 'get_instances' tool to fetch a list of all instances.
2. **Fetch Incidents**: Use the 'get_incidents' tool to fetch a list of all incidents, for a specific instance use
   'get_incidents_by_instance_id' or 'get_incident' tool to fetch details of a specific incident.
3. **Format Output**: Use Markdown to format the output in a readable way. Use tables or bullet points as needed.

# WHEN ASKED ABOUT METRICS, FOLLOW THESE STEPS:

1. **Query Prometheus**: Use the appropriate PromQL queries to retrieve relevant metrics using 'query_prometheus' tool.
2. **Format Output as CSV**: Return the results in CSV format inside a Markdown-style block, e.g.:

   ```csv-metrics
   timestamp,metric_name,value
   1710105600,cpu_usage,45.6
   1710105660,cpu_usage,46.2
   ```

3. **Ensure Proper Headers**: The first row should always be `timestamp,metric_name,value` (or another relevant schema).
4. **Provide Clean and Structured Data**: Avoid excessive precision and ensure values are readable.
5. **Timestamp Format**: Use Unix timestamps for time series data.
6. **Historical Data**: If requested, provide historical data for a specific time range.
7. **Time Range**: If a time range is requested, ensure the data is within the specified range. If no range is
    specified, provide the most recent data for the last 24 hours.
8. **Maximum Rows**: Limit the number of rows to 100 for better readability.
9. **Current time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# WHEN ASKED ABOUT PROCESSES, FOLLOW THESE STEPS:

1. **Fetch Process Data**: Use the 'get_instance_processes' tool to fetch a list of all processes for a
   specific instance.
2. **Format Output as CSV**: Return the results in CSV format inside a Markdown-style block, e.g.:

    ```csv-dataframe
    pid,username,name,cmd,cpu_percent,memory_percent
    1234,root,nginx,"/usr/sbin/nginx",0.5,0.1
    5678,root,apache,"/usr/sbin/apache",0.3,0.2
    ```

    Make sure it is a properly formatted CSV with the correct headers.

3. **Ensure Proper Headers**: The first row should always contain appropriate column names for process data.
4. **Provide Clean and Structured Data**: Avoid excessive precision and ensure values are readable.
5. **Maximum Rows**: Limit the number of rows to 100 for better readability.
"""


class ChatRoute:
    def __init__(self, prometheus: Prometheus, incident_db: IncidentDB, inventory_db: InventoryDB,
                 db_client: DatabaseClient):
        self.router = APIRouter()
        self.prom = prometheus
        self.incident_db = incident_db
        self.inventory_db = inventory_db
        self._setup_routes()
        self.checkpointer = MongoDBSaver(
            client=db_client,
            db_name="sysaidmin",
            checkpoint_collection_name="chat_checkpoints",
            writes_collection_name="chat_checkpoints_writes",
        )
        self.chatbot = create_react_agent(llm, self._create_tools(), prompt=PROMPT, checkpointer=self.checkpointer)

    def _setup_routes(self):
        self.router.post("/")(self.chat)

    def _create_tools(self) -> list[StructuredTool]:
        def get_incidents_by_instance_id(instance_id: str, status: Optional[Status] = None, type: Optional[Type] = None) -> list[dict]:
            """Fetch a list of all incidents for an instance

            Args:
                instance_id (str): The instance ID
                status (Status): The status of the incidents to fetch
                type (Type): The type of the incidents to fetch
            """
            return self.incident_db.get_incidents_by_instance_id(instance_id, status, type)

        def get_incidents(status: Optional[Status] = None, type: Optional[Type] = None) -> list[dict]:
            """Fetch a list of all incidents for an instance

            Args:
                status (Status): The status of the incidents to fetch
                type (Type): The type of the incidents to fetch
            """
            return self.incident_db.get_incidents(status, type)

        def get_incident(incident_id: str) -> list[dict]:
            """Fetch a details of an incident"""
            return self.incident_db.get_incident(incident_id)

        def get_instances() -> list[dict]:
            """Fetch a list of all instances"""
            return self.inventory_db.get_instances()

        def get_instance(instance_id: str) -> list[dict]:
            """Fetch a details of an instance"""
            return self.inventory_db.get_instance(instance_id)

        def get_prometheus_all_metrics() -> dict:
            """Fetch all Prometheus metrics"""
            return self.prom.prometheus.all_metrics()

        def query_prometheus(
            query: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, step: str = "1h"
        ) -> dict:
            """Query Prometheus with a custom PromQL query

            Args:
                query (str): The PromQL query to execute (use "instance_id" as a label for instance filtering, for
                    example 'node_filesystem_avail_bytes{instance_id=$instance_id}')
                start_time (datetime, optional): Start time for range queries
                end_time (datetime, optional): End time for range queries
                step (str, optional): Step interval for range queries (e.g., "1h", "5m")

            Returns:
                A dictionary with the query results from Prometheus
            """
            logger.info(f"Querying Prometheus with query: `{query}` (start: {start_time}, end: {end_time}, st: {step})")

            if start_time and end_time:
                # Range query
                return self.prom.prometheus.custom_query_range(query, start_time, end_time, step)
            else:
                # Instant query
                return self.prom.prometheus.custom_query(query)

        def get_instance_processes(instance_id: str) -> list[dict]:
            """Fetch a list of all processes for an instance"""
            return self.inventory_db.get_instance(instance_id).processes

        return [
            StructuredTool.from_function(
                func=get_incidents,
                name="get_incidents",
                description="Fetch a list of all incidents for an instance",
            ),
            StructuredTool.from_function(
                func=get_incident,
                name="get_incident",
                description="Fetch details of an incident",
            ),
            StructuredTool.from_function(
                func=get_instances,
                name="get_instances",
                description="Fetch a list of all instances",
            ),
            StructuredTool.from_function(
                func=get_instance,
                name="get_instance",
                description="Fetch details of an instance",
            ),
            StructuredTool.from_function(
                func=get_prometheus_all_metrics,
                name="get_prometheus_all_metrics",
                description="Get the list of all the metrics that the prometheus host scrapes.",
            ),
            StructuredTool.from_function(
                func=query_prometheus,
                name="query_prometheus",
                description=("Query Prometheus with a custom PromQL query (use 'instance_id' as a label for instance "
                             "filtering, for example 'node_filesystem_avail_bytes{instance_id=$instance_id}') "
                             "Don't use 'job' or 'instance' labels in the query"
                             "Use 'get_prometheus_all_metrics' to get the list of all the metrics that the prometheus "
                             "host scrapes."),
            ),
            StructuredTool.from_function(
                func=get_instance_processes,
                name="get_instance_processes",
                description="Fetch a list of all processes for an instance",
            ),
        ]

    async def chat(self, payload: dict):
        input = {
            "messages": [
                {"role": "user", "content": payload["message"]},
            ]
        }
        response = self.chatbot.invoke(
            input, config={"configurable": {"thread_id": str(payload["id"])}}
        )

        logger.info(f"Chat response:\n\n{response['messages'][-1].content}")

        return {"response": response["messages"][-1].content}
