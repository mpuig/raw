# Security checklist

Security requirements for RAW tools.

## Before delivering any tool

- [ ] **No hardcoded secrets** - Use environment variables
- [ ] **Input validation** - Check all parameters before use
- [ ] **No arbitrary code execution** - Never use eval/exec on inputs
- [ ] **Safe file operations** - Validate paths, prevent traversal
- [ ] **Timeout on network calls** - Prevent indefinite hangs

## Secure API key access

```python
import os

def fetch_data(ticker: str) -> dict:
    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("API_KEY not set in environment")
    # Use api_key safely...
```

## Input sanitization

```python
from pathlib import Path

def process_file(filepath: str) -> dict:
    # Prevent path traversal attacks
    safe_path = Path(filepath).resolve()
    if not safe_path.is_relative_to(Path.cwd()):
        raise ValueError("Invalid file path")
    return safe_path.read_text()
```

## Network timeouts

```python
import httpx

def fetch_api(url: str) -> dict:
    # Always set timeout to prevent hanging
    response = httpx.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
```

## Safe error messages

Don't leak sensitive information in errors:

```python
def authenticate(token: str) -> bool:
    # Bad - leaks valid tokens exist
    # raise ValueError(f"Token {token} not found")

    # Good - generic message
    raise ValueError("Authentication failed")
```
