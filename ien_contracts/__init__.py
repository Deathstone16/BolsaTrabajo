"""Contratos compartidos para extracción y compatibilidad."""

from .models import CandidateProfile, JobOffer, MatchRequest, MatchResult, ScoringConfig
from .utils import canonical_json, content_hash

__all__ = [
    "CandidateProfile",
    "JobOffer",
    "MatchRequest",
    "MatchResult",
    "ScoringConfig",
    "canonical_json",
    "content_hash",
]
