namespace HF { // eslint-disable-line @typescript-eslint/no-namespace, @typescript-eslint/no-unused-vars -- HF is the ordered global-script bundle namespace; modules change its shared runtime contract.
  /** Runtime counterpart of a required DOM/model entry, including sparse data. */
  export function requiredPresent<T>(value: T | null | undefined, context: string): T {
    if (value === null || value === undefined)
      throw new Error(`Missing required value: ${context}`);
    return value;
  }
  /** Render scalar values directly and retain structured JSON instead of losing it to [object Object]. */
  export function displayText(value: unknown): string {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint' || typeof value === 'symbol') return String(value);
    if (Array.isArray(value)) return value.map((item: unknown) => displayText(item)).join(',');
    const encoded: unknown = JSON.stringify(value);
    return typeof encoded === 'string' ? encoded : '';
  }

}
