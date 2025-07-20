Of course. I have analyzed the Context Engineering methodology, reviewed the provided codebase from `manager-codebase.xml`, and adapted our plan. As requested, User Story 3 (complex gap analysis) has been removed from the prototype scope; gaps will now result in a graceful termination of the workflow.

The existing codebase is highly functional and provides excellent building blocks, especially the `src/tools/confluence` module which includes a ready-to-use vector search API, and the `src/frameworks/graphmcp` which provides the orchestration layer. We will leverage these extensively.

Here is the plan presented as a series of `INITIAL.md` files for the `db_runbook_finder` prototype.

### `INITIAL-PLANNING.md`

#### ## Goal
The goal of this prototype is to validate the core functionality of the `db_runbook_finder` system. We will create an AI-orchestrated workflow that can automatically process a Jira incident, perform a semantic search against an indexed set of Confluence runbooks, and determine the most relevant procedures. This will prove the feasibility of reducing incident response time from minutes to seconds.

#### ## User Stories

| # | Title | As a / I want / So that |
|---|-------|-------------------------|
| **P-1** | Basic Workflow Orchestration | **As a** MC-DBA engineer**I want** a LangGraph workflow that automatically processes incident tickets and finds relevant runbooks**So that** I receive structured runbook recommendations without manual searching |
| **P-2** | Slack Team Notifications | **As a** MC-DBA team member**I want** automated Slack alerts with runbook recommendations or gap notifications**So that** the team has rapid incident awareness |

#### ## Acceptance Criteria
- The workflow successfully ingests a Jira ticket key.
- It calls the existing Confluence tool's vector search to find relevant runbooks.
- If runbooks are found, a comment with the top 3 recommendations is added to the Jira ticket.
- If no runbooks are found (a "gap"), a comment is added indicating this, and the workflow terminates cleanly.
- A notification summarizing the outcome (success or gap) is posted to the `#mc-dba-jira-notifications` Slack channel.
- The entire end-to-end process completes in under 30 seconds.
- The prototype is validated against two real Jira tickets.

#### ## Tasks

| Task | Goal | Timeline | Success Metric |
|------|------|----------|---------------|
| **Task 1** | Core Workflow Infrastructure Setup | Week 1, Days 1-2 | Workflow compiles and MCP connects |
| **Task 2** | Incident Fetching & Processing Node | Week 1, Days 3-4 | Fetches incident data from test tickets |
| **Task 3** | Runbook Search & Results Integration | Week 1, Day 5 - Week 2, Day 1 | Returns top 3 relevant runbooks via Confluence tool |
| **Task 4** | End-to-End Workflow & Gap Handling | Week 2, Days 2-3 | End-to-end execution  B["`db_runbook_finder` Workflow"];
    end

    subgraph "LangGraph Workflow (`graphmcp`)"
        B -- "jira_get_issue" --> C["Jira MCP Tool(from `src/tools/jira`)"];
        B -- "vector_search" --> D["Confluence MCP Tool(from `src/tools/confluence`)"];
        B -- "jira_add_comment" --> C;
        B -- "send_message" --> E["Slack MCP Tool"];
    end

    subgraph "External Systems"
        C --> F[Jira Cloud];
        D --> G[Confluence Cloud &Internal ChromaDB];
        E --> H[Slack Workspace];
    end
```

#### ## Data Model / APIs
We will primarily use existing APIs provided by the tools in the codebase. No new APIs need to be created for this prototype.

**Key Data Structure (`WorkflowState`):**
- `jira_key`: (string) The input ticket ID, e.g., "OVR-114".
- `incident_data`: (dict) Structured data from `jira_get_issue`.
- `runbooks`: (list) A list of runbook objects returned from `confluence/search/vector`.
- `status`: (string) The final state of the workflow, e.g., "SUCCESS" or "GAP_DETECTED".

**Key APIs to be Consumed:**
1.  **Jira Tool (`src/tools/jira/client.py`):**
    -   `jira_get_issue(issueIdOrKey)`: To fetch incident details.
    -   `jira_add_comment(issueIdOrKey, comment)`: To post results.
2.  **Confluence Tool (`src/tools/confluence/client.py`):**
    -   `POST /search/vector`: The core semantic search functionality. Called via the client's `vector_search` function.
    -   `POST /bulk/index`: (Pre-requisite) This tool must be run once to index the AAVA and MCDBA spaces.

#### ## User Flow
The workflow follows a conditional path based on the success of the semantic search.

```mermaid
flowchart TD
    A["Start Workflowwith Jira Key"] --> B["`fetch_incident_node`Get ticket data"]
    B --> C["`search_runbooks_node`Perform vector search"]
    C --> D{"Runbooks Found?"}
    D -- "Yes" --> E["`update_jira_with_results_node`Format results and add comment"]
    D -- "No" --> F["`terminate_with_gap_error_node`Add 'gap' comment to Jira"]
    E --> G["`notify_team_node`Send SUCCESS to Slack"]
    F --> G
    G --> H["End"]
```

### `INITIAL-IMPLEMENTATION.md`

#### ## File System Layout
Create a new directory for the use case, mirroring the `database_decommissioning` example.

```
src/
├── usecases/
│   ├── db_runbook_finder/
│   │   ├── __init__.py
│   │   ├── nodes.py         # Contains the implementation for each workflow node.
│   │   ├── state.py         # Defines the WorkflowState data class.
│   │   ├── workflow.py      # Defines the main LangGraph StateGraph.
│   │   └── tests/
│   │       ├── test_workflow.py # Unit & integration tests for the workflow.
│   └── ...
└── ...
```

#### ## Implementation Details

**Instructions for `claude-code`:**

**1. Create the `db_runbook_finder` module:**
   - Create the directory structure as specified in the "File System Layout".
   - In `src/usecases/db_runbook_finder/state.py`, define the `WorkflowState` class. It should contain fields for `jira_key`, `incident_data`, `runbooks`, and `status`.

**2. Implement the Workflow (`workflow.py`):**
   - Create a `DBRunbookFinderWorkflow` class.
   - Use the `_build_workflow` pattern from `src/usecases/database_decommissioning/workflow.py`.
   - Implement the conditional routing logic shown in the architecture diagram. The `runbook_search_router` function will check if the `state.runbooks` list is empty to decide the path.

**3. Implement the Nodes (`nodes.py`):**
   - **`fetch_incident_node`**:
     - Takes `state` as input.
     - Calls `self.mcp_client.call_tool("jira", "jira_get_issue", {"issueIdOrKey": state.jira_key})`.
     - Parses the response and stores the summary, description, and client name in `state.incident_data`.
     - **Gaps/Instructions**: The logic to extract a client name (e.g., "Neste") from a project key (e.g., "NESMCI") will need to be implemented here. The `database_decommissioning` use case likely lacks a direct example of this, so you will need to add a simple dictionary mapping.
       ```python
       # Example logic to add in the node
       PROJECT_TO_CLIENT_MAP = {"NESMCI": "Neste", "HEMCI": "Helvetia", ...}
       project_key = response["fields"]["project"]["key"]
       state.incident_data["client"] = PROJECT_TO_CLIENT_MAP.get(project_key, "Unknown")
       ```
   - **`search_runbooks_node`**:
     - Takes `state` as input.
     - Constructs a `query` string from `state.incident_data["summary"]` and `state.incident_data["description"]`.
     - Calls `self.mcp_client.call_tool("confluence", "vector_search", {"query": query, "space_key": "AAVA,MCDBA", "limit": 3})`. The `confluence` tool already handles searching across multiple spaces if the API supports it.
     - Stores the results in `state.runbooks`.
   - **`update_jira_with_results_node`**:
     - Formats a human-readable comment containing titles and links to the top 3 runbooks from `state.runbooks`.
     - Calls `self.mcp_client.call_tool("jira", "jira_add_comment", ...)`.
   - **`terminate_with_gap_error_node`**:
     - Creates a comment stating that no relevant runbooks were found.
     - Calls `self.mcp_client.call_tool("jira", "jira_add_comment", ...)`.
     - Sets `state.status = "GAP_DETECTED"`.
   - **`notify_team_node`**:
     - Checks `state.status`.
     - Formats a different Slack message for success vs. gap.
     - Calls `self.mcp_client.call_tool("slack", "send_message", ...)`.

#### ## Testing
- **Unit Tests (`test_workflow.py`):**
  - Test each node function individually.
  - Use `unittest.mock` to mock the `mcp_client.call_tool` method to avoid making real API calls.
  - Test the `runbook_search_router` logic with both empty and populated `runbooks` lists.
- **Integration Test (`test_workflow.py`):**
  - Create a test that runs the full workflow using two real, pre-selected Jira ticket IDs.
  - The test will require live connections to the Jira, Confluence, and Slack MCP servers.
  - Assert that the final Jira comment and Slack message are posted correctly for both a success case and a gap case (if a suitable ticket can be found).

#### ## Dependencies
- **Python Packages:** `langgraph`, `graphmcp_sdk`
- **MCP Servers:** `jira`, `confluence`, `slack`. The prototype assumes these are configured and running.
- **Pre-requisite Action:** The Confluence runbooks in spaces `AAVA` and `MCDBA` must be indexed for vector search by running the `confluence` tool's `/bulk/index` endpoint once before testing.

[1] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/8768170/688fdaf0-5e54-48eb-82b6-1f0f06da5332/manager-codebase.xml
[2] https://github.com/coleam00/context-engineering-intro