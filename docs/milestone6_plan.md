# Milestone 6 Plan: Memory And Resource Layer

Milestone 6 creates durable user memory and resource storage for M7 workflows.

Scope:

- SQLite memory store
- SQLite resource store
- standing goals
- idea capture
- basic text/tag search
- local Obsidian markdown note skeleton
- simple synthesis over stored ideas
- no live Gmail/WSJ ingestion yet
- no vector index yet

Security note:

- Resource content is treated as untrusted input.
- M6 stores source/citation metadata so later workflows can separate quoted/source facts from model judgments.

Acceptance:

- inbound ideas can be captured as memory records
- memory survives restart
- tag/text search works
- standing goals can be rendered as prompt context
- source resources preserve citation metadata
- Obsidian local connector writes reversible markdown notes
- synthesis references multiple idea records
