from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.artifacts import (
    ArtifactAdmissionService,
    ArtifactKind,
    ArtifactRecord,
    ArtifactStatus,
    ArtifactStore,
)
from agentic.credentials import CredentialKind, CredentialRef, CredentialStore
from agentic.policy.engine import PolicyEngine
from agentic.policy.rules import CapabilityRequest
from agentic.resources.store import ResourceStore
from agentic.sources import SourceDefinition, SourceKind, SourceRuntime, SourceStore


class Milestone8SourceCapabilityRuntimeTests(unittest.TestCase):
    def test_local_jsonl_source_collects_dedupes_and_writes_resource(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_file = root / "market.jsonl"
            source_file.write_text(
                '{"uri":"local://post-1","title":"AI market signal","content_text":"AI agent workflow demand increased."}\n',
                encoding="utf-8",
            )
            source_store = SourceStore(root / "sources.sqlite3")
            resource_store = ResourceStore(root / "resources.sqlite3")
            source = source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.LOCAL_FILE,
                    name="Local market source",
                    locator=source_file.as_uri(),
                    enabled=True,
                )
            )
            runtime = SourceRuntime(source_store=source_store, resource_store=resource_store)

            first = runtime.collect(source.source_id)
            second = runtime.collect(source.source_id)
            resources = resource_store.search("AI agent")

        self.assertEqual(first.collected_count, 1)
        self.assertEqual(first.new_count, 1)
        self.assertEqual(second.collected_count, 1)
        self.assertEqual(second.new_count, 0)
        self.assertEqual(len(resources), 1)

    def test_source_runtime_refuses_disabled_or_missing_collectors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_store = SourceStore(root / "sources.sqlite3")
            resource_store = ResourceStore(root / "resources.sqlite3")
            disabled = source_store.add_source(
                SourceDefinition(kind=SourceKind.LOCAL_FILE, name="Disabled", locator=str(root / "off.jsonl"))
            )
            runtime = SourceRuntime(source_store=source_store, resource_store=resource_store)

            with self.assertRaises(ValueError):
                runtime.collect(disabled.source_id)

            web = source_store.add_source(
                SourceDefinition(
                    kind=SourceKind.WEB_PAGE,
                    name="Web",
                    locator="https://example.invalid",
                    enabled=True,
                )
            )
            with self.assertRaises(ValueError):
                runtime.collect(web.source_id)

    def test_credential_refs_store_references_not_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CredentialStore(Path(tmpdir) / "credentials.sqlite3")
            ref = store.add(
                CredentialRef(
                    provider="gmail",
                    purpose="read newsletters",
                    reference="GMAIL_READONLY_TOKEN_ENV",
                    kind=CredentialKind.ENV_VAR,
                    scopes=["gmail.readonly"],
                )
            )
            reloaded = store.get(ref.credential_id)

            with self.assertRaises(ValueError):
                CredentialRef(
                    provider="github",
                    purpose="bad",
                    reference="ghp_thislooksrawandmustnotbestored",
                )

        self.assertEqual(reloaded.safe_label(), "gmail:env_var:GMAIL_READONLY_TOKEN_ENV")

    def test_source_and_credential_metadata_reject_secret_like_keys(self) -> None:
        with self.assertRaises(ValueError):
            SourceDefinition(
                kind=SourceKind.LOCAL_FILE,
                name="Bad Source",
                locator="file:///tmp/bad.jsonl",
                metadata={"api_key": "do-not-store"},
            )
        with self.assertRaises(ValueError):
            CredentialRef(
                provider="x",
                purpose="bad",
                reference="SAFE_ENV_NAME",
                metadata={"password": "do-not-store"},
            )

    def test_script_artifact_requires_review_approval_and_dry_run_before_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(Path(tmpdir) / "artifacts.sqlite3")
            admission = ArtifactAdmissionService(store)
            script = admission.submit_for_review(
                ArtifactRecord(
                    kind=ArtifactKind.SCRIPT,
                    name="generated watcher",
                    content="print('dry-run only')",
                )
            )

            blocked = admission.dry_run(script.artifact_id)
            approved = admission.approve(script.artifact_id)
            dry_run = admission.dry_run(script.artifact_id)
            active = admission.activate(script.artifact_id)

        self.assertEqual(script.status, ArtifactStatus.REVIEW_REQUIRED)
        self.assertTrue(blocked.requires_approval)
        self.assertEqual(approved.status, ArtifactStatus.APPROVED)
        self.assertTrue(dry_run.allowed)
        self.assertEqual(active.status, ArtifactStatus.ACTIVE)

    def test_policy_gates_sensitive_capabilities(self) -> None:
        policy = PolicyEngine()
        sensitive = [
            "artifact:script",
            "tool:browser_submit",
            "tool:email_send",
            "tool:file_write",
            "tool:shell",
            "tool:booking",
            "tool:payment",
            "connector:reddit",
        ]

        for capability in sensitive:
            decision = policy.decide(CapabilityRequest(capability=capability, action="execute"))
            self.assertTrue(decision.requires_approval, capability)


if __name__ == "__main__":
    unittest.main()
