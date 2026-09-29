namespace HF {
  export const escapeHTML = (value: unknown): string => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c] ?? c));
  export const fmt = (value: number | null | undefined, digits = 0): string => value == null || !Number.isFinite(value) ? '—' : new Intl.NumberFormat('en-GB', {maximumFractionDigits: digits, minimumFractionDigits: digits}).format(value);
  export const money = (value: number, digits = 0): string => `${value < 0 ? '−' : ''}€${fmt(Math.abs(value), digits)}`;
  export const millions = (value: number): string => `${value < 0 ? '−' : ''}€${fmt(Math.abs(value)/1e6, 2)}m`;
  export const safeURL = (value: string): string => { try { const u = new URL(value); return u.protocol === 'https:' ? escapeHTML(u.href) : '#'; } catch { return '#'; } };
  export const clamp = (v: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, v));
  export function filterProjects(projects: Project[], market: string, search: string): Project[] {
    const q = search.toLowerCase().trim();
    return projects.filter(p => (market === 'ALL' || p.market === market) && `${p.name} ${p.market} ${p.technology} ${p.stage}`.toLowerCase().includes(q));
  }
  export function finiteInput(value: FormDataEntryValue | null, label: string): number {
    if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} is required.`);
    const n = Number(value);
    if (!Number.isFinite(n)) throw new Error(`${label} must be a finite number.`);
    return n;
  }
  export function csvCell(value: unknown): string {
    let text = String(value ?? '');
    // Formula-injection defence for text values. Numeric values remain numeric.
    if (typeof value !== 'number' && /^[=+\-@\t\r]/.test(text)) text = `'${text}`;
    return `"${text.replace(/"/g, '""')}"`;
  }
  export function toCSV(rows: Record<string, unknown>[]): string {
    const keys = Object.keys(rows[0] ?? {});
    return [keys.map(csvCell).join(','), ...rows.map(r => keys.map(k => csvCell(r[k])).join(','))].join('\r\n');
  }
  export function download(name: string, content: string, mime = 'application/json'): void {
    const url = URL.createObjectURL(new Blob([content], {type: mime}));
    const a = document.createElement('a'); a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  export const PAGES: {id: Page; title: string; icon: string; group: string; subtitle: string}[] = [
    {id:'hybrid',title:'Hybrid systems lab',icon:'layers',group:'EXPLORE & LEARN',subtitle:'Explore architectures. Stress scenarios. Follow the energy.'},
    {id:'lessons',title:'Learning studio',icon:'document',group:'',subtitle:'Thirty-six architecture lessons. One evidence-led learning path.'},
    {id:'compare',title:'Scenario compare',icon:'activity',group:'',subtitle:'Compare outcomes without hiding differences in the assumptions.'},
    {id:'overview', title:'Command centre', icon:'grid', group:'WORKSPACE', subtitle:'From research to better energy decisions.'},
    {id:'storage', title:'Storage & flexibility', icon:'battery', group:'', subtitle:'Make every kilowatt-hour work harder.'},
    {id:'pv', title:'PV economics', icon:'sun', group:'', subtitle:'From generation assumptions to discounted value.'},
    {id:'research', title:'Research pillars', icon:'atom', group:'INTELLIGENCE', subtitle:'Four disciplines. One evidence-led programme.'},
    {id:'markets', title:'Market intelligence', icon:'globe', group:'', subtitle:'European opportunities, with evidence before conviction.'},
    {id:'forecast', title:'Forecast studio', icon:'chart', group:'', subtitle:'Explore futures. Never confuse scenarios with certainty.'},
    {id:'investment', title:'Investment desk', icon:'briefcase', group:'', subtitle:'Challenge the return. Understand the downside.'},
    {id:'pilots', title:'Construction & pilots', icon:'layers', group:'EXECUTION', subtitle:'Take hypotheses into the field.'},
    {id:'council', title:'Agent council', icon:'sparkles', group:'', subtitle:'Specialist perspectives. Independent challenge. Human decisions.'}
  ];
}
