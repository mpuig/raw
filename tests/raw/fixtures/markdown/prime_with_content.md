# RAW Context

> Run `raw prime` after compaction or new session

## Quick Reference

```bash
raw search "capability"            # Search tools (DO THIS FIRST)
raw list tools                     # Browse tools
raw create <name> --intent "..."   # Create workflow
raw create <name> --tool -d "..."  # Create tool (only if search finds nothing)
raw run <id> --dry                 # Test with mocks
raw run <id> [args]                # Execute
```

## Key Rules

1. **SEARCH FIRST** - `raw search` before creating tools
2. **Tools in `tools/`** - Reusable packages, auto-snapshotted on run
3. **Test before delivery** - `raw run --dry` before telling user it's ready
4. **Workflows immutable after publish** - use `raw create --from` to modify

## Creating Workflows

```bash
raw create stock-analysis --intent "Fetch TSLA data, calculate RSI"
# Implement run.py using tools from tools/
raw run <id> --dry                 # Test
raw run <id> --ticker TSLA         # Execute
```

## Creating Tools

```bash
raw search "stock data"            # Check existing first!
raw create fetch_stock --tool -d "Fetch stock data from yfinance"
# Implement tools/fetch_stock/tool.py + __init__.py + config.yaml
```

---

## Workflows (2)

- ✅ **stock-analysis** - Analyze TSLA stock data and generate charts
- 📝 **daily-report** - Generate daily sales report from database

## Tools (2)

- **fetch_stock**: Fetch stock data from yfinance
- **generate-pdf**: Generate PDF reports
