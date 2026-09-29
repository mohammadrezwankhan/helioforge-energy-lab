"""Versioned teaching catalogue and strict electrical-screening contract.

Advanced multi-carrier and dynamic cases are intentionally rejected by the energy
screen, not silently reduced to an unrelated battery calculation.
"""
from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Literal

from pydantic import Field, model_validator

from helioforge.schemas import StrictModel


@lru_cache(maxsize=1)
def catalog() -> dict:
    return json.loads(files('helioforge').joinpath('data/hybrid_catalog.json').read_text(encoding='utf-8'))


def get_system(system_id: str) -> dict:
    for item in catalog()['systems']:
        if item['id'] == system_id:
            return item
    raise ValueError('Unknown hybrid system identifier.')


def get_scenario(scenario_id: str) -> dict:
    for item in catalog()['scenarios']:
        if item['id'] == scenario_id:
            return item
    raise ValueError('Unknown hybrid scenario identifier.')


class HybridRequest(StrictModel):
    system_id: str = Field(default='remote-triad', max_length=80)
    scenario_id: str = Field(default='baseline', max_length=80)
    hours: int = Field(default=24, ge=2, le=168)
    control: Literal['GFL', 'GFM', 'Dual', 'Synchronous'] = 'GFM'
    solar_kw: float = Field(default=1200, ge=0, le=1_000_000)
    wind_kw: float = Field(default=800, ge=0, le=1_000_000)
    hydro_kw: float = Field(default=0, ge=0, le=1_000_000)
    generator_kw: float = Field(default=0, ge=0, le=1_000_000)
    battery_kwh: float = Field(default=3000, ge=0, le=10_000_000)
    battery_kw: float = Field(default=750, ge=0, le=1_000_000)
    load_kw: float = Field(default=650, gt=0, le=1_000_000)
    grid_import_kw: float = Field(default=0, ge=0, le=1_000_000)
    grid_export_kw: float = Field(default=0, ge=0, le=1_000_000)
    critical_fraction: float = Field(default=.65, gt=0, le=1)
    initial_soc: float = Field(default=.6, ge=0, le=1)
    min_soc: float = Field(default=.15, ge=0, lt=1)
    max_soc: float = Field(default=.9, gt=0, le=1)
    round_trip_efficiency: float = Field(default=.9, gt=0, le=1)
    import_eur_kwh: float = Field(default=.2, ge=-2, le=5)
    export_eur_kwh: float = Field(default=.06, ge=-2, le=5)
    generator_eur_kwh: float = Field(default=.28, ge=0, le=5)

    @model_validator(mode='after')
    def consistent(self):
        system, scenario = get_system(self.system_id), get_scenario(self.scenario_id)
        if not self.min_soc <= self.initial_soc <= self.max_soc or self.min_soc >= self.max_soc:
            raise ValueError('SOC must satisfy minimum <= initial <= maximum, with minimum < maximum.')
        reserve = scenario['modifiers'].get('reserve_floor', self.min_soc)
        if reserve > self.initial_soc or reserve >= self.max_soc:
            raise ValueError('The scenario reserve floor must not exceed initial SOC or reach maximum SOC.')
        if (self.battery_kw == 0) != (self.battery_kwh == 0):
            raise ValueError('Battery energy and power must both be zero or both positive.')
        for field, tech in [('solar_kw', 'solar'), ('wind_kw', 'wind'), ('hydro_kw', 'hydro'),
                            ('generator_kw', 'generator'), ('battery_kwh', 'battery')]:
            if getattr(self, field) and tech not in system['technologies']:
                raise ValueError(f'{field} is not an asset in this architecture. Choose a matching preset.')
        if system['topology'] == 'Off-grid' and (self.grid_import_kw or self.grid_export_kw):
            raise ValueError('An off-grid architecture cannot import or export through a utility connection.')
        if scenario['modifiers'].get('hours', 0) > self.hours:
            raise ValueError('The selected scenario requires a longer modeling horizon.')
        return self


def applicability(system: dict, scenario: dict) -> bool:
    sid, assets = scenario['id'], system['technologies']
    required = {'cloud-cover':'solar', 'wind-lull':'wind', 'low-river':'hydro',
                'generator-outage':'generator', 'battery-trip':'battery',
                'aged-battery':'battery', 'reserve-floor':'battery'}
    if sid in required and required[sid] not in assets:
        return False
    if sid in {'outage-4h', 'outage-24h', 'outage-72h', 'zero-export', 'export-cap',
               'import-cap', 'negative-prices', 'price-spike', 'reconnection', 'weak-grid'}:
        return system['topology'] != 'Off-grid'
    if sid == 'renewable-drought':
        return 'solar' in assets or 'wind' in assets
    if sid == 'black-start':
        return system['topology'] in {'Off-grid', 'Islandable', 'Networked'}
    return True


def validate_configuration(p: HybridRequest) -> dict:
    system, scenario = get_system(p.system_id), get_scenario(p.scenario_id)
    issues: list[str] = []
    if system['mode'] != 'screening':
        issues.append('Study-only architecture: a dedicated multi-carrier, network or technology model is required.')
    if scenario['mode'] != 'screening':
        issues.append('Study-only control scenario: dynamic or explicitly constrained optimization is required.')
    if not applicability(system, scenario):
        issues.append('This scenario does not apply to the selected architecture.')
    if system['topology'] == 'Off-grid' and p.control == 'GFL':
        issues.append('A grid-following-only island has no voltage/frequency reference in this teaching model.')
    if p.control == 'Synchronous' and not (p.hydro_kw > 0 or p.generator_kw > 0):
        issues.append('Synchronous control requires a configured hydro or dispatchable reference source.')
    if p.control in {'GFM', 'Dual'} and not (p.battery_kw > 0 or p.generator_kw > 0 or p.hydro_kw > 0):
        issues.append('The configured reference needs a battery converter or a synchronous source.')
    tags = [dict(label=system['topology'], reason='Derived from the selected point of interconnection.'),
            dict(label=system['coupling'], reason='Architecture coupling; the electrical screen remains AC-equivalent.'),
            dict(label=p.control, reason='Declared control assumption; not a validated control design.'),
            dict(label=system['mode'], reason='Capability of the numerical engine, not a maturity or safety certificate.')]
    if p.battery_kw:
        tags.append(dict(label=f'{p.battery_kwh / p.battery_kw:.1f} h storage',
                         reason='Nameplate battery energy / rated AC power; excludes SOC window and losses.'))
    if system['topology'] == 'Off-grid':
        tags.append(dict(label='No grid support', reason='Import and export ratings are both zero.'))
    if p.control == 'GFL' and scenario['id'].startswith('outage'):
        tags.append(dict(label='No island reference', reason='Local resources disconnect without an eligible island reference.'))
    return dict(valid=not issues, issues=issues, tags=tags, system_id=p.system_id,
                scenario_id=p.scenario_id, data_kind='synthetic_educational')
