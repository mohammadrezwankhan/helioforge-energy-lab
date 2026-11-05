"""The trusted packaged catalogue must satisfy its full public data contract."""

import json
from importlib.resources import files

from pydantic import TypeAdapter

from helioforge.hybrid import HybridRequest, catalog, get_scenario, get_system
from helioforge.hybrid_types import HybridCatalog


def test_packaged_catalogue_schema_and_presets_are_complete_without_changing_bytes() -> None:
    path = files("helioforge").joinpath("data/hybrid_catalog.json")
    before = path.read_bytes()
    data = catalog()
    validated = TypeAdapter(HybridCatalog).validate_python(data, strict=True)
    assert validated == data == json.loads(before)
    assert path.read_bytes() == before
    for system in data["systems"]:
        preset = HybridRequest.model_validate(system["preset"])
        assert preset.system_id == system["id"]
        assert get_system(system["id"]) is system
    for scenario in data["scenarios"]:
        assert get_scenario(scenario["id"]) is scenario
