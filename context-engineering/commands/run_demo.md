# Run Manager GraphMCP Demo

Execute the Manager component's GraphMCP framework database decommissioning workflow demonstration.

## Demo Execution

```bash
# Navigate to GraphMCP framework
cd src/frameworks/graphmcp

# Activate virtual environment
source .venv/bin/activate

# Run the database workflow demo with real processing
python run_db_workflow.py --database postgres_air --repo "https://github.com/bprzybysz/postgres-sample-dbs" --real

# Alternative: Run with mock data for faster demo
python run_db_workflow.py --database postgres_air --repo "https://github.com/bprzybysz/postgres-sample-dbs"
```

## Demo Validation

1. **Analyze Output**
   - Review workflow execution logs
   - Check structured logging output
   - Verify step completion status
   - Analyze performance metrics

2. **Identify Issues**
   - Check for MCP connection errors
   - Review workflow step failures
   - Analyze performance bottlenecks
   - Identify configuration issues

3. **Fix and Retry**
   - Address identified issues
   - Re-run demo to validate fixes
   - Document resolution steps
   - Update configuration if needed

## Alternative Demo Commands

```bash
# Quick demo with cached data (30 seconds)
make demo-mock

# Full demo with live MCP services (5-10 minutes)
make demo-real

# Complete database decommissioning workflow
make cmp DB=postgres_air

# Start demo UI for interactive workflow monitoring
make preview-streamlit
```

## Demo Success Criteria

- [ ] Workflow completes without errors
- [ ] All MCP clients connect successfully
- [ ] Database pattern discovery functions
- [ ] GitHub integration works (if configured)
- [ ] Slack notifications sent (if configured)
- [ ] Performance metrics within acceptable ranges
- [ ] Structured logging captures all steps

## Troubleshooting

**Common Issues:**
- MCP server connection failures → Check mcp_config.json
- GitHub token issues → Verify GITHUB_TOKEN environment variable
- Slack integration issues → Check SLACK_BOT_TOKEN configuration
- Performance issues → Check system resources and network connectivity

**Resolution Steps:**
1. Check GraphMCP configuration files
2. Verify environment variables
3. Test MCP server connectivity
4. Review structured logs for detailed error information
5. Consult GraphMCP documentation for specific issues