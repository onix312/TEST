# Do Not Feed the Cargo — Content Bible

**Scope:** approved species and content families; visual and numerical implementations are subject to iteration while maintaining GDD decisions. See [register](DECISIONS-001-100.md).

## Seven approved creatures

| Creature | Confirmed identity | Confirmed gameplay properties | Potential test scenarios (production proposals) |
|---|---|---|---|
| **Клёцка** | Mass-sensitive living cargo | Becomes heavier due to feeding or stress | Weight rise disturbs balance, carrying and straps |
| **Дрёмник** | Sleep-spore organism | Spreads sleep-inducing spores; light-averse | Ventilation failure in cargo hold or garage |
| **Мыльник** | Slippery organism | Produces slime, makes surfaces slippery | Braking and container grip with slick cargo |
| **Складень** | Object mimic | Camouflages as mundane cargo objects | Warehouse search, scans and item identification |
| **Искряк** | Electric organism | Generates dangerous electrical effects | Short circuit, insulation test, standby power |
| **Печник** | Heat-producing organism | Produces heat and thermally stresses surroundings | Climate and refrigeration edge cases |
| **Корешок** | Root organism | Anchors/entangles with roots | Cage attachment, escape prevention, tow issues |

**Important:** table deliberately does not assign health, speed, body shape, hostility percentages, feeding schedules or numerical thresholds; these have **not been approved**. All seven share base behavioral principles: autonomous instincts and physics, needs, individual variation, memory, readable signals, compatibility interactions, injuries up to permanent death, and possible escape.

## Species design card template

Every species implementation must include: `species_id`, approved thematic mechanic, physical scale constraints, sensors/perception, motive/needs, environmental triggers, physical locomotion and grabs, distinct audible/visual signs, containment mitigations, care and injury model, save/network representation, species interaction matrix, automated test scenarios, and asset/performance budgets. Proposed numbers must be clearly marked until balancing and playtests.

## Players and co-op

Playable first-person characters up to four, independent arms/hands, active Ragdoll, no permanent playable-character death as campaign loss. Soft specializations not classes. Cosmetically identifiable teammates (design proposals: silhouettes/clothing/gear) without granting hidden information.

## Vehicle content

- **Required vehicle class:** *enclosed cargo van* with physically traversable driver cabin and cargo area.
- **Vehicle variants:** multiple buyable new/used models with distinct payload capacity, footprint, stability, accessibility, traction and upgrade envelope; model count and numeric stats TBD.
- **Equipment:** cages, straps, hardpoint modules, shelves, seats, handrails, partitions, power/climate/diagnostic modules, tow/recovery equipment, radio/GPS, tools.
- **Operating facilities:** modular garage boxes, storage, mechanic stations, vet station, research and test benches, recycling, connected building utilities, secure creature pens.
- **Forbidden design drift:** open pickup replacing enclosed van, fully manual gearbox or free-surface climb as core travel mechanic.

## World and POI families

Procedural multi-biome road graph with primary road known and branching hidden roads; authored POI assemblies (gas station, bridge, roadside stop, industrial/workshop location, abandoned facility, settlements, checkpoint, warehouse, veterinary or emergency site). Individual location list and map layouts remain production proposals; they are not mandatory one-for-one GDD approvals.

World actors: ordinary drivers, significant independent drivers/competitors, traders, faction agents, dispatchers, police/patrol, emergency response, mobile black market, creditors and insurance representatives. Meaningful interactions persist when witnessed or communicated.

## Contracts

Recurring physical loop: pickup/preparation → creature welfare/containment → travel → delivery/settlement. Delivery can involve on-site capture; multiple active chains; normal flexible vs. urgent deadlines; preauthored bargaining; delivery penalties grounded in contract and evidence. Content matrix proposal: benign short/local, time-sensitive, remote long-haul, suspicious paperwork, special biological hazard, multi-vehicle major convoy. Exact contracts, rewards and faction names remain unapproved.

## Props and material language

Visible and physically legible: cage doors and latches, straps, full-body tools, jerrycans, official documents, scannable crate marks, manuals, ventilation ducts, switches and displays. Item identity includes owner/condition/quality/mass/state; hidden defects may be detected only through meaningful tests.

## Narrative content catalog

Permanent inherited garage with debts; grandfather's secrets; multiple significant factions and conflicting explanations; player agency produces branching outcomes. Named NPCs, individual faction brands, exact ending scripts and dialogue text **not approved**; see [World & Narrative](04-WORLD-NARRATIVE.md).

## Art and audio direction

Own distinctive angular low-poly; warm, welcoming daytime/garage juxtaposed with cold, uneasy forest roads and dangerous darkness; readable silhouettes and world-space feedback. Spatial acoustics from barriers/rooms, radio interference and mechanical/creature sounds. Avoid copying specific games' assets or recognizable designs.

## Asset status and licensing policy (production)

All creature model files, audio, art and fonts are **to be produced or properly licensed**, not present as a result of this GDD. Track source, author, license and export constraints per asset; no asset is considered complete until Unity integration and QA verify it.
