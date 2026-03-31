#!/usr/bin/env python3
"""
inference.py — Baseline inference script for the Email Triage OpenEnv.

Uses the OpenAI API client (compatible with any OpenAI-compatible endpoint)
to run an LLM agent against all 3 tasks and produce reproducible scores.

Environment variables required:
  API_BASE_URL  — e.g. https://api.openai.com/v1 or custom LLM endpoint
  MODEL_NAME    — e.g. gpt-4o-mini, meta-llama/Llama-3-8b-instruct
  HF_TOKEN      — Hugging Face / API key

Usage:
  python inference.py
"""

import os
import json
import sys
import time
import requests
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config from environment variables
# ---------------------------------------------------------------------------
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN or "sk-placeholder",
)

TASKS = ["task_easy", "task_medium", "task_hard"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def env_reset(task_id: str) -> dict:
    r = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id, "session_id": task_id})
    r.raise_for_status()
    return r.json()

def env_step(action: dict, session_id: str) -> dict:
    r = requests.post(f"{ENV_BASE_URL}/step", json={"action": action, "session_id": session_id})
    r.raise_for_status()
    return r.json()

def env_grade(task_id: str) -> dict:
    r = requests.post(f"{ENV_BASE_URL}/grade/{task_id}", params={"session_id": task_id})
    r.raise_for_status()
    return r.json()

def build_system_prompt() -> str:
    return """You are an expert email triage agent. You manage an inbox and must:
1. READ emails to understand their content
2. CLASSIFY each email as: spam | urgent | normal | newsletter
3. REPLY to urgent emails with professional, contextually appropriate responses
4. DELETE spam emails
5. ESCALATE critical/security issues
6. UNSUBSCRIBE from newsletters
7. ARCHIVE resolved emails
8. SUMMARIZE your triage work (for hard tasks)

Respond ONLY with a valid JSON action object. No other text.

Available action types:
- {"action_type": "read", "email_id": "e001"}
- {"action_type": "classify", "email_id": "e001", "content": "urgent"}
- {"action_type": "reply", "email_id": "e001", "content": "Dear Priya, I acknowledge the issue and am initiating rollback..."}
- {"action_type": "delete", "email_id": "e002"}
- {"action_type": "archive", "email_id": "e003"}
- {"action_type": "escalate", "email_id": "e001"}
- {"action_type": "unsubscribe", "email_id": "e004"}
- {"action_type": "summarize", "content": "Triaged 10 emails: 3 urgent replied, 2 spam deleted, 2 newsletters unsubscribed, 3 archived."}
- {"action_type": "noop"}
"""

def call_llm(messages: list) -> str:
    """Call the LLM and return the raw response text."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()

def parse_action(text: str) -> dict:
    """Parse LLM output as JSON action."""
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback — return a noop
        print(f"  [WARN] Could not parse action: {text[:100]}")
        return {"action_type": "noop"}

def obs_to_text(obs: dict) -> str:
    """Convert observation dict to readable text for the LLM."""
    stats = obs.get("inbox_stats", {})
    lines = [
        f"Step {obs.get('step', '?')} | Inbox: {stats.get('total', 0)} total, "
        f"{stats.get('unread', 0)} unread, {stats.get('urgent', 0)} urgent",
        f"Last action result: {obs.get('last_action_result', '')}",
        "",
        "INBOX:",
    ]
    for email in obs.get("emails", []):
        label = email.get("label", "unread")
        replied = " [replied]" if email.get("replied") else ""
        read = " [read]" if email.get("read") else ""
        lines.append(
            f"  [{email['id']}] {label.upper():12} | {email['subject'][:50]:50} | {email['sender']}{replied}{read}"
        )
    if obs.get("open_email_body"):
        lines += ["", "OPEN EMAIL:", obs["open_email_body"]]
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_task(task_id: str) -> float:
    print(f"\n{'='*60}")
    print(f"Running task: {task_id}")
    print('='*60)

    obs = env_reset(task_id)
    messages = [{"role": "system", "content": build_system_prompt()}]
    total_reward = 0.0
    max_steps = 50

    for step_num in range(max_steps):
        obs_text = obs_to_text(obs)
        messages.append({"role": "user", "content": obs_text})

        # Limit context window — keep system + last 6 turns
        if len(messages) > 14:
            messages = [messages[0]] + messages[-13:]

        try:
            action_text = call_llm(messages)
        except Exception as e:
            print(f"  [ERROR] LLM call failed: {e}")
            break

        action = parse_action(action_text)
        print(f"  Step {step_num+1:02d}: {action.get('action_type','?'):12} | {action.get('email_id',''):5} | {str(action.get('content',''))[:40]}")

        messages.append({"role": "assistant", "content": action_text})

        try:
            result = env_step(action, session_id=task_id)
        except Exception as e:
            print(f"  [ERROR] env.step failed: {e}")
            break

        total_reward += result.get("reward", 0.0)
        obs = result.get("observation", obs)

        if result.get("done", False):
            print(f"  → Episode done at step {step_num+1}")
            break

        time.sleep(0.1)  # Small delay to avoid rate limits

    # Grade the task
    try:
        grade_result = env_grade(task_id)
        score = grade_result.get("score", 0.0)
        breakdown = grade_result.get("breakdown", {})
        print(f"\n  GRADE: {score:.3f}")
        for k, v in breakdown.items():
            print(f"    {k}: {v}")
        return score
    except Exception as e:
        print(f"  [ERROR] Grading failed: {e}")
        return 0.0

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Email Triage OpenEnv — Baseline Inference")
    print(f"Model: {MODEL_NAME} @ {API_BASE_URL}")
    print(f"Environment: {ENV_BASE_URL}")

    # Check env is reachable
    try:
        r = requests.get(f"{ENV_BASE_URL}/health", timeout=10)
        r.raise_for_status()
        print(f"Environment health: {r.json()}")
    except Exception as e:
        print(f"[ERROR] Cannot reach environment at {ENV_BASE_URL}: {e}")
        sys.exit(1)

    scores = {}
    for task_id in TASKS:
        score = run_task(task_id)
        scores[task_id] = score

    print(f"\n{'='*60}")
    print("FINAL SCORES")
    print('='*60)
    for task_id, score in scores.items():
        print(f"  {task_id:20} : {score:.3f}")
    avg = sum(scores.values()) / len(scores)
    print(f"  {'AVERAGE':20} : {avg:.3f}")
    print('='*60)

    # Write scores to file for CI
    with open("baseline_scores.json", "w") as f:
        json.dump({"scores": scores, "average": avg, "model": MODEL_NAME}, f, indent=2)
    print("\nScores written to baseline_scores.json")

if __name__ == "__main__":
    main()
