"""Synthetic portfolio and official-source registry. No live regulatory claims."""
MARKETS = [
    {"code": "FR", "name": "France", "regulator": "CRE", "url": "https://www.cre.fr/",
     "segment": "Industrial campuses", "hypothesis": "Increase solar self-use and test time-of-use exposure."},
    {"code": "DE", "name": "Germany", "regulator": "Bundesnetzagentur", "url": "https://www.bundesnetzagentur.de/EN/Home/home_node.html",
     "segment": "Energy-intensive industry", "hypothesis": "Compare load management with the actual site network tariff."},
    {"code": "ES", "name": "Spain", "regulator": "CNMC", "url": "https://www.cnmc.es/",
     "segment": "Solar-rich commercial sites", "hypothesis": "Shift on-site PV generation into evening consumption."},
    {"code": "IT", "name": "Italy", "regulator": "ARERA", "url": "https://www.arera.it/en/",
     "segment": "Manufacturing clusters", "hypothesis": "Evaluate procurement savings alongside resilience requirements."},
    {"code": "NL", "name": "Netherlands", "regulator": "ACM", "url": "https://www.acm.nl/en",
     "segment": "Logistics and distribution", "hypothesis": "Test storage against site connection constraints and loading patterns."},
    {"code": "GB", "name": "Great Britain", "regulator": "Ofgem", "url": "https://www.ofgem.gov.uk/",
     "segment": "Commercial portfolios", "hypothesis": "Compare flexible tariffs and aggregator proposals using actual contracts."},
]
for market in MARKETS:
    market.update({"status": "needs_review", "effective_date": None, "reviewed_on": None,
                   "currency": "EUR", "tariff_basis": "illustrative", "connector_status": "source_link_only"})

SOURCES = [
    {"id": "entsoe", "name": "ENTSO-E Transparency Platform", "url": "https://www.entsoe.eu/data/transparency-platform/",
     "scope": "Electricity fundamentals and transparency data", "status": "not_connected"},
    {"id": "pvgis", "name": "European Commission · PVGIS", "url": "https://re.jrc.ec.europa.eu/pvg_tools/en/",
     "scope": "Site-specific PV yield inputs", "status": "not_connected"},
    {"id": "acer", "name": "ACER Monitoring Reports", "url": "https://www.acer.europa.eu/monitoring/MMR",
     "scope": "European market monitoring publications", "status": "source_link_only"},
]

# Every name and quantity here is an original, fictional demonstration record.
PROJECTS = [
    {"id": "HF-101", "name": "Solstice industrial", "market": "FR", "technology": "PV + BESS", "stage": "Due diligence", "pv_mwp": 68, "bess_mwh": 24, "capex_meur": 54.1, "progress": 74},
    {"id": "HF-102", "name": "Nordlicht campus", "market": "DE", "technology": "BESS", "stage": "Feasibility", "pv_mwp": 0, "bess_mwh": 40, "capex_meur": 15.6, "progress": 48},
    {"id": "HF-103", "name": "Aurora solar", "market": "ES", "technology": "PV", "stage": "Design review", "pv_mwp": 125, "bess_mwh": 0, "capex_meur": 73.8, "progress": 86},
    {"id": "HF-104", "name": "Vento repower", "market": "IT", "technology": "Wind", "stage": "M&A screening", "pv_mwp": 0, "wind_mw": 54, "bess_mwh": 0, "capex_meur": 67.4, "progress": 32},
    {"id": "HF-105", "name": "Delta logistics", "market": "NL", "technology": "PV + BESS", "stage": "Pilot", "pv_mwp": 12, "bess_mwh": 10, "capex_meur": 10.3, "progress": 63},
    {"id": "HF-106", "name": "Meridian works", "market": "GB", "technology": "PV + BESS", "stage": "Feasibility", "pv_mwp": 32, "bess_mwh": 16, "capex_meur": 28.7, "progress": 41},
]

PILOTS = [
    {"id": "P-01", "title": "Thermal signature study", "pillar": "Reliability", "status": "running", "site": "Solstice industrial", "instrument": "Cell temperature · Modbus gateway", "owner": "Reliability team", "evidence_note": "Synthetic record: baseline logging configured; no real asset connection.", "target": "Reduce false fault alerts"},
    {"id": "P-02", "title": "Low-impact foundations", "pillar": "Construction", "status": "instrumenting", "site": "Aurora solar", "instrument": "Load cell · displacement probe", "owner": "Civil engineering", "evidence_note": "Synthetic record: instrument installation checklist pending.", "target": "Compare ground disturbance"},
    {"id": "P-03", "title": "Habitat baseline survey", "pillar": "Sustainability", "status": "planned", "site": "Delta logistics", "instrument": "Transect protocol · field observations", "owner": "Ecology team", "evidence_note": "Synthetic record: ecological baseline survey has not been completed.", "target": "Establish an ecological baseline"},
    {"id": "P-04", "title": "Adaptive load envelope", "pillar": "Efficiency", "status": "validated", "site": "Meridian works", "instrument": "Revenue meter · synthetic load profile", "owner": "Energy systems", "evidence_note": "Synthetic record: validation describes a simulated test only.", "target": "Validate a peak-demand hypothesis"},
]
