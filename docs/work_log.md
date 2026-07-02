# Work Log

This log records substantive project work. Keep the table of contents updated when adding entries.

## Table Of Contents

- [2026-07-02 13:08 KST - Operator Boundary Deduplication](#2026-07-02-1308-kst---operator-boundary-deduplication)
- [2026-07-02 13:04 KST - Dotenv Support For API Keys](#2026-07-02-1304-kst---dotenv-support-for-api-keys)
- [2026-07-02 12:50 KST - Operator Role Boundary Hardening](#2026-07-02-1250-kst---operator-role-boundary-hardening)
- [2026-07-02 12:25 KST - Strict Operator Agent Boundary Rewrite](#2026-07-02-1225-kst---strict-operator-agent-boundary-rewrite)
- [2026-07-02 12:18 KST - Operator And Harness Boundary Clarification](#2026-07-02-1218-kst---operator-and-harness-boundary-clarification)
- [2026-07-02 12:07 KST - No-Preseed Agent Autonomy Diagnosis](#2026-07-02-1207-kst---no-preseed-agent-autonomy-diagnosis)
- [2026-07-02 11:31 KST - Model-Assisted Report Synthesis Finish-Line](#2026-07-02-1131-kst---model-assisted-report-synthesis-finish-line)
- [2026-07-02 11:30 KST - Core Tool Surface And API Web Search](#2026-07-02-1130-kst---core-tool-surface-and-api-web-search)
- [2026-07-02 11:00 KST - Tool And MCP Inventory Review](#2026-07-02-1100-kst---tool-and-mcp-inventory-review)
- [2026-07-01 11:40 KST - M7 Workflow Kernel Implementation](#2026-07-01-1140-kst---m7-workflow-kernel-implementation)
- [2026-07-01 11:58 KST - Roadmap Review And Work Log Rule](#2026-07-01-1158-kst---roadmap-review-and-work-log-rule)
- [2026-07-01 12:01 KST - M8 Source Capability And Artifact Runtime](#2026-07-01-1201-kst---m8-source-capability-and-artifact-runtime)
- [2026-07-01 12:11 KST - M9 Workflow Probe Pack](#2026-07-01-1211-kst---m9-workflow-probe-pack)
- [2026-07-01 12:51 KST - README Implementation Summary Refresh](#2026-07-01-1251-kst---readme-implementation-summary-refresh)
- [2026-07-01 13:38 KST - M10 Real-Only Runtime Boundary](#2026-07-01-1338-kst---m10-real-only-runtime-boundary)
- [2026-07-01 13:54 KST - M10 Operational Health Primitives](#2026-07-01-1354-kst---m10-operational-health-primitives)
- [2026-07-01 14:02 KST - Browser Smoke And Workflow Source Binding](#2026-07-01-1402-kst---browser-smoke-and-workflow-source-binding)
- [2026-07-01 14:14 KST - M10 Ops Smoke And Real GPU Model Validation](#2026-07-01-1414-kst---m10-ops-smoke-and-real-gpu-model-validation)
- [2026-07-01 14:28 KST - DeepResearch Ticket Booking Probe](#2026-07-01-1428-kst---deepresearch-ticket-booking-probe)
- [2026-07-01 14:39 KST - M11 Browser Transaction Runtime Design](#2026-07-01-1439-kst---m11-browser-transaction-runtime-design)
- [2026-07-01 15:10 KST - M11 Planning And Tooling Backbone](#2026-07-01-1510-kst---m11-planning-and-tooling-backbone)
- [2026-07-01 18:02 KST - Experience Loop And Requirement Smoke](#2026-07-01-1802-kst---experience-loop-and-requirement-smoke)
- [2026-07-01 18:19 KST - Autonomy Benchmark Review](#2026-07-01-1819-kst---autonomy-benchmark-review)
- [2026-07-01 18:30 KST - M11 Finish-Line Fixture Runtime](#2026-07-01-1830-kst---m11-finish-line-fixture-runtime)
- [2026-07-01 18:45 KST - Real Benchmark And Fake Path Removal](#2026-07-01-1845-kst---real-benchmark-and-fake-path-removal)
- [2026-07-01 18:54 KST - Real GPU Model Output Fix](#2026-07-01-1854-kst---real-gpu-model-output-fix)
- [2026-07-01 19:07 KST - Live Web Collection Primitive](#2026-07-01-1907-kst---live-web-collection-primitive)
- [2026-07-01 19:10 KST - Offline Regression Boundary Fix](#2026-07-01-1910-kst---offline-regression-boundary-fix)
- [2026-07-01 19:21 KST - Agent Behavior Observation Only](#2026-07-01-1921-kst---agent-behavior-observation-only)
- [2026-07-01 19:27 KST - Agent Skill Proposal Attempt And Reference Notes](#2026-07-01-1927-kst---agent-skill-proposal-attempt-and-reference-notes)
- [2026-07-01 19:34 KST - Skill Workshop Proposal Boundary](#2026-07-01-1934-kst---skill-workshop-proposal-boundary)
- [2026-07-01 20:32 KST - Real Harness Skill Proposal Runs](#2026-07-01-2032-kst---real-harness-skill-proposal-runs)
- [2026-07-01 20:52 KST - Learning Loop Bootstrap Adaptation](#2026-07-01-2052-kst---learning-loop-bootstrap-adaptation)
- [2026-07-01 21:18 KST - Real Workflow Building Harness Probe](#2026-07-01-2118-kst---real-workflow-building-harness-probe)
- [2026-07-01 22:02 KST - Durable Workflow Building Probe Task](#2026-07-01-2202-kst---durable-workflow-building-probe-task)
- [2026-07-01 22:10 KST - Approval Gated Skill Proposal Apply](#2026-07-01-2210-kst---approval-gated-skill-proposal-apply)
- [2026-07-01 22:23 KST - Active Skill Routing And Revision Proposals](#2026-07-01-2223-kst---active-skill-routing-and-revision-proposals)
- [2026-07-01 22:28 KST - Skill Proposal Review Diff](#2026-07-01-2228-kst---skill-proposal-review-diff)
- [2026-07-01 22:48 KST - Real Harness Probe Observability And Review-Bound Skill Apply](#2026-07-01-2248-kst---real-harness-probe-observability-and-review-bound-skill-apply)
- [2026-07-01 23:14 KST - Real Workflow Builder Probe Quality Gate](#2026-07-01-2314-kst---real-workflow-builder-probe-quality-gate)
- [2026-07-02 00:16 KST - Agent Generated WorkflowSpec Probe](#2026-07-02-0016-kst---agent-generated-workflowspec-probe)
- [2026-07-02 09:00 KST - Session Log And Workflow Lifecycle Gate](#2026-07-02-0900-kst---session-log-and-workflow-lifecycle-gate)
- [2026-07-02 09:11 KST - Live Source Binding And Scheduled Run](#2026-07-02-0911-kst---live-source-binding-and-scheduled-run)
- [2026-07-02 09:16 KST - Fast Single Model Default](#2026-07-02-0916-kst---fast-single-model-default)
- [2026-07-02 09:25 KST - Source Quality Gate](#2026-07-02-0925-kst---source-quality-gate)
- [2026-07-02 09:31 KST - Source Strategy Tuning Backlog](#2026-07-02-0931-kst---source-strategy-tuning-backlog)
- [2026-07-02 09:41 KST - Source Strategy Proposal And Recent Window Analysis](#2026-07-02-0941-kst---source-strategy-proposal-and-recent-window-analysis)
- [2026-07-02 09:48 KST - Durable Source Strategy Recovery Task](#2026-07-02-0948-kst---durable-source-strategy-recovery-task)
- [2026-07-02 09:53 KST - Automatic Source Recovery Enqueue](#2026-07-02-0953-kst---automatic-source-recovery-enqueue)
- [2026-07-02 10:05 KST - Runtime Tick Report Delivery](#2026-07-02-1005-kst---runtime-tick-report-delivery)
- [2026-07-02 10:13 KST - Continuous Runtime Daemon And Delivery UI](#2026-07-02-1013-kst---continuous-runtime-daemon-and-delivery-ui)
- [2026-07-02 10:31 KST - Front-Door Session Log And Unattended Report Delivery](#2026-07-02-1031-kst---front-door-session-log-and-unattended-report-delivery)
- [2026-07-02 10:39 KST - Finish-Line Benchmark For Blurry Requests](#2026-07-02-1039-kst---finish-line-benchmark-for-blurry-requests)
- [2026-07-02 10:59 KST - Report Quality And Source Identity Gate](#2026-07-02-1059-kst---report-quality-and-source-identity-gate)

## 2026-07-02 13:08 KST - Operator Boundary Deduplication

Summary:

- Replaced the duplicated role-boundary material at the top of `AGENTS.md` with a single concise non-negotiable project boundary.

Changed areas:

- `AGENTS.md` now starts with Codex's permitted actions, forbidden actions, decision rules, and real-use evaluation rule.
- The boundary now explicitly says Codex must not write or run concrete crawlers, macros, reports, schedules, source strategies, or workflows for the Agent.

Verification:

- Re-read the top of `AGENTS.md` and confirmed the boundary is the first project instruction and no longer duplicated.

Roadmap impact:

- Future crawling/newsletter/browser/memory probes must be evaluated through Harness-front-door Agent behavior, not operator-written vertical patches.

Next step:

- Resume no-preseed Harness sessions and only add generic primitives when the Agent's observed failures repeat across probes.

Lessons learned:

- Noisy or weak Agent output is an in-session feedback event first. It is not permission for Codex to create a site-specific filter, URL mapping, crawler, report shape, or workflow script.

## 2026-07-02 13:04 KST - Dotenv Support For API Keys

Summary:

- Added project-root `.env` support so local API credentials are available to CLI/config paths, tests that load config, and direct `web_search` calls.

Changed areas:

- Added local ignored `.env` with the Tavily API key and set file mode to `600`.
- Added `load_dotenv()` to `agentic/config/settings.py` and wired it into `load_app_config()`.
- Updated `agentic/tools/web_search.py` to load cwd `.env` before provider selection.
- Added dotenv regression coverage in `evals/test_config_and_prompts.py` and adjusted the web-search missing-key test to avoid default-provider assumptions.
- Documented automatic `.env` loading in `README.md`.

Verification:

- `.venv/bin/python -m unittest evals.test_config_and_prompts`
- `.venv/bin/python -m unittest evals.test_tool_surface evals.test_config_and_prompts`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- Confirmed `TAVILY_API_KEY` is present after config load without printing the value.

Roadmap impact:

- External search/API providers can now be configured locally without shell-export setup for every CLI/test run.

Next step:

- Run a live Tavily-backed `web_search` probe and then wire source-discovery recovery to prefer configured API providers before browser escalation.

Lessons learned:

- Test expectations around web-search provider failures should specify the provider explicitly; default provider behavior can legitimately change.

## 2026-07-02 12:50 KST - Operator Role Boundary Hardening

Summary:

- Strengthened the first section of `AGENTS.md` so future work starts from the corrected boundary: Codex is the Harness builder/evaluator, not the performer of concrete workflows.

Changed areas:

- Added a first-read project/operator boundary section to `AGENTS.md`.
- Added explicit allowed Codex actions, forbidden Codex actions, noisy-result feedback rules, and real-use reporting rules.
- Added `.agent/LESSONS.md` and `.agent/TASK_LOG.md` entries so the correction is reusable.

Verification:

- Re-read the beginning of `AGENTS.md` and confirmed the boundary is now the first project instruction after the title.

Roadmap impact:

- Future social crawling, newsletter, browser-ticket, and memory/idea probes must start through the Harness front door with no hidden URL/source/script/workflow seeding.
- Implementation work should be limited to reusable primitives observed as missing from actual Harness sessions.

Next step:

- Re-run no-preseed Harness sessions and improve only generic source-discovery, session-feedback, candidate-review, workflow-activation, and artifact-admission primitives proven necessary by real logs.

Lessons learned:

- Bad agent output is not permission for Codex to patch the target workflow. It is first a Harness session feedback turn; only repeated general capability gaps justify implementation.

## 2026-07-02 12:25 KST - Strict Operator Agent Boundary Rewrite

Summary:

- Rewrote the top of `AGENTS.md` in Korean-first terms so future operator work starts from the correct boundary: Codex builds and evaluates the Harness; the Harness agent performs concrete workflow work through exposed tools.

Changed areas:

- Replaced the prior boundary section with explicit role separation, allowed generic Harness work, forbidden domain-specific patching, and no-preseed evaluation rules.
- Added `.agent/LESSONS.md` guidance that user feedback on bad/noisy agent output must be given inside the Harness session, not converted into hidden operator-authored filters or scripts.
- Added a recent-task entry in `.agent/TASK_LOG.md`.

Verification:

- Re-read the top of `AGENTS.md` after patching and confirmed the boundary section is the first project instruction.

Roadmap impact:

- The next implementation slice remains generic source-discovery/session-recovery infrastructure only. DCInside, stock-gallery, Reddit, Gmail, WSJ, Interpark, and Obsidian examples must remain probes unless the agent creates the concrete workflow through Harness state.

Next step:

- Run no-preseed Harness sessions and improve only the generic source-discovery/review/bind lifecycle needed for the agent to act without operator-supplied URLs or scripts.

Lessons learned:

- Bad agent output should produce a Harness session feedback turn and observable recovery attempt. It should not trigger Codex to patch the specific target site or workflow directly.

## 2026-07-02 12:18 KST - Operator And Harness Boundary Clarification

Summary:

- Added an explicit top-level project boundary to `AGENTS.md`: Codex builds and evaluates the Harness, while the Harness agent must create or recover concrete workflows through exposed tools and reviewable runtime state.

Changed areas:

- Added `Non-Negotiable Project Boundary` at the top of `AGENTS.md`.
- Added reusable lesson and task-log entry clarifying that operator-authored crawlers, source URLs, extraction rules, noise filters, and hidden setup must not be counted as agent autonomy.

Verification:

- Read `AGENTS.md` after patching and confirmed the new section is the first project instruction.

Roadmap impact:

- Future work must evaluate no-preseed autonomy separately from preseeded-runtime validation.
- The next implementation slice should be a generic source-discovery lifecycle, not a DCInside crawler or stock-gallery filter.

Next step:

- Add a Harness-owned `source_discovery` task/lifecycle where the agent receives only allowed tools, stores source candidates, and gets candidates reviewed/bound before workflow activation.

Lessons learned:

- Useful workflow examples are probes, not implementation specs. If the agent produces noisy output, Codex should respond as the user inside the Harness session and observe recovery rather than directly patching domain-specific filtering logic.

## 2026-07-02 12:07 KST - No-Preseed Agent Autonomy Diagnosis

Summary:

- Re-ran the front-door workflow path without registering any source first. This corrected the previous interpretation of the `100/100` social-trend benchmark.
- Also started a second credential-free requirement probe for local idea synthesis under the same no-preseed rule.

Changed areas:

- No runtime code changes in this slice.
- Added this correction log and a durable lesson that preseeded sources are not agent discovery.

Verification:

- No-preseed stock request:
  - request: `주식갤을 계속 관찰해서 트렌드 보고하는 workflow 만들어줘.`
  - result: created proposed workflow `wf_2d76a16dd1c340c1bcee33a9da977b23`
  - source store: empty
  - task/delivery store: empty
  - blocker: source discovery/binding never happened because the WorkflowDesigner is deterministic and does not call tools.
- No-preseed idea synthesis request:
  - request: `내 아이디어들을 계속 모아서 주기적으로 연결점과 새 영감을 보고하는 workflow 만들어줘.`
  - result: created proposed workflow `wf_4ed3bf20a9954612bedfb016a750cbef`
  - source store: empty
  - task/delivery store: empty
  - blocker: local idea source discovery/registration is not tool-driven yet.

Roadmap impact:

- Real-usefulness score for true no-preseed autonomy is revised down from the previous preseeded benchmark claim. Current honest level is roughly `45/100` for source-discovery workflows: the harness can classify/propose/session-log, but it does not yet let the agent discover and register unknown sources using tools.
- The preseeded social-trend path remains useful as a runtime execution benchmark, but it must not be used as proof that the agent can discover `주식갤` or any unknown source.

Next step:

- Implement a no-preseed source-discovery loop: missing source binding should create an agent/tool task that can use allowed tools such as `web_search` or browser/search connectors, propose source candidates, and register/bind them only through reviewable runtime state.
- Add a no-preseed benchmark that fails unless source discovery, source registration, activation, live collection, report, and delivery all happen without preloaded URLs.

Lessons learned:

- Source registry seeding is a test fixture. It can prove downstream runtime behavior, but it is not agent autonomy.
- The next real gap is not another crawler. It is a tool-using source-discovery lifecycle owned by the Harness.

## 2026-07-02 11:31 KST - Model-Assisted Report Synthesis Finish-Line

Summary:

- Added and verified model-assisted report synthesis as part of the real finish-line workflow path.
- The first live Q4 synthesis benchmark returned `100/100`, but manual inspection found a prompt-meta line had been admitted as an insight. The parser/admission layer was tightened and the live benchmark was rerun successfully.

Changed areas:

- Hardened `agentic/synthesis/report.py` to filter prompt/meta claims such as `Goal: Extract...`, clean embedded `Claim:` fragments, and remove evidence-label clutter from claims.
- Added regression coverage in `evals/test_report_synthesis.py`.
- Updated `docs/roadmap.md` with the `Model-Assisted Report Synthesis` primitive.

Verification:

- `.venv/bin/python -m unittest evals.test_report_synthesis evals.test_finish_line_benchmark evals.test_report_delivery`
- `.venv/bin/python -m unittest discover -s evals` ran 257 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`
- Real Q4 live benchmark:
  - command: `.venv/bin/python -m agentic.app.cli finish-line-bench --state-dir /tmp/agentic-model-synthesis-live-q4-v2 --ntfy-topic 9ffae2bc-abc5-4173-943d1c0aed83 --timeout-s 300 --synthesis-model master-gemma-q4 --synthesis-max-tokens 768 --require-model-synthesis`
  - session: `sess_d14c9e19efeb49fc85519c51d393ea2b`
  - workflow: `wf_18fe68485681421182aa50da98d28a2e`
  - recovery task: `task_0526ceafda3f444c861ef804d793ccad`
  - report artifact: `art_a29a9a2aa9c3461e90b452e45182ecca`
  - delivery: `del_6a7a6eed7f424316bcb2469ed927ec5a`
  - report quality: `100`
  - report synthesis: `ok`, 3 grounded insights from `master-gemma-q4`
  - finish-line score: `100/100`

Roadmap impact:

- Real-usefulness score increases from 98/100 to 100/100 for the current social-trend finish-line benchmark: a vague one-line request plus two interview answers reached session log, active workflow, live source recovery, quality-gated report artifact, model-assisted grounded insight synthesis, and sent ntfy delivery.
- The score is benchmark-specific, not a blanket claim that Gmail, browser ticketing, Obsidian memory, or coding workflows are complete.

Next step:

- Package the same finish-line path into the serve/daemon default operating mode and add a persistent model runner option so repeated report synthesis avoids per-call GGUF reload cost.

Lessons learned:

- A numeric benchmark pass is not enough; manual artifact inspection caught a prompt-meta insight that the first admission pass missed.
- Model-assisted report synthesis needs deterministic filters around local model output. The model may provide useful grounded insight, but the runtime must remove instructions, schema text, and embedded reasoning debris before delivery.

## 2026-07-02 11:30 KST - Core Tool Surface And API Web Search

Summary:

- Added OpenClaw-style local file/process tools and an API-backed `web_search` tool with multiple provider adapters.

Changed areas:

- Added `agentic/tools/filesystem.py` for `read_file`, `write_file`, `edit_file`, `list_files`, `search_files`, and workspace-contained `apply_patch`.
- Added `agentic/tools/patch.py` for structured patch envelope application.
- Added `agentic/tools/execution.py` for `exec`, `process`, and `python_execute`.
- Added `agentic/tools/web_search.py` with Brave, Tavily, Exa, Serper, and SearXNG providers.
- Registered the new tools in `ToolRegistry.with_defaults()`.
- Updated policy so approval-gated paths allow read/search tools but require approval for write/patch/shell/Python/process tools.
- Updated docs for the new tool surface and web search provider env vars.

Verification:

- `.venv/bin/python -m unittest evals.test_tool_surface`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- The harness now has a broader default tool surface for coding and source discovery loops.
- Search can move beyond static HTTP fetch when source quality gates show extraction is weak or blocked.

Next step:

- Wire workflow source binding and source-strategy recovery to choose `web_search` as a fallback/escalation path before browser automation.

Lessons learned:

- OpenClaw's shape is useful, but the local harness still needs explicit policy gates because default `ToolRegistry` execution is otherwise direct and powerful.

## 2026-07-02 11:00 KST - Tool And MCP Inventory Review

Summary:

- Reviewed the current implemented ToolRegistry, connector, MCP adapter, source collector, and channel surfaces to clarify whether `web_search`/`web_extract` already exist and where an external API-backed implementation should attach.

Changed areas:

- Updated this work log only; no runtime code was changed.

Verification:

- Printed `ToolRegistry.with_defaults().schemas()` and confirmed the default tools are `add`, `web_fetch`, `html_extract_links`, `skill_workshop`, and `workflow_spec`.
- Ran `.venv/bin/python -m agentic.app.cli config-check`.
- Searched the codebase for `web_search`, `web_extract`, tool registration, MCP adapter, and connector registrations.

Roadmap impact:

- The current code has an MCP client boundary and web fetch/extract primitives, but no dedicated external search/extraction API connector yet.
- A future reliability improvement should add API-backed `web_search`/`web_extract` as either new local tools or an allowlisted MCP/search connector with provenance metadata and source quality admission.

Next step:

- Add a source/search connector design slice for API-backed search/extraction, then route workflow source binding through it when static HTTP extraction is too weak or blocked.

Lessons learned:

- The existing web capability is fetch-plus-static-link-extraction, not search. Treating `web_search` as already implemented would overstate the current connector surface.

## 2026-07-02 10:59 KST - Report Quality And Source Identity Gate

Summary:

- Added generic report quality admission so report artifacts must include useful sections, evidence, signals, source quality, and next watch points before ntfy delivery is enqueued.
- Strengthened live source collection quality so source identity embedded in URL query parameters is preserved; a DCInside stock-gallery run no longer passes with `dcbest` links.

Changed areas:

- Added `agentic/artifacts/report_quality.py` and wired quality metadata into `WorkflowInterpreter` report artifacts.
- Updated `ReportDeliveryService` to skip low-quality report artifacts instead of notifying the user.
- Added `href_contains_all` as an AND-style source extraction primitive for collectors, CLI source commands, and source strategy recovery.
- Tightened `SourceQualityReport` so explicit quality failure reasons block `ok`, including source identity drift and notice/bracket-code noise.
- Updated source strategy recovery proposals to add source identity fragments, default navigation excludes, bracket-number regex filters, and a safer `min_items` floor.
- Extended the finish-line benchmark result with `report_quality` and raised the passing score to 98 when delivery and report quality both pass.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- Real live command:
  `.venv/bin/python -m agentic.app.cli finish-line-bench --state-dir /tmp/agentic-report-quality-live-v4 --ntfy-topic 9ffae2bc-abc5-4173-943d1c0aed83 --timeout-s 120`
- Live result: workflow `wf_ef215eafca414b64864e80ba5c905ca4`, session `sess_1567200475f345af8fe87ca6810ee998`, recovery task `task_57338dc53faa46c0af4a799b6512db27`, artifact `art_1e9c48315a0b40afb1bb6c4bc4969df6`, delivery `del_7596e49af61746dc8b39a01662e50663`, report quality score 100, finish-line score 98/100.
- Manual artifact inspection confirmed evidence links use `id=stock_new2` and no longer start with the previous notice/bracket-code items.

Roadmap impact:

- The main social/community recurring workflow probe now verifies delivery plus source identity and report quality, not just lifecycle completion.
- Remaining gap is semantic synthesis quality: reports are still mostly deterministic evidence/keyword summaries rather than model-assisted insight and recommendation.

Next step:

- Add a model-assisted synthesis/admission step for report semantics that turns collected evidence into higher-signal insights while keeping source provenance and quality gates deterministic.

Lessons learned:

- A report quality gate can still be fooled if source relevance is not checked; quality must include source identity, not only shape and section count.
- Recovery proposals need AND-style href requirements; appending more OR-style `href_contains` fragments can widen collection instead of constraining it.

## 2026-07-02 10:39 KST - Finish-Line Benchmark For Blurry Requests

Summary:

- Added a repeatable front-door finish-line benchmark for the exact target shape: vague request, two interview answers, session log, WorkflowSpec lifecycle, scheduled runtime tick, automatic source recovery, report artifact, and real ntfy delivery.

Changed areas:

- Added `agentic/probes/finish_line.py`.
- Added CLI command `finish-line-bench`.
- Added `evals/test_finish_line_benchmark.py`.
- Tightened source inference so `ntfy/알림` is treated as output/channel, not a data source.
- Added a continuation answer for the mobile approval requirement smoke probe.
- Documented the finish-line benchmark command in `README.md`.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- Real live command:
  `.venv/bin/python -m agentic.app.cli finish-line-bench --state-dir /tmp/agentic-finish-line-live --ntfy-topic 9ffae2bc-abc5-4173-943d1c0aed83 --timeout-s 120`
- Live result: workflow `wf_c32f09778ac943949610968ed3ef0b57`, session `sess_5f977ce16943431697e5aeb8728086ad`, recovery task `task_4ffbbdddd2ca44ef83609dcb36913446`, artifact `art_ec9d74eb48a947b0a874437af4f720af`, delivery `del_e8842cc1090e46adbe82fdabd8de16d6`, score 96/100.

Roadmap impact:

- The main “blurry request plus 2 answers to delivered report” validation probe now exists and passes on a real live source with real ntfy delivery.
- Remaining gap is report quality and richer agent analysis, not workflow lifecycle reach.

Next step:

- Improve report generation semantics and add a report quality/admission gate so delivered reports are useful enough for regular 24/7 consumption.

Lessons learned:

- Benchmark commands should use the same front-door routes as the web UI; otherwise they prove a different path than the one the user will operate.
- Vague-request scoring should require interview answer count, session log evidence, and sent delivery, not only workflow status.

## 2026-07-02 10:31 KST - Front-Door Session Log And Unattended Report Delivery

Summary:

- Closed a key front-door gap: web workflow design now creates a full session log, attaches the session id to the created WorkflowSpec, advances lifecycle gates, and records lifecycle evidence.
- Fixed read-only low-risk ntfy report delivery so a personal notification does not incorrectly block execution behind an approval gate.

Changed areas:

- Added `SessionLogStore` wiring to `agentic/app/server.py` and `agentic/app/channel_app.py`.
- Added `/sessions` and `/sessions/{session_id}/events` API routes plus a Session Logs web panel.
- Added session-log attachment to workflow design and planning-answer routes.
- Updated capability planning so `channel:ntfy` is allowed for low-risk read-only owner notifications while high-risk and consequential capabilities remain gated.
- Removed runtime circular imports from `workflow_kernel.lifecycle`.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- Fresh web/API front-door probe in `/tmp/agentic-frontdoor-session-live` registered the real DCInside source, created active workflow `wf_8ac08754ff794335b5250237eed5aaa7`, and persisted session `sess_14055190e1e2472ea0416e138c11f93e` with user request, workflow proposal, lifecycle advance, and agent response events.
- Real runtime tick fetched the live source, observed an initial source quality failure, automatically ran source strategy recovery task `task_757dc8768a854b5d9ceaea0e12f5e792`, produced report artifact `art_2b7cfbba7cff46a0b23ddd9752b507ac`, and sent ntfy delivery `del_29bd7cfadafb4193bcde512f6b08a66d`.

Roadmap impact:

- Score: 92/100. The harness now reaches one-line front-door request to session log, active scheduled workflow, live source recovery, report artifact, and real ntfy delivery.
- Remaining gaps are multi-turn interview coverage for underspecified requests, richer report semantics, and packaging the daemon as an unattended service.

Next step:

- Add a finish-line benchmark that starts from an intentionally blurry request requiring 2-3 planning answers and proves the same path reaches delivered report without operator stitching.

Lessons learned:

- A personal owner notification is a report-delivery fact, not a consequential external action, when the workflow is low-risk and read-only.
- Full session logs must be created at the web front door, not only in probe code, otherwise successful lifecycle events are hard to audit.

## 2026-07-01 11:40 KST - M7 Workflow Kernel Implementation

Summary:

- Implemented the M7 Workflow Kernel as a framework layer rather than a vertical newsletter/crawler feature.

Changed areas:

- Added `agentic/workflow_kernel/` for intent routing, workflow design, workflow specs/runs, capability planning, and interpreter/builder v0.
- Added `agentic/scheduler/` for schedule records, schedule store, and due-runner v0.
- Added `agentic/artifacts/` for report/script/screenshot/dataset/config/log artifact records.
- Extended the local web UI/API with workflow design, approve, activate, pause, run, and status routes.
- Updated M7 docs and roadmap to mark newsletter/social trend/browser/coding/idea workflows as probes.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M7 is implemented.
- M8 should focus on source connectors, capability runtime, credential references, artifact admission, and generated-script review/dry-run.

Next step:

- Implement M8 Source, Capability, And Artifact Runtime.

Lessons learned:

- The harness must keep workflow control flow outside individual agents. Agents provide intelligence inside steps; the workflow engine owns lifecycle.
- Generated scripts must be artifacts first, executable capabilities later, and only after admission plus approval.
- Vertical use cases should prove `WorkflowSpec` expressiveness, not create separate daemon paths.

## 2026-07-01 11:58 KST - Roadmap Review And Work Log Rule

Summary:

- Added durable project instructions requiring roadmap review, next-step reporting, lessons learned, and append-only work-log maintenance after each substantive task.

Changed areas:

- Added root `AGENTS.md`.
- Added this `docs/work_log.md` file with a maintained table of contents.

Verification:

- Documentation-only change. No code verification required beyond file inspection.

Roadmap impact:

- No milestone implementation changed.
- Project process now requires every completed work item to reconnect to the roadmap.

Next step:

- M8 Source, Capability, And Artifact Runtime remains the recommended next milestone.

Lessons learned:

- The project is moving fast enough that process memory matters. The work log prevents roadmap drift and preserves why each framework-level decision was made.

## 2026-07-01 12:01 KST - M8 Source Capability And Artifact Runtime

Summary:

- Implemented the M8 framework primitives that let workflows declare sources, collect fake/default-safe source items, store raw resources, hold credential references, and gate generated artifacts.

Changed areas:

- Added `agentic/sources/` for source definitions, source policies, source items, dedupe store, fake collector, and source runtime.
- Added `agentic/credentials/` for secret-free credential references and SQLite persistence.
- Added artifact admission and dry-run gating to `agentic/artifacts/`.
- Extended policy gates for generated scripts, external connectors, browser submit, email send, file write, shell, booking, and payment.
- Added `docs/milestone8_status.md`.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M8 is implemented as framework substrate.
- Production crawlers and live OAuth remain intentionally deferred to M9 probes or later production hardening.

Next step:

- Implement M9 Workflow Probe Pack using the M7/M8 primitives.

Lessons learned:

- Source collection needs a durable raw-item layer before analysis. Otherwise reports lose auditability.
- Credential handling should store references only; even metadata keys can leak secrets if not filtered.
- Generated scripts need admission and dry-run semantics before execution becomes a runtime capability.

## 2026-07-01 12:11 KST - M9 Workflow Probe Pack

Summary:

- Implemented M9 probes that validate the harness framework with user-shaped scenarios without introducing bespoke runtime paths.

Changed areas:

- Added `agentic/workflow_probes/` with probe models, factory, and runner.
- Added probe specs for newsletter analysis, social trend intelligence, idea synthesis, browser watcher, and coding workflow.
- Added fake/default-safe source definitions for every probe.
- Represented browser watcher generated script as a review-required artifact instead of an executable step.
- Added `docs/milestone9_status.md`.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M9 is implemented as framework validation.
- M10 should harden the local runtime for continuous operation.

Next step:

- Implement M10 24/7 Hardening.

Lessons learned:

- A probe pack is useful only if it proves the framework shape. Keeping all probes on `WorkflowSpec` exposed whether primitives were truly reusable.
- Browser automation must keep generated scripts as review artifacts until M10+ operational controls and approvals are stronger.
- Fake/default-safe probes let the full suite verify architecture without requiring network, GPU, real browser, or credentials.

## 2026-07-01 12:51 KST - README Implementation Summary Refresh

Summary:

- Rewrote `README.md` as a current implementation overview covering Phase 0/1 and M2 through M9.

Changed areas:

- Documented the project as a local-first agent harness framework rather than a collection of one-off automations.
- Summarized implemented modules for local models, agent loop, channel/approval, durable runtime, connectors/MCP boundary, skills, memory/resources, workflow kernel, sources/capabilities/artifacts, and workflow probes.
- Added explicit "not implemented yet" boundaries for live Gmail, WSJ, Reddit/DCInside crawling, Playwright execution, autonomous scripts, public auth, marketplace, and 24/7 hardening.
- Refreshed command examples, runtime state paths, GPU smoke paths, WSL memory guidance, and latest verification status.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- No implementation milestone changed.
- Documentation now reflects M9 as the current completed framework-validation milestone and M10 as the next hardening milestone.

Next step:

- Implement M10 24/7 Hardening: daemon reliability, startup/shutdown behavior, observability, operational safety, and manual long-running smoke checks.

Lessons learned:

- The README needs to distinguish framework primitives from deferred production integrations, otherwise the milestone list can sound more production-ready than it is.
- The project has enough modules now that a repository map is part of the product surface, not just documentation polish.

## 2026-07-01 13:38 KST - M10 Real-Only Runtime Boundary

Summary:

- Started M10 by removing product runtime paths that silently generated fake source/model/connector behavior and replacing workflow probes with real local source execution.

Changed areas:

- Removed `ModelConfig.fake()` and the CLI `smoke --fake` path.
- Removed runtime `FakeConnector` from the product connector package.
- Removed `SourceKind.FAKE` and the default fake source collector.
- Added local collectors for files, mail-like JSONL, feed-like JSONL, browser-page files, and repository state.
- Changed `WorkflowInterpreter` collect steps to require `SourceRuntime` and `ResourceStore`.
- Changed workflow probes to use checked-in local source files or current repo state.
- Added `evals/test_milestone10_real_e2e.py` for a source-backed collect -> aggregate -> analyze -> report flow.
- Updated README, roadmap, and milestone status docs to describe the real-only boundary.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M10 is started.
- The first hardening step is complete: product runtime paths should fail clearly when real configuration is missing instead of inventing success data.

Next step:

- M10 step 2 should add operational health primitives: process uptime, task-pool health, collector health, recent failure panels, restart-safe status export, and alert hooks.

Lessons learned:

- A harness can use local fixtures in evals, but the product runtime must not generate invented source data.
- Workflow proposals without source binding should be blocked or fail clearly; completing them with synthetic collect results hides the exact problems M10 is supposed to surface.

## 2026-07-01 13:54 KST - M10 Operational Health Primitives

Summary:

- Added the first production-facing operational health layer for the local harness.

Changed areas:

- Added `agentic/ops/` with `HealthMonitor`, `HealthSnapshot`, and `RuntimeHealthStatus`.
- Health snapshots now summarize task, workflow, source, artifact, approval, and task-pool status.
- Added recent task/workflow failure reporting.
- Added missing enabled local-source warnings.
- Added `GET /ops/health` and `POST /ops/health/export`.
- Added an Ops Health panel to the web UI.
- Added CLI `ops-status`.
- Added `evals/test_milestone10_ops_health.py`.
- Updated README and `docs/milestone10_status.md`.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `.venv/bin/python -m agentic.app.cli ops-status`
- `timeout 5s .venv/bin/python -m agentic.app.cli serve --host 127.0.0.1 --port 8890`

Roadmap impact:

- M10 step 2 is complete.
- The harness now has a concrete operational surface for observing whether local runtime pieces are healthy, degraded, or unhealthy.

Next step:

- M10 step 3 should harden service lifecycle: graceful shutdown timing, restart smoke script, health-based exit checks, and manual long-running serve/worker smoke checklist.

Lessons learned:

- A local daemon needs a status surface before more automation is added; otherwise failures only appear as scattered traces.
- CLI health without a running server can be degraded because no task pool is attached. That distinction is useful because it tells us whether we are inspecting state offline or observing the live service.

## 2026-07-01 14:02 KST - Browser Smoke And Workflow Source Binding

Summary:

- Attempted Chrome plugin validation, found a Chrome bridge runtime blocker, then completed real HTTP/UI-path validation and fixed workflow design source binding.

Changed areas:

- Added `agentic/workflow_kernel/source_binding.py`.
- Web workflow design now binds known request sources to checked-in local sources or current repo state before persisting the `WorkflowSpec`.
- Updated server/channel app wiring to pass `SourceStore` into workflow design.
- Updated milestone docs and README.

Verification:

- Attempted Chrome plugin via `mcp__node_repl.js`; blocked by `codex/sandbox-state-meta: sandboxCwd is not a local file URI`.
- Started `serve` on `127.0.0.1:8891`.
- Executed real HTTP flow: workflow design -> approve -> activate -> run.
- Confirmed social trend workflow bound `community_web` to `examples/sources/market_community_posts.jsonl`.
- Confirmed run completed and created report artifact.
- Confirmed `GET /ops/health` returned `ok`.
- Confirmed `POST /ops/health/export` wrote `traces/state/health_snapshot.json`.
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M10 operational smoke exposed and fixed the gap between workflow design and real source execution.
- Chrome plugin validation remains blocked by the local tool bridge, not by the harness server.

Next step:

- M10 step 3 should add service lifecycle hardening and a repeatable browser/HTTP smoke checklist.

Lessons learned:

- Workflow design is not operational until its abstract source is bound to a concrete source record.
- Smoke tests are more useful when they include the web route sequence, not only unit-level workflow execution.

## 2026-07-01 14:14 KST - M10 Ops Smoke And Real GPU Model Validation

Summary:

- Added repeatable operational smoke checks and validated the configured local models on the RTX 4090 path.

Changed areas:

- Added `agentic/ops/smoke.py`.
- Added CLI `ops-smoke`.
- Added `ops-smoke --include-model --model ... --model-max-tokens ...`.
- Fixed `response_sanitizer` to preserve complete master decision JSON.
- Added safe extraction for explicit direct answers inside internal model text without exposing the full internal text.
- Added `evals/test_milestone10_ops_smoke.py`.
- Updated README and `docs/milestone10_status.md`.

Verification:

- `.venv/bin/python -m agentic.app.cli ops-smoke`
- `.venv/bin/python -m agentic.app.cli ops-smoke --include-model --model master-gemma-q4 --model-max-tokens 256`
- `.venv/bin/python -m agentic.app.cli smoke --model master-gemma-iq2 --max-tokens 192 --prompt '한국의 수도는 어디야? 답변만 한 문장으로 말해.'`
- `.venv/bin/python -m agentic.app.cli smoke --model master-gemma-q4 --max-tokens 256 --prompt '한국의 수도는 어디야? 답변만 한 문장으로 말해.'`
- `.venv/bin/python -m agentic.app.cli smoke --model subagent-diffusiongemma-q4 --max-tokens 64 --prompt 'Use add to compute 7+5. Return only the tool call JSON.'`
- `.venv/bin/python -m agentic.app.cli ask '7+5는 뭐지?'`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M10 step 3 is complete.
- The harness now has a repeatable operational smoke command and proof that the configured local GPU model path can execute the minimal master/subagent/tool loop.

Next step:

- M10 step 4 should harden service lifecycle: graceful shutdown timing, restart smoke scripts, health-based exit checks, and a longer running serve/worker soak checklist.

Lessons learned:

- Real model smoke exposed a sanitizer bug that unit tests had not caught: complete master decision JSON must be preserved for the harness loop.
- IQ2 needs more generation budget than the default short smoke for this prompt; `--max-tokens 192` produced the expected answer.
- DiffusionGemma Q4 can produce the intended tool-call JSON for the subagent role, and the full loop now completes with real GPU model calls.

## 2026-07-01 14:28 KST - DeepResearch Ticket Booking Probe

Summary:

- Ran a live probe for the blurry request "MSI 2026 결승전 표 예매해줘" across the current Master path, workflow-design path, local web UI/API, and notification boundary.

Changed areas:

- Documentation-only log entry. No code changes were made in this probe.

Verification:

- Attempted Chrome plugin control; blocked by `codex/sandbox-state-meta: sandboxCwd is not a local file URI`.
- Searched current public sources for MSI 2026 ticketing. LoL Esports shows MSI running June 28 to July 12, 2026, but no official ticketing page was found through search/Ticketlink/Interpark queries.
- Ran real GPU Master full loop: `.venv/bin/python -m agentic.app.cli ask 'MSI 2026 결승전 표 예매해줘'`; current Phase 1 path returned "답변을 정리하지 못했습니다."
- Ran real GPU Master raw smoke with `max_tokens=512`; Master correctly delegated research for official ticketing schedule/platform discovery.
- Submitted the blurry request to the web workflow designer on `127.0.0.1:8892`; it asked for a source/URL, proving partial interview behavior.
- Submitted a natural follow-up mentioning official ticket site discovery and ntfy; the designer proposed a high-risk Browser Watcher workflow.
- Approved, activated, and ran the proposal; capability planning stopped at `waiting_for_approval` for `channel:ntfy`.
- Attempted notify-user ntfy push. Sandbox DNS failed first, and escalated network egress was rejected by policy for external data transfer to ntfy.sh.

Roadmap impact:

- This probe confirms the next M10 work should not be another vertical automation. It should add framework primitives for interactive planning sessions, browser capability execution, login/input checkpoints, and approval-resumable workflow runs.

Next step:

- Implement the `Interactive Planning And Browser Action Runtime` slice: session-backed workflow design, `ASK_USER` runtime support, browser-action capability specs, credential/login checkpoints, approval-to-resume for waiting workflow runs, and a real browser adapter boundary.

Lessons learned:

- The local Master can reason about ticket booking when given enough generation budget, but the Phase 1 prompt/loop is not the right route for high-risk multi-step work.
- The workflow designer has the beginning of grilling/interview behavior, but it is stateless; follow-up answers must attach to a design session.
- High-risk tasks need first-class `ASK_USER`, `APPROVAL`, and `BROWSER_ACTION` primitives before the harness can safely attempt login-gated ticketing.
- ntfy is configured conceptually, but external delivery can be blocked by policy; the harness needs a local notification fallback and a clear external-egress approval story.

## 2026-07-01 14:39 KST - M11 Browser Transaction Runtime Design

Summary:

- Designed the framework gap needed for the MSI 2026 ticket booking workflow and converted it into a reusable browser transaction runtime milestone.

Changed areas:

- Added `docs/milestone11_browser_transaction_runtime_plan.md`.
- Updated `docs/roadmap.md` with Milestone 11: Interactive Browser Transaction Runtime.

Verification:

- Reviewed the current roadmap and M10 status.
- Rechecked current LoL Esports MSI 2026 public information: Daejeon Convention Center II, Grand Final on July 12, 2026, and NOL World ticket sales waves.
- Documentation-only change; no code tests were required.

Roadmap impact:

- M11 is now the next framework milestone after M10 hardening.
- The MSI ticket request is explicitly treated as a validation probe for planning sessions, live browser actions, login checkpoints, approval resume, and watcher retry primitives.

Next step:

- Implement M11-A through M11-F, starting with durable planning sessions and browser transaction intent routing.

Lessons learned:

- A ticket booking workflow is not a scraper plus click macro. It is a high-risk transaction workflow with official-source verification, user presence, approvals, and retryable state handling.
- The agent should not run continuously in 24/7 mode. Deterministic observation and state hashing should run cheaply, while model calls happen only on ambiguity or state changes.
- The reusable framework shape is `observe -> classify -> policy -> ask/act -> record -> retry`, not an MSI-specific script.

## 2026-07-01 15:10 KST - M11 Planning And Tooling Backbone

Summary:

- Implemented the first M11 backbone slice so blurry automation requests can become durable planning sessions, browser transaction workflow specs, and explicit tooling backlog items.

Changed areas:

- Added `IntentType.BROWSER_TRANSACTION`.
- Added `StepType.BROWSER_OBSERVE` and `StepType.BROWSER_ACTION`.
- Updated intent routing for ticket/booking/purchase/browser transaction requests.
- Extended `WorkflowDesigner` with browser transaction slot extraction and multi-turn continuation.
- Added `PlanningSessionStore`.
- Added `agentic/tooling/` with tooling request models, planner, and SQLite backlog store.
- Wired planning sessions and tooling backlog into the FastAPI app and web UI.
- Added `evals/test_milestone11_harness_backbone.py`.
- Updated README and added `docs/milestone11_status.md`.

Verification:

- `.venv/bin/python -m unittest evals.test_milestone11_harness_backbone`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M11 is now implemented at the backbone level.
- The harness can now represent "I need new tooling/capabilities before I can execute this workflow" as durable state instead of losing it as an ad hoc blocker.

Next step:

- Implement M11 runtime execution: executable `ASK_USER`, workflow pause/resume, approval-resume, local browser observation adapter with fixture pages, and retry state for unavailable/sold-out/browser-blocked states.

Lessons learned:

- The missing layer was not another connector; it was a durable translation layer from capability gaps to buildable tooling backlog.
- Planning sessions are the core bridge between blurry user intent and executable workflow specs.
- For 24/7 automation, the harness needs to remember both workflow state and tooling debt. Otherwise the agent cannot improve its environment over time.

## 2026-07-01 18:02 KST - Experience Loop And Requirement Smoke

Summary:

- Added a structured experience loop and script-only requirement smoke runner so user-shaped automation probes continuously produce reusable lessons and bottleneck data.

Changed areas:

- Added `agentic/experience/` with experience events, JSONL store, requirement probes, and requirement smoke runner.
- Added CLI commands:
  - `requirements-smoke`
  - `experience-list`
- Added `evals/test_experience_loop.py`.
- Updated `AGENTS.md` with Experience Loop operating rules.
- Added `docs/experience_loop.md`.
- Added `docs/requirements_smoke_status.md`.
- Updated README, roadmap, and user requirements docs.

Verification:

- `.venv/bin/python -m unittest evals.test_experience_loop`
- `.venv/bin/python -m agentic.app.cli requirements-smoke --state-dir traces/state/requirements_smoke_rerun --experience-path traces/experience.jsonl`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `.venv/bin/python -m agentic.app.cli experience-list --limit 3`

Roadmap impact:

- Added Experience Loop as a cross-cutting backbone.
- User requirement probes are now executable without UI and append structured events to `traces/experience.jsonl`.
- The harness can now accumulate evidence about what works, what is blocked by approval, and what missing tooling must be built next.

Next step:

- Implement M11 runtime execution slice: executable `ASK_USER`, workflow pause/resume, approval-resume, local browser fixture adapter, browser observation artifacts, and retry state.

Lessons learned:

- A failing smoke is productive when it records structured evidence. The first mobile approval probe exposed a source-routing gap and was immediately fixed.
- Completed local-source probes still need production bottlenecks recorded; otherwise local fixtures can make the harness look more ready than it is.
- Experience must be queryable by scripts, not just readable in narrative docs, so future agents can retrieve recent lessons before repeating work.

## 2026-07-01 18:19 KST - Autonomy Benchmark Review

Summary:

- Evaluated the current harness autonomy level and mapped common autonomous-agent benchmarks to the project roadmap.

Changed areas:

- Added `docs/autonomy_benchmark_review.md`.

Verification:

- Research/documentation task only.
- Reviewed current requirements smoke and M11 status docs.
- Browsed public benchmark references for WebArena, GAIA, OSWorld, WorkArena/BrowserGym, AgentBench, τ-bench, Mind2Web, SWE-bench, MCP-Bench, and related benchmark families.

Roadmap impact:

- Current harness is assessed as L2.2 / L5: strong workflow/backbone maturity, low real-world execution autonomy.
- Public benchmark readiness is currently near-zero for browser/OS/coding benchmarks until live adapters and action runtimes exist.
- Internal requirement smoke should remain the primary benchmark until M11 runtime execution is implemented.

Next step:

- Implement M11 runtime execution slice and add a browser fixture benchmark before attempting WebArena/Mind2Web-style evaluation.

Lessons learned:

- The project is ahead in orchestration and experience capture, but behind in grounded action.
- Public agent benchmarks mostly evaluate execution in real/simulated environments; our current system mostly evaluates representation and gating.
- The right near-term benchmark is not WebArena yet; it is a local fixture benchmark that exercises pause/resume, approval, browser observation, and retry state.

## 2026-07-01 18:30 KST - M11 Finish-Line Fixture Runtime

Superseded by the 2026-07-01 18:45 KST real-only correction below.

Summary:

- Implemented the first M11 finish-line execution slice so a browser transaction workflow can reach a completed report through local HTML fixtures.

Changed areas:

- Added `agentic/browser/` with `BrowserObservation`, `BrowserActionResult`, and `LocalFixtureBrowserAdapter`.
- Updated `CapabilityPlanner` so `connector:browser_fixture` is allowed only for local regression execution while live `connector:browser` remains missing.
- Updated `WorkflowInterpreter` so fixture/preapproved paths can execute `ASK_USER`, `BROWSER_OBSERVE`, `BROWSER_ACTION`, `APPROVAL`, and `REPORT`.
- Added checked-in browser fixtures for available, sold-out, and login-required states.
- Added `evals/test_milestone11_runtime_execution.py`.
- Updated `AGENTS.md`, README, roadmap, M11 status, autonomy benchmark review, and experience-loop docs.

Verification:

- `.venv/bin/python -m unittest evals.test_milestone11_runtime_execution`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `.venv/bin/python -m agentic.app.cli requirements-smoke`

Roadmap impact:

- M11 now has a script-only finish-line browser transaction benchmark for the safe local fixture path.
- Live browser automation remains intentionally blocked until a real adapter, user resume, approval-resume, and retry-state runtime are implemented.
- Autonomy score updated from L2.2 to L2.6 because execution can now complete in a local browser-contract environment, but not on live sites.

Next step:

- Implement M11 resume/retry runtime: pause/resume for user login, approval-resumable workflow runs, retry state for sold-out/not-open states, and then a real browser adapter behind the same contract.

Lessons learned:

- "End-to-end" must mean terminal useful state, not just workflow representation. The new fixture benchmark forces that distinction.
- A local fixture adapter is useful only if live paths stay blocked and explicit; otherwise it becomes fake product capability.
- Experience-loop rules apply to both Codex and Agentic. Codex should inspect recent experience before similar work, and Agentic should turn blocked runs into structured state.

## 2026-07-01 18:45 KST - Real Benchmark And Fake Path Removal

Summary:

- Removed fixture/preapproved browser execution from product paths and added a real user-requirement benchmark that actually attempts live/local capabilities.

Changed areas:

- Added `agentic/benchmarks/` with `real-bench` probes for memory, repo inspection, Gmail/WSJ, ticket browser readiness, ntfy, Reddit, DCInside, and local GGUF model execution.
- Removed `LocalFixtureBrowserAdapter` and browser fixture eval files from product/eval path.
- Removed `preapproved` approval bypass and `connector:browser_fixture` capability admission.
- Replaced product Gmail fixture connector with a real `GmailImapConnector`.
- Updated `AGENTS.md`, README, roadmap, M11 status, autonomy benchmark review, experience-loop docs, and added `docs/real_benchmark.md` plus `docs/real_benchmark_status.md`.

Verification:

- `.venv/bin/python -m py_compile agentic/benchmarks/models.py agentic/benchmarks/real.py agentic/connectors/gmail/imap.py agentic/app/cli.py agentic/workflow_kernel/interpreter.py agentic/workflow_kernel/capabilities.py agentic/workflow_kernel/designer.py`
- `.venv/bin/python -m agentic.app.cli config-check`
- `CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --model master-gemma-iq2 --model-max-tokens 12`
- `CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --skip-network --skip-ntfy --model master-gemma-q4 --model-max-tokens 32`
- `.venv/bin/python -m agentic.app.cli real-bench --skip-network --skip-ntfy --skip-model --no-persist-experience`
- `.venv/bin/python -m unittest discover -s evals` (`Ran 160 tests`, `OK (skipped=2)`)

Roadmap impact:

- Internal benchmark priority moved from fixture/representation checks to real execution checks.
- Autonomy assessment corrected to L2.3 / L5.
- Current real blockers are Gmail credentials, official ticket URL, live browser adapter, Reddit access strategy, and local model empty output.

Next step:

- Fix the local GGUF runner/template path so the model produces non-empty output, then implement real browser adapter + approval/input resume.

Lessons learned:

- A process that launches and returns code 0 is not enough; empty model output is not useful autonomy.
- ntfy and DCInside crawling work on real paths today, while Reddit needs a compliant connector/API path.
- Credential/input/tooling blockers should be first-class benchmark outcomes, not reasons to substitute fake data.

## 2026-07-01 18:54 KST - Real GPU Model Output Fix

Summary:

- Fixed the real local GGUF model empty-output bug.

Changed areas:

- Increased `master-gemma-q4` and `master-gemma-iq2` `max_tokens` from `64` to `256` in `config/config.toml`.
- Increased `real-bench --model-max-tokens` default from `16` to `256`.
- Updated `docs/real_benchmark_status.md` and README verification notes.

Verification:

- `.venv/bin/python -m agentic.app.cli smoke --model master-gemma-q4 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."`
- `.venv/bin/python -m agentic.app.cli smoke --model master-gemma-iq2 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."`
- `CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --skip-network --skip-ntfy --model master-gemma-q4`

Roadmap impact:

- The model-output blocker is resolved for master Gemma Q4/IQ2 smoke and real-bench.
- Remaining real-bench blockers are now Gmail credentials, ticket URL/live browser adapter, and Reddit 403/compliant connector strategy.

Next step:

- Build the real community-crawling workflow path: Master interview, real web discovery/tool use, crawler script/tool creation, ResourceStore persistence, scheduler interval, trend synthesis, report, and ntfy notification.

Lessons learned:

- Return code 0 is not enough for model health. Real-bench must require non-empty useful output.
- Gemma chat output can spend more than 64 tokens in thought before producing final JSON, so master budget must leave room for final.
- Sanitizer behavior was correct; the configuration budget was too low.

## 2026-07-01 19:07 KST - Live Web Collection Primitive

Summary:

- Added a generic real web collection and resource trend primitive for agents to use when designing crawler/watch workflows.

Changed areas:

- Added `web_fetch` and `html_extract_links` tools.
- Added `WebPageSourceCollector` for real HTTP(S) source collection into `ResourceStore`.
- Added generic extraction filters: `href_contains`, `href_excludes`, `text_excludes`, `text_exclude_regexes`, `min_text_chars`, and `limit`.
- Added CLI commands:
  - `web-collect`
  - `resource-trends`
- Added `summarize_resource_trends()` over `ResourceStore`.
- Updated README, roadmap, and real benchmark status docs.

Verification:

- `.venv/bin/python -m py_compile agentic/tools/web.py agentic/tools/registry.py agentic/sources/runtime.py agentic/app/cli.py agentic/benchmarks/real.py agentic/resources/store.py agentic/synthesis/resources.py`
- Real DCInside collection through `web-collect` with network escalation.
- `resource-trends --state-dir traces/state/web_collect --limit 30 --top-n 12`
- `CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --skip-ntfy --skip-model`

Roadmap impact:

- Community crawling now has a real reusable harness primitive, not a bespoke stock-gallery script.
- The remaining missing layer is agent-driven strategy selection/interview plus scheduler/report wiring.

Next step:

- Implement the workflow-design/runtime layer that lets Master interview the user, choose `web-collect` vs browser/API/script, persist the selected strategy, schedule it, synthesize trends, and notify.

Lessons learned:

- Static HTML collection is enough for DCInside list pages, but noisy titles require iterative filter tuning.
- The useful abstraction is not `crawl_stock_gallery`; it is `observe page -> select collection strategy -> store resources -> analyze trends -> record strategy lessons`.
- Real collection should store resources first; model calls should operate on persisted evidence, not raw transient page fetches.

## 2026-07-01 19:10 KST - Offline Regression Boundary Fix

Summary:

- Fixed a regression test that accidentally invoked the new real `WEB_PAGE` collector during the default offline eval suite.

Changed areas:

- Updated `evals/test_milestone8_source_capability_runtime.py` so the missing-collector assertion explicitly removes the web collector instead of relying on `WEB_PAGE` being unsupported.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- The live collection primitive remains real and opt-in, while default evals remain deterministic and network-free.

Next step:

- Build agent-driven collection strategy selection: interview the user, choose HTTP/API/browser/script, persist the strategy, schedule it, and route results through synthesis/report/notification.

Lessons learned:

- Adding a real capability changes old negative tests. The right boundary is explicit opt-in for networked execution, not pretending the capability does not exist.

## 2026-07-01 19:21 KST - Agent Behavior Observation Only

Summary:

- Stopped implementation work and observed the current harness/agent behavior against the user's blurry social-trend workflow request.

Changed areas:

- No implementation modules, tools, or workflow definitions were created or changed for this observation.
- Added only this work-log entry per project process.

Verification:

- Ran Phase 1 `ask` with the social trend workflow request.
- Ran existing `WorkflowDesigner` against vague requests and one follow-up answer.
- Ran real local GGUF smoke calls to compare short factual QA versus workflow-like prompts.
- Read `traces/phase1.jsonl` to confirm observed behavior.

Roadmap impact:

- Current Phase 1 agent loop is not yet a useful autonomous workflow designer.
- Existing deterministic `WorkflowDesigner` can shape a proposal, but it does not let the model choose tools, storage, collection strategy, or ask enough questions.

Next step:

- Reorient the next milestone around agent-observation harnessing: route vague user requests into a real Master interview loop, capture its decisions, and only then allow the agent to propose or create capabilities under approval.

Lessons learned:

- The harness currently succeeds on toy delegation but fails on blurry workflow requests.
- A rule-based designer is not a substitute for an autonomous Master that interviews, researches, chooses capabilities, and records lessons.
- Future work should evaluate what the agent actually does before adding any new primitive.

## 2026-07-01 19:27 KST - Agent Skill Proposal Attempt And Reference Notes

Summary:

- Researched OpenClaw skill/workflow loop references and attempted to have the current harness agent draft a workflow-building skill proposal.

Changed areas:

- Added `docs/agent_loop_reference_notes.md`.
- No implementation modules, tools, workflows, or skill files were created in this task.

Verification:

- Reviewed OpenClaw official repository and docs for Skills, Skill Workshop, Automation, Task Flow, and Scheduled Tasks.
- Searched for Hermes Agent primary sources; only secondary/benchmark references were found with enough confidence to record as directional, not implementation truth.
- Ran the current harness `ask` path with a workflow-building skill proposal request.
- Confirmed in `traces/phase1.jsonl` that the current Master returned `답변을 정리하지 못했습니다.`

Roadmap impact:

- The next useful milestone should focus on a Master interview/proposal loop and Skill Workshop-style proposal boundary.
- Skill creation must be agent-proposed and approval-applied, not operator-authored as a live file during observation.

Next step:

- Implement or expose the minimum harness surface that lets the agent create pending `SkillProposal` records after an interview turn, then observe whether it can use that surface on real vague requests.

Lessons learned:

- OpenClaw's Skill Workshop is the right shape: proposal first, apply only after review.
- Hermes-style self-improvement should be treated as an evidence-backed skill evolution loop, but current public primary-source confidence is low.
- The current Phase 1 Master cannot even draft a proposal, so more concrete tools are not the next bottleneck.

## 2026-07-01 19:34 KST - Skill Workshop Proposal Boundary

Summary:

- Added the first OpenClaw/Codex-inspired Skill Workshop boundary so agents can create pending skill proposals without writing active skill files.

Changed areas:

- Added `SkillProposal` and status models.
- Added SQLite-backed `SkillWorkshopStore` and `SkillWorkshopService`.
- Added agent-facing `skill_workshop` tool with `create`, `list`, `inspect`, `revise`, `reject`, and `quarantine`.
- Added CLI `skill-workshop` command for proposal inspection and management.
- Added eval coverage for proposal persistence, no active skill writes, existing-skill collision, terminal transitions, and default tool exposure.
- Updated README, roadmap, and agent-loop reference notes.

Verification:

- `.venv/bin/python -m unittest evals.test_skill_workshop`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `.venv/bin/python -m agentic.app.cli skill-workshop create --state-dir /tmp/agentic-skill-workshop-cli ...`
- `.venv/bin/python -m agentic.app.cli skill-workshop list --state-dir /tmp/agentic-skill-workshop-cli`

Roadmap impact:

- The harness now has a concrete proposal queue for agent-proposed skill evolution.
- The next bottleneck is making the Master/subagent loop choose this tool during vague workflow-design work.

Next step:

- Add a Master interview/proposal loop that can ask one question at a time, then call `skill_workshop` when it identifies reusable workflow-building behavior.

Lessons learned:

- The right unit of autonomy here is not active skill mutation; it is pending proposal creation with durable evidence.
- Tooling the workshop boundary gives the agent a safe action surface while preserving operator review.
- Lazy tool factory loading is needed to avoid circular imports between `ToolRegistry` and `SkillRegistry`.

## 2026-07-01 20:32 KST - Real Harness Skill Proposal Runs

Summary:

- Ran real user-shaped harness tasks through the local Master/Subagent loop and reached persisted pending skill proposals.

Changed areas:

- Updated master/subagent prompts so workflow and skill-creation requests route toward pending proposals.
- Added Master fallback routing for skill/workflow requests instead of returning `답변을 정리하지 못했습니다.`
- Added subagent malformed tool-call retry.
- Added raw-output fallback and JSON extraction for tool calls.
- Added natural-language `skill_workshop` intent recovery, preserving the agent's generated output as proposal body.
- Increased DiffusionGemma subagent context/output budget for long tool-call tasks.
- Added tests for workflow fallback, parser recovery, subagent retry, and skill-workshop natural-language recovery.

Verification:

- Real harness task: `workflow building ... skill proposal ... pending proposal만 만들어`.
- Real harness task: `주식갤 자동 크롤링하고 ... 주기적으로 트렌드 분석해서 보고서`.
- `skill-workshop list` confirmed two pending proposals:
  - `workflow-builder`
  - `vague-workflow-handler`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- The harness progressed from failing vague requests at Master answer fallback to persisted pending skill proposals through the agent loop.
- The next gap is proposal quality and lifecycle: proposal body cleanup, approval-gated apply, stale detection, and making this run as a durable background task rather than slow foreground `ask`.

Next step:

- Add a proposal review/apply path with approval, scanner checks, and UI/API visibility, then run the same user-shaped tasks through the web/durable runtime instead of foreground CLI.

Lessons learned:

- DiffusionGemma did infer the correct tool intent, but often emitted natural-language planning instead of strict JSON.
- A useful harness must recover structured actions from imperfect but clear model intent.
- Foreground `ask` is too slow for real workflow-building tasks; future real probes should enqueue durable background tasks and expose progress.

## 2026-07-01 20:52 KST - Learning Loop Bootstrap Adaptation

Summary:

- Adapted the provided Codex Agent Learning Loop bootstrap to this repo's existing Agentic experience loop instead of creating an unrelated parallel process.

Changed areas:

- Added `.agent/OPERATING_ROUTINE.md`, `.agent/MEMORY.md`, `.agent/LESSONS.md`, and `.agent/TASK_LOG.md`.
- Updated `AGENTS.md` with the repo-local start/work/finish learning loop and memory discipline.
- Updated `docs/experience_loop.md` to explain how `.agent/` relates to `agentic.experience`, `traces/experience.jsonl`, `docs/work_log.md`, and Skill Workshop proposals.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `.venv/bin/python -m agentic.app.cli requirements-smoke`

Roadmap impact:

- No framework milestone implementation changed.
- The operator loop is now aligned with the existing Experience Loop primitive and Skill Workshop proposal boundary.

Next step:

- Add a proposal review/apply path with approval, scanner checks, and UI/API visibility, then run slow workflow-building tasks through the web/durable runtime instead of foreground CLI.

Lessons learned:

- The bootstrap prompt's memory/lesson/task-log shape is useful, but this repo already has machine-readable experience and project work-log channels.
- `.agent/` should stay concise and operator-facing; structured evidence belongs in `traces/experience.jsonl`, and repeated procedures should move through Skill Workshop proposals before becoming active skills.

## 2026-07-01 21:18 KST - Real Workflow Building Harness Probe

Summary:

- Added and ran a real workflow-building harness probe that throws a vague automation request at the harness, answers the interview loop, and verifies that the agent creates a pending Skill Workshop proposal.

Changed areas:

- Added `agentic/probes/` with `run_workflow_builder_probe`.
- Added `harness-probe` CLI command.
- Added state-dir injection for `FullLoopRuntime.from_config` and `ToolRegistry.with_defaults` so real tool actions and probe observation use the same persistence boundary.
- Improved natural-language `skill_workshop` recovery to extract the actual `proposal_body` markdown block instead of storing surrounding explanatory text.
- Increased DiffusionGemma subagent output budget to 512 tokens for workflow-building proposal tasks.
- Documented the `harness-probe` command in `README.md`.

Verification:

- Real GPU-backed probe request: `반복 자동화 워크플로우 만들어줘`.
- Harness interview answers covered community web-page sources, agent-selected collection strategy, 1-minute collection, 1-hour analysis, web report, and ntfy alert.
- v1/v2/v3 showed progress from wrong store observation and truncated/noisy proposal bodies to cleaner proposal-body extraction.
- v4 produced a persisted pending `vague-workflow-builder` proposal with trigger, interview, discovery, proposal, approval, recording, and evolution bullets.
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- The harness now has a scriptable real probe for the central product loop: vague request -> interview -> reusable proposal.
- This supports the Experience Loop and Skill System roadmap, but the next gap is still execution lifecycle: these probes should run as durable background tasks with progress, not foreground model calls.

Next step:

- Move `harness-probe` execution into the durable task/runtime path and add proposal review/apply UI with approval and scanner checks.

Lessons learned:

- Running the same probe repeatedly surfaced concrete progress: state observation was fixed, proposal noise was reduced, and output budget was raised enough to complete the proposal.
- DiffusionGemma still prefers natural-language tool intent over exact JSON for this task class, so robust action recovery remains necessary.
- GPU-backed real probes should be run unsandboxed when validating llama.cpp GPU usage; sandboxed foreground runs can appear hung without attaching the model process to the RTX 4090.

## 2026-07-01 22:02 KST - Durable Workflow Building Probe Task

Summary:

- Moved the single general workflow-building probe from a foreground CLI-only path into the durable task runtime.

Changed areas:

- Added `TaskRouter` so durable workers can dispatch by task kind instead of assuming every task is a `chat_turn`.
- Added `WorkflowBuilderProbeExecutor` and `workflow_builder_probe` task kind.
- Added `harness-probe-task` CLI command to enqueue, run, poll, and report the durable probe task.
- Wired `serve` runtime to support both `chat_turn` and `workflow_builder_probe` task kinds.
- Added `/probes/workflow-builder` web route and a minimal homepage form to enqueue the same probe from the UI.
- Added regression tests for task routing, durable probe execution boundary, and web route enqueue behavior.
- Updated `README.md` and `.agent/TASK_LOG.md`.

Verification:

- Real GPU-backed durable task:
  - command: `.venv/bin/python -m agentic.app.cli harness-probe-task --state-dir /tmp/agentic-harness-probe-task-real ...`
  - task id: `task_5613e58b8b3e4deeac71b04e54b24c2d`
  - lifecycle: `queued -> running -> completed`
  - result: pending `vague-workflow-builder` proposal `skp_0a09b1550e7f4a7bb4eb36e846a6efed`
- Direct SQLite reload confirmed the durable task result persisted.
- `skill-workshop list --state-dir /tmp/agentic-harness-probe-task-real` confirmed the pending proposal persisted.
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- This advances the Durable Runtime, Skill System, and Experience Loop primitives together: long-running agent observations now run as durable tasks and produce reviewable skill proposals.
- The selected single high-freedom scenario remains `vague request -> interview -> reusable workflow-building proposal`.

Next step:

- Implement approval-gated Skill Workshop proposal review/apply in the web UI so the user can inspect, approve, and activate agent-proposed skills without direct file writes.

Lessons learned:

- The main latency problem was not only model speed; it was that useful probe runs had no durable lifecycle. Moving them into `TaskStore` makes progress, errors, and results observable.
- `TaskRouter` is a necessary framework primitive before more agent task kinds are added.
- The harness is now closer to the intended loop: Codex builds framework primitives, Agentic receives a vague task, interviews through a structured probe, and the agent produces a reviewable proposal.

## 2026-07-01 22:10 KST - Approval Gated Skill Proposal Apply

Summary:

- Completed the next lifecycle step for agent-generated skill proposals: request approval, approve, apply, and load the active skill.

Changed areas:

- Added `SkillLoader.load_text` so proposed skill text can be validated before writing an active `SKILL.md`.
- Added `SkillWorkshopService.request_apply` and `SkillWorkshopService.apply`.
- `apply` now checks approved `skill:apply` approval payload fields: proposal id, target skill name, and content hash.
- Added CLI commands:
  - `skill-workshop request-apply`
  - `skill-workshop apply`
  - `approvals list|approve|deny`
- Added web routes and homepage panel for skill proposals:
  - `GET /skills/proposals`
  - `POST /skills/proposals/{proposal_id}/request-apply`
  - `POST /skills/proposals/{proposal_id}/apply`
- Wired `serve` and static app creation to the Skill Workshop service.
- Applied the real agent-generated `vague-workflow-builder` proposal into `skills/vague-workflow-builder/SKILL.md` after approval.
- Updated `README.md`.

Verification:

- Real proposal used: `skp_0a09b1550e7f4a7bb4eb36e846a6efed` from the durable workflow-building probe.
- Created approval request: `appr_2747fccbd89c440ebacae739089ac89f`.
- Approved the request, then applied the proposal.
- Confirmed `skills/vague-workflow-builder/SKILL.md` exists and `SkillLoader('skills').load_all()` loads `vague-workflow-builder`.
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `create_channel_app(load_app_config(...))` smoke check.

Roadmap impact:

- This advances the Skill System from proposal-only into a reviewable activation lifecycle.
- The central scenario now reaches: vague prompt -> interview answers -> durable agent task -> pending skill proposal -> approval request -> approved active skill.

Next step:

- Make the active skill actually participate in agent routing/prompt context for future vague workflow-building requests, then rerun the same scenario and verify the agent uses the active skill instead of relying only on hard-coded fallback/probe prompts.

Lessons learned:

- A proposal lifecycle without apply is not enough; useful self-evolution needs a safe activation boundary.
- Approval payloads must include content hash to prevent stale approvals from applying revised proposal text.
- Applying a skill should be a framework service action, not an agent file write.

## 2026-07-01 22:23 KST - Active Skill Routing And Revision Proposals

Summary:

- Connected active skills to the real Master/Subagent prompt path and verified the previously applied `vague-workflow-builder` skill is selected during the single general workflow-building probe.

Changed areas:

- Added optional skill context blocks to `PromptBuilder`.
- `MasterAgent` and `SubAgent` now accept `SkillRegistry`, route the original user request to active skills, and inject compact skill context into model prompts.
- `FullLoopRuntime.from_config` now loads active skills from `skills/` and shares the registry with Master/Subagent.
- Trace payloads for `master_model_called` and `subagent_model_called` include selected skill names.
- Added compact skill context limits and increased master model context window to avoid prompt-too-long failures.
- Improved skill routing to use `Original request:` instead of matching examples embedded in probe prompts.
- Added `propose_revision` and duplicate-create recovery so an agent proposal for an existing active skill becomes a pending revision proposal.
- Added trigger metadata to `skills/vague-workflow-builder/SKILL.md`.
- Updated `README.md`.

Verification:

- First real run exposed `prompt is too long (1108 tokens, max 1020)`.
- After compact context and master context update, real durable probe completed.
- A broad routing run exposed false positives from prompt examples like Gmail, Obsidian, repo, and browser.
- After routing extraction, trace confirmed:
  - `master_model_called ['vague-workflow-builder']`
  - `subagent_model_called ['vague-workflow-builder']`
- Final real durable probe completed and created pending revision proposal `skp_93ae34999ad54d6a8b5fa9cfc99c2637` for the existing active `vague-workflow-builder`.
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- The single general scenario now reaches active skill reuse and self-evolution proposal, not just one-time proposal creation.
- This tightens the Skill System, Experience Loop, and Durable Runtime integration around a real end-to-end path.

Next step:

- Improve proposal quality review for revisions: normalize generated proposal bodies, surface diffs against the active skill, and make the web UI show exactly what will change before approval.

Lessons learned:

- Skill routing over the entire prompt is too noisy; routing must focus on the user's original intent, not embedded examples or transcripts.
- Active skills can increase prompt size enough to break local GGUF context limits; compact skill context and context-window budgeting are core runtime concerns.
- Self-evolving behavior needs a revision path. Otherwise the first successful active skill causes later improvement attempts to fail as duplicates.

## 2026-07-01 22:28 KST - Skill Proposal Review Diff

Summary:

- Added review/diff support for pending skill proposals, especially active-skill revision proposals.

Changed areas:

- Added `SkillProposalReview` and `SkillWorkshopService.review`.
- Review validates candidate `SKILL.md` text before apply.
- Review reports mode, target path, active text, candidate text, validation status, and unified diff.
- Added markdown body normalization to reduce formatting-only diff noise from generated proposal bodies.
- Added CLI `skill-workshop review`.
- Web skill proposal panel now includes validation and diff preview.
- Updated `README.md`.

Verification:

- Real revision proposal reviewed: `skp_93ae34999ad54d6a8b5fa9cfc99c2637`.
- Review mode: `revision`.
- Validation: `ok`.
- Diff showed meaningful changes against `skills/vague-workflow-builder/SKILL.md`, including recording/evolution wording and trigger keyword changes.
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `create_channel_app(load_app_config(...))` smoke check.

Roadmap impact:

- This improves the self-evolution loop by making agent-proposed active-skill revisions inspectable before approval/apply.
- The single general scenario now reaches a reviewable revision state with human-readable evidence.

Next step:

- Add approval UI affordances that bind a displayed review hash/diff to the apply approval, so the user approves exactly the candidate text they inspected.

Lessons learned:

- A generated revision proposal is not enough; the operator needs a diff against the active skill to judge whether self-evolution is useful.
- Formatting noise can obscure semantic changes, so proposal review needs light normalization before diffing.
- Review output is now the right place to gather evidence before any approval-gated apply.

## 2026-07-01 22:48 KST - Real Harness Probe Observability And Review-Bound Skill Apply

Summary:

- Hardened the self-evolution loop by binding skill apply approvals to the exact reviewed candidate/diff hashes, then ran a real durable workflow-builder probe using a user-shaped social-trend automation request.

Changed areas:

- `SkillProposalReview` now includes active, candidate, diff, and review hashes.
- `SkillWorkshopService.request_apply` includes those hashes in the approval payload.
- `SkillWorkshopService.apply` recomputes review hashes and rejects drift before writing an active `SKILL.md`.
- `TaskWorker` now refreshes heartbeat in a background loop while a long executor/model call is running.
- `TaskPool` accepts a heartbeat interval for tests and future tuning.
- Master/Subagent model calls can pass trace through to the local provider while keeping fake providers compatible.
- README now documents worker heartbeat observability and review-bound skill apply.

Verification:

- Real prior revision `skp_93ae34999ad54d6a8b5fa9cfc99c2637` was review-bound, approved as `appr_de3dbc1f32cd42c58917d2d3a303c6f7`, and applied to `skills/vague-workflow-builder/SKILL.md`.
- Real durable task `task_e9ca15a5e7dc41e995a2ae7175ca1d11` completed for request `주식갤과 미국 주식 레딧을 계속 관찰해서 트렌드를 보고해주는 반복 자동화 워크플로우를 만들어줘`.
- The task recorded 28 heartbeat events while the local model/subagent path ran.
- The harness selected `vague-workflow-builder` and created pending revision proposal `skp_58908bc02b2f42ab92b37760f901501a`.
- Review of `skp_58908bc02b2f42ab92b37760f901501a` validated successfully and produced review hash `17598933abacf8e8134b6682be9a8ea3fb8fb12270d445ca9b59461535414bcc`.
- Structured experience event recorded: `exp_23b561a782d3483ea2084e70715763a1`.
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- The Skill System and Experience Loop are now safer: agent-proposed revisions are inspectable, hash-bound, approval-gated, and auditable.
- Durable Runtime observability improved for long local GGUF calls, which is required before 24/7 operation.
- The social-trend user requirement can now be used as a real harness-level probe without writing bespoke crawler/workflow code.

Next step:

- Run the same real durable probe once more with provider-level model trace enabled, then improve the workflow-building probe so it asks and preserves all required interview slots instead of collapsing the user's first answer into cadence.

Lessons learned:

- A real long-running local model call can look dead unless the durable task worker refreshes heartbeat independently of executor internals.
- The harness is now better than the previous run: it reached terminal completion and generated a pending revision proposal, but the run still took about seven minutes and needs model-call timing in trace for better bottleneck analysis.
- Skill self-evolution needs exact review/apply binding; otherwise a user can approve one diff and accidentally apply another.

## 2026-07-01 23:14 KST - Real Workflow Builder Probe Quality Gate

Summary:

- Ran the social-trend workflow-builder request through the durable harness again and improved probe quality checks so a task is not counted useful merely because it completed.

Changed areas:

- Improved `WorkflowDesigner` answer normalization so meta guidance such as "interview first" does not get stored as cadence.
- Preserved extra user guidance after the current interview slots are filled.
- Compacted skill-workshop fallback instructions so the Master delegates a smaller task to the Subagent.
- Added provider-level `max_tokens` trace payloads and a compact subagent generation budget for skill-workshop tasks.
- Added post-store proposal quality checks requiring the seven workflow-builder labels: Trigger, Interview, Discovery, Proposal, Approval, Recording, Evolution.
- Made proposal-body recovery and quality checks tolerate markdown-bold labels such as `- **Trigger**:`.
- Added `raw_text_chars` to `model_call_completed` trace events so sanitized-empty model outputs no longer look like missing output.

Verification:

- Real durable task completed: `task_e30c5c605c094b969b242ba17ac05c5d`.
- Real pending revision proposal created: `skp_41825d67d2954946a63c1e19f79e92c6`.
- Task duration was about 415 seconds with 28 heartbeat events.
- Trace showed `master-gemma-q4` with `max_tokens=256` and `subagent-diffusiongemma-q4` with `max_tokens=384`.
- The generated proposal contained all seven expected labels and passed the stricter quality gate.
- `.venv/bin/python -m unittest discover -s evals` ran 200 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- The Skill System and Experience Loop now have a stronger finish-line check for the single general workflow-building scenario.
- The harness is improving across real runs: previous runs completed but produced truncated or low-quality proposal bodies; this run completed with a usable pending revision.
- Remaining roadmap gap: `nvidia-smi` snapshots after completion do not prove live GPU residency; the next real model run should confirm `raw_text_chars` appears in provider trace.

Next step:

- Run the next finish-line probe: review/apply the pending proposal only after approval, then ask the Harness to build a concrete WorkflowSpec from a vague recurring automation request without Codex writing the workflow itself.

Lessons learned:

- Task completion is not autonomy. Generated artifacts need domain-shaped quality gates before they count as useful.
- Shorter model budgets can work when the delegated task is compact, but truncation must be detected after persistence.
- Real probe reports should include both progress over the prior run and the next bottleneck, or the project will drift back into synthetic success.

## 2026-07-02 00:16 KST - Agent Generated WorkflowSpec Probe

Summary:

- Added a framework path where the Harness asks the local agents to create a reviewable `WorkflowSpec` proposal from the same vague recurring automation request, without Codex writing the concrete workflow.

Changed areas:

- Added `workflow_spec` tool for creating/listing/inspecting proposed `WorkflowSpec` records without executing, approving, or activating them.
- Added compact tool arguments (`trigger`, `source`, `step_types`, `output`) that the tool normalizes into full `WorkflowSpec` shape.
- Added `run_workflow_spec_probe` plus durable `workflow_spec_probe` task execution and CLI commands.
- Routed explicit `workflow_spec` Master fallback requests before generic skill-workshop workflow-building fallback.
- Added workflow-spec natural-language/partial-JSON recovery for malformed compact model output.
- Added tests for tool creation, compact shape normalization, recovery, retry routing, durable task execution, and probe quality gates.
- Updated roadmap extension primitives with the `WorkflowSpec Tool` boundary.

Verification:

- Real durable task completed: `task_6f202702698141428dc0d642b28e3a30`.
- Real proposed workflow created: `wf_08fd1c5ecd3f4824957d0517f41ee77b`.
- The saved workflow is `status=proposed`, name `stock-trend-monitor`, trigger `interval:60s`, sources `reddit` and `dcinside-gallery`, output `report`, and steps `collect -> analyze -> aggregate -> report`.
- Trace showed Master `master-gemma-q4` and Subagent `subagent-diffusiongemma-q4`; subagent emitted malformed compact JSON, and Harness recovered it into `tool_called:workflow_spec`.
- Task recorded 30+ heartbeats while local model execution ran.
- `.venv/bin/python -m unittest discover -s evals` ran 210 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- The single general workflow-building scenario advanced from "creates a skill revision proposal" to "creates a proposed WorkflowSpec artifact".
- This is closer to the framework objective: user sends a vague recurring automation request, Harness interviews, local agents plan, and the runtime stores a reviewable workflow primitive.
- Remaining gap: the proposed WorkflowSpec is not yet reviewed/approved/activated/executed, and source connectors for `reddit`/`dcinside-gallery` are not bound to real connector records.

Next step:

- Add WorkflowSpec review/approval/apply semantics and source binding checks so the proposed workflow can move from `proposed` to reviewable/approved without Codex writing the workflow.

Lessons learned:

- Asking the model for full nested WorkflowSpec JSON is brittle and slow; compact intent fields plus Harness normalization are a better framework boundary.
- Malformed tool-call recovery should preserve agent intent when enough fields are present, instead of forcing another long model retry.
- The Harness should count progress only when the persisted artifact passes a quality gate, not when the model merely says it planned something.

## 2026-07-02 09:00 KST - Session Log And Workflow Lifecycle Gate

Summary:

- Added the next framework layer after proposed `WorkflowSpec`: full session logging and deterministic lifecycle gates for review, source binding, approval, activation, and run admission.

Changed areas:

- Added `agentic/sessions/` with SQLite-backed `SessionLogStore`.
- Added `WorkflowStore.update_spec`.
- Added `agentic/workflow_kernel/lifecycle.py` for `review`, `bind_sources`, `approve`, `activate`, and `run_once`.
- Added CLI `workflow-lifecycle`.
- Added `config/config.fast.toml` and `subagent-gemma-iq2` for fast IQ2/IQ2 iteration probes.
- Updated `run_workflow_spec_probe` so user request, interview turns, agent instruction, agent response, and created workflow artifacts are persisted in `sessions.sqlite3`.
- Updated README and roadmap with the new lifecycle/session primitives.

Verification:

- Real Q4/Q4 durable run completed as `task_e8ce3e16f1714049a3551ed04efe0b57` in about 446 seconds.
- It created session `sess_549a8dd1bf164b8e99352c75fe9eb53d` with 8 auditable session events.
- It created proposed workflow `wf_9b5e45a25852414993e7bb496272aabf`.
- Lifecycle review passed with score 90 and warning `source_binding_missing`.
- Source binding failed honestly with missing sources `reddit` and `dcinside-gallery`.
- Approval was blocked with reason `source_binding_missing`.
- Fast IQ2/IQ2 run completed faster, about 169 seconds, but failed because the subagent emitted thought text instead of valid `workflow_spec` JSON.
- `.venv/bin/python -m unittest discover -s evals` ran 214 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`
- `.venv/bin/python -m agentic.app.cli --config config/config.fast.toml config-check`

Roadmap impact:

- The Harness improved from "proposed spec exists" to "proposed spec is auditable and lifecycle-gated".
- Current real-usefulness score is 38/100: the Harness can interview, generate a spec, log the full session, review it, and block unsafe/unsupported activation. It cannot yet bind live community sources, activate a schedule, execute repeated collection, produce hourly reports, or notify the user from the workflow run.

Next step:

- Implement generic live source binding strategy and scheduler execution admission so the same proposed workflow can bind real sources, become active, and run repeatedly without Codex writing a specific crawler.

Lessons learned:

- Full session logs are now required evidence for every real Harness evaluation.
- IQ2/IQ2 is faster but currently unreliable for tool-call generation; keep Q4/Q4 as the real evaluation path.
- The bigger speed bottleneck is likely per-turn llama.cpp process startup and model loading, so a persistent model worker/server is a higher-leverage iteration improvement.

## 2026-07-02 09:11 KST - Live Source Binding And Scheduled Run

Summary:

- Advanced the same agent-generated social-trend `WorkflowSpec` from source-binding blocker to active scheduled execution against enabled live web source definitions.

Changed areas:

- Added multi-source collect support in `WorkflowInterpreter`.
- Updated Workflow lifecycle source binding so collect steps receive all bound source IDs.
- Added activation-time schedule creation for interval triggers.
- Added interval `next_run_at` calculation in `SchedulerRunner`.
- Added CLI `sources add-web/list/collect` and `scheduler-run-due`.
- Adjusted capability policy so read-only bound `web_page` sources are allowed without extra approval, while consequential actions remain gated.
- Added tests for web-page read admission, multi-source binding, activation, due-run, and schedule interval state.

Verification:

- Existing agent-generated workflow `wf_9b5e45a25852414993e7bb496272aabf` bound to two enabled live web sources: `reddit` and `dcinside-gallery`.
- Lifecycle review improved from score 90 with `source_binding_missing` to score 100.
- Workflow approved and activated.
- Activation created schedule `sch_a1e8544661bb468c88917e5c351c86a0`.
- `scheduler-run-due` reached live network collection with escalated network permission and completed run `wfr_8d8e5e44e936414ca5d92353bb4549e7`.
- First successful run collected 20 resources and created report artifact `art_4d59e64235a049e6a662947f4aaf776a`.
- Second successful run `wfr_48bf34d0bb984a40aa49f6064b17bb78` recorded `next_run_at=2026-07-02T00:11:40.921274+00:00`.
- Focused evals passed: `.venv/bin/python -m unittest evals.test_workflow_lifecycle_session_log evals.test_milestone7_workflow_kernel`.

Roadmap impact:

- Real-usefulness score increased from 38/100 to 62/100.
- The Harness can now move a proposed spec through source binding, approval, activation, schedule creation, live collection, deterministic analysis, aggregation, and report artifact creation.
- Remaining gap: source extraction quality is poor and nav-heavy; report quality and notification delivery are not yet useful enough for the user's hourly alert expectation.

Next step:

- Add generic source extraction quality gates and agent-driven source tuning so live collection yields actual target posts/items before reports are sent.

Lessons learned:

- Read-only live source access should be gated by explicit enabled source binding, not by a blanket approval requirement.
- Scheduler success and report usefulness are separate finish lines; a completed run can still produce a weak report.
- Dedupe-only new resources are not enough for trend reporting; recurring analysis needs a recent-window resource query.

## 2026-07-02 09:16 KST - Fast Single Model Default

Summary:

- Checked GPU state and model sizes, then switched the default runtime config to use the lighter Gemma IQ2 model for both Master and Subagent during rapid Harness iteration.

Changed areas:

- `config/config.toml` now defaults to `master-gemma-iq2` and `subagent-gemma-iq2`.
- `README.md` now documents IQ2/IQ2 as the default fast iteration path while preserving Q4/DiffusionGemma as opt-in quality probes.

Verification:

- `nvidia-smi` showed no active model process and only baseline GPU memory use.
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- Supports faster iteration toward the next M12 slice: source quality gates and finish-line workflow execution.

Next step:

- Continue with generic source extraction quality gates so scheduled workflows do not report low-quality navigation-heavy collections as useful insight.

Lessons learned:

- For local framework development, a single resident/light model path is more valuable than role-specialized heavy models until the Harness lifecycle itself is reliable.

## 2026-07-02 09:25 KST - Source Quality Gate

Summary:

- Added a generic source quality gate so workflow runs do not create report artifacts from navigation-heavy or off-target source collections.

Changed areas:

- Added `agentic/sources/quality.py` with `SourceQualityReport` and source item scoring.
- `SourceRuntime.collect()` now evaluates collected `SourceItem` records and returns quality evidence.
- `WorkflowInterpreter` now records `workflow_source_quality_failed` and fails collect/report execution with `SourceQualityError` when source quality is below threshold.
- `web-collect` and `sources collect` include quality reports in CLI output.
- Added `evals/test_source_quality_gate.py`.
- Updated roadmap with `Source Quality Gate`.

Verification:

- `.venv/bin/python -m unittest discover -s evals` ran 219 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`
- Real live DCInside raw page collection returned quality `ok=false`, score `47`, with reasons `navigation_like_items`, `off_source_path_items`, and `score_below_threshold`.
- A live workflow validation probe against the same page failed with `SourceQualityError` and created zero report artifacts.

Roadmap impact:

- Real-usefulness score remains 62/100 rather than increasing materially: the Harness now prevents bad reports, but still does not autonomously tune source extraction or deliver hourly ntfy reports.
- This moves the project from "scheduled run completed" toward "scheduled run must be useful before reporting."

Next step:

- Add agent-driven source strategy revision: when the Source Quality Gate fails, preserve the quality evidence and create a retry/tuning task or skill/tooling proposal instead of stopping as a dead-end failure.

Lessons learned:

- Collection completion is not enough; usefulness needs admission gates before report and notification steps.
- Off-path scoring should apply to HTTP/HTTPS page sources, not local JSONL files with custom URIs.
- Navigation detection needs token-aware matching so content words such as "rally" or "users discussed" are not misclassified as UI navigation.

## 2026-07-02 09:31 KST - Source Strategy Tuning Backlog

Summary:

- Converted source quality failures from dead-end workflow errors into structured source strategy tuning backlog items.

Changed areas:

- Added `agentic/sources/strategy.py` for `source:strategy_tuning` tooling request creation.
- `WorkflowInterpreter` now optionally writes a tooling backlog item when source quality fails.
- `WorkflowLifecycleService`, channel app, static app, scheduler due runner, and workflow lifecycle CLI now pass `ToolingBacklogStore` into workflow execution.
- Added CLI `tooling list` for scriptable backlog inspection.
- Extended `evals/test_source_quality_gate.py` to verify backlog creation and agent-review payloads.
- Updated roadmap with `Source Strategy Tuning`.

Verification:

- `.venv/bin/python -m unittest discover -s evals` ran 219 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`
- Real live DCInside raw page workflow failed with `SourceQualityError`, created zero report artifacts, and persisted one `source:strategy_tuning` tooling request.
- `.venv/bin/python -m agentic.app.cli tooling list --state-dir /tmp/agentic-source-tuning-live` showed candidate actions: `revise_extraction_filters`, `exclude_navigation_text`, `constrain_links_to_source_path`, and browser/API escalation consideration.

Roadmap impact:

- Real-usefulness score increases slightly from 62/100 to 64/100: the Harness still does not autonomously tune and deliver reports, but it now preserves the next action as structured work rather than silent failure.
- This moves the social trend validation path closer to a self-improving loop: fail -> evidence -> proposed strategy revision.

Next step:

- Add an execution path where the agent consumes `source:strategy_tuning` backlog, proposes a revised source definition or WorkflowSpec patch, and reruns the collect gate.

Lessons learned:

- A quality gate is only half the loop; the other half is converting the failure into auditable next work.
- Avoid import cycles between workflow/source/tooling modules by keeping strategy helpers lightweight and importing tooling types lazily where needed.

## 2026-07-02 09:41 KST - Source Strategy Proposal And Recent Window Analysis

Summary:

- Added the next framework layer after `source:strategy_tuning`: quality-failure backlog can now become a reviewable source strategy proposal, be applied to the source definition, and rerun through the real collection path.

Changed areas:

- Added `agentic/sources/strategy_workshop.py` with `SourceStrategyProposal`, SQLite proposal store, and `SourceStrategyWorkshopService`.
- Added `SourceStore.update_source()` and CLI `source-strategy propose/list/inspect/apply/reject`.
- `SourceRuntime.collect()` now returns `recent_resource_ids` in addition to new `resource_ids`.
- `WorkflowInterpreter` now analyzes recent stored resources when a recurring collect run has no newly persisted items.
- Added `evals/test_source_strategy_workshop.py` and recurring recent-window coverage in `evals/test_milestone10_real_e2e.py`.
- Updated roadmap with `Source Strategy Tuning` as proposal/apply/rerun and added `Recent-Window Analysis`.

Verification:

- `.venv/bin/python -m unittest discover -s evals` ran 223 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`
- Real live state `/tmp/agentic-source-tuning-live` converted `tooling_7af8069858bc4968907ee4cb188eea61` into proposal `ssprop_69b49cc87ce64694ae8476f91e456191`.
- Applying that proposal changed the live DCInside source extraction strategy to constrain links to `/board/view` and exclude navigation text.
- Real live `sources collect` improved quality from previous score `47` to `100`, with `ok=true`, `nav_like_count=0`, and `off_path_count=0`.
- Real live workflow rerun completed and created report artifact `art_da1e7487da864777810eecb33b70a5c7`, analyzing 20 recent items even when `new_count=0`.

Roadmap impact:

- Real-usefulness score increases from 64/100 to 70/100: the Harness can now turn a real source quality failure into an applied strategy revision and rerun to a report. It still lacks autonomous agent consumption of that backlog, daemonized hourly execution, ntfy report delivery, and stronger report semantics.

Next step:

- Wire source strategy proposals into the agent/runtime loop so a Master/Subagent can inspect pending `source:strategy_tuning` requests, propose/apply safe read-only source revisions, rerun the workflow, and notify the user without Codex manually invoking CLI steps.

Lessons learned:

- Dedupe is necessary but can starve recurring analysis; recurring workflows need a recent-window input separate from newly collected resources.
- Source tuning should remain a proposal lifecycle: evidence -> pending metadata patch -> apply -> rerun quality gate, not an ad hoc crawler rewrite.

## 2026-07-02 09:48 KST - Durable Source Strategy Recovery Task

Summary:

- Added a durable runtime recovery path for source strategy tuning so a pending or applied `source:strategy_tuning` request can be handled as one task: proposal discovery/creation, safe read-only apply, live workflow rerun, and tooling completion.

Changed areas:

- Added `agentic/sources/strategy_recovery.py` with `SourceStrategyRecoveryService`, `SourceStrategyRecoveryExecutor`, and task kind `source_strategy_recovery`.
- Added `SourceStrategyProposalStore.find_by_tooling()` so recovery can reuse existing pending/applied proposals.
- Extended CLI `source-strategy` with `recover`, `recover-pending`, and `recover-task`.
- Added `evals/test_source_strategy_recovery.py` for sync recovery, proposal-only recovery, and durable task execution.
- Updated roadmap with `Source Strategy Recovery`.

Verification:

- `.venv/bin/python -m unittest discover -s evals` ran 226 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`
- Real live durable task `task_40bc9514961e49afbca22e70481324f0` ran `source_strategy_recovery` against `/tmp/agentic-source-tuning-live`.
- The task recorded heartbeat events, reran workflow `wf_cf816065ea444b3ca304854b2c2ae472`, produced run `wfr_6c7caedc159e4fcfb5e3a0fbc11dc299`, created report artifact `art_031d7c1acb13439c94b756ac46450c4f`, and preserved source quality `score=100`.
- The original tooling request `tooling_7af8069858bc4968907ee4cb188eea61` is now `completed`.

Roadmap impact:

- Real-usefulness score increases from 70/100 to 74/100: the recovery loop is now a durable task with heartbeat and completion state. The remaining blockers are automatic enqueue on quality failure, daemonized schedule execution, ntfy report delivery, and richer report semantics.

Next step:

- Add an automatic hook/admission path so `workflow_source_strategy_tuning_requested` can enqueue `source_strategy_recovery` without manual CLI invocation, then deliver completed workflow reports through ntfy/web inbox.

Lessons learned:

- A self-improving Harness should close the loop in task state, not only in CLI commands. Recovery work needs heartbeat, terminal status, and tooling completion just like user-facing workflows.

## 2026-07-02 09:53 KST - Automatic Source Recovery Enqueue

Summary:

- Connected source quality failures to automatic durable recovery task enqueue, so `workflow_source_strategy_tuning_requested` now produces queued `source_strategy_recovery` work without a manual proposal/recovery command.

Changed areas:

- Added `SourceStrategyRecoveryEnqueuer` in `agentic/sources/strategy_recovery.py`.
- `WorkflowInterpreter` now accepts a source recovery enqueuer and records `workflow_source_strategy_recovery_enqueued`.
- `WorkflowLifecycleService`, CLI `workflow-lifecycle`, and scheduler due-runner paths now pass the recovery enqueuer into workflow execution.
- Added CLI `source-strategy kick-recovery` to run already queued recovery tasks through the durable worker.
- Added `evals/test_source_strategy_auto_enqueue.py`.
- Updated roadmap to define `Source Strategy Recovery` as `quality failure -> recovery task queued -> safe apply -> live rerun -> tooling completed`.

Verification:

- `.venv/bin/python -m unittest discover -s evals` ran 227 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`
- Fresh live state `/tmp/agentic-auto-recovery-live` ran workflow `wf_4c37b419a0614dc8bccd26454edf8324` against the raw DCInside page.
- The first live run failed at the quality gate with score `47` and automatically enqueued task `task_dd5089106fa14da5be4275705ca70e7b`.
- `source-strategy kick-recovery` submitted that queued task, which applied strategy proposal `ssprop_df15d1c995f04a669e40cea4e77e2cf7`, reran the workflow as `wfr_8d173fa8e564451992302c7c0c63fa6c`, created report artifact `art_f1c8754cf7ec40bbbd28ed557d77b1f0`, passed quality with score `100`, and marked tooling `tooling_4bc3cb323b164c48872420a3c01f3329` completed.

Roadmap impact:

- Real-usefulness score increases from 74/100 to 78/100: source quality failure now creates durable recovery work automatically and that queued task can be executed by the worker to a report. Remaining blockers are a daemon loop that continuously kicks queued work, ntfy/web report delivery, and richer report generation.

Next step:

- Add a local daemon/serve runtime worker loop that continuously kicks queued recovery/workflow tasks and sends completed report artifacts through ntfy/web inbox.

Lessons learned:

- Hooking failure events to durable tasks is the right boundary: the workflow can fail honestly, while the runtime still creates resumable repair work.

## 2026-07-02 10:05 KST - Runtime Tick Report Delivery

Summary:

- Added a generic report delivery primitive and a scriptable runtime tick so queued recovery work can run to a report artifact and notify the user through ntfy.

Changed areas:

- Added `agentic/delivery/` with durable delivery records, SQLite store, and `ReportDeliveryService`.
- Extended `NtfyChannel` with generic `send_text()` while keeping approval notifications intact.
- Added artifact kind/status filtering in `ArtifactStore`.
- Added `RuntimeTickService` in `agentic/runtime/tick.py`.
- Added CLI `runtime-tick` to run scheduler due work, kick queued durable tasks, wait for completion, enqueue report deliveries, and send ntfy notifications.
- Fixed `source-strategy recover-task --no-wait` so it now truly enqueues only instead of claiming the task.
- Added delivery/tick eval coverage.

Verification:

- `.venv/bin/python -m unittest discover -s evals` ran 232 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`
- Real ntfy delivery retried a previously failed report delivery from `/tmp/agentic-auto-recovery-live` and moved `del_03537849500c495698222ad7be443d71` to `sent`.
- A live queued `source_strategy_recovery` task `task_8ec9af9a6b0a4a8580183dcc49621153` was submitted by `runtime-tick`, reran the live workflow, created report artifact `art_d8a2b38aa7684522b5d96575f3b174fe`, and sent delivery `del_8150cbdd5a474506ba8466d9efd71726` through ntfy.

Roadmap impact:

- Real-usefulness score increases from 78/100 to 82/100: the loop now reaches queued durable recovery -> live workflow rerun -> report artifact -> ntfy delivery from one runtime tick. Remaining blockers are a continuous daemon loop, web inbox visibility, richer report semantics, and a full start-to-finish vague chat session that creates and activates the workflow without operator CLI stitching.

Next step:

- Turn `runtime-tick` into a continuous local daemon/serve loop and surface deliveries/reports in the web UI so 24/7 operation no longer depends on manual CLI ticks.

Lessons learned:

- Outbound report delivery needs its own durable state. A report artifact alone does not prove the user received anything, and a transient network failure must be retryable instead of becoming chat-only history.

## 2026-07-02 10:13 KST - Continuous Runtime Daemon And Delivery UI

Summary:

- Turned the one-shot runtime tick into a continuous runtime daemon loop and exposed daemon/delivery state through the local web API/UI.

Changed areas:

- Added `RuntimeDaemonLoop` in `agentic/runtime/daemon_loop.py`.
- Added CLI `runtime-daemon` for scriptable finite or long-running daemon execution.
- Extended `serve` with daemon interval/timeout and ntfy report-delivery options.
- Wired `create_channel_app()` startup/shutdown to start and stop the runtime daemon.
- Registered `source_strategy_recovery` in the web/serve durable task router.
- Wired the serve-time workflow interpreter to enqueue source recovery tasks from quality failures.
- Added `/daemon`, `/daemon/tick`, and `/deliveries` routes.
- Added Runtime Daemon and Deliveries panels to the local web UI.
- Added daemon loop and web delivery eval coverage.

Verification:

- `.venv/bin/python -m unittest discover -s evals` ran 235 tests successfully with 2 skips.
- `.venv/bin/python -m agentic.app.cli config-check`
- `runtime-daemon` ran against `/tmp/agentic-auto-recovery-live`, submitted queued recovery task `task_bd47ec0c382e4bdb9ad4def467b1ed3b`, reran the live workflow, produced report artifact `art_f4d7ae40132144b7ad52b91ff8c924b8`, and sent ntfy delivery `del_8fee4d3afe64433f8ac419c0f5269a5e`.
- `GET /deliveries` on the live state returned the sent delivery.
- A real `serve` process on `127.0.0.1:8899` returned `GET /daemon` with `running=true` and increasing `tick_count`, and `GET /deliveries` returned sent report deliveries.

Roadmap impact:

- Real-usefulness score increases from 82/100 to 86/100: the harness now has a continuous local loop that can kick queued work, process live recovery, send report delivery, and show daemon/delivery state in the web UI. Remaining blockers are richer report generation, full vague-chat/session-to-active-workflow flow, stronger source semantics, and durable service packaging for true unattended 24/7 operation.

Next step:

- Close the start-of-flow gap: make a vague chat/planning session produce a reviewed, source-bound, approved, active scheduled workflow that the daemon can run and deliver without operator CLI stitching.

Lessons learned:

- A one-shot tick is a useful probe, but a local harness needs a visible continuous loop. The user should be able to see whether the daemon is alive, how many ticks ran, and whether report deliveries reached `sent`.
