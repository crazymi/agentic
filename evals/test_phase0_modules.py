from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from agentic.agents.master import MasterAgent
from agentic.agents.subagent import SubAgent
from agentic.config.models import ModelConfig
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.prompts.builder import PromptBuilder
from agentic.runtime.spawn import simulate_subagent_spawn
from agentic.tasks.subagent_task import SubAgentTask, TaskState
from agentic.tools.add import add
from agentic.tools.parser import parse_tool_call
from agentic.tools.registry import ToolRegistry
from agentic.traces.logger import TraceLogger


class Phase0ModuleTests(unittest.TestCase):
    def test_master_model_generates_text(self) -> None:
        provider = LocalGGUFProvider(_echo_model("master"))
        agent = MasterAgent(provider=provider, prompt_builder=PromptBuilder())

        response = agent.generate("hello")

        self.assertIn("master response", response.text)
        self.assertIn("hello", response.text)

    def test_subagent_model_generates_text(self) -> None:
        provider = LocalGGUFProvider(_echo_model("subagent"))
        tools = ToolRegistry.with_defaults()
        agent = SubAgent(
            provider=provider,
            prompt_builder=PromptBuilder(),
            tools=tools,
        )
        task = SubAgentTask("Use add to compute 1+1.")

        response = agent.generate_for_task(task)

        self.assertIn("subagent response", response.text)
        self.assertIn("add", response.text)

    def test_tool_schema_is_visible_to_subagent(self) -> None:
        prompt = PromptBuilder().subagent_prompt(
            SubAgentTask("Compute 1+1."),
            ToolRegistry.with_defaults().schemas(),
        )

        self.assertIn('"name": "add"', prompt)
        self.assertIn('"required": ["a", "b"]', prompt)

    def test_add_tool_returns_2(self) -> None:
        result = add(1, 1)

        self.assertEqual(result, 2)

    def test_tool_call_json_is_parsed(self) -> None:
        call = parse_tool_call('{"tool":"add","arguments":{"a":1,"b":1}}')

        self.assertEqual(call.tool, "add")
        self.assertEqual(call.arguments, {"a": 1, "b": 1})

    def test_tool_registry_executes_parsed_call(self) -> None:
        call = parse_tool_call('{"tool":"add","arguments":{"a":1,"b":1}}')

        result = ToolRegistry.with_defaults().execute(call)

        self.assertEqual(result, 2)

    def test_invalid_tool_call_json_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid tool call JSON"):
            parse_tool_call("{not json")

    def test_subagent_task_can_be_created(self) -> None:
        task = SubAgentTask("Compute 1+1.")

        self.assertTrue(task.task_id)
        self.assertEqual(task.state, TaskState.CREATED)
        self.assertEqual(task.instruction, "Compute 1+1.")

    def test_subagent_task_state_transitions_are_explicit(self) -> None:
        task = SubAgentTask("Compute 1+1.")

        task.transition(TaskState.RUNNING)
        task.transition(TaskState.TOOL_REQUESTED)
        task.transition(TaskState.TOOL_COMPLETED)
        task.mark_result("2")
        task.transition(TaskState.COMPLETED)

        self.assertEqual(task.state, TaskState.COMPLETED)
        self.assertEqual(task.result, "2")

    def test_invalid_subagent_task_transition_fails(self) -> None:
        task = SubAgentTask("Compute 1+1.")

        with self.assertRaisesRegex(ValueError, "invalid task transition"):
            task.transition(TaskState.COMPLETED)

    def test_agent_spawn_can_be_simulated(self) -> None:
        task = SubAgentTask("Compute 1+1.")

        spawned = simulate_subagent_spawn(task)

        self.assertTrue(spawned.simulated)
        self.assertEqual(spawned.task.task_id, task.task_id)

    def test_trace_records_model_call_and_tool_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "trace.jsonl"
            trace = TraceLogger(trace_path)

            trace.record("model_called", {"role": "master"})
            trace.record("tool_called", {"tool": "add", "arguments": {"a": 1, "b": 1}})
            trace.record("tool_result", {"tool": "add", "result": 2})

            lines = trace_path.read_text(encoding="utf-8").splitlines()
            events = trace.read_events()

        self.assertEqual(len(lines), 3)
        self.assertEqual([event.event_type for event in events], [
            "model_called",
            "tool_called",
            "tool_result",
        ])
        self.assertEqual(json.loads(lines[2])["payload"]["result"], 2)


def _echo_model(role: str) -> ModelConfig:
    script = (
        "import sys; "
        "prompt=sys.stdin.read(); "
        "print(sys.argv[1] + ' response: ' + prompt[:10000])"
    )
    return ModelConfig(
        model_id=f"local-echo-{role}",
        name=f"local-echo-{role}",
        role=role,
        executable=sys.executable,
        command_template=(sys.executable, "-c", script, role),
        timeout_s=10.0,
    )


if __name__ == "__main__":
    unittest.main()
