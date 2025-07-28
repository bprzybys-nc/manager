/Users/bprzybysz/nc-src/ovora - blaise (my) ovora with manager
/Users/bprzybysz/nc-src/ovora_aava - marcin ovora
/Users/bprzybysz/nc-src/ovora_main - alex ovora


all these ovora are different branches/commits, you could say versions of the ovora system
each of them contains manager where usecases are defined

1. alex ovora contains incomplete workflow (usecase-executor/usecases/incident_assistant) but workflow that is defined most properly as for integration with system. our goal is to complete this workflow
2. marcin ovora contains most mature workflow which is missing only some functionality described in 3. and uses mongo db as vector db that need to be replaced with chromadb as vector db. still this implementation realizes proper functionality of creating and using metadata while populating vector db and using it to properly search and find a runbook
3. blaise ovora contains tools for exploring discovery of runbooks from confluence and populating vector db with them and searching for best couple of fits. however it is unclear whether it uses metadata and if so whether it uses it correctly (like in marcin version)
4. most probably runbook usage needs to be adjusted/changed. idea is to, once runbook is found to use it as kinda general/or more directly as guideline for creating automatic diagnostic and remediation script (depending on whether runbook provides any of these) of which proper definition is then solidified with web search (brave search. not sure which version implements it if any. needs to be verified and handled in plan). scripts should be applied/executed as it is in marcin case. however ideally we reuse existing functionality unless adviced otherwise
5. we need to think whether it's best to complete usecase-executor/usecases/incident_assistant. or just use it as source for proper workflow integration and create separate usecase 
6. as for blaise and marcin branches/versions we can focus on manager

* final implementation uses only chromadb based vector db. as for target dbs to be remediated (not vectoir db) we focus on oracle dbs first, leaving other db providers not implemented (pls use properly declared interfaces with abstract/virtual methods like in strategy pattern)
* try to define interface (check public methods that should be implemented) as middle step to replace mongo db with chromdb
* first for sure we should create branch from main 'feat/big-integration' (already done for alex version). then translate marcin usecase very carefully to alex usecase patterns (integration and what not)
* blaise version has quite properly defined context engineering with CLAUDE.md and other needed files. we should create such for other two versions/branches. however how to do it optimally I leave it to you Claude. assuming that in the end we'll work on branched from alex/ or simply alex (main) version we don't need to create full scope context engineering for marcin version. also we can reuse blaise version's context engineering to speed up works on it. however it will be best to create full context engineering for alex version entire ovora folder (once branched)
* when talkking about context engineering I mean https://github.com/coleam00/context-engineering-intro
* blaise version of manager (this project) defines commands to create INITIAL.md to generate prp from this INITIAL.md and execute created prp
* this task is kinda huge I don't know how to break it into doable tasks - pls help me 
* it would be best to create context engineering from alex project, so assume it is done for alex project (verify it)

we were talk about this during meeting from which transciption u'll find in src/usecases/db_runbook_finder/docs/big-integra-meeting/fixed-transcript-pl.md (polish language). there's also screenshot made (last two screenshots on Desktop folders)


