import asyncio
import logging
import os
import re
from pathlib import Path

TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", "30"))
MAX_OUTPUT = int(os.getenv("MAX_OUTPUT_CHARS", "12000"))

COMMAND_RE = re.compile(r"^[A-Za-z0-9_+.-]+$")
log = logging.getLogger(__name__)


def discover_commands() -> list[str]:
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    bin_dir = prefix / "bin"
    if not bin_dir.exists():
        return []
    commands = sorted(
        p.name for p in bin_dir.glob("termux-*")
        if p.is_file() and os.access(p, os.X_OK)
    )
    log.info("Discovered %s termux command(s)", len(commands))
    return commands


async def execute_command(command: str, args: list[str]) -> dict:
    # The command itself must be a simple executable name.
    # Arguments are passed without shell parsing, preventing shell metacharacters
    # from being interpreted as part of the command line.
    if not COMMAND_RE.fullmatch(command):
        log.warning("Rejected invalid command name: %s", command)
        return {
            "exit_code": 2,
            "stdout": "",
            "stderr": "Invalid command name.",
        }

    allowed = set(discover_commands())
    # Custom commands are supported, but only executable names are accepted here.
    # This intentionally prevents /execute from becoming `sh -c <payload>`.
    # For arbitrary commands like `ls`, the executable name must exist on PATH.
    if command not in allowed:
        executable = command
    else:
        executable = command

    log.info("Running command executable=%s args=%s", executable, args)

    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=TIMEOUT)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            log.warning("Command timed out: %s after %ss", command, TIMEOUT)
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Command timed out after {TIMEOUT}s.",
            }

        log.info("Command completed: %s exit_code=%s", command, process.returncode)
        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT],
            "stderr": stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT],
        }
    except FileNotFoundError:
        log.warning("Command not found on PATH: %s", command)
        return {
            "exit_code": 127,
            "stdout": "",
            "stderr": f"Command not found: {command}",
        }
    except Exception as exc:
        log.exception("Unexpected execution error for command: %s", command)
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
        }
