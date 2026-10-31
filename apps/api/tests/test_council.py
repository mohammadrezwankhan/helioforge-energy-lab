"""Orchestration tests use a fake SDK module, never an external provider."""
import asyncio
import sys
import types

import pytest
from pydantic import ValidationError

from helioforge.council import ROLES, openai_council
from helioforge.council_protocol import (
    CRITIC_MAX_OUTPUT_TOKENS,
    CRITIC_MAX_TURNS,
    MAX_CROSS_EXAMINATION_ROUNDS,
    SPECIALIST_COUNT,
    SPECIALIST_MAX_OUTPUT_TOKENS,
    SPECIALIST_MAX_TURNS,
    WORKFLOW_TIMEOUT_SECONDS,
    protocol_metadata,
    runner_invocation_count,
)
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


def test_local_protocol_metadata_reports_checklists_without_agent_execution():
    limits = protocol_metadata(mode='local')['limits']

    assert limits['specialist_count'] == 0
    assert limits['configured_specialist_count'] == 0
    assert limits['executed_specialist_count'] == 0
    assert limits['configured_critic_count'] == 0
    assert limits['executed_critic_count'] == 0
    assert limits['local_checklist_section_count'] == 8
    assert limits['expected_runner_invocations'] == 0
    assert limits['completed_runner_invocations'] == 0
    assert limits['runner_invocation_semantics'] == (
        'No Agents SDK or provider invocation; eight fixed checklist sections, '
        'deterministic summary, no critic execution.'
    )


def test_eight_concurrent_specialists_then_cross_examination_then_critic(monkeypatch):
    started, finished, calls = [], [], []

    class Runner:
        @staticmethod
        async def run(agent, payload, max_turns, run_config):
            calls.append(agent.name)
            assert agent.model == 'test-model-no-real-provider'
            assert max_turns == 2
            assert run_config.tracing_disabled is True
            if agent.name == 'Independent committee critic':
                assert len(finished) == 16
                value = agent.output_type(recommendation='Collect evidence.',
                                          unresolved_risks=['Synthetic inputs'], next_actions=['Verify data.'])
            else:
                started.append(agent.name)
                for _ in range(20):
                    if len(started) >= 8:
                        break
                    await asyncio.sleep(0)
                assert len(started) >= 8
                finished.append(agent.name)
                value = agent.output_type(summary='Mock result, not a live review.',
                                          risks=['Evidence missing'], required_evidence=['Site data'])
            return types.SimpleNamespace(final_output=value)

    install_fake_sdk(monkeypatch, Runner)
    result = asyncio.run(openai_council(
        CouncilRequest(mode='openai', consent_to_external_processing=True), {'data_kind':'synthetic'}))
    assert len(calls) == 17
    assert len(result['reviews']) == 8
    assert calls[-1] == 'Independent committee critic'
    assert result['execution'] == 'eight_specialists_cross_examination_then_critic'
    assert len(result['rounds']) == 2
    assert len(result['protocol']) == 17
    assert result['consensus']['identity_verified'] is False
    assert result['rounds'][1]['phase'] == 'cross_examination'
    assert result['protocol_metadata']['id'] == 'helioforge-council/v1'
    assert result['protocol_metadata']['external_execution_status'] == 'completed'
    assert result['protocol_metadata']['consent_to_external_processing'] is True
    assert result['protocol_metadata']['limits']['expected_runner_invocations'] == 17
    assert result['protocol_metadata']['limits']['completed_runner_invocations'] == 17
    assert result['protocol_metadata']['limits']['specialist_count'] == SPECIALIST_COUNT
    assert result['protocol_metadata']['limits']['configured_specialist_count'] == SPECIALIST_COUNT
    assert result['protocol_metadata']['limits']['executed_specialist_count'] == SPECIALIST_COUNT
    assert result['protocol_metadata']['limits']['configured_critic_count'] == 1
    assert result['protocol_metadata']['limits']['executed_critic_count'] == 1
    assert result['protocol_metadata']['limits']['local_checklist_section_count'] == 0
    assert result['runner_invocations'] == runner_invocation_count(1)
    assert len(ROLES) == SPECIALIST_COUNT
    assert result['protocol_metadata']['limits']['workflow_timeout_seconds'] == WORKFLOW_TIMEOUT_SECONDS
    assert result['protocol_metadata']['limits']['specialist_max_turns'] == SPECIALIST_MAX_TURNS
    assert result['protocol_metadata']['limits']['specialist_max_output_tokens'] == SPECIALIST_MAX_OUTPUT_TOKENS
    assert result['protocol_metadata']['limits']['critic_max_turns'] == CRITIC_MAX_TURNS
    assert result['protocol_metadata']['limits']['critic_max_output_tokens'] == CRITIC_MAX_OUTPUT_TOKENS
    assert result['protocol_metadata']['cost']['potentially_billable'] is True
    assert result['protocol_metadata']['cost']['estimate_usd'] is None
    assert result['protocol_metadata']['cancellation']['status'] == 'not_triggered'
    assert result['protocol_metadata']['cancellation']['provider_stop_confirmed'] is None
    assert result['protocol_metadata']['integrity']['signature_verified'] is False


def test_two_cross_examination_rounds_have_twenty_five_runner_invocations(monkeypatch):
    calls = []

    class Runner:
        @staticmethod
        async def run(agent, payload, max_turns, run_config):
            calls.append(agent.name)
            if agent.name == 'Independent committee critic':
                value = agent.output_type(recommendation='Collect evidence.',
                                          unresolved_risks=['Synthetic inputs'], next_actions=['Verify data.'])
            else:
                value = agent.output_type(summary='Mock result, not a live review.',
                                          risks=['Evidence missing'], required_evidence=['Site data'])
            return types.SimpleNamespace(final_output=value)

    install_fake_sdk(monkeypatch, Runner)
    request = CouncilRequest(mode='openai', consent_to_external_processing=True,
                             cross_examination_rounds=2)
    result = asyncio.run(openai_council(request, {'data_kind':'synthetic'}))

    assert len(calls) == 25
    limits = result['protocol_metadata']['limits']
    assert limits['cross_examination_rounds'] == 2
    assert limits['expected_runner_invocations'] == 25
    assert limits['completed_runner_invocations'] == 25
    assert result['model_calls'] == 25
    assert MAX_CROSS_EXAMINATION_ROUNDS == request.cross_examination_rounds
    assert result['runner_invocations'] == runner_invocation_count(2)
    with pytest.raises(ValidationError):
        CouncilRequest(cross_examination_rounds=MAX_CROSS_EXAMINATION_ROUNDS + 1)


def test_consensus_preserves_disagreement():
    from helioforge.council import vote_summary
    result = vote_summary([{'stance':'revise'}, {'stance':'insufficient'}, {'stance':'proceed_research'}])
    assert result['unanimous'] is False
    assert result['entropy_bits'] == pytest.approx(1.5849625)
    assert result['probability_of_correctness'] is None
    assert sum(result['dirichlet_mean'].values()) == pytest.approx(1)


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
