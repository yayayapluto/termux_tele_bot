import os
import secrets
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn

from agent.executor import discover_commands, execute_command

load_dotenv("agent/.env")

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8787"))
AGENT_TOKEN = os.environ["AGENT_TOKEN"]

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Termux TeleBot Agent")


class ExecuteRequest(BaseModel):
    command: str
    args: list[str] = []


def authorize(authorization: str | None):
    expected = f"Bearer {AGENT_TOKEN}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        log.warning("Unauthorized agent request")
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
async def health():
    log.info("Health check request")
    return {"ok": True, "service": "termux-agent"}


@app.get("/commands")
async def commands(authorization: str | None = Header(default=None)):
    authorize(authorization)
    commands_list = discover_commands()
    log.info("Commands requested, discovered=%s", len(commands_list))
    return {"commands": commands_list}


@app.post("/execute")
async def execute(req: ExecuteRequest, authorization: str | None = Header(default=None)):
    authorize(authorization)
    log.info("Execute request: command=%s args=%s", req.command, req.args)
    result = await execute_command(req.command, req.args)
    log.info("Execute result: command=%s exit_code=%s", req.command, result.get("exit_code"))
    return result


if __name__ == "__main__":
    log.info("Starting Termux agent on %s:%s", HOST, PORT)
    uvicorn.run(app, host=HOST, port=PORT)
