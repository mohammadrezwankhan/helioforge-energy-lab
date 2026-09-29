namespace HF {
  export type MarketCode = 'FR' | 'DE' | 'ES' | 'IT' | 'NL' | 'GB';
  export type Page = 'hybrid' | 'lessons' | 'compare' | 'overview' | 'storage' | 'pv' | 'research' | 'markets' | 'forecast' | 'investment' | 'pilots' | 'council';
  export type Inputs = Record<string, string | number | boolean | null | number[]>;
  export interface BaseResult { model: string; warnings: string[]; run_id?: string; created_at?: string; input_sha256?: string }
  export interface DispatchPoint { hour: number; label: string; load_kw: number; pv_kw: number; charge_kw: number; discharge_kw: number; grid_import_kw: number; grid_export_kw: number; curtailed_kw: number; soc_start_kwh: number; soc_end_kwh: number; soc_pct: number; import_eur_mwh: number }
  export interface Dispatch extends BaseResult { data_kind: string; market: MarketCode; duration_hours: number; capacity_kwh: number; power_kw: number; baseline_cost_eur: number; optimized_cost_eur: number; savings_eur: number; savings_pct: number | null; energy_savings_eur: number; peak_savings_eur: number; wear_cost_eur: number; baseline_peak_kw: number; optimized_peak_kw: number; discharged_kwh: number; equivalent_discharge_cycles: number; terminal_soc_kwh: number; solver: string; solver_status: string; schedule: DispatchPoint[] }
  export interface FinanceRow { year: number; gross_margin_eur: number; opex_eur: number; augmentation_eur: number; cfads_eur: number; debt_service_eur: number; interest_eur: number; debt_balance_eur: number; equity_cashflow_eur: number; dscr: number | null; cumulative_eur: number; contracted_fraction: number }
  export interface Finance extends BaseResult { npv_eur: number; irr_pct: number | null; payback_years: number | null; minimum_dscr: number | null; dscr_covenant: number; covenant_pass: boolean | null; level_payment_debt_capacity_eur: number; capex_eur: number; rows: FinanceRow[] }
  export interface PV extends BaseResult { capex_eur: number; lcoe_eur_mwh: number; npv_eur: number; first_year_generation_mwh: number; panel_count: number; indicative_land_ha: number; capture_price_eur_mwh: number; rows: { year: number; generation_mwh: number; cashflow_eur: number; replacement_eur: number }[] }
  export interface Acquisition extends BaseResult { ev_ebitda: number; implied_equity_value_eur: number; screening_dcf_eur: number; valuation_gap_eur: number; unlevered_irr_pct: number | null }
  export interface Forecast extends BaseResult { market: MarketCode; seed: number; paths: number; data_kind: string; rows: { year: number; p10_eur_mwh: number; p50_eur_mwh: number; p90_eur_mwh: number; negative_price_probability: number }[] }
  export interface Drift extends BaseResult { baseline_fraction: number; sigma_fraction: number; drift_pct: number; alert_count: number; alert_indices: number[]; series: { index: number; residual_pct: number; z_score: number }[] }
  export interface Reliability extends BaseResult { survival_pct: number; conditional_failure_pct: number; conditional_median_remaining_hours: number }
  export interface Sustainability extends BaseResult { lifetime_generation_mwh: number; intensity_gco2e_kwh: number; net_counterfactual_avoided_tco2e: number; project_lifecycle_tco2e: number }
  export interface Market { code: MarketCode; name: string; regulator: string; url: string; segment: string; hypothesis: string; status: string; effective_date: string | null; reviewed_on: string | null; currency: string; tariff_basis: string; connector_status: string }
  export interface Source { id: string; name: string; url: string; scope: string; status: string }
  export interface Project { id: string; name: string; market: MarketCode; technology: string; stage: string; pv_mwp: number; wind_mw?: number; bess_mwh: number; capex_meur: number; progress: number }
  export interface Pilot { id: string; title: string; pillar: string; status: 'planned' | 'instrumenting' | 'running' | 'validated'; site: string; instrument: string; owner: string; evidence_note: string; target: string; updated_at?: string }
  export interface Review { agent: string; summary: string; risks: string[]; required_evidence: string[] }
  export interface Council { hybrid_run_id?: string | null; mode: 'local' | 'openai'; execution: string; model?: string; market: MarketCode; reviewed_brief: string; reviews: Review[]; decision: { recommendation: string; unresolved_risks: string[]; next_actions: string[] }; warnings: string[]; run_id?: string }
  export interface RunRecord { id: string; kind: string; created_at: string; input_hash: string }
  export interface Dashboard {
    version: string; data_kind: string; as_of: string; market: MarketCode; portfolio: Project[]; markets: Market[]; sources: Source[]; pilots: Pilot[];
    dispatch: Dispatch; finance: Finance; pv: PV; acquisition: Acquisition; forecast: Forecast; drift: Drift; reliability: Reliability; sustainability: Sustainability; council: Council;
    defaults: { storage: Inputs; finance: Inputs; pv: Inputs; forecast: Inputs; acquisition: Inputs; reliability: Inputs; sustainability: Inputs };
    professional_context: { user_reported_pv_pipeline_gwp: string; as_of: string; note: string };
  }
  export interface ViewState { champion?: ChampionState; hybrid: HybridState; page: Page; connected: boolean; busy: boolean; data: Dashboard; marketFilter: string; search: string; chartMode: 'dispatch' | 'prices'; forecastYears: number; runs: RunRecord[]; motionOff: boolean }
  export interface Series { name: string; values: number[]; color: string; dashed?: boolean; area?: boolean }
}
