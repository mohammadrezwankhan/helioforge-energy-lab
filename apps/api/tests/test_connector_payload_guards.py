"""Connector inputs fail before malformed upstream data is recorded as evidence."""

import asyncio
import json
import socket

import pytest

from helioforge import integrations


def weather_body(value: object = 12.5) -> dict[str, object]:
    return {
        "hourly": {
            "time": ["2026-11-05T00:00"],
            "temperature_2m": [value],
            "wind_speed_10m": [2.0],
            "shortwave_radiation": [0.0],
        },
        "hourly_units": {"temperature_2m": "°C"},
    }


@pytest.mark.parametrize(
    "payload",
    [[], {"hourly": []}, weather_body(True), weather_body(False)],
)
def test_weather_rejects_malformed_shapes_and_boolean_observations(
    monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    async def upstream(_url: str, _params: dict[str, str | float]) -> bytes:
        return json.dumps(payload).encode()

    monkeypatch.setattr(integrations, "upstream", upstream)
    with pytest.raises(ValueError):
        asyncio.run(integrations.weather(integrations.WeatherRequest()))


@pytest.mark.parametrize("units", [None, [], "celsius", {"temperature_2m": False}])
def test_weather_rejects_unstructured_unit_metadata(monkeypatch: pytest.MonkeyPatch, units: object) -> None:
    payload = {**weather_body(), "hourly_units": units}

    async def upstream(_url: str, _params: dict[str, str | float]) -> bytes:
        return json.dumps(payload).encode()

    monkeypatch.setattr(integrations, "upstream", upstream)
    with pytest.raises(ValueError):
        asyncio.run(integrations.weather(integrations.WeatherRequest()))


@pytest.mark.parametrize("configuration", [None, [], True, "device"])
def test_modbus_allowlist_requires_an_object_before_any_socket_access(
    monkeypatch: pytest.MonkeyPatch, configuration: object
) -> None:
    monkeypatch.setenv("HELIOFORGE_MODBUS_DEVICES", json.dumps(configuration))
    with pytest.raises(ValueError):
        integrations.modbus_read(integrations.ModbusRequest(device="meter"))


@pytest.mark.parametrize("port", [True, False, 502.5, None, float("inf"), float("nan")])
def test_modbus_rejects_noninteger_configuration_before_dispatch(
    monkeypatch: pytest.MonkeyPatch, port: object
) -> None:
    configuration = {"meter": {"host": "127.0.0.1", "port": port}}
    monkeypatch.setenv("HELIOFORGE_MODBUS_DEVICES", json.dumps(configuration))
    attempted: list[tuple[str, int]] = []

    def connect(address: tuple[str, int], timeout: float) -> socket.socket:
        attempted.append(address)
        assert timeout == 3
        raise OSError("Test refuses actual socket access")

    monkeypatch.setattr(socket, "create_connection", connect)
    with pytest.raises(ValueError):
        integrations.modbus_read(integrations.ModbusRequest(device="meter"))
    assert attempted == []
