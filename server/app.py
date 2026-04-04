# """
# server/app.py — FastAPI app for Email Triage OpenEnv.
# Required location for openenv validate multi-mode deployment check.
# """

# from __future__ import annotations
# import os
# import json
# from typing import Dict

# from fastapi import FastAPI, HTTPException, Request
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware

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

# _envs: Dict[str, EmailTriageEnv] = {}
# _DEFAULT_SESSION = "default"
# _DEFAULT_TASK = "task_easy"


# def _get_env(session_id: str = _DEFAULT_SESSION) -> EmailTriageEnv:
#     if session_id not in _envs:
#         env = EmailTriageEnv(task_id=_DEFAULT_TASK)
#         env.reset()
#         _envs[session_id] = env
#     return _envs[session_id]


# def _serialize(val):
#     if hasattr(val, "value"):
#         return val.value
#     if isinstance(val, dict):
#         return {k: _serialize(v) for k, v in val.items()}
#     if isinstance(val, list):
#         return [_serialize(i) for i in val]
#     if hasattr(val, "__dict__"):
#         return {k: _serialize(v) for k, v in val.__dict__.items() if not k.startswith("_")}
#     return val


# async def _parse_body(request: Request) -> dict:
#     try:
#         body_bytes = await request.body()
#         if body_bytes and body_bytes.strip() not in (b"", b"null"):
#             parsed = json.loads(body_bytes)
#             if isinstance(parsed, dict):
#                 return parsed
#     except Exception:
#         pass
#     return {}


# @app.get("/health")
# async def health():
#     return {"status": "ok", "service": "email-triage-openenv", "version": "1.0.0"}


# @app.post("/reset")
# async def reset(request: Request):
#     body = await _parse_body(request)
#     task_id = body.get("task_id") or _DEFAULT_TASK
#     session_id = body.get("session_id") or _DEFAULT_SESSION
#     if task_id not in GRADERS:
#         task_id = _DEFAULT_TASK
#     env = EmailTriageEnv(task_id=task_id)
#     env.reset()
#     _envs[session_id] = env
#     obs = env.reset()
#     return JSONResponse(content=_serialize(obs))


# @app.post("/step")
# async def step(request: Request):
#     body = await _parse_body(request)
#     if not body:
#         raise HTTPException(status_code=400, detail="Request body required.")
#     session_id = body.get("session_id") or _DEFAULT_SESSION
#     action_data = body.get("action")
#     if not action_data or not isinstance(action_data, dict):
#         raise HTTPException(status_code=400, detail="'action' field required.")
#     try:
#         action = Action(
#             action_type=action_data.get("action_type", "noop"),
#             email_id=action_data.get("email_id"),
#             content=action_data.get("content"),
#         )
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Invalid action: {e}")
#     env = _get_env(session_id)
#     try:
#         obs, reward, done, info = env.step(action)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Step error: {e}")
#     return JSONResponse(content={
#         "observation": _serialize(obs),
#         "reward": float(reward),
#         "done": bool(done),
#         "info": {k: (v.value if hasattr(v, "value") else v) for k, v in info.items()},
#     })


# @app.get("/state")
# async def state(session_id: str = _DEFAULT_SESSION):
#     env = _get_env(session_id)
#     return JSONResponse(content=_serialize(env.state()))


# @app.get("/tasks")
# async def list_tasks():
#     return JSONResponse(content={"tasks": [
#         {"id": "task_easy",   "name": "Basic Email Classification", "difficulty": "easy",   "max_steps": 50, "score_range": [0.0, 1.0]},
#         {"id": "task_medium", "name": "Priority Inbox Management",  "difficulty": "medium", "max_steps": 50, "score_range": [0.0, 1.0]},
#         {"id": "task_hard",   "name": "Full Triage Workflow",       "difficulty": "hard",   "max_steps": 50, "score_range": [0.0, 1.0]},
#     ]})


# @app.post("/grade/{task_id}")
# async def grade(task_id: str, request: Request):
#     if task_id not in GRADERS:
#         raise HTTPException(status_code=404, detail=f"Unknown task_id '{task_id}'.")
#     body = await _parse_body(request)
#     session_id = body.get("session_id") or request.query_params.get("session_id") or _DEFAULT_SESSION
#     env = _get_env(session_id)
#     score, breakdown = run_grader(task_id, env.state())
#     return JSONResponse(content={"task_id": task_id, "score": score, "breakdown": breakdown})


# def main():
#     """Main entry point — required by openenv validate."""
#     import uvicorn
#     port = int(os.environ.get("PORT", 7860))
#     uvicorn.run("server.app:app", host="0.0.0.0", port=port, reload=False)


# # Required by openenv validate
# if __name__ == "__main__":
#     main()



"""
server/app.py — FastAPI app for Email Triage OpenEnv.
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
    description="A real-world email triage environment. Implements OpenEnv spec: step()/reset()/state().",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
    if hasattr(val, "value"):
        return val.value
    if isinstance(val, dict):
        return {k: _serialize(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialize(i) for i in val]
    if hasattr(val, "__dict__"):
        return {k: _serialize(v) for k, v in val.__dict__.items() if not k.startswith("_")}
    return val


async def _parse_body(request: Request) -> dict:
    try:
        body_bytes = await request.body()
        if body_bytes and body_bytes.strip() not in (b"", b"null"):
            parsed = json.loads(body_bytes)
            if isinstance(parsed, dict):
                return parsed
    except Exception:
        pass
    return {}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "email-triage-openenv", "version": "1.0.0"}


@app.post("/reset")
async def reset(request: Request):
    body = await _parse_body(request)
    task_id = body.get("task_id") or _DEFAULT_TASK
    session_id = body.get("session_id") or _DEFAULT_SESSION
    if task_id not in GRADERS:
        task_id = _DEFAULT_TASK
    env = EmailTriageEnv(task_id=task_id)
    env.reset()
    _envs[session_id] = env
    obs = env.reset()
    return JSONResponse(content=_serialize(obs))


@app.post("/step")
async def step(request: Request):
    body = await _parse_body(request)
    if not body:
        raise HTTPException(status_code=400, detail="Request body required.")
    session_id = body.get("session_id") or _DEFAULT_SESSION
    action_data = body.get("action")
    if not action_data or not isinstance(action_data, dict):
        raise HTTPException(status_code=400, detail="'action' field required.")
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
        "observation": _serialize(obs),
        "reward": float(reward),
        "done": bool(done),
        "info": {k: (v.value if hasattr(v, "value") else v) for k, v in info.items()},
    })


@app.get("/state")
async def state(session_id: str = _DEFAULT_SESSION):
    env = _get_env(session_id)
    return JSONResponse(content=_serialize(env.state()))


@app.get("/tasks")
async def list_tasks():
    return JSONResponse(content={"tasks": [
        {"id": "task_easy",   "name": "Basic Email Classification", "difficulty": "easy",   "max_steps": 50, "score_range": [0.0, 1.0]},
        {"id": "task_medium", "name": "Priority Inbox Management",  "difficulty": "medium", "max_steps": 50, "score_range": [0.0, 1.0]},
        {"id": "task_hard",   "name": "Full Triage Workflow",       "difficulty": "hard",   "max_steps": 50, "score_range": [0.0, 1.0]},
    ]})


@app.post("/grade/{task_id}")
async def grade(task_id: str, request: Request):
    if task_id not in GRADERS:
        raise HTTPException(status_code=404, detail=f"Unknown task_id '{task_id}'.")
    body = await _parse_body(request)
    session_id = body.get("session_id") or request.query_params.get("session_id") or _DEFAULT_SESSION
    env = _get_env(session_id)
    score, breakdown = run_grader(task_id, env.state())
    return JSONResponse(content={"task_id": task_id, "score": score, "breakdown": breakdown})


def main():
    """Entry point — required by openenv validate."""
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
