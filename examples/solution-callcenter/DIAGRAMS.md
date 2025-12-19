# Visual diagrams

Text-based diagrams explaining the call center solution architecture and flows.

## System architecture

```
                                 Internet
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              ┌─────▼─────┐   ┌────▼────┐   ┌─────▼─────┐
              │  Customer │   │   Web   │   │    SMS    │
              │   Phone   │   │   Chat  │   │  Customer │
              └─────┬─────┘   └────┬────┘   └─────┬─────┘
                    │               │               │
                    │               │               │
              ┌─────▼──────────────▼───────────────▼─────┐
              │          Twilio Voice Gateway             │
              │     (Phone, SMS, WebRTC connections)      │
              └─────────────────┬───────────────────────┬─┘
                                │                       │
                                │                       │
          ┌─────────────────────▼───────────────────────▼──────┐
          │                  Load Balancer                      │
          │              (nginx / AWS ALB)                      │
          └─────────┬────────────────────────────┬──────────────┘
                    │                            │
          ┌─────────▼────────┐         ┌────────▼──────────┐
          │  App Instance 1  │         │  App Instance 2   │
          │  ┌────────────┐  │         │  ┌────────────┐   │
          │  │  FastAPI   │  │         │  │  FastAPI   │   │
          │  │   Server   │  │         │  │   Server   │   │
          │  └─────┬──────┘  │         │  └─────┬──────┘   │
          │        │         │         │        │          │
          │  ┌─────▼──────┐  │         │  ┌─────▼──────┐   │
          │  │Conversation│  │         │  │Conversation│   │
          │  │  Engine    │  │         │  │  Engine    │   │
          │  └────────────┘  │         │  └────────────┘   │
          └─────────┬────────┘         └─────────┬──────────┘
                    │                            │
                    │                            │
          ┌─────────▼────────────────────────────▼──────────┐
          │              Shared Services                     │
          │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
          │  │  Redis   │  │PostgreSQL│  │   LLM    │      │
          │  │  (State) │  │  (Data)  │  │ Provider │      │
          │  └──────────┘  └──────────┘  └──────────┘      │
          └──────────────────────────────────────────────────┘
```

## Voice call flow

```
┌─────────┐                                                    ┌──────────┐
│Customer │                                                    │ Twilio   │
└────┬────┘                                                    └────┬─────┘
     │                                                              │
     │ 1. Dial phone number                                        │
     ├──────────────────────────────────────────────────────────►  │
     │                                                              │
     │                                                         ┌────▼─────┐
     │                                                         │Call Center│
     │                                                         │   Server  │
     │                                                         └────┬─────┘
     │                                                              │
     │ 2. TwiML response (WebSocket URL)                           │
     │ ◄────────────────────────────────────────────────────────── │
     │                                                              │
     │ 3. WebSocket connection established                         │
     ├──────────────────────────────────────────────────────────►  │
     │                                                              │
     │                                                         ┌────▼─────┐
     │                                                         │Voice     │
     │                                                         │Pipeline  │
     │                                                         │(Pipecat) │
     │                                                         └────┬─────┘
     │                                                              │
     │ 4. Audio stream (bidirectional)                             │
     ├──────────────────────────────────────────────────────────►  │
     │ ◄────────────────────────────────────────────────────────── │
     │                                                              │
     │                                                         ┌────▼─────┐
     │                                                         │ Deepgram │
     │                                                         │   STT    │
     │                                                         └────┬─────┘
     │                                                              │
     │                                                         ┌────▼─────┐
     │                                                         │   Bot    │
     │                                                         │  Engine  │
     │                                                         └────┬─────┘
     │                                                              │
     │                                                         ┌────▼─────┐
     │                                                         │   LLM    │
     │                                                         │(GPT/Claude│
     │                                                         └────┬─────┘
     │                                                              │
     │                                                         ┌────▼─────┐
     │                                                         │ElevenLabs│
     │                                                         │   TTS    │
     │                                                         └────┬─────┘
     │                                                              │
     │ 5. AI response (audio)                                      │
     │ ◄────────────────────────────────────────────────────────── │
     │                                                              │
     │ 6. Call ends                                                 │
     ├──────────────────────────────────────────────────────────►  │
     │                                                              │
     │                                                         ┌────▼─────┐
     │                                                         │Post-Call │
     │                                                         │Workflow  │
     │                                                         └──────────┘
     │
```

## Conversation turn flow

```
┌─────────┐      ┌──────────┐      ┌─────┐      ┌─────────┐      ┌──────────┐
│Customer │      │   STT    │      │ Bot │      │   LLM   │      │   TTS    │
└────┬────┘      └────┬─────┘      └──┬──┘      └────┬────┘      └────┬─────┘
     │                │                │               │                │
     │ Speaks         │                │               │                │
     ├───────────────►│                │               │                │
     │                │                │               │                │
     │                │ Text           │               │                │
     │                ├───────────────►│               │                │
     │                │                │               │                │
     │                │                │ Messages +    │                │
     │                │                │ Tools Schema  │                │
     │                │                ├──────────────►│                │
     │                │                │               │                │
     │                │                │               │ Tool call?     │
     │                │                │               ├───────────┐    │
     │                │                │               │           │    │
     │                │                │               │◄──────────┘    │
     │                │                │               │                │
     │                │                │◄──Tool Call───┤                │
     │                │                │               │                │
     │                │ Execute Tool   │               │                │
     │                │ ◄──────────────┤               │                │
     │                │                │               │                │
     │                │ Tool Result    │               │                │
     │                │ ───────────────►               │                │
     │                │                │               │                │
     │                │                │ Tool Result   │                │
     │                │                ├──────────────►│                │
     │                │                │               │                │
     │                │                │               │ Generate       │
     │                │                │               │ Response       │
     │                │                │               ├───────────┐    │
     │                │                │               │           │    │
     │                │                │               │◄──────────┘    │
     │                │                │               │                │
     │                │                │◄──Response────┤                │
     │                │                │               │                │
     │                │                │ Response Text │                │
     │                │                ├───────────────────────────────►│
     │                │                │               │                │
     │                │                │               │                │ Audio
     │ Hears          │                │               │                │
     │◄───────────────────────────────────────────────────────────────┤
     │                │                │               │                │
```

## Tool execution flow

```
┌─────────────┐
│     LLM     │
│   Decides   │
│  to call    │
│    tool     │
└──────┬──────┘
       │
       │ Tool call: check_order_status(order_id="ORD-12345")
       │
       ▼
┌─────────────────────┐
│   Tool Executor     │
│  (CallCenterTool    │
│     Executor)       │
└──────┬──────────────┘
       │
       │ 1. Lookup tool function in registry
       │
       ▼
┌─────────────────────┐
│   Tool Function     │
│ check_order_status  │
└──────┬──────────────┘
       │
       │ 2. Call function with arguments
       │
       ▼
┌─────────────────────┐
│  Mock Database /    │
│  Real API Call      │
└──────┬──────────────┘
       │
       │ 3. Return result
       │
       ▼
┌─────────────────────┐
│  {                  │
│    "success": true, │
│    "status": "...", │
│    "tracking": "..." │
│  }                  │
└──────┬──────────────┘
       │
       │ 4. Return to LLM
       │
       ▼
┌─────────────────────┐
│      LLM            │
│  Generates natural  │
│  language response  │
└─────────────────────┘
```

## Post-call workflow

```
┌──────────────┐
│  Call Ends   │
└──────┬───────┘
       │
       │ Trigger
       │
       ▼
┌──────────────────────┐
│  Post-Call Workflow  │
└──────┬───────────────┘
       │
       ├─────► Step 1: Generate Summary
       │       ┌──────────────────┐
       │       │ Use LLM to       │
       │       │ summarize        │
       │       │ transcript       │
       │       └────────┬─────────┘
       │                │
       ├─────► Step 2: Update CRM
       │       ┌──────────────────┐
       │       │ Create activity  │
       │       │ record in CRM    │
       │       └────────┬─────────┘
       │                │
       ├─────► Step 3: Send Email (if needed)
       │       ┌──────────────────┐
       │       │ Send follow-up   │
       │       │ email to customer│
       │       └────────┬─────────┘
       │                │
       ├─────► Step 4: Create Ticket (if low satisfaction)
       │       ┌──────────────────┐
       │       │ Create support   │
       │       │ ticket for       │
       │       │ follow-up        │
       │       └────────┬─────────┘
       │                │
       └─────► Step 5: Log Metrics
               ┌──────────────────┐
               │ Send to analytics│
               │ system (DataDog, │
               │ New Relic, etc.) │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │  Workflow        │
               │  Complete        │
               └──────────────────┘
```

## Configuration loading

```
┌──────────────────┐
│ Application      │
│ Startup          │
└────────┬─────────┘
         │
         │ 1. Load config.yaml
         │
         ▼
┌──────────────────┐
│  config.yaml     │
│  (defaults)      │
└────────┬─────────┘
         │
         │ 2. Override with environment variables
         │
         ▼
┌──────────────────┐
│  .env file /     │
│  ENV vars        │
└────────┬─────────┘
         │
         │ 3. Parse with Pydantic
         │
         ▼
┌──────────────────┐
│  CallCenterConfig│
│  (validated)     │
└────────┬─────────┘
         │
         │ 4. Validate required keys
         │
         ▼
┌──────────────────┐
│  Config ready    │
│  for use         │
└──────────────────┘
```

## Skill registration

```
┌─────────────────────────┐
│  skills/__init__.py     │
└───────────┬─────────────┘
            │
            │ Import all skill modules
            │
            ▼
┌──────────────────────────────────────────┐
│  lookup_customer.py                      │
│  ┌──────────────────────────────────┐   │
│  │ def lookup_customer(...)         │   │
│  │     return {...}                 │   │
│  │                                  │   │
│  │ TOOL_SCHEMA = {                 │   │
│  │   "name": "lookup_customer",    │   │
│  │   "description": "...",         │   │
│  │   "parameters": {...}           │   │
│  │ }                               │   │
│  └──────────────────────────────────┘   │
└────────────────┬─────────────────────────┘
                 │
                 │ Register in
                 │
                 ▼
┌─────────────────────────────────────────┐
│  TOOLS_REGISTRY = {                     │
│    "lookup_customer": lookup_customer,  │
│    "check_order": check_order_status,   │
│    ...                                  │
│  }                                      │
│                                         │
│  TOOLS_SCHEMA = [                       │
│    LOOKUP_CUSTOMER_SCHEMA,              │
│    CHECK_ORDER_SCHEMA,                  │
│    ...                                  │
│  ]                                      │
└─────────────────┬───────────────────────┘
                  │
                  │ Used by
                  │
                  ▼
┌─────────────────────────────────────────┐
│  ConversationEngine                     │
│  - tools_schema → sent to LLM           │
│  - executor → executes tools            │
└─────────────────────────────────────────┘
```

## Error handling flow

```
┌──────────────┐
│  Tool Call   │
└──────┬───────┘
       │
       │ Try execute
       │
       ▼
┌──────────────────┐
│  Tool Function   │
└──────┬───────────┘
       │
       ├─────► Success path
       │       ┌──────────────────┐
       │       │ Return result:   │
       │       │ {                │
       │       │   "success": true│
       │       │   "data": {...}  │
       │       │ }                │
       │       └────────┬─────────┘
       │                │
       │                ▼
       │       ┌──────────────────┐
       │       │ LLM uses result  │
       │       │ in response      │
       │       └──────────────────┘
       │
       └─────► Error path
               ┌──────────────────┐
               │ Catch exception  │
               │ Return error:    │
               │ {                │
               │   "success":false│
               │   "error": "..." │
               │   "message":"..."│
               │ }                │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │ LLM interprets   │
               │ error and        │
               │ explains to user │
               └──────────────────┘
```

## Deployment architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Cloud Provider                       │
│                  (AWS / GCP / Azure)                    │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │              Kubernetes Cluster                   │ │
│  │                                                   │ │
│  │  ┌──────────────┐         ┌──────────────┐     │ │
│  │  │   Ingress    │         │   Ingress    │     │ │
│  │  │  Controller  │         │  Controller  │     │ │
│  │  └──────┬───────┘         └──────┬───────┘     │ │
│  │         │                         │             │ │
│  │         ▼                         ▼             │ │
│  │  ┌──────────────┐         ┌──────────────┐     │ │
│  │  │  Call Center │         │  Call Center │     │ │
│  │  │     Pod 1    │         │     Pod 2    │     │ │
│  │  └──────┬───────┘         └──────┬───────┘     │ │
│  │         │                         │             │ │
│  │         └────────────┬────────────┘             │ │
│  │                      │                          │ │
│  │                      ▼                          │ │
│  │         ┌────────────────────────┐              │ │
│  │         │    Redis Cluster       │              │ │
│  │         │   (State Storage)      │              │ │
│  │         └────────────────────────┘              │ │
│  │                      │                          │ │
│  │                      ▼                          │ │
│  │         ┌────────────────────────┐              │ │
│  │         │  PostgreSQL (RDS)      │              │ │
│  │         │   (Data Storage)       │              │ │
│  │         └────────────────────────┘              │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  External Services:                                     │
│  - OpenAI / Anthropic                                  │
│  - Deepgram                                            │
│  - ElevenLabs                                          │
│  - Twilio                                              │
└─────────────────────────────────────────────────────────┘
```
