from __future__ import annotations

import asyncio
import html
import logging
from zoneinfo import ZoneInfo

import httpx

from .models import Job

log = logging.getLogger(__name__)
MAX_LEN = 4000  # Telegram's limit is 4096
TZ = ZoneInfo("Europe/Stockholm")


class Telegram:
    """Sends messages via the Telegram Bot API. With no token it prints to stdout (dry run)."""

    def __init__(self, token: str | None, chat_id: str | None, client: httpx.AsyncClient):
        self.token, self.chat_id, self.client = token, chat_id, client
        self._lock = asyncio.Lock()

    @property
    def dry_run(self):
        return not (self.token and self.chat_id)

    async def send(self, text: str, button: tuple[str, str] | None = None) -> bool:
        if self.dry_run:
            print("\n----- [dry run] Telegram message -----\n" + text + (f"\n[{button[0]}] {button[1]}" if button else ""))
            return True
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if button and button[1].startswith("http"):
            payload["reply_markup"] = {"inline_keyboard": [[{"text": button[0], "url": button[1]}]]}
        async with self._lock:  # keep well under Telegram's ~1 msg/s per chat limit
            for attempt in range(5):
                try:
                    r = await self.client.post(f"https://api.telegram.org/bot{self.token}/sendMessage", json=payload)
                    if r.status_code == 429:
                        await asyncio.sleep(r.json().get("parameters", {}).get("retry_after", 5) + 1)
                        continue
                    if r.status_code == 400 and "reply_markup" in payload:
                        payload.pop("reply_markup")  # e.g. an apply URL Telegram rejects; send without the button
                        continue
                    r.raise_for_status()
                    await asyncio.sleep(1.1)
                    return True
                except httpx.HTTPError as e:
                    log.warning("Telegram send failed (attempt %d): %s", attempt + 1, e)
                    await asyncio.sleep(2**attempt)
        return False

    async def send_job(self, job: Job) -> bool:
        return await self.send(format_job(job), ("📝 Ansök / läs annonsen", job.extra.get("apply_url") or job.url))

    async def send_digest(self, title: str, jobs: list[Job]) -> bool:
        lines = [f"• <a href=\"{html.escape(j.url, quote=True)}\">{html.escape(j.title)}</a>"
                 f" — {html.escape(j.company)}" + (f" <i>({html.escape(_short(j.location))})</i>" if j.location else "")
                 for j in sorted(jobs, key=lambda j: (j.company.lower(), j.title.lower()))]
        ok, chunk = True, f"<b>{html.escape(title)}</b>\n"
        for line in lines:
            if len(chunk) + len(line) + 1 > MAX_LEN:
                ok &= await self.send(chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk.strip():
            ok &= await self.send(chunk)
        return ok


def _short(s: str, n: int = 80) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def format_job(job: Job) -> str:
    parts = [f"🚨 <b>{html.escape(job.title)}</b>", f"🏢 {html.escape(job.company)}"]
    if job.location:
        parts.append(f"📍 {html.escape(_short(job.location, 150))}")
    if job.posted:
        posted = job.posted if job.posted.tzinfo else job.posted.replace(tzinfo=TZ)
        parts.append(f"🕐 Publicerad {posted.astimezone(TZ).strftime('%Y-%m-%d %H:%M')}")
    elif job.extra.get("posted_text"):
        parts.append(f"🕐 {html.escape(job.extra['posted_text'])}")
    parts.append(f"🔗 {html.escape(job.url)}")
    return "\n".join(parts)
