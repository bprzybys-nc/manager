
from pydantic import BaseModel
from typing import Optional


class ProcessedCommand(BaseModel):
    """
    A processed command with its result, risk, and human confirmation.
    """

    command: str
    result: Optional[str] = None
    risk: Optional[str] = None
    risk_justification: Optional[str] = None
    human_confirmation: Optional[str] = None
    interpretation: Optional[str] = None

postgres_diagnostic_commands = [
    ProcessedCommand(
        command="SELECT pid, usename, now() - query_start AS duration, state, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 5;",
        result="""
   pid   | usename |    duration     | state  |                                                                      query                                                                      
---------+---------+-----------------+--------+-------------------------------------------------------------------------------------------------------------------------------------------------
 1051331 | admin   | 00:00:01.924259 | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 1051333 | admin   | 00:00:01.819413 | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 1051335 | admin   | 00:00:01.69282  | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 1051337 | admin   | 00:00:01.601366 | active | SELECT count(*) FROM generate_series(1, 10000000) s;
 1051343 | admin   | 00:00:00        | active | SELECT pid, usename, now() - query_start AS duration, state, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 5;
(5 rows)
""",
    ),
    ProcessedCommand(
        command="SELECT * FROM pg_stat_database WHERE deadlocks > 0;",
        result="""
""",
    ),
    ProcessedCommand(
        command="SELECT relname, n_dead_tup FROM pg_stat_user_tables WHERE n_dead_tup > 1000 ORDER BY n_dead_tup DESC LIMIT 5;",
        result="""
relname | n_dead_tup 
---------+------------
(0 rows)
""",
    ),
    ProcessedCommand(
        command="SELECT relname, seq_scan, idx_scan, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables ORDER BY n_tup_upd + n_tup_del DESC LIMIT 5;",
        result="""
 relname | seq_scan | idx_scan | n_tup_ins | n_tup_upd | n_tup_del 
---------+----------+----------+-----------+-----------+-----------
(0 rows)
""",
    ),
       ProcessedCommand(
        command="SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total_size FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 5;",
        result="""
 relname | total_size 
---------+------------
(0 rows)
""",
    )
]



json_commands=[]
for command in postgres_diagnostic_commands:
    json_commands.append(command.model_dump())

json_data={"incident_id": "34783", "instance_id": "instance_id", "commands": json_commands, "response_endpoint": "/confirmations"}

import json

# Validate JSON structure
try:
    # Convert to JSON string and back to validate
    json_string = json.dumps(json_data)
    parsed_json = json.loads(json_string)
    
    # Check required fields
    required_fields = ["incident_id", "instance_id", "commands", "response_endpoint"]
    missing_fields = [field for field in required_fields if field not in parsed_json]
    
    if missing_fields:
        print(f"Error: Missing required fields: {', '.join(missing_fields)}")
    else:
        print("JSON validation successful")
        print(json_data)
except Exception as e:
    print(f"JSON validation error: {str(e)}")