# Do Not Feed the Cargo — Master Game Design Document

**Status:** Baseline of approved design GDD-001—100. **Genre:** first-person physics-driven solo/1–4 co-op cargo delivery, emergent systemic comedy/horror. **Revision:** 1.0 (2026-10-18).

> Normative authority: [Approved Decision Register](DECISIONS-001-100.md). Any number, technical choice, content item, or workflow not expressly in that register or in approved user discussions is a **production proposal**, not an additional approved GDD fact.

## High concept

Players inherit the grandfather's indebted delivery company, its decrepit permanent garage, and a closed cargo van. They negotiate contracts to find, safely capture, contain, care for and transport unusual living creatures across generated road networks. The hold is a traversable physical space, not a non-interactive inventory. Cargo can shift, break restraints, escape, injure people and alter the journey. Players take risks, rescue one another, repair vehicles, negotiate with NPCs and build a company that continues after a branching story conclusion.

**Player promise:** "Get the cargo there, by any physically possible means; survive consequences you can understand." Co-op misadventures are systemic rather than arbitrary cutscenes.

## Pillars and constraints

1. **Physical causality and agency** — two physical hands, real objects, active Ragdoll, inertia in vehicles, material/condition-dependent failures. Convenient controls do not grant teleportation, omniscience or script immunity (GDD-049—059, 063).
2. **Living cargo** — autonomous species instincts, emotions/needs, mutual compatibility, injuries, death, physical enclosure and care, no guaranteed safety (017—024, 083).
3. **Dangerous logistics** — a configurable closed van with cabin, door to hold, rear doors and side slider, multiple purchased/rented models, several vans for major contracts, damage and recovery (025—031, 058—074).
4. **Causal living world** — generated roads and biomes, NPCs with memory, real information propagation, investigations and factions, route discovery, optional events and player choice (001—006, 035—048, 064—071).
5. **Company without dead ends** — debts, insurance, legal/black-market contracts, warehouse and staff automation, modular garage, crafting and research; failures are meaningful but recoverable (012—016, 072—091).
6. **Readable low-poly cozy horror** — distinctive stylized look, warm safe hub vs. eerie nights, spatial sound, diegetic instruments, optional onboarding and accessible overlays (093—098).

## Primary loops

**Expedition:** investigate/select contracts → gather available intelligence → price/deadline/advance negotiation → inspect vehicle and collect equipment → physically load and secure cages/creatures → navigate an accessible generated network → react to road/weather/NPC/creature incidents → deliver and settle → repair, improve and prepare again.

**Company:** track financial obligations → receive physical supplies, inspect defects → warehouse/plan use → hire and schedule qualified support staff → fabricate, test, recycle and maintain → expand garage and fleet → pursue story/faction goals.

**Research:** observe properties → find/buy schematics → reverse-engineer or experiment → physically assemble prototype → instrumented tests → adjust drawing → field use → investigate failures; passing a test never proves absolute safety.

## Session/world model

- 1–4 players with solo support; join during expeditions. Leaving removes character but leaves shared cargo. Host departure saves and ends session; same host resumes.
- Garage persists. Each trip generates a new map (roads/biomes/POIs), while NPC histories, consequences, company state and relevant creature stories persist as abstract world records.
- No simulation progress while session is offline. During active sessions garage staff and remote incidents progress; time-skip by group consent, serious events interrupt.
- Contract targets 15–30, 35–60, 60–120 minutes. Duration is a design target, not forced countdown; urgent contracts may have deadlines.
- Travel by closed freight vans; usual expedition single van, major expeditions may deploy several at once. Every basic gameplay action must remain possible solo without a mandatory second player.

## World, navigation and law

- Major roads/destination visible early, side roads and POIs discovered through clues/exploration. Map is physical paper/device; no map hotkey revealing undiscovered content; optional GPS may be inaccurate/stale.
- Players may leave roads or split up on foot, constrained by terrain physics, load, physical communication range and real risk.
- Ordinary traffic runs basic driving AI; important NPC drivers, traders, faction actors and competitors have persistent goals/assets/memories.
- Crashes create real blockages and injured NPCs, cargo loss, creatures at large; responders must learn of and reach accidents.
- Police enforcement, searches and pursuits rely on witnesses, proof, radio propagation and physically available patrols. Arrest and confiscation lead to playable recovery routes, not terminal Game Over.
- Documents, regional permits and smuggling are physical and can be falsified; detection comes from actual inspection and accumulated evidence.

## Creature roster

Approved starting species: **Клёцка** (mass can increase with feeding/stress), **Дрёмник** (sleep-inducing spores; dislikes light), **Мыльник** (slime/slipperiness), **Складень** (mimics cargo items), **Искряк** (electrical hazard), **Печник** (heat), **Корешок** (roots/entanglement). See [Content Bible](03-CONTENT-BIBLE.md). Specific numerical tuning and visual silhouettes are implementation work, not approved.

## Progression and narrative

- Core progression is company, fleet, tools and technology. Players develop soft proficiencies without hard classes or blocking basic actions (092).
- Story about inheritance, debts and grandfather's secret is non-linear, faction-driven and branches into multiple endings. The established company survives the conclusion (093).
- Difficulty is systemic, not level-scaled revenge. Event pacing adapts within causal world logic. Recoverability after insolvency, confiscation or stranding remains essential (094).

## Alpha scope and acceptance

**First full playable milestone = large alpha**, **not** the small vertical slice proposal the user explicitly declined (099). It must include seven species, several closed vans, developed garage, autonomous NPCs, economic systems, physical manufacturing, multiple regions and the full 1–4 player core loop. Internal technical prototypes before this milestone are required engineering checkpoints but are *not* a renamed or reduced first-alpha scope.

**Alpha acceptance:** fresh solo and 4-player sessions can execute and resume a complete physical contract loop; vehicle/creature/network/save invariants hold; systems represented by GDD-099 are demonstrably integrated, not mocked marketing claims; losses can be recovered; failed tests block release. See [Production & QA](06-PRODUCTION-QA.md).

## Change control

GDD-100 freezes **approved player-facing intent**, not all code designs. Agents can decide implementation details compatible with rules, but must flag any changed meaning, scope reduction, or new game system as `PROPOSED / REQUIRES APPROVAL`. New suggestions remain in separate backlog until user approves.
