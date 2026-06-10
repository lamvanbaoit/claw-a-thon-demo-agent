# claw-a-thon-demo-agent

A simple interview Q&A agent wired for an OpenAI-compatible model, configured to use VNG Cloud MaaS (Minimax model).

## What it does

- Takes a question/interview topic
- Supports multiple routers/endpoints (configured to use VNG Cloud MaaS API platform)
- Calls `MODEL=minimax/minimax-m2.5` through configured `BASE_URL`s
- Produces structured interview-style Q&A

## Files

- `agent/interview_qa.md` — agent prompt
- `agent_schema.json` — expected input/output shape
- `run_interview.py` — runner program
- `.env.example` — model config example
- `routers.json` — router list and strategy
- `requirements.txt` — Python dependencies

## Setup

```bash
cd /Users/lap14947/Documents/claw-a-thon-demo-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Config your `.env` with the following variables:
```env
MODEL=minimax/minimax-m2.5
BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
OPENAI_API_KEY=your_actual_vng_cloud_api_key
ROUTERS_FILE=routers.json
ROUTER_STRATEGY=round_robin
```

## Router config

`routers.json` example:

```json
{
  "strategy": "round_robin",
  "routers": [
    "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"
  ]
}
```

## Run with the model

Remember to load your environment variables before running:

```bash
export $(grep -v '^#' .env | xargs) && python run_interview.py \
  --topic "ZaloPay SB testing" \
  --question "How would you test the loan repayment create API?" \
  --show-router
```

## Dry run without model

```bash
python run_interview.py \
  --topic "ZaloPay SB testing" \
  --question "How would you test this flow?" \
  --dry-run
```

