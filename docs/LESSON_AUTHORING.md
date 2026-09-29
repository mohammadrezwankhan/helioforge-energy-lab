# Author a lesson or architecture

## Single source of truth

Edit `apps/api/helioforge/data/hybrid_catalog.json`. Each system has a stable ID, topology, coupling, control assumption, technology IDs, capability mode, preset inputs, learning focus, evidence requirements and source references. Each lesson references an existing system and applicable scenario; it supplies original objectives, steps, quiz options, one answer index per question and explanations.

The current 36 activities are short self-study lessons, not a complete accredited energy-engineering syllabus. Advanced lessons ask learners to design a model boundary and evidence plan; they do not pretend to calculate unsupported physics. Suggested activity minutes are author estimates, not measured completion times.

## Required contribution contract

1. Define a decision, units, learner prerequisites and a meaningful misconception. Make the example reproducible without proprietary data.
2. Declare `screening` only when the actual engine supports the configuration. New carrier/network/control science needs its own model, equations and independent reference case first. Otherwise use `study` and a specific evidence requirement.
3. Set unavailable electrical assets to zero. Keep battery energy/power both positive or both zero. Respect SOC ordering and reserve floors. Off-grid presets must have zero grid ratings and a valid reference assumption.
4. Choose an applicable scenario. Prefer one-change-at-a-time comparisons. Discuss demand service and initial/terminal energy before interpreting costs.
5. Write distinct distractors and exactly one intended answer per question. An explanation must teach the reason, not merely repeat the selected answer. Do not copy vendor/exam/course questions or figures.
6. Add tests for scope, applicability, import/export compatibility, conservation and grading. Run the generation script, rebuild and inspect desktop/mobile views. Include source dates and usage rights for any external data.

```bash
python scripts/generate-hybrid-assets.py
python -m pytest apps/api/tests
cd apps/web && npm run build && npm test
```

## File contracts

`helioforge.hybrid.v1` wraps all validated electrical inputs and is accepted by Import setup. A plain complete input object is also accepted. Unknown input fields are rejected; files over 100 KB are rejected in the UI.

`helioforge.lesson.v1` exports the lesson, matching experiment configuration and an educational notice. It is an export for teachers/contributors, not a runtime lesson-upload interface. To edit lessons, change the canonical JSON and rebuild.

`helioforge.progress.v1` exports passed self-check IDs. Progress uses local browser storage when available; it is not a verified credential or a teacher's authenticated gradebook. Comparison runs are in-memory session state and can be exported as `helioforge.comparison.v1`; they are not automatically restored after reload.

## Definition of done

The learner can state the assumption, execute the supported experiment (or identify the needed advanced model), explain the result, identify what was not modeled and produce a reproducible evidence file. A new attractive card alone is not a finished lesson.
