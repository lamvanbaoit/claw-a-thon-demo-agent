#!/usr/bin/env python3
import argparse
import json
import os
import sys
from itertools import cycle
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).parent
PROMPT_PATH = ROOT / "agent" / "interview_qa.md"
ROUTERS_FILE = ROOT / os.getenv("ROUTERS_FILE", "routers.json")


def load_prompt() -> str:
    return PROMPT_PATH.read_text() if PROMPT_PATH.exists() else ""


def load_routers():
    strategy = os.getenv("ROUTER_STRATEGY", "")
    routers = [os.getenv("BASE_URL", "")]
    if ROUTERS_FILE.exists():
        data = json.loads(ROUTERS_FILE.read_text())
        routers = data.get("routers", routers) or routers
        strategy = data.get("strategy", strategy)
    return routers, strategy


def get_client(base_url: str) -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "dummy")
    return OpenAI(api_key=api_key, base_url=base_url)


def build_output(topic: str, question: str, context: str = "", audience: str = ""):
    answer = (
        f"For {topic}, I would start by clarifying the goal, scope, and success criteria. "
        f"Then I would break the problem into key parts, identify risks, and validate assumptions."
    )
    stronger = (
        f"For {topic}, my approach would be: first clarify the objective and constraints, "
        f"then decompose the problem into modules or steps, define what good looks like, "
        f"and validate with evidence or examples before concluding."
    )
    key_points = [
        "Clarify goal and scope",
        "Break the problem into smaller parts",
        "State assumptions explicitly",
        "Mention risks and validation",
    ]
    follow_ups = []
    if not context:
        follow_ups.append("What is the interview context or role?")
    if not audience:
        follow_ups.append("Is this for a technical interview, QA interview, or product interview?")
    return {
        "question": question,
        "answer": answer,
        "stronger_version": stronger,
        "key_points": key_points,
        "follow_up_questions": follow_ups,
    }


def build_messages(topic: str, question: str, context: str, audience: str, prompt: str):
    user_payload = {
        "topic": topic,
        "question": question,
        "context": context,
        "audience": audience,
    }
    return [
        {"role": "system", "content": prompt or "You are an interview Q&A agent."},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def call_model(topic: str, question: str, context: str, audience: str, model: str):
    routers, strategy = load_routers()
    prompt = load_prompt()
    messages = build_messages(topic, question, context, audience, prompt)
    last_error = None

    if strategy == "round_robin":
        iterator = routers
    else:
        iterator = routers

    for base_url in iterator:
        try:
            client = get_client(base_url)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
            )
            return resp.choices[0].message.content or "", base_url
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All routers failed: {last_error}")


def main():
    parser = argparse.ArgumentParser(description="Interview Q&A agent with multi-router support")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--context", default="")
    parser.add_argument("--audience", default="")
    parser.add_argument("--model", default=os.getenv("MODEL", "minimax/minimax-m2.5"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Use local stub output instead of calling the model")
    parser.add_argument("--show-router", action="store_true", help="Print which router was used")
    args = parser.parse_args()

    if args.dry_run:
        result = build_output(args.topic, args.question, args.context, args.audience)
        used_router = None
    else:
        try:
            content, used_router = call_model(args.topic, args.question, args.context, args.audience, args.model)
            result = {"raw": content}
        except Exception as e:
            print(f"Model call failed: {e}", file=sys.stderr)
            sys.exit(1)

    if args.json:
        out = result if not args.show_router else {**result, "router": used_router}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if args.dry_run:
        print(f"## Question\n{result['question']}\n")
        print(f"## Answer\n{result['answer']}\n")
        print(f"## Stronger Version\n{result['stronger_version']}\n")
        print("## Key Points")
        for item in result["key_points"]:
            print(f"- {item}")
        if result["follow_up_questions"]:
            print("\n## Follow-up Questions")
            for item in result["follow_up_questions"]:
                print(f"- {item}")
    else:
        if args.show_router:
            print(f"[router] {used_router}")
        print(result["raw"])


if __name__ == "__main__":
    main()
