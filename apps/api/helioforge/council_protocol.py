"""Versioned limits and disclosure fields for council execution."""
from __future__ import annotations

PROTOCOL_ID = "helioforge-council/v1"
SPECIALIST_COUNT = 8
SPECIALIST_MAX_TURNS = 2
SPECIALIST_MAX_OUTPUT_TOKENS = 1800
CRITIC_MAX_TURNS = 2
CRITIC_MAX_OUTPUT_TOKENS = 2200
MAX_CROSS_EXAMINATION_ROUNDS = 2
WORKFLOW_TIMEOUT_SECONDS = 300


def runner_invocation_count(cross_examination_rounds: int) -> int:
    """Count SDK Runner.run invocations, not provider HTTP requests or billable turns."""
    return SPECIALIST_COUNT * (1 + cross_examination_rounds) + 1


def protocol_metadata(
    *,
    mode: str,
    requested_cross_examination_rounds: int = 1,
    consent_to_external_processing: bool = False,
    external_execution_status: str | None = None,
    completed_runner_invocations: int | None = None,
    model: str | None = None,
    cancellation_status: str | None = None,
    provider_stop_confirmed: bool | None = None,
    task_id: str | None = None,
) -> dict:
    """Return auditable protocol facts without implying provider or reviewer authority."""
    external = mode == "openai"
    status = external_execution_status or ("completed" if external else "not_requested")
    expected = runner_invocation_count(requested_cross_examination_rounds) if external else 0
    configured_specialists = SPECIALIST_COUNT if external else 0
    configured_critics = 1 if external else 0
    executed_specialists = (
        SPECIALIST_COUNT if status == "completed" else
        0 if not external or status == "not_started" else None
    )
    executed_critics = (
        1 if status == "completed" else
        0 if not external or status == "not_started" else None
    )
    return {
        "id": PROTOCOL_ID,
        "mode": mode,
        "external_execution_status": status,
        "consent_to_external_processing": bool(consent_to_external_processing and external),
        "provider": "OpenAI" if external else None,
        "model": model if external else None,
        "limits": {
            "workflow_timeout_seconds": WORKFLOW_TIMEOUT_SECONDS if external else None,
            # Keep specialist_count as the external configured-role count for compatibility;
            # executed counts are separate and are zero in local mode.
            "specialist_count": configured_specialists,
            "configured_specialist_count": configured_specialists,
            "executed_specialist_count": executed_specialists,
            "configured_critic_count": configured_critics,
            "executed_critic_count": executed_critics,
            "local_checklist_section_count": SPECIALIST_COUNT if not external else 0,
            "specialist_max_turns": SPECIALIST_MAX_TURNS if external else None,
            "specialist_max_output_tokens": SPECIALIST_MAX_OUTPUT_TOKENS if external else None,
            "critic_max_turns": CRITIC_MAX_TURNS if external else None,
            "critic_max_output_tokens": CRITIC_MAX_OUTPUT_TOKENS if external else None,
            "requested_cross_examination_rounds": requested_cross_examination_rounds,
            "cross_examination_rounds": requested_cross_examination_rounds if external else 0,
            "expected_runner_invocations": expected,
            "completed_runner_invocations": completed_runner_invocations if external else 0,
            "runner_invocation_semantics": (
                "One Agents SDK Runner.run invocation per specialist and phase plus one critic invocation. "
                "Each invocation may use up to the configured turns; counts do not establish provider HTTP "
                "requests, token usage, or monetary cost."
                if external else
                "No Agents SDK or provider invocation; eight fixed checklist sections, deterministic summary, no critic execution."
            ),
        },
        "cost": {
            "potentially_billable": external,
            "attempt_may_have_incurred_provider_usage": external and status != "not_started",
            "estimate_usd": None,
            "actual_cost_usd": None,
            "usage_budget_enforced_by_application": False,
            "status": "unknown_until_provider_usage_is_checked" if external else "not_applicable",
            "failure_may_still_be_billable": external and status in {"failed", "timed_out"},
        },
        "cancellation": {
            "status": cancellation_status or ("not_triggered" if external else "not_applicable"),
            "provider_stop_confirmed": provider_stop_confirmed if external else None,
            "scope": (
                "Outstanding asyncio tasks are cancelled on failure, timeout, or request cancellation; "
                "the provider may continue work already accepted."
                if external else "No external task was started."
            ),
        },
        "integrity": {
            "task_id": task_id,
            "task_id_semantics": (
                "Truncated SHA-256 correlation identifier for the serialized review payload; it is not a "
                "signature or evidence of authorship, authority, truth, or approval."
                if external else None
            ),
            "input_sha256_semantics": (
                "The local persistence layer's digest identifies serialized request inputs. It does not verify "
                "the source, signer, scientific validity, or approval."
            ),
            "reviewer_identity_verified": False,
            "evidence_authenticity_verified": False,
            "signature_verified": False,
            "critic_signoff": False,
            "human_approval_recorded": False,
        },
    }


def external_failure_detail(
    *,
    status: str,
    message: str,
    cross_examination_rounds: int,
    model: str | None,
    consent_to_external_processing: bool = True,
) -> dict:
    """Build an API error payload that does not claim provider-side cancellation."""
    return {
        "message": message,
        "protocol": protocol_metadata(
            mode="openai",
            requested_cross_examination_rounds=cross_examination_rounds,
            consent_to_external_processing=consent_to_external_processing,
            external_execution_status=status,
            completed_runner_invocations=0 if status == "not_started" else None,
            model=model,
            cancellation_status=("best_effort_requested" if status in {"failed", "timed_out"} else "not_applicable"),
            provider_stop_confirmed=False if status in {"failed", "timed_out"} else None,
        ),
        "result_recorded": False,
    }
