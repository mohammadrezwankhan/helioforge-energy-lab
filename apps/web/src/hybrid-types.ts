namespace HF {
  export interface HybridInputs {
    system_id:string; scenario_id:string; hours:number; control:'GFL'|'GFM'|'Dual'|'Synchronous';
    solar_kw:number; wind_kw:number; hydro_kw:number; generator_kw:number; battery_kwh:number; battery_kw:number;
    load_kw:number; grid_import_kw:number; grid_export_kw:number; critical_fraction:number;
    initial_soc:number; min_soc:number; max_soc:number; round_trip_efficiency:number;
    import_eur_kwh:number; export_eur_kwh:number; generator_eur_kwh:number;
  }
  export interface HybridTechnology {id:string;name:string;icon:string;color:string;boundary:string}
  export interface HybridSystem {
    id:string;name:string;family:string;topology:string;coupling:string;control:HybridInputs['control'];
    technologies:string[];description:string;learning_focus:string;evidence:string;
    mode:'screening'|'study';level:string;preset:HybridInputs;source_ids:string[];
  }
  export interface HybridScenario {id:string;name:string;category:string;modifiers:Record<string,number|boolean>;description:string;mode:'screening'|'study'}
  export interface Lesson {id:string;system_id:string;title:string;level:string;minutes:number;objectives:string[];steps:{title:string;body:string}[];scenario_id:string;quiz:{question:string;options:string[];answer:number;explanation:string}[];source_ids:string[]}
  export interface HybridCatalogue {version:string;data_kind:string;coverage_statement:string;sources:{id:string;name:string;url:string;reviewed_on:string;scope:string}[];technologies:HybridTechnology[];systems:HybridSystem[];scenarios:HybridScenario[];lessons:Lesson[]}
  export interface HybridTag {label:string;reason:string}
  export interface HybridPoint {
    hour:number;label:string;load_kw:number;target_load_kw:number;served_kw:number;critical_load_kw:number;
    pv_kw:number;wind_kw:number;hydro_kw:number;generator_kw:number;charge_kw:number;discharge_kw:number;
    grid_import_kw:number;grid_export_kw:number;curtailed_kw:number;unserved_kw:number;critical_unserved_kw:number;
    scheduled_shed_kw:number;soc_start_kwh:number;soc_end_kwh:number;soc_pct:number;
    grid_connected:boolean;state:string;import_eur_kwh:number;variable_cost_eur:number;balance_residual_kw:number;
  }
  export interface HybridResult extends BaseResult {
    data_kind:string;system_id:string;scenario_id:string;duration_hours:number;policy:string;
    total_load_kwh:number;served_kwh:number;unserved_kwh:number;critical_unserved_kwh:number;
    critical_served_pct:number;load_served_pct:number;renewable_available_kwh:number;
    grid_import_kwh:number;grid_export_kwh:number;generator_kwh:number;curtailed_kwh:number;
    charged_kwh:number;discharged_kwh:number;initial_energy_kwh:number;terminal_energy_kwh:number;
    battery_energy_delta_kwh:number;effective_capacity_kwh:number;effective_power_kw:number;
    variable_cost_eur:number;max_balance_residual_kw:number;tags:HybridTag[];schedule:HybridPoint[];
  }
  export interface ComparedRun {id:string;name:string;inputs:HybridInputs;result:HybridResult}
  export interface HybridState {
    inputs:HybridInputs; result:HybridResult|null; resultInputs:HybridInputs|null; search:string;family:string;topology:string;
    lessonId:string;progress:string[];quizResult:{passed:boolean;correct:number;total:number}|null;
    objectId:string;hour:number;compare:ComparedRun[];busy:boolean;
    inputError:string|null; draft:Record<string,string>|null;
  }
}
