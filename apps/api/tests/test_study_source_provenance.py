from helioforge.studies import StudyRequest, evaluate


def test_original_financial_conventions_cite_implementation_without_external_validation_claim():
    for study in ["pv-reserve", "investment-waterfall"]:
        result = evaluate(StudyRequest(study=study))
        assert result["sources"]
        assert any("First-party" in source["title"] for source in result["sources"])
        assert any("independent" in limit for limit in result["limitations"])
