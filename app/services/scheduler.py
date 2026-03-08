"""
Scheduler Service — LinkedIn Agent
====================================
Runs an asyncio background loop that checks the config for scheduler settings
and triggers the message-processing pipeline automatically at defined intervals.
Config is read directly from SQLite via sqlite3 to avoid circular imports.
"""

import asyncio
import logging
import sqlite3
import os
from datetime import datetime, time as dt_time

logger = logging.getLogger("scheduler")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data.db")


def _read_cfg(key: str, default: str = "") -> str:
    try:
        conn = sqlite3.connect(os.path.abspath(DB_PATH))
        row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


async def _run_agent():
    """Fires the full process_messages pipeline (same as the API endpoint)."""
    try:
        from ..routers.messages import _process_messages_internal
        logger.info("⏰ Scheduler: iniciando varredura automática de mensagens...")
        await _process_messages_internal()
        logger.info("✅ Scheduler: varredura concluída.")
    except Exception as e:
        logger.error(f"Scheduler error during agent run: {e}")


async def scheduler_loop():
    """
    Background asyncio task that runs forever.
    Every 60 seconds it checks whether:
      1. scheduler_active == 'true'
      2. The current time is >= scheduler_start (e.g. "08:00")
      3. Enough time has passed since the last run (scheduler_interval hours)
    """
    last_run: datetime | None = None

    while True:
        try:
            active = _read_cfg("scheduler_active", "false") == "true"
            start_str = _read_cfg("scheduler_start", "08:00")
            interval_h = int(_read_cfg("scheduler_interval", "24"))

            now = datetime.now()

            if active:
                # Parse start time
                try:
                    h, m = map(int, start_str.split(":"))
                    start_time = dt_time(h, m)
                except Exception:
                    start_time = dt_time(8, 0)

                past_start = now.time() >= start_time

                should_run = False
                if last_run is None:
                    should_run = past_start
                else:
                    hours_since = (now - last_run).total_seconds() / 3600
                    should_run = hours_since >= interval_h

                if should_run:
                    last_run = now
                    asyncio.create_task(_run_agent())

        except Exception as e:
            logger.warning(f"Scheduler loop error: {e}")

        await asyncio.sleep(60)
