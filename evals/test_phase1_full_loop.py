from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.models.local_gguf import ModelResponse
from agentic.runtime.full_loop import FullLoopRuntime
from agentic.runtime.subagent_loop import SubagentLoop, _extract_proposal_body, _retry_instruction
from agentic.runtime.tool_bridge import ToolBridge
from agentic.skills.workshop import SkillWorkshopStore
from agentic.runtime.turn import MasterTurn
from agentic.tasks.ledger import TaskLedger
from agentic.tasks.subagent_task import TaskState
from agentic.tools.registry import ToolRegistry
from agentic.tools.skill_workshop import skill_workshop_tool
from agentic.tools.workflow_spec import workflow_spec_tool
from agentic.traces.logger import TraceLogger
from agentic.traces.replay import TraceReplay
from agentic.workflow_kernel import WorkflowStore


class FakeMasterAgent:
    def __init__(self, text: str):
        self.text = text
        self.messages: list[str] = []

    def generate(self, user_message: str) -> ModelResponse:
        self.messages.append(user_message)
        return ModelResponse(
            text=self.text,
            command=("fake-master",),
            returncode=0,
            raw_text=self.text,
        )


class FakeSubagent:
    def __init__(self, text: str):
        self.text = text

    def generate_for_task(self, task) -> ModelResponse:
        return ModelResponse(
            text=self.text,
            command=("fake-subagent",),
            returncode=0,
            raw_text=self.text,
        )


class SequentialFakeSubagent:
    def __init__(self, texts: list[str]):
        self.texts = list(texts)

    def generate_for_task(self, task) -> ModelResponse:
        text = self.texts.pop(0)
        return ModelResponse(
            text=text,
            command=("fake-subagent",),
            returncode=0,
            raw_text=text,
        )


class Phase1FullLoopTests(unittest.TestCase):
    def test_full_loop_answers_addition_with_fake_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = _runtime(
                tmpdir,
                master_text="unstructured master output",
                subagent_text='{"tool":"add","arguments":{"a":1,"b":1}}',
            )

            result = runtime.run_user_message("1+1은 뭐지?")

        self.assertTrue(result.ok)
        self.assertEqual(result.final_answer, "2")
        self.assertIsNotNone(result.task)
        self.assertEqual(result.task.state, TaskState.COMPLETED)
        self.assertEqual(result.task.result, "2")

    def test_full_loop_trace_contains_expected_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "trace.jsonl"
            runtime = _runtime(
                tmpdir,
                master_text="unstructured master output",
                subagent_text='{"tool":"add","arguments":{"a":1,"b":1}}',
            )

            result = runtime.run("1+1은 뭐지?")
            replay = TraceReplay.from_path(trace_path)

        self.assertTrue(result.ok)
        replay.assert_ordered_events(
            [
                "user_message_received",
                "master_model_called",
                "master_delegation_decision",
                "subagent_task_created",
                "subagent_model_called",
                "tool_called:add",
                "tool_result:add",
                "subagent_reported",
                "master_final_answer",
            ]
        )

    def test_full_loop_returns_direct_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = _runtime(
                tmpdir,
                master_text='{"action":"answer","answer":"hello"}',
                subagent_text='{"tool":"add","arguments":{"a":1,"b":1}}',
            )

            result = runtime.run("Say hello.")

        self.assertTrue(result.ok)
        self.assertEqual(result.final_answer, "hello")
        self.assertIsNone(result.task)

    def test_full_loop_accepts_phase1_decision_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = _runtime(
                tmpdir,
                master_text='{"decision":"answer","answer":"2"}',
                subagent_text='{"tool":"add","arguments":{"a":1,"b":1}}',
            )

            result = runtime.run("Answer directly.")

        self.assertTrue(result.ok)
        self.assertEqual(result.final_answer, "2")

    def test_full_loop_returns_failure_result_on_subagent_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = _runtime(
                tmpdir,
                master_text="unstructured master output",
                subagent_text="{not json",
            )

            result = runtime.run("1+1은 뭐지?")

        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "malformed_tool_call")
        self.assertIn("Failed:", result.final_answer)
        self.assertIsNotNone(result.task)
        self.assertEqual(result.task.state, TaskState.FAILED)

    def test_subagent_retries_malformed_tool_call_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            runtime = FullLoopRuntime(
                master_turn=MasterTurn(FakeMasterAgent("unstructured master output"), trace=trace),  # type: ignore[arg-type]
                subagent_loop=SubagentLoop(
                    agent=SequentialFakeSubagent(
                        [
                            "I should use a tool.",
                            '{"tool":"add","arguments":{"a":1,"b":1}}',
                        ]
                    ),
                    tool_bridge=ToolBridge(trace=trace),
                    trace=trace,
                ),
                ledger=TaskLedger(trace=trace),
                trace=trace,
            )

            result = runtime.run_user_message("1+1은 뭐지?")
            replay = TraceReplay.from_path(Path(tmpdir) / "trace.jsonl")

        self.assertTrue(result.ok)
        self.assertEqual(result.final_answer, "2")
        self.assertIn("subagent_tool_call_retry", replay.event_types())

    def test_subagent_recovers_skill_workshop_natural_language_intent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workshop_db = Path(tmpdir) / "skill_workshop.sqlite3"
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            tools = ToolRegistry(
                [
                    skill_workshop_tool(
                        workshop_db,
                        skills_root=Path(tmpdir) / "skills",
                    )
                ]
            )
            runtime = FullLoopRuntime(
                master_turn=MasterTurn(
                    FakeMasterAgent(
                        '{"action":"delegate","task":"Create a pending skill proposal using the skill_workshop tool."}'
                    ),
                    trace=trace,
                ),  # type: ignore[arg-type]
                subagent_loop=SubagentLoop(
                    agent=FakeSubagent(
                        'Tool: `skill_workshop`\n'
                        'Parameters:\n'
                        '- `action`: "create"\n'
                        '- `name`: "workflow-building"\n'
                        '- `description`: "Guide vague workflow requests"\n'
                        '\nProposal body:\n'
                        '```markdown\n'
                        '# Workflow Building\n'
                        'Ask one missing question at a time.\n'
                        '```'
                    ),
                    tool_bridge=ToolBridge(registry=tools, trace=trace),
                    trace=trace,
                ),
                ledger=TaskLedger(trace=trace),
                trace=trace,
            )

            result = runtime.run_user_message("workflow building skill proposal 만들어줘")
            replay = TraceReplay.from_path(Path(tmpdir) / "trace.jsonl")
            proposal = SkillWorkshopStore(workshop_db).list(limit=1)[0]

        self.assertTrue(result.ok)
        self.assertIn("workflow-building", result.final_answer)
        self.assertIn("subagent_tool_call_recovered", replay.event_types())
        self.assertEqual(
            proposal.proposal_body,
            "# Workflow Building\nAsk one missing question at a time.",
        )

    def test_recovered_skill_proposal_body_prefers_labeled_bullets(self) -> None:
        output = "\n".join(
            [
                "The user wants to create a pending skill proposal.",
                "Tool: skill_workshop",
                "- Trigger: User asks for automation.",
                "- Interview: Ask one question at a time.",
                "- Discovery: Identify tools and connectors.",
                "- Proposal: Propose a workflow spec.",
            ]
        )

        body = _extract_proposal_body(output)

        self.assertTrue(body.startswith("- Trigger"))
        self.assertNotIn("Tool: skill_workshop", body)

    def test_recovered_skill_proposal_body_accepts_bold_labeled_bullets(self) -> None:
        output = "\n".join(
            [
                "Tool: skill_workshop",
                "- **Trigger**: User asks for automation.",
                "- **Interview**: Ask one question at a time.",
                "- **Discovery**: Identify tools and connectors.",
                "- **Proposal**: Propose a workflow spec.",
            ]
        )

        body = _extract_proposal_body(output)

        self.assertTrue(body.startswith("- **Trigger**"))
        self.assertIn("- **Proposal**", body)

    def test_subagent_recovers_workflow_spec_json_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_db = Path(tmpdir) / "workflows.sqlite3"
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            tools = ToolRegistry(
                [
                    workflow_spec_tool(workflow_db),
                ]
            )
            runtime = FullLoopRuntime(
                master_turn=MasterTurn(
                    FakeMasterAgent(
                        '{"action":"delegate","task":"Create a pending WorkflowSpec using the workflow_spec tool."}'
                    ),
                    trace=trace,
                ),  # type: ignore[arg-type]
                subagent_loop=SubagentLoop(
                    agent=FakeSubagent(
                        """
                        {
                          "name": "Community Trend Workflow",
                          "goal": "Collect and report community trends.",
                          "triggers": [{"type": "interval", "value": "interval:60s"}],
                          "sources": [{"kind": "community_web"}],
                          "steps": [
                            {"step_type": "collect", "name": "Collect sources"},
                            {"step_type": "analyze", "name": "Analyze signals"},
                            {"step_type": "report", "name": "Render report"}
                          ],
                          "outputs": [{"kind": "report"}],
                          "success_criteria": ["A report is created."]
                        }
                        """
                    ),
                    tool_bridge=ToolBridge(registry=tools, trace=trace),
                    trace=trace,
                ),
                ledger=TaskLedger(trace=trace),
                trace=trace,
            )

            result = runtime.run_user_message("workflow spec 만들어줘")
            replay = TraceReplay.from_path(Path(tmpdir) / "trace.jsonl")
            spec = WorkflowStore(workflow_db).list_specs(limit=1)[0]

        self.assertTrue(result.ok)
        self.assertEqual(spec.status.value, "proposed")
        self.assertIn("subagent_tool_call_recovered", replay.event_types())

    def test_workflow_spec_retry_instruction_keeps_workflow_spec_tool(self) -> None:
        instruction = _retry_instruction(
            original_instruction="Create a pending WorkflowSpec using the workflow_spec tool.",
            previous_output='{"tool":"workflow_spec","arguments":{"action":"create","goal"',
            error_message="invalid tool call JSON",
        )

        self.assertIn('"tool":"workflow_spec"', instruction)
        self.assertIn("Keep every string short", instruction)
        self.assertNotIn('"tool":"skill_workshop"', instruction)

    def test_subagent_recovers_compact_workflow_spec_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_db = Path(tmpdir) / "workflows.sqlite3"
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            tools = ToolRegistry([workflow_spec_tool(workflow_db)])
            runtime = FullLoopRuntime(
                master_turn=MasterTurn(
                    FakeMasterAgent(
                        '{"action":"delegate","task":"Create a pending WorkflowSpec using the workflow_spec tool."}'
                    ),
                    trace=trace,
                ),  # type: ignore[arg-type]
                subagent_loop=SubagentLoop(
                    agent=FakeSubagent(
                        """
                        {
                          "name": "Compact Trend Workflow",
                          "goal": "Report recurring trend signals.",
                          "trigger": "interval:60s",
                          "source": "community_web+reddit",
                          "step_types": ["collect", "analyze", "report"],
                          "output": "report"
                        }
                        """
                    ),
                    tool_bridge=ToolBridge(registry=tools, trace=trace),
                    trace=trace,
                ),
                ledger=TaskLedger(trace=trace),
                trace=trace,
            )

            result = runtime.run_user_message("workflow spec 만들어줘")
            spec = WorkflowStore(workflow_db).list_specs(limit=1)[0]

        self.assertTrue(result.ok)
        self.assertEqual([step.step_type.value for step in spec.steps], ["collect", "analyze", "report"])
        self.assertEqual([source["kind"] for source in spec.sources], ["community_web", "reddit"])

    def test_subagent_recovers_truncated_compact_workflow_spec_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_db = Path(tmpdir) / "workflows.sqlite3"
            trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
            tools = ToolRegistry([workflow_spec_tool(workflow_db)])
            runtime = FullLoopRuntime(
                master_turn=MasterTurn(
                    FakeMasterAgent(
                        '{"action":"delegate","task":"Create a pending WorkflowSpec using the workflow_spec tool."}'
                    ),
                    trace=trace,
                ),  # type: ignore[arg-type]
                subagent_loop=SubagentLoop(
                    agent=FakeSubagent(
                        '{"tool":"workflow_spec","arguments":{"action":"create",'
                        '"name":"stock-trend-monitor",'
                        '"goal":"Report stock community trends.",'
                        '"description":"Recurring trend analysis.",'
                        '"trigger":"interval:60s",'
                        '"source":["reddit","dcinside-gallery"],'
                        '"step_types":["collect","analyze","aggregate","report"],'
                        '"output":"report",'
                        '"success_criteria":["Trend report is generated"],'
                        '"assumptions":["Web access is available"],...'
                    ),
                    tool_bridge=ToolBridge(registry=tools, trace=trace),
                    trace=trace,
                ),
                ledger=TaskLedger(trace=trace),
                trace=trace,
            )

            result = runtime.run_user_message("workflow spec 만들어줘")
            spec = WorkflowStore(workflow_db).list_specs(limit=1)[0]

        self.assertTrue(result.ok)
        self.assertEqual(spec.name, "stock-trend-monitor")
        self.assertEqual([step.step_type.value for step in spec.steps], ["collect", "analyze", "aggregate", "report"])
        self.assertEqual([source["kind"] for source in spec.sources], ["reddit", "dcinside-gallery"])


def _runtime(
    tmpdir: str,
    *,
    master_text: str,
    subagent_text: str,
) -> FullLoopRuntime:
    trace = TraceLogger(Path(tmpdir) / "trace.jsonl")
    return FullLoopRuntime(
        master_turn=MasterTurn(FakeMasterAgent(master_text), trace=trace),  # type: ignore[arg-type]
        subagent_loop=SubagentLoop(
            agent=FakeSubagent(subagent_text),
            tool_bridge=ToolBridge(trace=trace),
            trace=trace,
        ),
        ledger=TaskLedger(trace=trace),
        trace=trace,
    )


if __name__ == "__main__":
    unittest.main()
