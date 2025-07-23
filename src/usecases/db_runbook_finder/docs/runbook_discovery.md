# Confluence Runbook Discovery Algorithm Flowchart

Based on the hierarchical discovery strategy discussed, here's the comprehensive flowchart for the runbook discovery algorithm:

## Main Discovery Flow

```mermaid
flowchart TD
    A["Start Discovery Process"] --> B["Initialize Target Spaces['AAVA', 'MCDBA']"]
    B --> C["Create Parallel Discovery Tasks"]
    C --> D["Execute Concurrent Discovery"]
    
    D --> E["Space Root Discovery"]
    D --> F["Hierarchy Traversal Discovery"]
    D --> G["Content Structure Analysis"]
    D --> H["Label-Based Discovery"]
    
    E --> I["Aggregate Results"]
    F --> I
    G --> I
    H --> I
    
    I --> J["Deduplicate Runbooks"]
    J --> K["Extract Hierarchy Paths"]
    K --> L["Organize by Client Structure"]
    L --> M["Prepare Vector Storage Metadata"]
    M --> N["Return Discovered Runbooks"]
```

## Detailed Space Root Discovery

```mermaid
flowchart TD
    A["Space Root Discovery(space_key)"] --> B["Define Search Patterns"]
    B --> C["Execute CQL Queries"]
    
    C --> D["Pattern 1:'title ~ runbook'"]
    C --> E["Pattern 2:'title ~ playbook'"]
    C --> F["Pattern 3:'title ~ procedure'"]
    C --> G["Pattern 4:'label = runbook'"]
    C --> H["Pattern 5:'text ~ step-by-step'"]
    
    D --> I["Collect Results"]
    E --> I
    F --> I
    G --> I
    H --> I
    
    I --> J["Filter Candidates"]
    J --> K{"Is Valid Runbook?"}
    K -->|Yes| L["Add to Results"]
    K -->|No| M["Discard"]
    L --> N["Return Space Runbooks"]
    M --> N
```

## Hierarchy Traversal Algorithm

```mermaid
flowchart TD
    A["Start Hierarchy Traversal(parent_page_id, depth=0)"] --> B{"Depth > Max Depth(5)?"}
    B -->|Yes| C["Return Empty List"]
    B -->|No| D["Get Page Children"]
    
    D --> E["Initialize Results List"]
    E --> F["For Each Child Page"]
    
    F --> G{"Is Child a Runbook?"}
    G -->|Yes| H["Extract Runbook Metadata"]
    G -->|No| I["Skip to Recursion"]
    
    H --> J["Add to Results"]
    J --> I["Recursive Call(child_id, depth+1)"]
    I --> K["Merge Child Results"]
    
    K --> L{"More Children?"}
    L -->|Yes| F
    L -->|No| M["Return All Results"]
```

## Runbook Validation Process

```mermaid
flowchart TD
    A["Page Validation Input"] --> B["Title Analysis"]
    A --> C["Content Structure Analysis"]
    A --> D["Label Analysis"]
    
    B --> E{"Contains RunbookKeywords?"}
    E -->|Yes| F["Title Score +1.0"]
    E -->|No| G["Title Score +0.0"]
    
    C --> H["Check Numbered Steps"]
    C --> I["Check Troubleshooting Keywords"]
    C --> J["Check Command Examples"]
    C --> K["Check Prerequisites"]
    
    H --> L["Calculate Content Score"]
    I --> L
    J --> L
    K --> L
    
    D --> M{"Has RunbookLabels?"}
    M -->|Yes| N["Label Score +1.0"]
    M -->|No| O["Label Score +0.0"]
    
    F --> P["Combine Scores"]
    G --> P
    L --> P
    N --> P
    O --> P
    
    P --> Q{"Combined Score > 0.7?"}
    Q -->|Yes| R["Valid Runbook"]
    Q -->|No| S["Not a Runbook"]
```

## Content Structure Analysis Detail

```mermaid
flowchart TD
    A["Content Analysis(page_content)"] --> B["Initialize Score = 0.0"]
    
    B --> C["Check Numbered StepsRegex: '\\d+\\.\\s+'"]
    C --> D{"Found?"}
    D -->|Yes| E["Score += 0.3"]
    D -->|No| F["Continue"]
    
    E --> G["Check Troubleshooting Keywords"]
    F --> G
    G --> H["Count Keyword Matches['error', 'issue', 'problem', 'solution']"]
    H --> I["Score += min(matches * 0.1, 0.3)"]
    
    I --> J["Check Code BlocksRegex: '```
    J --> K{"Found?"}
    K -->|Yes| L["Score += 0.2"]
    K -->|No| M["Continue"]
    
    L --> N["Check PrerequisitesRegex: 'prerequisite|requirement'"]
    M --> N
    N --> O{"Found?"}
    O -->|Yes| P["Score += 0.2"]
    O -->|No| Q["Final Score"]
    
    P --> R["Return min(score, 1.0)"]
    Q --> R
```

## Hierarchy Path Construction

```
flowchart TD
    A["Build Hierarchy Path(page)"] --> B["Initialize Path Components[]"]
    B --> C["Set Current Page = Input Page"]
    
    C --> D["Add Page Title to Components"]
    D --> E{"Has ParentAncestors?"}
    E -->|Yes| F["Get Parent Page ID"]
    E -->|No| G["Add Space Key"]
    
    F --> H["Fetch Parent Page"]
    H --> I["Set Current Page = Parent"]
    I --> D
    
    G --> J["Reverse Components Order(Root to Leaf)"]
    J --> K["Join with '/' Separator"]
    K --> L["Return Full Hierarchy Path'SPACE/Parent/Child/Page'"]
```

## Parallel Processing Architecture

```
flowchart TD
    A["Parallel Discovery Orchestrator"] --> B["Create Task Groups"]
    
    B --> C["Space AAVA Tasks"]
    B --> D["Space MCDBA Tasks"]
    
    C --> E["AAVA Root Discovery"]
    C --> F["AAVA Hierarchy Traversal"]
    C --> G["AAVA Content Analysis"]
    C --> H["AAVA Label Discovery"]
    
    D --> I["MCDBA Root Discovery"]
    D --> J["MCDBA Hierarchy Traversal"]
    D --> K["MCDBA Content Analysis"]
    D --> L["MCDBA Label Discovery"]
    
    E --> M["asyncio.gather()"]
    F --> M
    G --> M
    H --> M
    I --> M
    J --> M
    K --> M
    L --> M
    
    M --> N["Process Results"]
    N --> O["Handle Exceptions"]
    O --> P["Aggregate Valid Results"]
    P --> Q["Return Combined Runbooks"]
```

## Client Organization Flow

```
flowchart TD
    A["Organize by Client Hierarchy(runbooks[])"] --> B["Initialize Client Structure"]
    
    B --> C["For Each Runbook"]
    C --> D["Extract Client from Path"]
    D --> E{"Client Type?"}
    
    E -->|Helvetia| F["Add to client_specific['helvetia']"]
    E -->|Bravida| G["Add to client_specific['bravida']"]
    E -->|Neste| H["Add to client_specific['neste']"]
    E -->|Grohe| I["Add to client_specific['grohe']"]
    E -->|General| J["Add to general[]"]
    
    F --> K{"More Runbooks?"}
    G --> K
    H --> K
    I --> K
    J --> K
    
    K -->|Yes| C
    K -->|No| L["Return Organized Structure"]
```

## Vector Storage Preparation

```
flowchart TD
    A["Prepare for Vector Storage(runbook_data)"] --> B["Extract Core Content"]
    B --> C["Combine Title + Content"]
    C --> D["Build Metadata Object"]
    
    D --> E["Add Hierarchy Path"]
    D --> F["Add Client Information"]
    D --> G["Add Depth Level"]
    D --> H["Add Parent Pages"]
    D --> I["Add Discovery Method"]
    D --> J["Add Confidence Score"]
    D --> K["Add Confluence URL"]
    
    E --> L["Create Vector Storage Document"]
    F --> L
    G --> L
    H --> L
    I --> L
    J --> L
    K --> L
    
    L --> M["Return Formatted Document{id, content, metadata}"]
```

## Performance Optimization Flow

```
flowchart TD
    A["Cache Manager Check"] --> B{"Cache Hit?"}
    B -->|Yes| C["Return Cached Data"]
    B -->|No| D["Execute API Call"]
    
    D --> E["Store in Cache(data, timestamp)"]
    E --> F["Return Fresh Data"]
    
    C --> G["Check TTL Validity"]
    G --> H{"Cache Still Valid?"}
    H -->|Yes| I["Use Cached Data"]
    H -->|No| J["Refresh Cache"]
    
    J --> D
    F --> K["Continue Processing"]
    I --> K
```

This comprehensive flowchart system provides a complete view of the hierarchical runbook discovery algorithm, showing how it handles multi-level traversal, content validation, client organization, and performance optimization while maintaining the full Confluence hierarchy structure for the db_runbook_finder system.