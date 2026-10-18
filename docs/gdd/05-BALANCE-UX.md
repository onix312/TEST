# Do Not Feed the Cargo — Balance, Input & UX

**Authority:** approved GDD-004, 007, 017–034, 049–060, 092–098. Values in examples are **test targets/proposals**, not approved numerical tuning.

## Experience targets

Cooperative 1–4 player physics comedy with stressful biological freight. Players have skill agency; long-form failure is consequential but not terminal. Three preferred run-length bands **15–30, 35–60, 60–120 minutes**. Most ordinary deliveries do not have oppressive countdowns; urgent orders declare time consequences.

**Difficulty:** risk from actual creature/contract/vehicle/weather conditions; director shapes pacing but cannot cheat. No hidden stat scaling because the company gets richer. Dedicated tunables for economy, hazard cadence and accessibility must not invalidate sim rules.

## Input philosophy

- Responsive keyboard/controller gas/brake/steer, automatic gear selection.
- First-person body with independent hand actions, contextual grabs and object affordances.
- Standard vault/climb on appropriate obstacles, NOT universal climbing.
- Sprint, crouch, slide and jump; carried weight, surface condition and inertia matter.
- Ragdoll is physical with partial control, physically attached head camera with full rotation. Provide sickness warnings and configurable non-gameplay visual accessibility where consistent with GDD-057; changing head-follow rule would require approval.
- Interaction hints only when looking at usable objects, not global x-ray highlights. All primary tasks possible solo.

## Diegetic UX

Information usually comes from world-space devices: van gauges, physical map/compass, optional imperfect GPS, paper contracts, receipts and permissions, radio, workbench terminals and scanners. HUD stays minimal and contextual; subtitle size and warning visibility adjustable. No hidden road/reputation/cargo truth leakage.

**Information states:** `unknown`, `observed`, `reported`, `verified`, `stale` are **proposed** UI data tags that help represent existing approved uncertainty. Evidence sources must be inspectable when gameplay requires it.

## Core balancing surfaces

| Domain | Knobs to test | Invariants |
|---|---|---|
| Carrying | grip, strain, speed reduction, capacity | can transport objects solo with alternative gear/path |
| Driving | cargo mass, braking, weather traction, fuel use | risk is predictable through world cues and instruments |
| Creatures | needs cadence, escape impulse, sensory thresholds | autonomous not random omnipotence; can die, good care helps |
| Contracts | length, deadline, payout, risk, penalties | terms legible; standard jobs flexible, urgent terms clear |
| Finance | wages, rent, debt interest, loans, replacement costs | bankruptcy not hard game over |
| Police | reaction delays, evidence quality, patrol travel | no instant reinforcement, no global omniscient wanted state |
| Supply | stock, travel time, staff budgets, tool wear | no material teleportation, no offline time |
| Production | material yield, skill effects, hidden defects, test cost | a passed test is not absolute guarantee |

## Onboarding (GDD-096)

No mandatory disconnected tutorial. Start at grandfather's garage, opt-in prompts and training stations, first calm contract teaches physical pickup/loading/strapping and navigation. Explain risks through real feedback and available manuals. Tutorial may be skipped or revisited. Both solo and 4-player sessions must work.

## Accessibility and comfort

Subtitles incl. speaker and radio differentiation; remappable inputs, adjustable UI scale and essential sensory cues. Provide audio/video alternatives for important alerts but without giving facts that devices cannot know. Avoid unnecessary flashing/light extremes in low-poly night scenes. Player's chosen **fully rotating head camera** in Ragdoll remains a nonnegotiable approved design; document possible motion sickness and test with appropriate controls/options *only if they do not contradict the chosen camera behavior*.

## Quality gates and playtest design

- First-time player can complete opening delivery without external walkthrough or second mandatory teammate.
- Test four-player physical cargo handoff, vehicle instability, captured creature containment, shift of inertia and crash recovery.
- Test mixed-language/subtitle accessibility, radio failure and map misinformation with intentional player communication.
- Balance replay through telemetry on session duration, failed catches, bug-trapped items, accidental creature deaths, injuries, losses, recoveries and early quit.
- Use playtest feedback to propose change requests; don't silently rewrite approved rules.

## Definition of "fair"

A threat should have discoverable cause/signals, at least one meaningful response (which may be risky/expensive), consequences proportionate to player choice and recovery routes that respect physical state. Unexpected chaos is allowed; arbitrary UI omniscience or random irrevocable save destruction is not.
