import {createHash} from 'node:crypto';

// Only the reviewed inline scripts receive permission. No wildcard script hosts
// or unsafe-inline script execution is needed by the standalone application.
// Input is our generated HTML, never untrusted markup; this is not a sanitizer.
export function domainSecurityPolicy(pages) {
  const hashes = new Set();
  for (const html of pages) {
    for (const script of html.matchAll(/<script(?=[\t\n\f\r />])([^>]*)>([\s\S]*?)<\/script(?=[\t\n\f\r />])[^>]*>/gi)) {
      if (!/\bsrc\s*=/i.test(script[1])) {
        hashes.add(`'sha256-${createHash('sha256').update(script[2]).digest('base64')}'`);
      }
    }
  }
  const scripts = "'self' " + [...hashes].sort().join(' ');
  return `default-src 'self'; script-src ${scripts}; script-src-elem ${scripts}; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'`;
}
