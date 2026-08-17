import httpx
import logging
from bot.config import AGENT_TOKEN, AGENT_URL, REQUEST_TIMEOUT, MAX_OUTPUT_CHARS

log = logging.getLogger(__name__)


async def health() -> dict:
    log.info("Checking agent health at %s/health", AGENT_URL)
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(f"{AGENT_URL}/health")
        response.raise_for_status()
        data = response.json()
        log.info("Agent health response: %s", data)
        return data


async def discover() -> dict:
    log.info("Fetching command list from agent")
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{AGENT_URL}/commands",
            headers={"Authorization": f"Bearer {AGENT_TOKEN}"},
        )
        response.raise_for_status()
        data = response.json()
        log.info("Agent returned %s commands", len(data.get("commands", [])))
        return data


async def execute(command: str, args: list[str] | None = None) -> dict:
    payload = {"command": command, "args": args or []}
    log.info("Executing via agent: command=%s args=%s", command, payload["args"])
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT + 5) as client:
        response = await client.post(
            f"{AGENT_URL}/execute",
            headers={"Authorization": f"Bearer {AGENT_TOKEN}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    for key in ("stdout", "stderr"):
        if isinstance(data.get(key), str):
            data[key] = data[key][:MAX_OUTPUT_CHARS]
    log.info("Agent execution completed: command=%s exit_code=%s", command, data.get("exit_code"))
    return data
