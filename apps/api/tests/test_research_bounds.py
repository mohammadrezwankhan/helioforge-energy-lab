import pytest
from pydantic import ValidationError

from helioforge.schemas import DriftRequest, ReliabilityRequest


def test_reliability_rejects_overflow_scale():
    with pytest.raises(ValidationError):
        ReliabilityRequest(shape=2, scale_hours=1, age_hours=1e200, horizon_hours=1)


def test_drift_rejects_nonfinite_ratio_scale():
    with pytest.raises(ValidationError):
        DriftRequest(expected=[1e-308] * 30, observed=[1e308] * 30)
