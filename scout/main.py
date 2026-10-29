"""Job scout: polls job sources, filters for summer internships and notifies via Telegram.

  python -m scout run                 # one poll
  python -m scout run --loop 330      # poll every interval for 330 minutes (GitHub Actions)
  python -m scout check [keys...]     # fetch sources and print matches, no state/notifications
  python -m scout telegram-setup      # find your Telegram chat id
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

from .filter import JobFilter
from .sources import FETCHERS
from .state import State
from .telegram import Telegram

log = logging.getLogger("scout")
ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
FAIL_ALERT_THRESHOLD = 15   # consecutive failed polls before warning (~30 min at 2 min interval)
CONCURRENCY = 8


def load_sources(path=ROOT / "sources.yaml"):
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    settings = cfg.get("settings") or {}
    sources = [s for s in cfg["sources"] if s.get("enabled", True)]
    keys = [s["key"] for s in sources]
    if len(keys) != len(set(keys)):
        raise SystemExit("sources.yaml: duplicate keys")
    for s in sources:
        if s["type"] not in FETCHERS:
            raise SystemExit(f"sources.yaml: unknown type {s['type']!r} for {s['key']}")
    return settings, sources


def make_client():
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30, connect=10),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        limits=httpx.Limits(max_connections=20),
    )


async def fetch_source(client, sem, src, src_state):
    async with sem:
        t = time.monotonic()
        jobs = await FETCHERS[src["type"]](client, src, src_state.setdefault("data", {}))
        log.debug("%s: %d jobs in %.1fs", src["key"], len(jobs), time.monotonic() - t)
        return jobs


class Scout:
    def __init__(self, client, telegram, state, job_filter, settings, sources):
        self.client, self.tg, self.state, self.filter = client, telegram, state, job_filter
        self.sources = sources
        self.default_interval = float(settings.get("interval_minutes", 2))
        self.last_polled: dict[str, float] = {}
        self.sem = asyncio.Semaphore(CONCURRENCY)

    def due(self, src):
        interval = float(src.get("interval", self.default_interval)) * 60
        return time.monotonic() - self.last_polled.get(src["key"], -1e9) >= interval - 5

    async def poll(self):
        due = [s for s in self.sources if self.due(s)]
        for s in due:
            self.last_polled[s["key"]] = time.monotonic()
        results = await asyncio.gather(
            *(fetch_source(self.client, self.sem, s, self.state.source(s["key"])) for s in due),
            return_exceptions=True,
        )
        backlog, this_poll = [], set()
        for src, result in zip(due, results):
            st = self.state.source(src["key"])
            if isinstance(result, BaseException):
                await self.on_failure(src, st, result)
                continue
            await self.on_success(src, st, result)
            new = [j for j in result if self.filter.matches(j, src.get("require_tech", False))
                   and not self.state.is_seen(j.uid) and not self.state.is_seen(j.fingerprint)
                   and j.fingerprint not in this_poll]
            this_poll.update(j.fingerprint for j in new)
            if not st["initialized"]:
                # First successful fetch of this source: everything is "new", so summarize instead of spamming.
                backlog.extend(new)
                st["initialized"] = True
                continue
            for job in new:
                log.info("NEW %s | %s | %s | %s", job.company, job.title, job.location, job.url)
                if await self.tg.send_job(job):
                    self.state.mark_seen(job)
        if backlog:
            log.info("Initial digest: %d open matching jobs", len(backlog))
            if await self.tg.send_digest(f"📋 {len(backlog)} öppna sommarjobb/internships just nu", backlog):
                for job in backlog:
                    self.state.mark_seen(job)
            else:
                for src in due:  # retry the digest next poll
                    if any(j.source == src["key"] for j in backlog):
                        self.state.source(src["key"])["initialized"] = False
        return self.state.save()

    async def on_failure(self, src, st, exc):
        st["fails"] = st.get("fails", 0) + 1
        st["last_error"] = f"{type(exc).__name__}: {exc}"[:300]
        log.warning("%s failed (%d in a row): %s", src["key"], st["fails"], st["last_error"])
        if st["fails"] >= FAIL_ALERT_THRESHOLD and not st.get("alerted"):
            if await self.tg.send(f"⚠️ Källan <b>{src['name']}</b> ({src['key']}) har misslyckats "
                                  f"{st['fails']} gånger i rad.\n<code>{_esc(st['last_error'])}</code>"):
                st["alerted"] = True

    async def on_success(self, src, st, jobs):
        if st.get("alerted"):
            await self.tg.send(f"✅ Källan <b>{src['name']}</b> fungerar igen.")
        prev = st.get("last_count", 0)
        if prev >= 10 and not jobs:
            log.warning("%s returned 0 jobs (previously %d), page format may have changed", src["key"], prev)
        st.update(fails=0, alerted=False, last_ok=_now_iso(), last_count=len(jobs))
        st.pop("last_error", None)


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit_state(message):
    """Commit and push state/, which in GitHub Actions is a worktree of the `state` branch."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT / "state", capture_output=True, text=True)

    git("add", "-A", ".")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return
    git("commit", "-m", message)
    for _ in range(3):
        if git("push", "-u", "origin", "HEAD:state").returncode == 0:
            return
        git("pull", "--rebase", "-X", "theirs", "origin", "state")
        time.sleep(5)
    log.error("Could not push state")


async def cmd_run(args):
    settings, sources = load_sources()
    if args.only:
        sources = [s for s in sources if s["key"] in args.only]
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not args.dry_run and not (token and chat):
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (or use --dry-run)")
    state = State(ROOT / "state")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    async with make_client() as client:
        tg = Telegram(None if args.dry_run else token, chat, client)
        scout = Scout(client, tg, state, JobFilter.load(ROOT / "filters.yaml"), settings, sources)
        deadline = time.monotonic() + args.loop * 60
        while True:
            started = time.monotonic()
            try:
                if await scout.poll() and args.commit:
                    git_commit_state("state: new jobs seen")
            except Exception:
                log.exception("Poll crashed")
            if not args.loop or time.monotonic() >= deadline or stop.is_set():
                break
            sleep = max(5.0, 60 * min(float(s.get("interval", scout.default_interval)) for s in sources)
                        - (time.monotonic() - started))
            try:
                await asyncio.wait_for(stop.wait(), timeout=min(sleep, max(0, deadline - time.monotonic())))
            except asyncio.TimeoutError:
                pass
            if stop.is_set():
                break
    state.save()
    if args.commit:
        git_commit_state("state: end of run")


async def cmd_check(args):
    """Fetch sources once and print what matches. Doesn't touch state or send anything."""
    _, sources = load_sources()
    if args.keys:
        sources = [s for s in sources if s["key"] in args.keys]
    flt = JobFilter.load(ROOT / "filters.yaml")
    sem = asyncio.Semaphore(CONCURRENCY)
    async with make_client() as client:
        results = await asyncio.gather(*(fetch_source(client, sem, s, {}) for s in sources), return_exceptions=True)
    for src, res in zip(sources, results):
        if isinstance(res, BaseException):
            print(f"✗ {src['key']:16} ERROR {type(res).__name__}: {str(res)[:150]}")
            continue
        matches = [j for j in res if flt.matches(j, src.get("require_tech", False))]
        print(f"✓ {src['key']:16} {len(res):5} jobs, {len(matches)} matching")
        for j in matches if not args.all else res:
            print(f"     - {j.title} | {j.company} | {j.location[:70]} | {j.url}")


async def cmd_telegram_setup(args):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        try:
            token = input("Bot token från @BotFather: ").strip()
        except EOFError:
            raise SystemExit("Ingen terminal att läsa från. Kör kommandot i ett vanligt terminalfönster, "
                             "eller sätt TELEGRAM_BOT_TOKEN först.")
    print("Skicka ett meddelande (t.ex. /start) till din bot i Telegram nu. Väntar...")
    async with make_client() as client:
        for _ in range(60):
            r = await client.get(f"https://api.telegram.org/bot{token}/getUpdates", params={"timeout": 10})
            r.raise_for_status()
            for upd in r.json()["result"]:
                chat = (upd.get("message") or {}).get("chat")
                if chat:
                    print(f"\nTELEGRAM_CHAT_ID = {chat['id']}  ({chat.get('first_name') or chat.get('title')})")
                    tg = Telegram(token, str(chat["id"]), client)
                    await tg.send("✅ Job scout är kopplad! Här kommer notiserna om nya sommarjobb.")
                    return
        print("Inget meddelande mottaget, försök igen.")


def main(argv=None):
    p = argparse.ArgumentParser(prog="scout", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="poll sources and notify")
    r.add_argument("--loop", type=float, default=0, metavar="MINUTES", help="keep polling for this many minutes")
    r.add_argument("--dry-run", action="store_true", help="print messages instead of sending")
    r.add_argument("--commit", action="store_true", help="git commit + push state after changes")
    r.add_argument("--only", nargs="+", metavar="KEY", help="only these source keys")
    c = sub.add_parser("check", help="fetch sources and print matches (no state, no messages)")
    c.add_argument("keys", nargs="*")
    c.add_argument("--all", action="store_true", help="print all jobs, not only matches")
    sub.add_parser("telegram-setup", help="find your chat id and send a test message")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run({"run": cmd_run, "check": cmd_check, "telegram-setup": cmd_telegram_setup}[args.cmd](args))
