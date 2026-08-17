import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn

from agent.executor import discover_commands, execute_command

load_dotenv("agent/.env")

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8787"))
AGENT_TOKEN = os.environ["AGENT_TOKEN"]

app = FastAPI(title="Termux TeleBot Agent")


class ExecuteRequest(BaseModel):
    command: str
    args: list[str] = []


def authorize(authorization: str | None):
    expected = f"Bearer {AGENT_TOKEN}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
async def health():
    return {"ok": True, "service": "termux-agent"}


@app.get("/commands")
async def commands(authorization: str | None = Header(default=None)):
    authorize(authorization)
    return {"commands": discover_commands()}


@app.post("/execute")
async def execute(req: ExecuteRequest, authorization: str | None = Header(default=None)):
    authorize(authorization)
    return await execute_command(req.command, req.args)


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
