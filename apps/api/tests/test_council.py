"""Orchestration tests use a fake SDK module, never an external provider."""
import asyncio
import sys
import types

import pytest

from helioforge.council import openai_council
from helioforge.schemas import CouncilRequest


class FakeAgent:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def install_fake_sdk(monkeypatch, runner):
    module = types.ModuleType('agents')
    module.Agent = FakeAgent
    module.ModelSettings = FakeAgent
    module.RunConfig = FakeAgent
    module.Runner = runner
    monkeypatch.setitem(sys.modules, 'agents', module)
    monkeypatch.setenv('OPENAI_MODEL', 'test-model-no-real-provider')


def test_eight_concurrent_specialists_then_critic(monkeypatch):
    started, finished, calls = [], [], []

    class Runner:
        @staticmethod
        async def run(agent, payload, max_turns, run_config):
            calls.append(agent.name)
            assert agent.model == 'test-model-no-real-provider'
            assert max_turns == 2
            assert run_config.tracing_disabled is True
            if agent.name == 'Independent committee critic':
                assert len(finished) == 8
                value = agent.output_type(recommendation='Collect evidence.',
                                          unresolved_risks=['Synthetic inputs'], next_actions=['Verify data.'])
            else:
                started.append(agent.name)
                for _ in range(20):
                    if len(started) == 8:
                        break
                    await asyncio.sleep(0)
                assert len(started) == 8
                finished.append(agent.name)
                value = agent.output_type(summary='Mock result, not a live review.',
                                          risks=['Evidence missing'], required_evidence=['Site data'])
            return types.SimpleNamespace(final_output=value)

    install_fake_sdk(monkeypatch, Runner)
    result = asyncio.run(openai_council(CouncilRequest(), {'data_kind':'synthetic'}))
    assert len(calls) == 9
    assert len(result['reviews']) == 8
    assert calls[-1] == 'Independent committee critic'
    assert result['execution'] == 'eight_parallel_specialists_then_critic'


def test_provider_failure_cancels_sibling_reviews(monkeypatch):
    cancelled = []

    class Runner:
        @staticmethod
        async def run(agent, *_args, **_kwargs):
            if agent.name == 'Storage engineer':
                await asyncio.sleep(0.01)
                raise RuntimeError('Synthetic provider failure')
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                cancelled.append(agent.name)
                raise

    install_fake_sdk(monkeypatch, Runner)

    async def exercise():
        with pytest.raises(RuntimeError, match='Synthetic provider failure'):
            await openai_council(CouncilRequest(), {})
        # Assert before the event loop closes, so loop shutdown cannot hide a leak.
        assert len(cancelled) == 7

    asyncio.run(exercise())
