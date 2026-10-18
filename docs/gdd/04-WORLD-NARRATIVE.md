# Do Not Feed the Cargo — World, Narrative & Factions

**Authority:** GDD-001–048, GDD-064–073 and GDD-093. This document distinguishes **approved narrative structure** from **proposed story-writing tasks**.

## Premise

The players inherit their grandfather's aging garage, a struggling creature-delivery business and inherited debt. Routine freight work gradually exposes suspicious customers, contradictory descriptions of creature origins, hidden equipment and links between the grandfather and competing organizations. The story is nonlinear; players decide whether and when to follow leads.

The inherited company persists between dynamically generated expedition maps. Memories and consequences that matter to named NPCs and factions persist as abstract history. Offline time does not pass.

## Narrative form and play

- Story delivered through NPC encounters, documents, physically discoverable evidence, contractual offers, radio and exploration; player can choose to focus on deliveries instead.
- Factions have distinct interests and imperfect information; story decisions and actions influence access to suppliers, jobs, pricing, treatment by authorities and eventual finale.
- Multiple endings resolve the **central mystery** but do not end the save. Post-finale sandbox continues in the same company with meaningful consequences.
- Preauthored dialogue with branching choices; no need for generative LLM speech. Localization planned with English-first and Russian support; exact localization pipeline is implementation decision.
- Contracts can be combined or negotiated, and secrecy, bribes, repairs, rescue, theft and smuggling are systems-driven actions with consequences.

## Knowledge and trust architecture

Evidence is physically acquired: documents, damaged equipment, eyewitness accounts, radio traffic, traces at crash sites, behavior of creatures. Information may be false, stale or incomplete. NPCs share knowledge only via actual encounters, radio/communications, alarms and witnesses. No global wanted-level broadcast or omniscient map.

A **proposed** normalized information record:
`Observation { subjectId, observerId, timestamp, positionOrArea, confidence, sourceId, communicatedTo[] }`.
Persistence across expeditions stores salient claims and relationships, not physics of distant live NPCs while offline.

## Narrative arc (planning outline, not approved plot canon)

| Arc | Proposed focus | Proof point in play |
|---|---|---|
| Inheritance | debts, garage, first ordinary jobs | player can choose contracts and repair vehicle |
| Uneasy jobs | conflicting permits, strange cargo and competitors | factions disagree; clues live in world |
| Dangerous supply chain | experimental containment technology and black market | competing valid solutions, physical consequences |
| Grandfather's history | reconstruct conflicting accounts and motivations | investigative evidence can change relationships |
| Last expedition | multiple factions compete over a discovered truth | player decisions lead to different durable endings |
| Aftermath | operate a transformed company | sandbox remains viable, persistent consequences |

Neither the precise nature of the grandfather's secret nor number of endings has been agreed. Writing those requires a narrative proposal and later approval, not automatic classification as GDD-093 detail.

## Factions (roles approved, identities proposed)

**Approved roles:** legitimate suppliers, significant competing carriers, regional police and regulators, mobile black-market intermediaries, creditors/insurers, independent research contacts, emergency responders, workers. Each may have autonomous decision rules, relations and memory. Proper names, symbols and fixed territories are **pending content design**.

**Faction card template:** public function, concealed goal, resource limitations, known information, rivals, legal reach, contract list, credibility/history, communication channels, consequences and ending influence. Faction AI cannot summon units or know secrets without causal pathways.

## Incident-to-story examples (noncanonical scenarios)

- Crash of competitor on rainy pass → blocked road → escaped creature → rescue/salvage/blackmail choices → survivors remember help or abandonment.
- Fake permit at checkpoint → suspicion and physical search → chase, arrest, confiscation, legal appeal or recovery → reputation changes.
- Warehouse inventory inconsistency → mimic organism hidden as a box → physical search and damage → staff reaction if present/aware.

These exemplify emergent systems, not scripted mandatory story scenes.

## Safety against unsatisfying loss

Creature death may be permanent; owned inventory can be confiscated; company can sink into severe debt. However the *player* must retain an active path to continue, including legal or risky property recovery, emergency transport options and eventual debt rehabilitation. Arrest gameplay cannot trap someone indefinitely.

## Narrative production checklist

Plot revelation must be justified by real evidence or character actions; decisions cannot irreversibly delete solo playability; all endings leave the company playable; dialogue branching tested for contradictions; regional permits and institution responses use knowledge propagation not magical discovery.
