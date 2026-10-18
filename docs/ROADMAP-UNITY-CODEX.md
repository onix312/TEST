# Do Not Feed the Cargo — Roadmap for Unity + Codex

**2026-10-18 baseline.** **Approved alpha scope** = GDD-099 (large alpha). **Approved workflow** = GDD-100 (tracked phased implementation, tests, separate authorization for substantive GDD changes).

## Planning rules

1. This is the **first full playable alpha** and must contain: all seven creatures; several enclosed vans; developed modular garage; autonomous important NPCs; economy, contracts, physical fabrication and multiple generated regions; 1–4-player co-op.
2. Work below is broken into internal deliverables for risk control. Early intermediate builds **do not constitute a smaller substitute alpha**.
3. Specific libraries/versions/metrics are **implementation proposals**, not new approved design decisions.
4. Every auto-generated task references GDD IDs, clearly bounded work and its blocking dependencies; a human starts execution, inspects results and runs Unity QA.
5. Parallelism only after ownership of scene/prefab/code modules is separated. Never integrate a state-schema change without migration and restoration tests.

## First milestones

| Stage | Outcome | Blocking proof |
|---|---|---|
| P0 — Foundations | Unity project, build settings, test runner, save schema, deterministic IDs, logging | headless compile, EditMode smoke, restore from backup |
| P1 — Character physics | first-person controller, physical hands/grabbing, full head-follow Ragdoll, contextual vault | 1/2/4 player touch/transfer and crash-recovery tests |
| P2 — Van dynamics | drivable enclosed van, walkable hold, automatic gearbox, cargo/seat inertia, straps, damage | network load/cargo test, emergency tow/repair |
| P3 — Creatures | all seven distinct species with state, sensory cues, care, capture, dynamic containment | seven species-specific behavior tests; injury/escape |
| P4 — World + net | roads, POIs, multiple regions/biomes, on-/off-road, seamless session join, persistent histories | road graph reachability; reconnection and host save |
| P5 — Contract loop | negotiation, pickup, physical delivery, payment/penalty, day/weather, events | repeatable solo and 4-player complete trip |
| P6 — Garage + economy | fleet/rent/insurance/debt, garage/warehouse, staff/physical suppliers, research and fabrication | no magical inventory; no offline advance; recovery |
| P7 — Society + narrative | significant NPCs, legal evidence and policing, witness communication, branching story framework | causality traces and recoverable arrest/confiscation |
| P8 — Big alpha | multi-region, several vans, seven creatures, robust loops, sound, UX, Windows build | regression matrix and human playtests signed off |

## Acceptance of the actual big alpha

Demonstrate on real Unity Windows build: fresh and resumed solo/1–4 co-op sessions; multiple distinct biome road networks; each species exercising approved unique mechanic; several enclosed vans including interior and damage; physical cargo handoff between moving vehicles as feasible physics; functioning modular garage, qualified staff, physical inventory, real supplies and fabrication; legal/illegal contracts and recovery paths; accessible onboarding, first-person camera and spatial audio; no game-breaking save corruption; no artificial offline progression. Assertions about performance must be measured and documented.

## Automated development workflow (office application)

- **Step 1:** connect a valid existing Unity project in settings.
- **Step 2:** click **Do Not Feed the Cargo → GDD + очередь** in GDD tab. Bundled docs are copied safely to the target project's `.ai-office/gdd` as approved baseline only when no different approved document exists; existing nonmatching GDD causes a stop (not overwrite).
- **Step 3:** auto-generated task DAG is created **paused by default** and categorized by phase. No Codex run is launched.
- **Step 4:** press **DFTC → открыть следующий этап** to unpause only the first unfinished phase (P0–P8). The next phase stays locked until all previous-phase tasks are merged after human QA. This does **not** start Codex.
- **Step 5:** inspect tasks, run the existing orchestra manually; jobs use isolated snapshots, dependencies, checkpoints and conflict checks. Codex is not permitted to auto-apply DFTC work into the main Unity project.
- **Step 6:** execute Unity EditMode/PlayMode and game build locally from the Unity tab; XML reports must contain at least one passing test and zero failures; do not represent successful Codex exit as confirmed Unity behavior.
- **Step 7:** approve and merge tested code deliberately; failed checks stay pending; restore checkpoint when required.

**Local infrastructure:** GameDev AI Office depends on Python + PySide6 for source mode, independent OpenAI API only if API model routes are selected. Codex CLI and Unity Editor must be installed, logged in and configured on the user's machine. Existing ChatGPT conversation does not stream automatically into local app.

## Task generation policy

The office seed plan is a set of **bounded Codex-oriented scaffolding tasks**, not an automatically executing comprehensive coding agent. It intentionally does not auto-create credits, external accounts, Unity licenses, bank transactions or public releases. Work beyond the seed DAG should be created from each milestone after review of actual code and tests.

## QA / triage

**Blocker:** corrupted saves, reproducible physics desync, unauthorized changes to approved rules, irreversible data loss, false-positive successful QA. **High:** solo dead-end, invisible cargo, inconsistent staff budgets or fake progress. **Normal:** cosmetic polish and tuning. Merge policy: protected working baseline, never auto-merge PR into main. See [Production & QA](gdd/06-PRODUCTION-QA.md).
