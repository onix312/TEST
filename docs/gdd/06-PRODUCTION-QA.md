# Do Not Feed the Cargo — Production, QA & Change Control

**State:** approved GDD baseline + **proposed engineering process**. The large alpha defined in GDD-099 is the first planned complete playable release target. Intermediate smoke builds exist to reduce risk and are not a substitute for the alpha scope.

## Source of truth

- [Register of 100 approved decisions](DECISIONS-001-100.md) is normative.
- [Master GDD](01-MASTER-GDD.md), [System Design](02-SYSTEM-DESIGN.md), [Content Bible](03-CONTENT-BIBLE.md), [Narrative](04-WORLD-NARRATIVE.md), [Balance & UX](05-BALANCE-UX.md) interpret the register; conflicting details are flagged, not silently reapproved.
- [Roadmap](../ROADMAP-UNITY-CODEX.md) schedules engineering work.
- Separate **PROPOSALS** and **CHANGE REQUESTS** track anything beyond approved decisions; no AI agent may mark new design choices approved.

## Project architecture and tooling (proposed)

- Unity C# with locked Unity Editor version, packages and Windows build target. Exact engine version/package pins documented in target game repo when created.
- GameDev AI Office (this repository) is a **local Windows orchestration application, not the Unity game**.
- Codex workers modify only isolated workspace copies of `Assets/`, `Packages/`, `ProjectSettings/`; Git auto-commits/push and destructive modifications are not authorized as part of worker prompts.
- ChatGPT/API text agents propose plans and reports but cannot approve GDD or claim compilation or tested performance.
- Unity Bridge runs build/EditMode/PlayMode operations only in a correctly configured local Unity installation, not implicitly on CI.
- Before applying Codex edits: compare workspace vs source hashes, detect conflicts, checkpoint Unity folders, block unresolved deletions and merge into live game only under permitted policy.
- Windows packaging of the *office tool* is a separate product from Unity game builds.

## Engineering phase gates

| Gate | Main outcome | Automated evidence before next gate |
|---|---|---|
| P0 | repository/toolchain, design import, task DAG, CI | docs verified, Python tests, startup/offscreen smoke |
| P1 | authoritative player physics, two hands and Ragdoll | repeatable grab/contact/ragdoll tests, network simulation |
| P2 | closed van, cargo hold and vehicle sub-systems | payload stability, inertia and door/seat tests |
| P3 | seven distinct creatures and physical enclosures | species unit tests, perception, care, containment |
| P4 | generated roads, biomes, NPC routing, 1–4 join/leave | connectivity, save/resume, travel/reconnect |
| P5 | contracts, money, persistent garage and multi-van | contract completion, ownership/damage persistence |
| P6 | economy, staff, warehouse, research, production | stock auditing, staff budgets, crafting/test edge cases |
| P7 | law, police, insurance, evidence and narrative skeleton | communication-causality, loss/recovery, regression |
| P8 | large alpha integration, content, accessibility and polish | 1–4 player journeys, crash/restore, performance profile |

**Policy:** P0–P8 are planning stages, **not** permission to delay or eliminate agreed alpha features. Workstreams can overlap safely once interfaces are frozen, but integration and QA gates cannot be skipped.

## Definition of Done for a task

Each task includes GDD ID references, implementation slice, allowed files/modules, dependent tasks, tests to run, game-visible acceptance criteria and regressions to monitor. Completion requires code produced, review evidence, relevant build/test results, no unresolved blocker, migration plan for modified saves, and documented limitations. "Agent exited" is not the same as "done".

## Test tiers

**Fast:** Python orchestration and GDD integrity validation; C# compilation and EditMode unit tests; state serialization and deterministic generation tests.

**Scenario:** Unity PlayMode physical interactions and creature behaviors; network 1/2/4 clients with packet loss, reconnect, ragdoll and multi-vehicle cargo moves; partial failure while saving; player exits; checked exception paths.

**Full run:** garage → pickup → physical capture/load → road incidents → delivery → paid settlement → return → company progression → save/load, including a 60–120-minute scenario; world knowledge propagation and legal responses verified by traces.

**Content:** all seven species have unique functioning mechanics, several vans and regions are testable, no locked solo-required co-op step.

**Performance:** frame time, physics step stability, bandwidth, object counts, long-running heap and file footprint across realistic computers. Targets chosen from actual Unity platform tests, not invented GDD facts.

## Safety and data integrity

Never discard a working save without backup. Validate save schema and retention; use atomic writes and test rollback. Respect workspace isolation and skip unresolved conflicts. No installations, money transactions, automated outbound messages or deleting user data without explicit authorization. Credentials are never placed in repo files. No automated PR merge to `main`.

## CI and release signals

Office: Linux/Python unit and pure-code smoke; Windows Qt-offscreen smoke; Windows packaging workflow; smoke check game-doc manifest. Game: separate Unity build/test workflow once a Unity project is linked and licenses/toolchain available. Failure at any stage must be observable with logs, not optimistic UI progress.

## Risks and mitigations

1. **Physics + network:** moving van with awake ragdolls/creatures; prototype authoritative state before scale.
2. **100 systems together:** strict dependencies, controlled parallel tasks, isolated workspaces and domain-boundary tests.
3. **NPC economy simulation:** simulation LOD for non-present regions, no offline progression.
4. **Huge first alpha:** many internal staged smoke builds; no quiet scope reduction.
5. **Narrative undefined details:** maintain pending proposals and do not pretend faction names/endings exist.
6. **User-facing Windows app:** tests in CI do not prove performance on the actual target Windows + Unity installation.

## Change request template

`CR-ID | GDD refs | reason | before | after | player-facing impact | technical impact | tests | approval (pending/approved/rejected)`.

An AI can draft a CR but cannot approve it. Any gameplay change to GDD-001–100 waits for explicit user decision before merge.
