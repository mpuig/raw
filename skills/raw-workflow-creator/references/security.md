# Security checklist

Security requirements for RAW workflows.

## Before delivering any workflow

- [ ] **No hardcoded secrets** - All API keys use environment variables
- [ ] **No secrets in logs** - Don't print API keys or tokens
- [ ] **Input validation** - Validate user inputs before using them
- [ ] **Safe file paths** - Don't allow path traversal (`../`)
- [ ] **Timeout on all requests** - Prevent hanging on unresponsive APIs
- [ ] **No eval/exec** - Never execute user-provided code

## Environment variable pattern

```python
import os

api_key = os.environ.get("API_KEY")
if not api_key:
    raise ValueError("API_KEY environment variable not set. Add it to .env file.")
```

## Safe file handling

```python
from pathlib import Path

def save_result(filename: str, data: str) -> Path:
    # Prevent path traversal
    safe_name = Path(filename).name  # Strips any directory components
    output_path = self.results_dir / safe_name
    output_path.write_text(data)
    return output_path
```

## Network timeouts

```python
import httpx

response = httpx.get(url, timeout=30)  # Always set timeout
```
