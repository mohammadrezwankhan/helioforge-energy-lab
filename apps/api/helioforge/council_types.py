"""Concrete data contracts for local evidence checks and optional council results."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from helioforge.council_protocol import ProtocolMetadata

Stance = Literal["proceed_research", "revise", "insufficient"]


class Vote(TypedDict):
    stance: Stance


class VoteSummary(TypedDict):
    counts: dict[str, int]
    entropy_bits: float | None
    dirichlet_mean: dict[str, float]
    prior: str
    unanimous: bool
    probability_of_correctness: None
    identity_verified: bool


class EvidenceFinding(TypedDict):
    code: str
    scope: str
    message: str
    required_evidence: str


class EvidenceRecord(TypedDict):
    record_index: int
    kind: str | None
    digest_status: str
    finding_codes: list[str]


class EvidenceReview(TypedDict):
    status: str
    records_checked: int
    records: list[EvidenceRecord]
    findings: list[EvidenceFinding]
    semantics: str
    critic_execution: str


class LocalReview(TypedDict):
    agent: str
    summary: str
    risks: list[str]
    required_evidence: list[str]


class ExternalReview(LocalReview, Vote):
    response_to_challenge: str


class Decision(TypedDict):
    recommendation: str
    unresolved_risks: list[str]
    next_actions: list[str]


class LocalCouncilResult(TypedDict):
    mode: Literal["local"]
    hybrid_run_id: str | None
    execution: str
    protocol_metadata: ProtocolMetadata
    evidence_review: EvidenceReview
    reviewed_brief: str
    market: str
    reviews: list[LocalReview]
    decision: Decision
    warnings: list[str]


class ReviewRound(TypedDict):
    round: int
    phase: str
    reviews: list[ExternalReview]
    consensus: VoteSummary


class ProtocolMessage(TypedDict):
    sender: str
    recipient: str
    task_id: str
    action: str
    round: NotRequired[int]
    payload: ExternalReview | Decision
    critic_signoff: bool


class ExternalCouncilResult(TypedDict):
    mode: Literal["openai"]
    execution: str
    model: str
    protocol_metadata: ProtocolMetadata
    market: str
    hybrid_run_id: str | None
    reviewed_brief: str
    reviews: list[ExternalReview]
    rounds: list[ReviewRound]
    protocol: list[ProtocolMessage]
    consensus: VoteSummary
    model_calls: int
    runner_invocations: int
    decision: Decision
    warnings: list[str]
