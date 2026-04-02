# """
# server.py — FastAPI server implementing the OpenEnv HTTP API.

# Endpoints:
#   POST /reset          → reset environment, return initial observation
#   POST /step           → execute action, return (obs, reward, done, info)
#   GET  /state          → return full internal state
#   GET  /health         → health check
#   GET  /tasks          → list available tasks
#   POST /grade/{task_id} → run grader and return score
# """

# from __future__ import annotations
# import os
# from typing import Optional, Dict, Any

# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel

# from env.environment import EmailTriageEnv
# from env.models import Action
# from tasks.graders import run_grader, GRADERS

# app = FastAPI(
#     title="Email Triage OpenEnv",
#     description=(
#         "A real-world email triage environment for AI agent training and evaluation. "
#         "Implements the full OpenEnv spec: step() / reset() / state()."
#     ),
#     version="1.0.0",
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # In-memory environment store (one env per session — suitable for hackathon/eval)
# _envs: Dict[str, EmailTriageEnv] = {}
# _DEFAULT_SESSION = "default"


# def _get_env(session_id: str = _DEFAULT_SESSION) -> EmailTriageEnv:
#     if session_id not in _envs:
#         _envs[session_id] = EmailTriageEnv()
#     return _envs[session_id]


# # ---------------------------------------------------------------------------
# # Request / Response schemas
# # ---------------------------------------------------------------------------

# class ResetRequest(BaseModel):
#     task_id: Optional[str] = "task_easy"
#     session_id: Optional[str] = _DEFAULT_SESSION


# class StepRequest(BaseModel):
#     action: Action
#     session_id: Optional[str] = _DEFAULT_SESSION


# class StepResponse(BaseModel):
#     observation: dict
#     reward: float
#     done: bool
#     info: dict


# class GradeResponse(BaseModel):
#     task_id: str
#     score: float
#     breakdown: dict


# # ---------------------------------------------------------------------------
# # Endpoints
# # ---------------------------------------------------------------------------

# @app.get("/health")
# async def health():
#     """Health check — returns 200 if the server is up."""
#     return {"status": "ok", "service": "email-triage-openenv"}


# @app.get("/tasks")
# async def list_tasks():
#     """List all available tasks."""
#     tasks = [
#         {
#             "id": "task_easy",
#             "name": "Basic Email Classification",
#             "difficulty": "easy",
#             "description": "Classify all emails and mark spam for deletion.",
#         },
#         {
#             "id": "task_medium",
#             "name": "Priority Inbox Management",
#             "difficulty": "medium",
#             "description": "Sort inbox, reply to urgent emails, unsubscribe from newsletters.",
#         },
#         {
#             "id": "task_hard",
#             "name": "Full Triage Workflow",
#             "difficulty": "hard",
#             "description": "Complete inbox zero: classify, reply, escalate, archive, summarize.",
#         },
#     ]
#     return {"tasks": tasks}


# @app.post("/reset")
# async def reset(request: ResetRequest):
#     """Reset the environment for a given task and return the initial observation."""
#     task_id = request.task_id or "task_easy"
#     session_id = request.session_id or _DEFAULT_SESSION
#     env = EmailTriageEnv(task_id=task_id)
#     _envs[session_id] = env
#     obs = env.reset()
#     return obs.model_dump()


# # @app.post("/step", response_model=StepResponse)
# # async def step(request: StepRequest):
# #     """Execute one action and return the new observation, reward, done flag, and info."""
# #     session_id = request.session_id or _DEFAULT_SESSION
# #     env = _get_env(session_id)
# #     try:
# #         obs, reward, done, info = env.step(request.action)
# #     except Exception as e:
# #         raise HTTPException(status_code=400, detail=str(e))
# #     return StepResponse(
# #         observation=obs.model_dump(),
# #         reward=reward,
# #         done=done,
# #         info=info,
# #     )

# @app.post("/step", response_model=StepResponse)
# async def step(request: StepRequest):
#     session_id = request.session_id if request.session_id else _DEFAULT_SESSION
#     env = _get_env(session_id)

#     if env is None:
#         raise HTTPException(status_code=400, detail="Session not found")

#     try:
#         obs, reward, done, info = env.step(request.action)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

#     reward_value = reward.total if hasattr(reward, "total") else reward

#     return {
#         "observation": obs.model_dump(),
#         "reward": float(reward_value),
#         "done": bool(done),
#         "info": info if isinstance(info, dict) else {}
#     }

# @app.get("/state")
# async def state(session_id: str = _DEFAULT_SESSION):
#     """Return the full internal environment state (for debugging/evaluation)."""
#     env = _get_env(session_id)
#     raw_state = env.state()
#     # Serialize enums
#     serializable = {}
#     for k, v in raw_state.items():
#         if k == "emails":
#             serializable[k] = {
#                 eid: {
#                     ek: ev.value if hasattr(ev, "value") else ev
#                     for ek, ev in email.items()
#                 }
#                 for eid, email in v.items()
#             }
#         else:
#             serializable[k] = v
#     return serializable


# @app.post("/grade/{task_id}", response_model=GradeResponse)
# async def grade(task_id: str, session_id: str = _DEFAULT_SESSION):
#     """Run the programmatic grader for the given task and return the score."""
#     if task_id not in GRADERS:
#         raise HTTPException(status_code=404, detail=f"Unknown task_id '{task_id}'.")
#     env = _get_env(session_id)
#     raw_state = env.state()
#     score, breakdown = run_grader(task_id, raw_state)
#     return GradeResponse(task_id=task_id, score=score, breakdown=breakdown)


# # ---------------------------------------------------------------------------
# # Entry point (for local dev)
# # ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     import uvicorn
#     port = int(os.environ.get("PORT", 7860))
#     uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)


"""
server.py — FastAPI server implementing the OpenEnv HTTP API.

FIXED ISSUES:
  1. /reset now accepts empty body, no-body, or JSON body (no more 422 errors)
  2. /step accepts action with or without session_id
  3. Observation serializes enum values to strings correctly
  4. All endpoints return clean JSON that the openenv validator accepts

Endpoints:
  POST /reset          → reset environment, return initial observation
  POST /step           → execute action, return (obs, reward, done, info)
  GET  /state          → return full internal state
  GET  /health         → health check (returns 200)
  GET  /tasks          → list available tasks
  POST /grade/{task_id} → run grader and return score
"""

from __future__ import annotations
import os
import json
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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

# ---------------------------------------------------------------------------
# In-memory environment store
# ---------------------------------------------------------------------------
_envs: Dict[str, EmailTriageEnv] = {}
_DEFAULT_SESSION = "default"
_DEFAULT_TASK = "task_easy"


def _get_env(session_id: str = _DEFAULT_SESSION) -> EmailTriageEnv:
    if session_id not in _envs:
        env = EmailTriageEnv(task_id=_DEFAULT_TASK)
        env.reset()
        _envs[session_id] = env
    return _envs[session_id]


def _serialize(val):
    """Recursively serialize a value, converting enums to strings."""
    if hasattr(val, "value"):
        return val.value
    if isinstance(val, dict):
        return {k: _serialize(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialize(i) for i in val]
    if hasattr(val, "__dict__"):
        return {k: _serialize(v) for k, v in val.__dict__.items() if not k.startswith("_")}
    return val


def _obs_to_dict(obs) -> dict:
    """Convert Observation object to a clean serializable dict."""
    return _serialize(obs)


async def _parse_body(request: Request) -> dict:
    """Parse request body safely — returns {} on empty/missing/invalid body."""
    try:
        body_bytes = await request.body()
        if body_bytes and body_bytes.strip() not in (b"", b"null"):
            parsed = json.loads(body_bytes)
            if isinstance(parsed, dict):
                return parsed
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check — returns 200."""
    return {"status": "ok", "service": "email-triage-openenv", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# /reset — THE CRITICAL FIX
# Accepts: empty POST, empty JSON {}, or {"task_id": "...", "session_id": "..."}
# ---------------------------------------------------------------------------

@app.post("/reset")
async def reset(request: Request):
    """
    Reset the environment and return the initial observation.
    Works with empty body, empty JSON, or {"task_id": "task_easy"}.
    """
    body = await _parse_body(request)

    task_id = body.get("task_id") or _DEFAULT_TASK
    session_id = body.get("session_id") or _DEFAULT_SESSION

    # Guard: only accept known task IDs
    if task_id not in GRADERS:
        task_id = _DEFAULT_TASK

    env = EmailTriageEnv(task_id=task_id)
    env.reset()
    _envs[session_id] = env

    obs = env.reset()
    return JSONResponse(content=_obs_to_dict(obs))


# ---------------------------------------------------------------------------
# /step
# ---------------------------------------------------------------------------

@app.post("/step")
async def step(request: Request):
    """Execute one action. Body: {"action": {"action_type": "..."}, "session_id": "..."}"""
    body = await _parse_body(request)

    if not body:
        raise HTTPException(status_code=400, detail="Request body is required for /step.")

    session_id = body.get("session_id") or _DEFAULT_SESSION
    action_data = body.get("action")

    if not action_data or not isinstance(action_data, dict):
        raise HTTPException(status_code=400, detail="'action' field (dict) is required.")

    try:
        action = Action(
            action_type=action_data.get("action_type", "noop"),
            email_id=action_data.get("email_id"),
            content=action_data.get("content"),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid action: {e}")

    env = _get_env(session_id)

    try:
        obs, reward, done, info = env.step(action)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step error: {e}")

    return JSONResponse(content={
        "observation": _obs_to_dict(obs),
        "reward": float(reward),
        "done": bool(done),
        "info": {k: (v.value if hasattr(v, "value") else v) for k, v in info.items()},
    })


# ---------------------------------------------------------------------------
# /state
# ---------------------------------------------------------------------------

@app.get("/state")
async def state(session_id: str = _DEFAULT_SESSION):
    """Return full internal environment state."""
    env = _get_env(session_id)
    return JSONResponse(content=_serialize(env.state()))


# ---------------------------------------------------------------------------
# /tasks
# ---------------------------------------------------------------------------

@app.get("/tasks")
async def list_tasks():
    """List all available tasks."""
    return JSONResponse(content={"tasks": [
        {
            "id": "task_easy",
            "name": "Basic Email Classification",
            "difficulty": "easy",
            "description": "Classify all 10 emails by type and delete spam.",
            "max_steps": 50,
            "score_range": [0.0, 1.0],
        },
        {
            "id": "task_medium",
            "name": "Priority Inbox Management",
            "difficulty": "medium",
            "description": "Classify inbox, reply to urgent emails, unsubscribe from newsletters.",
            "max_steps": 50,
            "score_range": [0.0, 1.0],
        },
        {
            "id": "task_hard",
            "name": "Full Triage Workflow",
            "difficulty": "hard",
            "description": "Full inbox zero: classify, reply, escalate, archive, summarize.",
            "max_steps": 50,
            "score_range": [0.0, 1.0],
        },
    ]})


# ---------------------------------------------------------------------------
# /grade/{task_id}
# ---------------------------------------------------------------------------

@app.post("/grade/{task_id}")
async def grade(task_id: str, request: Request):
    """Run the grader for task_id and return score + breakdown."""
    if task_id not in GRADERS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown task_id '{task_id}'. Available: {list(GRADERS.keys())}"
        )

    body = await _parse_body(request)
    session_id = (
        body.get("session_id")
        or request.query_params.get("session_id")
        or _DEFAULT_SESSION
    )

    env = _get_env(session_id)
    score, breakdown = run_grader(task_id, env.state())
    return JSONResponse(content={"task_id": task_id, "score": score, "breakdown": breakdown})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
