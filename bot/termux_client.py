import httpx
from bot.config import AGENT_TOKEN, AGENT_URL, REQUEST_TIMEOUT, MAX_OUTPUT_CHARS


async def health() -> dict:
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(f"{AGENT_URL}/health")
        response.raise_for_status()
        return response.json()


async def discover() -> dict:
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{AGENT_URL}/commands",
            headers={"Authorization": f"Bearer {AGENT_TOKEN}"},
        )
        response.raise_for_status()
        return response.json()


async def execute(command: str, args: list[str] | None = None) -> dict:
    payload = {"command": command, "args": args or []}
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
    return data
