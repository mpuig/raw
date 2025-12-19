# Quick start guide

Get the call center solution running in 5 minutes.

## Prerequisites

- Python 3.10+
- uv installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- API keys for: OpenAI/Anthropic, Deepgram, ElevenLabs, Twilio

## Steps

### 1. Install dependencies

```bash
cd examples/solution-callcenter
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
```

### 3. Run the server

```bash
uv run python -m callcenter.main
```

The server will start on `http://localhost:8000`.

### 4. Check health

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "checks": {
    "liveness": {"status": "healthy"}
  }
}
```

### 5. Test with Twilio

For local development, expose your server publicly with ngrok:

```bash
ngrok http 8000
```

Then configure your Twilio phone number webhook:

- Voice webhook: `https://your-id.ngrok.io/voice/twilio`
- Status callback: `https://your-id.ngrok.io/voice/status`

Call your Twilio number to test the AI agent!

## What's next

- Customize the system prompt in `src/callcenter/prompts.py`
- Add new skills in `src/callcenter/skills/`
- Modify the post-call workflow in `src/callcenter/workflows/post_call.py`
- Connect to your CRM by implementing the database interfaces

## Troubleshooting

**Server won't start:**
- Check that all required API keys are set in `.env`
- Verify Python version: `python --version` (should be 3.10+)

**Health check fails:**
- Ensure no other service is using port 8000
- Check server logs for error messages

**Calls don't connect:**
- Verify Twilio webhook URLs are publicly accessible
- Check Twilio console for webhook error logs
- Ensure webhook path matches config.yaml

## Documentation

- Full documentation: [README.md](README.md)
- Architecture details: [ARCHITECTURE.md](ARCHITECTURE.md)
- RAW Platform docs: [../../docs/](../../docs/)
