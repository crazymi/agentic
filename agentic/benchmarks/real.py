from __future__ import annotations

import imaplib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, replace
from email.parser import BytesParser
from email.policy import default
from html import unescape
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

from agentic.benchmarks.models import (
    RealBenchmarkProbeResult,
    RealBenchmarkResult,
    RealBenchmarkStatus,
)
from agentic.config.settings import AppConfig
from agentic.experience.models import ExperienceEvent, ExperienceEventType
from agentic.experience.store import ExperienceStore
from agentic.memory.idea import capture_idea
from agentic.memory.store import MemoryStore
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.resources.store import ResourceStore
from agentic.sources import SourceDefinition, SourceKind, SourceRuntime, SourceStore
from agentic.synthesis.ideas import synthesize_ideas


DEFAULT_REDDIT_URL = "https://www.reddit.com/r/stocks/hot.json?limit=10"
DEFAULT_DCINSIDE_URL = "https://gall.dcinside.com/board/lists/?id=neostock"


@dataclass(frozen=True)
class RealBenchmarkOptions:
    state_dir: str | Path | None = None
    experience_path: str | Path | None = None
    persist_experience: bool = True
    include_network: bool = True
    include_ntfy: bool = True
    include_model: bool = True
    model_id: str = ""
    model_max_tokens: int = 256
    model_prompt: str = "한국의 수도는 어디야? 답변만 한 문장으로 말해."
    reddit_url: str = DEFAULT_REDDIT_URL
    dcinside_url: str = DEFAULT_DCINSIDE_URL
    ticket_url: str = ""


def run_real_benchmark(config: AppConfig, options: RealBenchmarkOptions | None = None) -> RealBenchmarkResult:
    options = options or RealBenchmarkOptions()
    tempdir: tempfile.TemporaryDirectory[str] | None = None
    if options.state_dir is None:
        tempdir = tempfile.TemporaryDirectory()
        state_dir = Path(tempdir.name)
    else:
        state_dir = Path(options.state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
    experience_path = Path(options.experience_path) if options.experience_path else config.trace_dir / "experience.jsonl"
    try:
        probes = [
            _probe_idea_memory(state_dir),
            _probe_repo_self_inspection(config.root),
            _probe_gmail_wsj(state_dir),
            _probe_ticket_browser(options.ticket_url),
        ]
        if options.include_ntfy:
            probes.append(_probe_ntfy_delivery())
        if options.include_network:
            probes.extend(
                [
                    _probe_reddit_live(options.reddit_url),
                    _probe_dcinside_live(options.dcinside_url, state_dir),
                ]
            )
        if options.include_model:
            probes.append(_probe_model(config, options))
        result = RealBenchmarkResult(
            ok=all(probe.ok for probe in probes),
            state_dir=str(state_dir),
            experience_path=str(experience_path) if options.persist_experience else None,
            probes=probes,
        )
        if options.persist_experience:
            _record_experience(experience_path, result)
        return result
    finally:
        if tempdir is not None:
            tempdir.cleanup()


def _probe_idea_memory(state_dir: Path) -> RealBenchmarkProbeResult:
    started = _now()
    try:
        store = MemoryStore(state_dir / "memory.sqlite3")
        capture = capture_idea(
            store,
            (
                "실사용 벤치마크: WSJ 뉴스, 커뮤니티 트렌드, 브라우저 자동화, "
                "아이디어 메모를 하나의 Agent Harness 경험치 루프로 묶는다."
            ),
            source="real_benchmark",
        )
        synthesis = synthesize_ideas(store, query="Agent Harness")
        return RealBenchmarkProbeResult(
            probe_id="idea_memory_real",
            title="AI memory and idea synthesis",
            requirement="채팅으로 보낸 아이디어를 저장, 태깅, 연결하고 주기적으로 영감 보고서를 만든다.",
            status=RealBenchmarkStatus.COMPLETED,
            summary="Created real memory records and a synthesis insight in SQLite state.",
            evidence={
                "memory_id": capture.memory.memory_id,
                "followup_question_id": capture.followup_question.memory_id,
                "synthesis": synthesis,
                "state": str(state_dir / "memory.sqlite3"),
            },
            next_actions=["Connect this memory path to the web/mobile channel and Obsidian export."],
            started_at=started,
            finished_at=_now(),
        )
    except Exception as exc:
        return _failed(
            "idea_memory_real",
            "AI memory and idea synthesis",
            "채팅으로 보낸 아이디어를 저장, 태깅, 연결하고 주기적으로 영감 보고서를 만든다.",
            started,
            exc,
        )


def _probe_repo_self_inspection(root: Path) -> RealBenchmarkProbeResult:
    started = _now()
    try:
        status = _run(["git", "status", "--short"], cwd=root)
        tracked = _run(["git", "ls-files"], cwd=root)
        files = [line for line in tracked.splitlines() if line.strip()]
        return RealBenchmarkProbeResult(
            probe_id="harness_self_inspection_real",
            title="Harness self-improvement repo inspection",
            requirement="Agentic harness가 자기 repo를 실제로 읽고 개선 작업을 찾는다.",
            status=RealBenchmarkStatus.COMPLETED,
            summary="Read actual git status and tracked file inventory.",
            evidence={
                "dirty_entries": len([line for line in status.splitlines() if line.strip()]),
                "tracked_files": len(files),
                "sample_files": files[:10],
            },
            next_actions=["Promote repo inspection into an approval-gated patch/test workflow."],
            started_at=started,
            finished_at=_now(),
        )
    except Exception as exc:
        return _failed(
            "harness_self_inspection_real",
            "Harness self-improvement repo inspection",
            "Agentic harness가 자기 repo를 실제로 읽고 개선 작업을 찾는다.",
            started,
            exc,
        )


def _probe_gmail_wsj(state_dir: Path) -> RealBenchmarkProbeResult:
    started = _now()
    user = os.getenv("AGENTIC_GMAIL_IMAP_USER", "")
    password = os.getenv("AGENTIC_GMAIL_IMAP_APP_PASSWORD", "")
    if not user or not password:
        _notify_user(
            "Agentic credential 필요",
            "WSJ/Gmail 실사용 벤치마크를 위해 AGENTIC_GMAIL_IMAP_USER와 APP_PASSWORD가 필요합니다.",
        )
        return RealBenchmarkProbeResult(
            probe_id="gmail_wsj_real",
            title="WSJ Gmail newsletter ingestion",
            requirement="Gmail의 WSJ 뉴스레터를 읽어 투자/스타트업 관점으로 분석한다.",
            status=RealBenchmarkStatus.NEEDS_CREDENTIAL,
            summary="No Gmail IMAP credential is configured, so no mailbox access was attempted.",
            evidence={"required_env": ["AGENTIC_GMAIL_IMAP_USER", "AGENTIC_GMAIL_IMAP_APP_PASSWORD"]},
            blockers=["gmail_credential_missing"],
            next_actions=["Provide a read-only Gmail credential reference or OAuth connector before rerun."],
            started_at=started,
            finished_at=_now(),
        )
    try:
        with imaplib.IMAP4_SSL("imap.gmail.com", timeout=20) as client:
            client.login(user, password)
            client.select("INBOX", readonly=True)
            status, ids = client.search(None, 'OR', 'FROM', '"wsj.com"', 'SUBJECT', '"WSJ"')
            if status != "OK":
                raise RuntimeError(f"imap search failed: {status}")
            message_ids = ids[0].split()[-5:]
            subjects: list[str] = []
            for message_id in message_ids:
                fetch_status, data = client.fetch(message_id, "(RFC822.HEADER)")
                if fetch_status != "OK":
                    continue
                header = next((part[1] for part in data if isinstance(part, tuple)), b"")
                if header:
                    subjects.append(str(BytesParser(policy=default).parsebytes(header).get("subject", "")))
        status_value = RealBenchmarkStatus.COMPLETED if subjects else RealBenchmarkStatus.COMPLETED_EMPTY
        return RealBenchmarkProbeResult(
            probe_id="gmail_wsj_real",
            title="WSJ Gmail newsletter ingestion",
            requirement="Gmail의 WSJ 뉴스레터를 읽어 투자/스타트업 관점으로 분석한다.",
            status=status_value,
            summary=f"Read Gmail INBOX over IMAP and found {len(subjects)} recent WSJ-like message(s).",
            evidence={"subjects": subjects, "state_dir": str(state_dir)},
            next_actions=["Persist fetched messages as resources and run goal-grounded analysis."],
            started_at=started,
            finished_at=_now(),
        )
    except Exception as exc:
        return _failed(
            "gmail_wsj_real",
            "WSJ Gmail newsletter ingestion",
            "Gmail의 WSJ 뉴스레터를 읽어 투자/스타트업 관점으로 분석한다.",
            started,
            exc,
        )


def _probe_ticket_browser(ticket_url: str) -> RealBenchmarkProbeResult:
    started = _now()
    if not ticket_url:
        _notify_user(
            "Agentic 입력 필요",
            "티켓 예매 실사용 벤치마크를 위해 공식 예매 URL이 필요합니다.",
        )
        return RealBenchmarkProbeResult(
            probe_id="ticket_browser_real",
            title="Login-gated browser transaction",
            requirement="MSI 2026 같은 티켓 예매를 실제 브라우저에서 관찰하고 승인 경계까지 진행한다.",
            status=RealBenchmarkStatus.NEEDS_INPUT,
            summary="No real ticket URL was provided; the benchmark did not fabricate a target site.",
            evidence={"required_argument": "--ticket-url"},
            blockers=["ticket_url_missing", "live_browser_adapter_missing"],
            next_actions=[
                "Provide an official ticket URL.",
                "Implement a real Playwright/Chrome adapter with login checkpoint and approval resume.",
            ],
            started_at=started,
            finished_at=_now(),
        )
    return RealBenchmarkProbeResult(
        probe_id="ticket_browser_real",
        title="Login-gated browser transaction",
        requirement="MSI 2026 같은 티켓 예매를 실제 브라우저에서 관찰하고 승인 경계까지 진행한다.",
        status=RealBenchmarkStatus.BLOCKED_BY_TOOLING,
        summary="A real URL was provided, but no live browser adapter is implemented yet.",
        evidence={"ticket_url": ticket_url},
        blockers=["live_browser_adapter_missing"],
        next_actions=["Implement real Playwright/Chrome adapter; do not use local fixtures."],
        started_at=started,
        finished_at=_now(),
    )


def _probe_ntfy_delivery() -> RealBenchmarkProbeResult:
    started = _now()
    ok = _notify_user(
        "Agentic real-bench",
        "실사용 벤치마크 ntfy 전송 테스트입니다.",
    )
    if ok:
        return RealBenchmarkProbeResult(
            probe_id="ntfy_delivery_real",
            title="Mobile notification delivery",
            requirement="승인/credential/input 필요 시 모바일 알림을 실제로 보낸다.",
            status=RealBenchmarkStatus.COMPLETED,
            summary="Sent a real ntfy notification through the configured notify path.",
            evidence={"delivered": True},
            started_at=started,
            finished_at=_now(),
        )
    return RealBenchmarkProbeResult(
        probe_id="ntfy_delivery_real",
        title="Mobile notification delivery",
        requirement="승인/credential/input 필요 시 모바일 알림을 실제로 보낸다.",
        status=RealBenchmarkStatus.NEEDS_CREDENTIAL,
        summary="No working ntfy path was available from the benchmark process.",
        blockers=["ntfy_config_missing_or_network_blocked"],
        next_actions=["Configure AGENTIC_NTFY_TOPIC/NOTIFY_USER_TOPIC or the notify-user skill script."],
        started_at=started,
        finished_at=_now(),
    )


def _probe_reddit_live(url: str) -> RealBenchmarkProbeResult:
    started = _now()
    try:
        payload = _http_get(url, accept="application/json")
        parsed = json.loads(payload)
        posts = parsed.get("data", {}).get("children", [])
        titles = [str(post.get("data", {}).get("title", "")) for post in posts[:10]]
        titles = [title for title in titles if title]
        return RealBenchmarkProbeResult(
            probe_id="reddit_stocks_live",
            title="Reddit stock trend crawl",
            requirement="미국 주식 Reddit 최근/hot 글을 실제로 수집하고 트렌드 분석 재료로 저장한다.",
            status=RealBenchmarkStatus.COMPLETED if titles else RealBenchmarkStatus.COMPLETED_EMPTY,
            summary=f"Fetched Reddit live JSON and extracted {len(titles)} title(s).",
            evidence={"url": url, "titles": titles},
            next_actions=["Persist live posts into ResourceStore and add trend analysis/report step."],
            started_at=started,
            finished_at=_now(),
        )
    except Exception as exc:
        return _failed(
            "reddit_stocks_live",
            "Reddit stock trend crawl",
            "미국 주식 Reddit 최근/hot 글을 실제로 수집하고 트렌드 분석 재료로 저장한다.",
            started,
            exc,
        )


def _probe_dcinside_live(url: str, state_dir: Path) -> RealBenchmarkProbeResult:
    started = _now()
    try:
        source_store = SourceStore(state_dir / "dcinside_sources.sqlite3")
        resource_store = ResourceStore(state_dir / "dcinside_resources.sqlite3")
        source = source_store.add_source(
            SourceDefinition(
                kind=SourceKind.WEB_PAGE,
                name="DCInside stock gallery live page",
                locator=url,
                enabled=True,
                metadata={
                    "extract": {
                        "href_contains": ["/board/view"],
                        "href_excludes": ["no=1", "no=45649"],
                        "text_excludes": ["공지", "AD"],
                        "text_exclude_regexes": [r"^\[\d+\]$"],
                        "min_text_chars": 4,
                        "limit": 10,
                    }
                },
            )
        )
        collection = SourceRuntime(source_store=source_store, resource_store=resource_store).collect(source.source_id)
        resources = [resource_store.get(resource_id) for resource_id in collection.resource_ids]
        titles = [resource.title for resource in resources]
        return RealBenchmarkProbeResult(
            probe_id="dcinside_stock_live",
            title="DCInside stock gallery crawl",
            requirement="주식갤 최근 글을 실제로 수집하고 트렌드 분석 재료로 저장한다.",
            status=RealBenchmarkStatus.COMPLETED if titles else RealBenchmarkStatus.COMPLETED_EMPTY,
            summary=f"Fetched DCInside live HTML and stored {len(titles)} resource(s).",
            evidence={
                "url": url,
                "titles": titles[:10],
                "resource_ids": collection.resource_ids,
                "state_dir": str(state_dir),
            },
            next_actions=["Add scheduler interval and trend synthesis over persisted resources."],
            started_at=started,
            finished_at=_now(),
        )
    except Exception as exc:
        return _failed(
            "dcinside_stock_live",
            "DCInside stock gallery crawl",
            "주식갤 최근 글을 실제로 수집하고 트렌드 분석 재료로 저장한다.",
            started,
            exc,
        )


def _probe_model(config: AppConfig, options: RealBenchmarkOptions) -> RealBenchmarkProbeResult:
    started = _now()
    selected = options.model_id or config.runtime.default_master_model
    try:
        model = config.model(selected)
        if options.model_max_tokens > 0:
            model = replace(model, max_tokens=options.model_max_tokens)
        response = LocalGGUFProvider(model).generate(options.model_prompt)
        gpu_hint = _run(["nvidia-smi"], cwd=config.root, timeout=10)
        text = response.text.strip()
        return RealBenchmarkProbeResult(
            probe_id="local_model_real",
            title="Local GGUF model execution",
            requirement="RTX 4090 로컬 모델을 실제로 구동해 Agent Harness 판단/응답에 사용한다.",
            status=RealBenchmarkStatus.COMPLETED if text else RealBenchmarkStatus.COMPLETED_EMPTY,
            summary=f"Ran configured local model {selected} and received {len(text)} output chars.",
            evidence={
                "model_id": selected,
                "output": text[:500],
                "returncode": response.returncode,
                "gpu_visible": "NVIDIA" in gpu_hint,
            },
            next_actions=["Run the same benchmark through the full master/subagent workflow path."],
            started_at=started,
            finished_at=_now(),
        )
    except Exception as exc:
        return _failed(
            "local_model_real",
            "Local GGUF model execution",
            "RTX 4090 로컬 모델을 실제로 구동해 Agent Harness 판단/응답에 사용한다.",
            started,
            exc,
        )


def _http_get(url: str, *, accept: str) -> str:
    req = request.Request(
        url,
        headers={
            "User-Agent": "agentic-real-benchmark/0.1 (+local personal harness)",
            "Accept": accept,
        },
        method="GET",
    )
    with request.urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _extract_dcinside_titles(html: str) -> list[str]:
    titles: list[str] = []
    for match in re.finditer(r'<a[^>]+href="[^"]*(?:/board/view|/mgallery/board/view)[^"]*"[^>]*>(.*?)</a>', html, re.I | re.S):
        text = re.sub(r"<[^>]+>", " ", match.group(1))
        title = unescape(re.sub(r"\s+", " ", text)).strip()
        if title and title not in titles:
            titles.append(title)
        if len(titles) >= 10:
            break
    return titles


def _notify_user(title: str, message: str) -> bool:
    topic = os.getenv("AGENTIC_NTFY_TOPIC") or os.getenv("NOTIFY_USER_TOPIC")
    server = (os.getenv("AGENTIC_NTFY_SERVER") or os.getenv("NOTIFY_USER_SERVER") or "https://ntfy.sh").rstrip("/")
    if topic:
        try:
            req = request.Request(
                f"{server}/{topic}",
                data=message.encode("utf-8"),
                headers={"Title": title},
                method="POST",
            )
            with request.urlopen(req, timeout=10) as response:
                return 200 <= int(response.status) < 300
        except (HTTPError, URLError, TimeoutError):
            pass
    script = Path(os.getenv("CODEX_HOME", str(Path.home() / ".codex"))) / "skills" / "notify-user" / "scripts" / "send_ntfy.sh"
    if script.exists():
        completed = subprocess.run(
            [str(script), title, message],
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
        return completed.returncode == 0
    return False


def _record_experience(path: Path, result: RealBenchmarkResult) -> None:
    store = ExperienceStore(path)
    for probe in result.probes:
        store.append(
            ExperienceEvent(
                event_type=ExperienceEventType.SMOKE_RUN,
                subject=probe.probe_id,
                summary=probe.summary,
                evidence=probe.to_record(),
                lessons=[
                    "Real benchmark results must not be replaced by fixtures or fabricated success.",
                    *probe.blockers,
                ],
                tags=["real_benchmark", probe.status.value],
            )
        )


def _run(args: list[str], *, cwd: Path, timeout: int = 20) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"command failed: {args}")
    return completed.stdout.strip()


def _failed(
    probe_id: str,
    title: str,
    requirement: str,
    started_at: str,
    exc: Exception,
) -> RealBenchmarkProbeResult:
    return RealBenchmarkProbeResult(
        probe_id=probe_id,
        title=title,
        requirement=requirement,
        status=RealBenchmarkStatus.FAILED_LIVE_ATTEMPT,
        summary=f"Live attempt failed: {type(exc).__name__}: {exc}",
        evidence={"error_type": type(exc).__name__, "message": str(exc)[:500]},
        blockers=[f"{probe_id}_live_attempt_failed"],
        next_actions=["Inspect evidence and implement the missing real connector/runtime path."],
        started_at=started_at,
        finished_at=_now(),
    )


def _now() -> str:
    from agentic.workflow_kernel.models import utc_now

    return utc_now()
