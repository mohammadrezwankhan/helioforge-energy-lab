# Hybrid cross-browser observations (partial)

These observations are from 9 November 2026 on Windows, source commit
`e7e1f0c5373b8d35a397d6f61f016e69fcbda1d8`, Playwright 1.64.1, and a
1440 × 900 viewport. They do not establish general browser compatibility.

## Standalone preview

1. Run `node scripts/preview-demo.mjs` and open `http://127.0.0.1:4173/`
   in Firefox 157.0 or Playwright WebKit 27.2.
2. Select **Hospital islanding microgrid** and the **Four-hour outage**
   scenario. The displayed values were identical in both engines: 100.0%
   critical load served; 93.2% total load served; 970.8 kWh shortfall
   including planned shedding; 4.05 MWh imported; and 0.45 MWh terminal
   battery energy, from 1.80 MWh initial energy.
3. Neither engine produced an uncaught page error or page-level horizontal
   overflow. Firefox logged no console errors. WebKit logged 29 console
   errors in one run, including inline-style CSP refusals and a 404 for the
   preview's optional `/api/overview` request.

The **Run** control was disabled in this standalone preview. It displays
frozen bundled Python results and cannot execute an edited configuration;
therefore these observations do not complete the requested new-run workflow.

## Local API comparison

With the local Python API served at `http://127.0.0.1:8765`, its allowed
origin set to that exact origin and external AI disabled, select the same
architecture, change `solar_kw` to 777 and run. Both engines displayed
100.0% critical load served, 100.0% total load served, 7.11 MWh grid import
and 0.45 MWh terminal energy. Neither had a page error or page-level overflow.
Firefox logged no console errors; WebKit logged inline-style CSP refusals.

The same WebKit refusal also reproduced on a minimal page with only a native
`select` under `style-src 'self'` and `style-src-attr 'none'`. This points to
a browser/native-control interaction, but its visual impact was not established.
The policy was not weakened. The requested baseline
`python -m pytest apps/api/tests/test_hybrid.py` passed 328 tests locally with
one Starlette deprecation warning on commit
`0b38f449611333e52b913b62c1d48d7d85495b82`, whose preceding change was
test-only.

**Still needed:** reconcile the preview's disabled Run control with the issue's
requested edited-input run, and review the WebKit console warning and any
visual impact. This note is partial evidence, not compatibility certification.

A subsequent [preview-origin hybrid run](hybrid-preview-journey.md) uses an
explicitly enabled local hybrid bridge and records Firefox and WebKit results.
