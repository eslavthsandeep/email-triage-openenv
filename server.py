"""
server.py — FastAPI server implementing the OpenEnv HTTP API.

Endpoints:
  POST /reset          → reset environment, return initial observation
  POST /step           → execute action, return (obs, reward, done, info)
  GET  /state          → return full internal state
  GET  /health         → health check
  GET  /tasks          → list available tasks
  POST /grade/{task_id} → run grader and return score
"""

from __future__ import annotations
import os
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from env.environment import EmailTriageEnv
from env.models import Action
from tasks.graders import run_grader, GRADERS

app = FastAPI(
    title="Email Triage OpenEnv",
    description=(
        "A real-world email triage environment for AI agent training and evaluation. "
        "Implements the full OpenEnv spec: step() / reset() / state()."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory environment store (one env per session — suitable for hackathon/eval)
_envs: Dict[str, EmailTriageEnv] = {}
_DEFAULT_SESSION = "default"


def _get_env(session_id: str = _DEFAULT_SESSION) -> EmailTriageEnv:
    if session_id not in _envs:
        _envs[session_id] = EmailTriageEnv()
    return _envs[session_id]


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    task_id: Optional[str] = "task_easy"
    session_id: Optional[str] = _DEFAULT_SESSION


class StepRequest(BaseModel):
    action: Action
    session_id: Optional[str] = _DEFAULT_SESSION


class StepResponse(BaseModel):
    observation: dict
    reward: float
    done: bool
    info: dict


class GradeResponse(BaseModel):
    task_id: str
    score: float
    breakdown: dict


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check — returns 200 if the server is up."""
    return {"status": "ok", "service": "email-triage-openenv"}


@app.get("/tasks")
async def list_tasks():
    """List all available tasks."""
    tasks = [
        {
            "id": "task_easy",
            "name": "Basic Email Classification",
            "difficulty": "easy",
            "description": "Classify all emails and mark spam for deletion.",
        },
        {
            "id": "task_medium",
            "name": "Priority Inbox Management",
            "difficulty": "medium",
            "description": "Sort inbox, reply to urgent emails, unsubscribe from newsletters.",
        },
        {
            "id": "task_hard",
            "name": "Full Triage Workflow",
            "difficulty": "hard",
            "description": "Complete inbox zero: classify, reply, escalate, archive, summarize.",
        },
    ]
    return {"tasks": tasks}


# @app.post("/reset")
# async def reset(request: ResetRequest):
#     """Reset the environment for a given task and return the initial observation."""
#     task_id = request.task_id or "task_easy"
#     session_id = request.session_id or _DEFAULT_SESSION
#     env = EmailTriageEnv(task_id=task_id)
#     _envs[session_id] = env
#     obs = env.reset()
#     return obs.model_dump()
@app.post("/reset")
async def reset(request: ResetRequest):
    """Reset the environment for a given task and return the initial observation."""
    task_id = request.task_id or "task_easy"
    session_id = request.session_id or _DEFAULT_SESSION

    env = EmailTriageEnv(task_id=task_id)
    _envs[session_id] = env

    obs = env.reset()

    return {
        "observation": obs.model_dump(),  # wrap it
        "reward": 0,
        "done": False,
        "info": {}
    }


@app.post("/step", response_model=StepResponse)
async def step(request: StepRequest):
    """Execute one action and return the new observation, reward, done flag, and info."""
    session_id = request.session_id or _DEFAULT_SESSION
    env = _get_env(session_id)
    try:
        obs, reward, done, info = env.step(request.action)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StepResponse(
        observation=obs.model_dump(),
        reward=reward,
        done=done,
        info=info,
    )


@app.get("/state")
async def state(session_id: str = _DEFAULT_SESSION):
    """Return the full internal environment state (for debugging/evaluation)."""
    env = _get_env(session_id)
    raw_state = env.state()
    # Serialize enums
    serializable = {}
    for k, v in raw_state.items():
        if k == "emails":
            serializable[k] = {
                eid: {
                    ek: ev.value if hasattr(ev, "value") else ev
                    for ek, ev in email.items()
                }
                for eid, email in v.items()
            }
        else:
            serializable[k] = v
    return serializable


@app.post("/grade/{task_id}", response_model=GradeResponse)
async def grade(task_id: str, session_id: str = _DEFAULT_SESSION):
    """Run the programmatic grader for the given task and return the score."""
    if task_id not in GRADERS:
        raise HTTPException(status_code=404, detail=f"Unknown task_id '{task_id}'.")
    env = _get_env(session_id)
    raw_state = env.state()
    score, breakdown = run_grader(task_id, raw_state)
    return GradeResponse(task_id=task_id, score=score, breakdown=breakdown)


# ---------------------------------------------------------------------------
# Entry point (for local dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
