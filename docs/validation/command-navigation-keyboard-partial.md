# Command palette and mobile navigation: keyboard observations (partial)

On 9 November 2026, an automated keyboard-only walkthrough used Chromium
151.0.7922.34 on Windows and the standalone preview started with
`node scripts/preview-demo.mjs` at `http://127.0.0.1:4173/`. The exercised
application source was commit `e7e1f0c5373b8d35a397d6f61f016e69fcbda1d8`.

At 1440 × 900, Tab reached **Find anything Ctrl K: commands and
architectures**. Enter opened the dialog named **Find anything** and focused
the expanded **Search commands** combobox. The accessibility tree showed a
**Commands** listbox and a selected option. Escape closed the dialog and
returned focus to its trigger. Opening with Ctrl+K from the document body
focused the same combobox; Escape returned focus to the body.

At 390 × 900, Tab reached **Toggle navigation**. Enter opened navigation,
set `aria-expanded` to true, made the main region inert and focused the
current **Hybrid systems lab** navigation item. Escape closed the menu, set
`aria-expanded` to false and returned focus to **Toggle navigation**.

**Still needed:** repeat this path with a human screen-reader user and record
the browser and assistive technology versions, spoken names and current states,
focus entry and return, and any status or error announcements. No screen
reader or spoken output was observed in this automated pass. This is not a
whole-app accessibility certification.
