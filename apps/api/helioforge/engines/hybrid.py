"""Transparent hourly energy-adequacy policy. NOT an optimizer or stability model.

Policy: renewables -> target load -> charge from surplus -> battery discharge ->
grid -> dispatchable backup -> unserved target load. Export unused renewable
surplus within its limit (curtail instead when export price is negative).
Initial battery energy is explicit; no cyclic terminal SOC constraint is claimed.
"""
from __future__ import annotations

import math

from helioforge.hybrid import HybridRequest, get_scenario, get_system, validate_configuration


def simulate_hybrid(p: HybridRequest) -> dict:
    validation = validate_configuration(p)
    if not validation['valid']:
        raise ValueError(' '.join(validation['issues']))
    system, scenario = get_system(p.system_id), get_scenario(p.scenario_id)
    m = scenario['modifiers']
    cap = p.battery_kwh * m.get('capacity_factor', 1.)
    power = p.battery_kw * m.get('battery_factor', 1.)
    lo, hi = cap * max(p.min_soc, m.get('reserve_floor', p.min_soc)), cap * p.max_soc
    energy = cap * p.initial_soc
    initial = energy
    eta = math.sqrt(p.round_trip_efficiency)
    rows = []
    for t in range(p.hours):
        hour = t % 24
        load = p.load_kw * (.78 + .18 * math.sin((hour-8)*math.pi/12)**2
                            + (.25 if 17 <= hour <= 20 else 0)) * m.get('load_factor', 1.)
        if 17 <= hour <= 20:
            load *= m.get('step_factor', 1.)
        pv = p.solar_kw * max(0., math.sin((hour-6)*math.pi/12)) * m.get('solar_factor', 1.)
        wind = p.wind_kw * (.38 + .16 * math.sin(hour*.43 + 1.)) * m.get('wind_factor', 1.)
        hydro = p.hydro_kw * .6 * m.get('hydro_factor', 1.)
        renewables = pv + wind + hydro
        outage = m.get('outage_start', -1) <= t < m.get('outage_start', -1) + m.get('outage_hours', 0)
        connected = system['topology'] != 'Off-grid' and not outage
        generator_limit = p.generator_kw * m.get('generator_factor', 1.)
        reference = (p.control in {'GFM', 'Dual'} and power > 0 and cap > 0) or (
            p.control in {'GFM', 'Dual', 'Synchronous'} and (generator_limit > 0 or hydro > 0))
        island_capable = system['topology'] in {'Off-grid', 'Islandable'} and reference
        energized = connected or island_capable
        # Non-critical load is deliberately shed only during a grid outage. An
        # always-off-grid system attempts its full ordinary load.
        target = load * p.critical_fraction if outage else load
        critical_load = load * p.critical_fraction
        start = energy
        charge = discharge = imp = exp = generation = 0.
        if energized:
            direct = min(renewables, target)
            surplus, deficit = max(0., renewables-direct), max(0., target-direct)
            charge = min(surplus, power, max(0., hi-energy)/eta)
            energy += charge*eta
            surplus -= charge
            discharge = min(deficit, power, max(0., energy-lo)*eta)
            energy -= discharge/eta
            deficit -= discharge
            if connected:
                imp = min(deficit, p.grid_import_kw * m.get('import_factor', 1.))
                deficit -= imp
                if p.export_eur_kwh >= 0:
                    exp = min(surplus, p.grid_export_kw * m.get('export_factor', 1.))
            generation = min(deficit, generator_limit)
            deficit -= generation
            served = target-deficit
            curtail = surplus-exp
        else:
            served, curtail = 0., renewables
        critical_unserved = max(0., critical_load-served)
        tariff = p.import_eur_kwh
        if m.get('negative_prices') and 10 <= hour <= 15:
            tariff = -.05
        if 17 <= hour <= 20:
            tariff *= m.get('price_factor', 1.)
        residual = renewables + generation + discharge + imp - served - charge - exp - curtail
        rows.append(dict(hour=t, label=f'D{t//24+1} {hour:02d}:00', load_kw=load,
                         target_load_kw=target, served_kw=served, critical_load_kw=critical_load,
                         pv_kw=pv, wind_kw=wind, hydro_kw=hydro, generator_kw=generation,
                         charge_kw=charge, discharge_kw=discharge, grid_import_kw=imp,
                         grid_export_kw=exp, curtailed_kw=curtail, unserved_kw=load-served,
                         critical_unserved_kw=critical_unserved, scheduled_shed_kw=load-target,
                         soc_start_kwh=start, soc_end_kwh=energy, soc_pct=100*energy/cap if cap else 0.,
                         grid_connected=connected, state='Grid connected' if connected else 'Island energized' if energized else 'De-energized',
                         import_eur_kwh=tariff,
                         variable_cost_eur=imp*tariff-exp*p.export_eur_kwh+generation*p.generator_eur_kwh,
                         balance_residual_kw=residual))
    def total(key):
        return sum(r[key] for r in rows)
    demand, critical_demand = total('load_kw'), total('critical_load_kw')
    warnings = [
        'Synthetic hourly energy screen using a fixed greedy policy, not cost optimization, a forecast or a dispatch instruction.',
        'No voltage, frequency, reactive power, fault current, protection, black-start or transfer-transient simulation.',
        'Initial battery energy is supplied explicitly. Terminal SOC is unconstrained; compare runs using both stored-energy endpoints.',
        'Variable energy cost excludes CAPEX, OPEX, demand charges, wear, fuel inventory, taxes and value of lost load. Do not annualize this run.',
        'A synthetic 24-hour resource shape repeats for longer horizons. No measured weather or probabilistic reliability claim.',
        'Battery energy provenance is not tracked; no renewable share or emissions credit is inferred from discharge.',
        'A declared GFM/reference mode is a structural teaching assumption, not proof of real island stability.',
    ]
    if system['coupling'] == 'DC':
        warnings.append('DC architecture shown conceptually; calculations are AC-equivalent. No DC-bus dynamics, shared-inverter clipping or DC cable losses.')
    if p.hydro_kw:
        warnings.append('Hydro is a fixed electrical availability proxy; water balance, head and environmental releases are excluded.')
    return dict(model='hybrid-greedy-hourly-v1', data_kind='synthetic_educational',
                system_id=p.system_id, scenario_id=p.scenario_id, duration_hours=p.hours,
                policy='renewables_then_battery_then_grid_then_backup',
                total_load_kwh=demand, served_kwh=total('served_kw'),
                unserved_kwh=total('unserved_kw'), critical_unserved_kwh=total('critical_unserved_kw'),
                critical_served_pct=100*(1-total('critical_unserved_kw')/critical_demand),
                load_served_pct=100*total('served_kw')/demand,
                renewable_available_kwh=total('pv_kw')+total('wind_kw')+total('hydro_kw'),
                grid_import_kwh=total('grid_import_kw'), grid_export_kwh=total('grid_export_kw'),
                generator_kwh=total('generator_kw'), curtailed_kwh=total('curtailed_kw'),
                charged_kwh=total('charge_kw'), discharged_kwh=total('discharge_kw'),
                initial_energy_kwh=initial, terminal_energy_kwh=energy,
                battery_energy_delta_kwh=energy-initial,
                effective_capacity_kwh=cap, effective_power_kw=power,
                variable_cost_eur=total('variable_cost_eur'),
                max_balance_residual_kw=max(abs(r['balance_residual_kw']) for r in rows),
                tags=validation['tags'], warnings=warnings, schedule=rows)
