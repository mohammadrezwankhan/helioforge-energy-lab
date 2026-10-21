namespace HF {
  export interface PublishedRuntimeFacts {
    applicationUrl: string;
    publicSource: string;
    sourceRevision: string;
    runtimeSha256: string;
  }
  const releaseRepository = 'https://github.com/mohammadrezwankhan/helioforge-energy-lab';
  const releaseOverview = 'https://mkgrid.co.technology/';
  let publishedFacts: PublishedRuntimeFacts | null = null;
  let releaseRequest: Promise<void> | undefined;
  let releaseStatus = 'Release identity unavailable until the publication manifest is loaded.';

  export function parsePublishedRuntimeFacts(raw: unknown, applicationUrl: string): PublishedRuntimeFacts | null {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
    const value = raw as Record<string, unknown>;
    if (value.applicationUrl !== applicationUrl || value.publicSource !== releaseRepository ||
        typeof value.sourceRevision !== 'string' || !/^[a-f0-9]{40}$/.test(value.sourceRevision) ||
        typeof value.runtimeSha256 !== 'string' || !/^[a-f0-9]{64}$/.test(value.runtimeSha256)) return null;
    return {applicationUrl, publicSource: releaseRepository, sourceRevision: value.sourceRevision, runtimeSha256: value.runtimeSha256};
  }

  export function releaseProvenanceMarkup(): string {
    const source = publishedFacts ? `${releaseRepository}/tree/${publishedFacts.sourceRevision}` : releaseRepository;
    return `<div class="release-provenance" data-release-provenance><nav aria-label="Source and methods"><a href="${releaseOverview}methodology/">Methodology</a><a href="${releaseOverview}app.json">App facts</a><a data-release-source href="${source}">Public source${publishedFacts ? ' · exact revision' : ''}</a></nav><div data-release-identity>${publishedFacts ? `<p>Source revision <code>${publishedFacts.sourceRevision}</code></p><p>Published runtime SHA-256 <code>${publishedFacts.runtimeSha256}</code></p><p>The manifest identifies the published artifact; these values do not certify its scientific conclusions.</p>` : `<p>${escapeHTML(releaseStatus)}</p>`}</div></div>`;
  }

  function updateReleaseHosts(): void {
    for (const host of document.querySelectorAll<HTMLElement>('[data-release-provenance]')) {
      const source = host.querySelector<HTMLAnchorElement>('[data-release-source]');
      if (source) {
        source.href = publishedFacts ? `${releaseRepository}/tree/${publishedFacts.sourceRevision}` : releaseRepository;
        source.textContent = `Public source${publishedFacts ? ' · exact revision' : ''}`;
      }
      const identity = host.querySelector<HTMLElement>('[data-release-identity]');
      if (identity) {
        const markup = releaseProvenanceMarkup();
        const start = markup.indexOf('<div data-release-identity>') + '<div data-release-identity>'.length;
        identity.innerHTML = markup.slice(start, markup.lastIndexOf('</div></div>'));
      }
    }
  }

  export async function refreshReleaseProvenance(): Promise<void> {
    if (!releaseRequest) {
      releaseRequest = (async () => {
        const application = new URL(location.href);
        application.hash = ''; application.search = '';
        if (application.protocol !== 'https:' || !application.pathname.endsWith('/run/')) {
          releaseStatus = 'Release identity unavailable for this local copy. Inspect the source and build records supplied with it.';
          return;
        }
        try {
          const manifest = new URL('../app.json', application);
          const response = await fetch(manifest.href, {credentials: 'omit', cache: 'no-store', signal: AbortSignal.timeout(8000)});
          if (!response.ok) throw new Error('Manifest unavailable');
          publishedFacts = parsePublishedRuntimeFacts(await response.json(), application.href);
          if (!publishedFacts) throw new Error('Manifest identity invalid');
        } catch {
          publishedFacts = null;
          releaseStatus = 'Release identity unavailable: the publication manifest could not be loaded or validated. The preview remains usable.';
        }
      })();
    }
    await releaseRequest;
    updateReleaseHosts();
  }
}
