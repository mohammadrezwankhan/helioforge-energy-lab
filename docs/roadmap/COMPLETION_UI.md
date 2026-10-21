# Completion UI implementation

`apps/web/src/completion-ui.ts` adds a DOM enhancement controller for the existing learning studio, study workbench and saved-run comparison. It exports:

```ts
HF.createCompletionController(getState: () => HF.ViewState): {
  refresh(): void;
  destroy(): void;
}
```

The controller is constructed once in `app.ts` with the live `ViewState` closure and refreshed after the study, workflow and experience controllers. Its TypeScript and stylesheet are included in both the app and standalone build. The disposer removes delegated listeners, the mutation observer and every `mountEnergyScene` loop. DOM decoration temporarily disconnects its observer to prevent feedback starvation; quiz scores persist synchronously against the submitted lesson ID.

## Behavior and evidence boundary

- Foundation lessons are open. An Applied lesson unlocks after all nine Foundation self-checks pass. An Advanced lesson unlocks after all nine Foundation and ten Applied checks pass. The existing quiz must score every question correctly. The app stores IDs and exact quiz scores in browser `localStorage`; old `hf-lessons-v2` IDs remain readable. Users can reset the existing progress or export a local record. It is editable browser state, not signed-in identity or independently verified mastery.
- The two comparison viewports choose among pinned runs and feed `mountEnergyScene` the corresponding saved architecture and schedule point. Both show a shared-time slider built from the finite hour intersection. Camera presets and pause controls are independent. Reduced motion is honored. The current hybrid result has no geographic coordinates or voltage measurements, so the UI says those contours are unavailable.
- The annual-storage tariff profile edits the existing `storage-annual` `tariff` JSON array of 24 EUR/kWh values, bounded to 0–3. Pointer dragging and keyboard editing update the actual study field and mark the old result stale through the existing study controller. “Apply profile & recalculate” submits the existing study form to the local API. The control is unavailable in disconnected preview mode, where changed values cannot be recalculated.
- Learning exports and the existing locally signed record state plainly that browser-generated evidence does not establish identity, authority, accreditation, certification or independent mastery.

## Verification

Targeted pure-logic tests are in `apps/web/tests/completion-ui.test.mjs`; run `node --test tests/completion-ui.test.mjs` from `apps/web`. They cover exact 24-value tariff bounds, tier prerequisites, saved mastery parsing and common schedule hours. `scripts/browser-completion.py` exercises the actual integrated quiz, tariff and scene workflows.

Manual browser checks for the wired app:

1. Clear browser learning progress. Confirm Foundation is open and Applied/Advanced are marked unavailable. Pass all nine Foundation quizzes with every answer correct; Applied should then unlock. Fail one answer and confirm it does not count. Repeat through all ten Applied quizzes to unlock Advanced. Confirm the 100% requirement and local-record caveat are visible.
2. Export progress and inspect the JSON for lesson IDs, exact scores, timestamps and `identity_verification: "none"`. Reset progress through the existing confirmation dialog and confirm both lesson completion and tier gates reset.
3. Pin two runs with different architectures and schedule points, open Scenario compare, and confirm two canvases show the saved architectures. Change each camera preset separately, select another pinned run, and drag the shared hour slider. Inspect the displayed point values against each run's saved `schedule`. Toggle pause and the app's reduced-motion setting; navigate away and back to confirm only two fresh canvases are mounted.
4. In Storage, select **8760-hour dispatch and tariff builder**. Drag a chart bar and edit it with keyboard focus plus arrows/Home/End. Confirm the `tariff` JSON textarea changes to 24 bounded values and the bundled result becomes stale/hidden. With the API connected, apply and confirm the returned result inputs contain that edited array; in preview mode, confirm the control reports that recalculation is unavailable.
5. Check the compare and storage views at 390px, keyboard-tab through selectors, pause/camera controls, the tariff chart and all hourly sliders. Confirm headings and live-status text remain available and no horizontal page overflow is introduced.

These UI interactions do not provide course accreditation, model certification, engineering approval or scientific validation.
