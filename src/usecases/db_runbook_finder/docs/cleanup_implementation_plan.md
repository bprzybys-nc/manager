# Cleanup Implementation Plan

**Generated**: 2025-07-22  
**Scope**: `src/usecases/db_runbook_finder`  
**Execution Order**: Sequential phases with validation

## Plan Overview

**Total Actions**: 8 steps across 3 phases  
**Risk Level**: 🟡 Medium (test coverage gaps identified)  
**Estimated Impact**: ~1,200 lines removed, 50% test file reduction  

## Phase 1: Critical Fixes (Immediate - No Risk)

### Step 1.1: Fix Server Class Name References
**Risk**: 🟢 None - Simple string replacement  
**Impact**: Cosmetic fixes in logging and documentation  

```bash
# Fix logging statement
sed -i 's/RunbookRepositoryMCPServer initialized/RunbookRepositoryServer initialized/g' mcp_server/server.py

# Fix documentation
sed -i 's/class RunbookRepositoryMCPServer/class RunbookRepositoryServer/g' MCP_FUNCTIONALITY_REPORT.md
```

**Validation**: 
```bash
grep -n "RunbookRepositoryMCPServer" mcp_server/server.py MCP_FUNCTIONALITY_REPORT.md
# Should return no results
```

## Phase 2: Safe File Removal (High Priority - Low Risk)

### Step 2.1: Remove Development/Debug Artifacts
**Risk**: 🟢 None - Not used in production  
**Impact**: Remove ~235 lines of debug code  

```bash
rm tests/test_fixes_chromadb.py tests/test_final_fixes.py simple_test.py
```

**Validation**:
```bash
ls tests/test_fixes_chromadb.py tests/test_final_fixes.py simple_test.py
# Should return "No such file or directory"
```

### Step 2.2: Relocate External Tool Tests
**Risk**: 🟢 None - Preserves functionality  
**Impact**: Maintain tool test coverage in proper location  

```bash
mkdir -p tests/tools/jira
mv tests/test_jira_endpoints_agent6.py tests/tools/jira/test_api_endpoints.py
```

**Validation**:
```bash
ls tests/tools/jira/test_api_endpoints.py
# Should exist and be accessible
python -m pytest tests/tools/jira/test_api_endpoints.py --collect-only
# Should discover tests without errors
```

### Step 2.3: Remove Obsolete Architecture Tests (Part 1)
**Risk**: 🟢 None - Architecture no longer used  
**Impact**: Remove ~2,056 lines of obsolete test code  

```bash
rm tests/test_workflow_basic.py
rm -rf tests/unit/test_strategies/
```

**Validation**:
```bash
ls tests/unit/test_strategies/
# Should return "No such file or directory"
```

### Step 2.4: Remove Integration Test (CONDITIONAL)
**Risk**: 🟡 Medium - Contains unique E2E workflow coverage  
**Impact**: Remove 501 lines, but may lose test coverage  
**Condition**: Only execute if E2E coverage is added elsewhere  

```bash
# CONDITIONAL - Execute only after coverage analysis confirms safety
# rm tests/integration/test_mcp_server_integration.py
echo "SKIPPING: Requires E2E coverage analysis first"
```

## Phase 3: Functionality Consolidation (Medium Priority - Medium Risk)

### Step 3.1: Remove Redundant Mock Data from nodes.py
**Risk**: 🟢 Low - Mock data available elsewhere  
**Impact**: Remove ~96 lines of duplicate mock generation  

```bash
# Create backup first
cp nodes.py nodes.py.backup

# Remove mock data functions (to be done manually)
echo "Manual removal required for:"
echo "- _get_mock_jira_response() (lines 433-475)"  
echo "- _get_mock_confluence_response() (lines 477-529)"
```

**Validation**:
```bash
python -m pytest tests/test_nodes.py -v
# Should pass - nodes.py should work with test data instead
```

### Step 3.2: Test Suite Validation
**Risk**: 🟢 None - Validation only  
**Impact**: Confirm remaining tests work properly  

```bash
# Run remaining production tests
python -m pytest tests/test_comprehensive_chromadb_endpoints.py -v
python -m pytest tests/test_vector_chromadb_endpoints.py -v  
python -m pytest tests/test_workflow.py -v
python -m pytest tests/test_nodes.py -v

# Run relocated tool tests
python -m pytest tests/tools/ -v
```

### Step 3.3: Documentation Update
**Risk**: 🟢 None - Documentation only  
**Impact**: Update test documentation to reflect changes  

```bash
# Update README.md if it references removed tests
# Update any test documentation
echo "Update documentation to reflect new test structure"
```

## Execution Checklist

### Pre-execution Validation
- [ ] Current working directory: `src/usecases/db_runbook_finder`
- [ ] All existing tests pass: `python -m pytest tests/ -x`
- [ ] No uncommitted changes that might be lost
- [ ] Backup created if needed

### Phase 1 Execution ✅
- [ ] Step 1.1: Server class name fixes applied and validated

### Phase 2 Execution ✅  
- [ ] Step 2.1: Debug artifacts removed and validated
- [ ] Step 2.2: External tool tests relocated and validated
- [ ] Step 2.3: Obsolete architecture tests removed and validated
- [ ] Step 2.4: Integration test handling decided (skip for now)

### Phase 3 Execution ✅
- [ ] Step 3.1: Mock data functions removed and validated
- [ ] Step 3.2: Test suite validation completed
- [ ] Step 3.3: Documentation updated

### Post-execution Validation
- [ ] All remaining tests pass: `python -m pytest tests/ -v`
- [ ] Test coverage maintained at acceptable level
- [ ] No broken imports or missing dependencies
- [ ] Git status clean (all changes committed)

## Risk Mitigation

### Identified Risks
1. **E2E Workflow Coverage Gap**: `test_mcp_server_integration.py` contains unique end-to-end testing
2. **Mock Data Dependencies**: Nodes.py mock functions might be used elsewhere
3. **Test Import Dependencies**: Removed tests might be imported by other tests

### Mitigation Strategies
1. **Backup Strategy**: Create backups of critical files before modification
2. **Incremental Validation**: Test after each phase, not just at the end  
3. **Rollback Plan**: Keep removed files in git history for potential restoration
4. **Coverage Monitoring**: Run test coverage analysis before and after

## Success Criteria

### Quantitative Goals
- [ ] ~1,200 lines of obsolete code removed
- [ ] Test file count reduced from 16 to ~8 files  
- [ ] All remaining tests pass with >95% success rate
- [ ] No broken import dependencies

### Qualitative Goals  
- [ ] Cleaner codebase with focused test suite
- [ ] External tool tests properly organized for maintenance
- [ ] Production workflow tests maintained and functional
- [ ] Documentation reflects new structure

## Rollback Procedure

If issues are encountered:

```bash
# Restore from backup
git checkout HEAD -- .  # If changes not committed
# OR
git revert <commit-hash>  # If changes already committed

# Restore specific files if needed
cp nodes.py.backup nodes.py  # If backup was created
```

## Notes

- External tool tests relocated to `tests/tools/` for easier tool updates
- Integration test removal postponed pending coverage analysis
- Mock data consolidation focuses on standardizing test data approach
- All changes maintain backward compatibility for production workflows