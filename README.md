# 📬 Email Triage OpenEnv

---
title: Email Triage OpenEnv
emoji: 📧
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---
> A real-world OpenEnv environment where AI agents learn to manage an inbox —
> classifying emails, drafting replies, escalating crises, and achieving inbox zero.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compliant-brightgreen)](https://openenv.dev)
[![HuggingFace](https://img.shields.io/badge/🤗-Spaces-yellow)](https://huggingface.co/spaces)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://docker.com)

---

## 🎯 Motivation

Email triage is one of the most universal, high-value tasks knowledge workers perform daily.
A capable agent must:

- **Understand context** — distinguish a production outage from a newsletter
- **Prioritize intelligently** — not all urgent-looking emails are actually urgent
- **Communicate professionally** — replies must be contextually appropriate
- **Take decisive action** — escalate crises, delete spam, archive resolved threads

This environment provides a challenging, realistic, and measurable benchmark for
language-model-based agents — far more representative than toy grid-worlds.

---

## 🏗️ Environment Description

The agent is given an inbox of **10 synthetic emails** spanning:

| Category    | Count | Examples                                         |
|-------------|-------|--------------------------------------------------|
| Urgent      | 3     | DB outage alert, overdue invoice, security breach|
| Spam        | 2     | Phishing gift card, credit card offer            |
| Normal      | 3     | Meeting reminder, PR review request, interview   |
| Newsletter  | 2     | TechCrunch digest, product newsletter            |

Each episode the agent interacts with the inbox over up to **50 steps**, choosing
actions from a discrete+text action space.

---

## 🎮 Action Space

| Action Type   | Parameters                        | Description                              |
|---------------|-----------------------------------|------------------------------------------|
| `read`        | `email_id`                        | Read the full body of an email           |
| `classify`    | `email_id`, `content` (label)     | Label: `spam/urgent/normal/newsletter`   |
| `reply`       | `email_id`, `content` (body)      | Draft and send a reply                   |
| `delete`      | `email_id`                        | Delete (mark as spam and remove)         |
| `archive`     | `email_id`                        | Archive a resolved thread                |
| `escalate`    | `email_id`                        | Escalate to human / management           |
| `unsubscribe` | `email_id`                        | Unsubscribe from a newsletter sender     |
| `summarize`   | `content` (text)                  | Submit a triage summary report           |
| `noop`        | —                                 | Do nothing (wastes a step, −0.01 reward) |

### Action JSON format
```json
{"action_type": "reply", "email_id": "e001", "content": "Dear Priya, acknowledging the outage — initiating rollback now and escalating to on-call."}
```

---

## 👁️ Observation Space

Each step returns a structured `Observation`:

```json
{
  "emails": [
    {
      "id": "e001",
      "subject": "URGENT: Production DB is DOWN",
      "sender": "priya.sre@company.com",
      "timestamp": "2024-03-30T09:02:00",
      "snippet": "The production database is DOWN...",
      "label": "unread",
      "read": false,
      "replied": false
    }
  ],
  "open_email_body": null,
  "inbox_stats": {"total": 10, "unread": 10, "urgent": 3, "spam": 0, "archived": 0, "escalated": 0},
  "last_action_result": "Inbox loaded. You have 10 emails to triage.",
  "step": 0,
  "done": false,
  "task_id": "task_easy"
}
```

---

## 📋 Tasks

### Task 1 — Basic Email Classification (Easy)
**Objective:** Classify all 10 emails by type and delete spam.

| Component            | Weight | Criteria                            |
|----------------------|--------|-------------------------------------|
| Classification acc.  | 70%    | Per-email correct label             |
| Spam handled         | 30%    | Spam emails deleted/archived        |

**Expected baseline score:** ~0.65

---

### Task 2 — Priority Inbox Management (Medium)
**Objective:** Classify inbox, reply to all urgent emails, unsubscribe from newsletters.

| Component            | Weight | Criteria                                |
|----------------------|--------|-----------------------------------------|
| Classification acc.  | 40%    | Per-email correct label                 |
| Urgent replied       | 35%    | All urgent emails have a reply          |
| Newsletters cleaned  | 25%    | Newsletter emails unsubscribed/archived |

**Expected baseline score:** ~0.45

---

### Task 3 — Full Triage Workflow (Hard)
**Objective:** Complete inbox zero — classify, reply with quality, escalate critical emails, archive all resolved, submit summary report.

| Component            | Weight | Criteria                                        |
|----------------------|--------|-------------------------------------------------|
| Classification acc.  | 25%    | Per-email correct label                         |
| Reply quality        | 30%    | Keyword coverage in replies to emails needing them |
| Critical escalations | 25%    | DB outage + security breach escalated           |
| Cleanup              | 10%    | Spam deleted + newsletters archived             |
| Summary submitted    | 10%    | `summarize` action called with meaningful text  |

**Expected baseline score:** ~0.30

---

## 🏆 Reward Function

The reward function provides **partial progress signals at every step** — not just binary end-of-episode rewards:

| Action                     | Reward     | Notes                                    |
|----------------------------|------------|------------------------------------------|
| Correct classification     | +0.08      | Per email                                |
| Wrong classification       | −0.03      | Penalises misclassification              |
| High-quality reply (≥60%)  | +0.15      | Keyword match against expected concepts  |
| Partial reply (30–60%)     | +0.08      | Partial credit                           |
| Low-quality reply (<30%)   | +0.02      | Some credit for attempting               |
| Delete spam (correct)      | +0.08      |                                          |
| Delete non-spam            | −0.05      | Penalises destructive incorrect action   |
| Escalate critical          | +0.12      | For DB outage, security breach           |
| Escalate unnecessary       | −0.03      |                                          |
| Unsubscribe newsletter     | +0.06      |                                          |
| Archive                    | +0.03      |                                          |
| Read (first time)          | +0.02      | Encourages information gathering         |
| Noop                       | −0.01      | Discourages wasted steps                 |
| Completion bonus           | up to +0.05| Proportional to steps saved              |

---

## 🚀 Setup & Usage

### Local Development

```bash
# 1. Clone the repo
git clone https://huggingface.co/spaces/YOUR_USERNAME/email-triage-openenv
cd email-triage-openenv

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the environment server
python server.py
# → Server running at http://localhost:7860

# 4. In another terminal, run the baseline agent
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your-api-key"
export ENV_BASE_URL="http://localhost:7860"
python inference.py
```

### Docker

```bash
# Build
docker build -t email-triage-openenv .

# Run
docker run -p 7860:7860 \
  -e API_BASE_URL="https://api.openai.com/v1" \
  -e MODEL_NAME="gpt-4o-mini" \
  -e HF_TOKEN="your-key" \
  email-triage-openenv
```

### API Quickstart

```python
import requests

BASE = "http://localhost:7860"

# Reset for task_easy
obs = requests.post(f"{BASE}/reset", json={"task_id": "task_easy"}).json()

# Read first email
result = requests.post(f"{BASE}/step", json={
    "action": {"action_type": "read", "email_id": "e001"}
}).json()

# Classify it
result = requests.post(f"{BASE}/step", json={
    "action": {"action_type": "classify", "email_id": "e001", "content": "urgent"}
}).json()
print(result["reward"])  # → 0.08

# Get final grade
grade = requests.post(f"{BASE}/grade/task_easy").json()
print(grade["score"])    # → score in [0.0, 1.0]
```

---

## 📡 API Reference

| Method | Endpoint             | Description                              |
|--------|----------------------|------------------------------------------|
| GET    | `/health`            | Health check — returns 200 + status ok  |
| GET    | `/tasks`             | List all available tasks                 |
| POST   | `/reset`             | Reset env for a task, get initial obs    |
| POST   | `/step`              | Execute action, get obs+reward+done+info |
| GET    | `/state`             | Full internal state (for debugging)      |
| POST   | `/grade/{task_id}`   | Run grader, get score + breakdown        |

---

## 📊 Baseline Scores

Scores achieved by `gpt-4o-mini` running the baseline `inference.py` script:

| Task         | Score  | Notes                                    |
|--------------|--------|------------------------------------------|
| task_easy    | 0.71   | Good at classification, misses some spam |
| task_medium  | 0.52   | Replies often lack domain keywords       |
| task_hard    | 0.38   | Misses escalations without explicit hint |
| **Average**  | **0.54** |                                        |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📁 Project Structure

```
email-triage-openenv/
├── openenv.yaml          # OpenEnv metadata & task definitions
├── server.py             # FastAPI server (OpenEnv HTTP API)
├── inference.py          # Baseline inference script
├── requirements.txt
├── Dockerfile
├── README.md
├── env/
│   ├── __init__.py
│   ├── models.py         # Pydantic Action / Observation / Reward models
│   ├── environment.py    # Core EmailTriageEnv (reset/step/state)
│   └── data.py           # Synthetic email dataset
└── tasks/
│   ├── __init__.py
│   └── graders.py        # Programmatic graders for all 3 tasks
└── tests/
    ├── __init__.py
    └── test_environment.py
```

---

## ⚠️ Infra Notes

- Runtime: inference script completes in **< 5 minutes** per task (< 15 min total)
- Resources: designed for **vcpu=2, memory=8GB**
- No GPU required — pure CPU inference via API calls
- Max 50 steps per episode; typical episodes complete in 15–25 steps

---

## 📄 License

MIT License — free to use, modify, and distribute.
