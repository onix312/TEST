"""Approved Do Not Feed the Cargo GDD bootstrap and dependency-aware Codex backlog.

Works from source and the packaged GameDev AI Office. This module DOES NOT
launch Codex or Unity, overwrite other approved GDDs, or touch game sources.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from office_core import ProjectStore, resource_path

BASELINE_MARKER = "<!-- DFTC-APPROVED-BASELINE: 2026-10-18 -->"
DOCS = (
    "DECISIONS-001-100.md",
    "01-MASTER-GDD.md",
    "02-SYSTEM-DESIGN.md",
    "03-CONTENT-BIBLE.md",
    "04-WORLD-NARRATIVE.md",
    "05-BALANCE-UX.md",
    "06-PRODUCTION-QA.md",
    "README.md",
)
ROADMAP = "ROADMAP-UNITY-CODEX.md"


@dataclass(frozen=True)
class PlannedTask:
    key: str
    phase: str
    title: str
    gdd: str
    depends: tuple[str, ...] = ()
    acceptance: str = ""


# Dependencies point only backward; tasks are proposed implementation scopes,
# NOT new GDD decisions or evidence that the underlying game already exists.
PLAN = (
    PlannedTask("P0-CORE", "P0", "Скелет Unity, системный clock и устойчивые ID", "001,008,099,100",
                acceptance="Editor compiles; deterministic entity IDs; no offline time progression."),
    PlannedTask("P0-TESTS", "P0", "Unity EditMode/PlayMode smoke и протокол QA", "008,099,100", ("P0-CORE",),
                "Small Unity tests exist and report actual outcomes; no fake passes."),
    PlannedTask("P0-SAVES", "P0", "Версионированные сохранения компании и экспедиций", "001,008,011,100",
                ("P0-TESTS",), "Atomic saves, backups, schema checks and restore-after-crash tests."),
    PlannedTask("P1-MOVE", "P1", "FPS-передвижение и контекстное лазание", "049,050,051,055,056",
                ("P0-CORE",), "Responsive solo/controller movement, crouch/slide, slope/mass effects."),
    PlannedTask("P1-HANDS", "P1", "Две физические руки и переноска", "049,050,054", ("P1-MOVE",),
                "Network-safe grab/drop, two-person carry, handoff without object teleportation."),
    PlannedTask("P1-RAGDOLL", "P1", "Физический Ragdoll и камера головы", "052,053,057", ("P1-HANDS",),
                "Head follows full ragdoll rotation, partial control and recovery."),
    PlannedTask("P2-VAN", "P2", "Закрытый фургон и интерактивная кабина", "025,026,030,058,059,060",
                ("P0-CORE",), "Walkable enclosed hold; keyboard/controller auto transmission; physical switches."),
    PlannedTask("P2-CARGO", "P2", "Клетки, ремни, пассажиры и инерция", "025,049,050,058,063",
                ("P2-VAN","P1-HANDS"), "Contact/strap stability under turns, seatbelts, physical freight."),
    PlannedTask("P2-DAMAGE", "P2", "Повреждения, ремонт, эвакуация", "027,028,029,030,031",
                ("P2-VAN",), "Subsystem-specific damage, physical repair, recovery from immobilization."),
    PlannedTask("P2-FLEET", "P2", "Несколько фургонов и передача груза на ходу", "061,062,063,074",
                ("P2-CARGO","P2-DAMAGE"), "Several enclosed models, per-vehicle state, physical inter-van moves."),
    PlannedTask("P3-AI", "P3", "Базовый ИИ, потребности, уход и клетки существ", "017,018,019,020,021,022,023,024,083",
                ("P0-CORE","P2-CARGO"), "Perception-limited autonomous behavior, care, injury, physical escape."),
    PlannedTask("P3-KLETSKA", "P3", "Клёцка — изменение массы", "019,050", ("P3-AI",),
                "Demonstrably shifting creature mass changes load and physical handling."),
    PlannedTask("P3-DREMNIK", "P3", "Дрёмник — споры и свет", "019,020,021,024",
                ("P3-AI",), "Spores physically affect exposed area; light influences behavior."),
    PlannedTask("P3-MYLNIK", "P3", "Мыльник — скользкие поверхности", "019,027,031",
                ("P3-AI",), "Slime visibly changes grip/traction and can be mitigated."),
    PlannedTask("P3-SKLADEN", "P3", "Складень — мимикрия под груз", "019,020,083,085",
                ("P3-AI",), "Physically plausible item disguise; detection by actual clues."),
    PlannedTask("P3-ISKRJAK", "P3", "Искряк — электрические эффекты", "019,021,082,083,090",
                ("P3-AI",), "Electric hazards interact with real components and insulation."),
    PlannedTask("P3-PECHNIK", "P3", "Печник — тепло", "019,021,082",
                ("P3-AI",), "Thermal load affects housing/vehicle systems predictably."),
    PlannedTask("P3-KORESHOK", "P3", "Корешок — корни и сцепление", "019,024,083",
                ("P3-AI",), "Root entanglement/contact modeled in test enclosure."),
    PlannedTask("P4-ROADS", "P4", "Несколько биомов, граф дорог и физические карты", "001,002,003,004,005,006,040,041,042",
                ("P0-SAVES",), "Reachable seeded networks, unknown roads stay undisclosed."),
    PlannedTask("P4-NET", "P4", "Сеть 1–4, join/leave, VOIP и физическая синхронизация", "008,009,010,011,043,044,045,063",
                ("P1-RAGDOLL","P2-FLEET"), "Join mid-run, host exit saves, cargo consistent across clients."),
    PlannedTask("P4-NPC", "P4", "Трафик, свидетели и автономные значимые NPC", "035,036,037,038,039,046,047,048,064,065",
                ("P4-ROADS",), "NPC perception and message propagation causally traceable."),
    PlannedTask("P5-CONTRACT", "P5", "Контракты, доставка, переговоры и оплата", "007,012,013,014,015,016,017",
                ("P4-ROADS","P3-AI"), "Pickup/care/delivery/payment loop runs solo without hidden teleports."),
    PlannedTask("P5-WEATHER", "P5", "Погода, время, усталость и события", "031,032,033,034,035,036,037,094",
                ("P5-CONTRACT",), "World and travel respond to conditions; time skip interruptible."),
    PlannedTask("P6-GARAGE", "P6", "Модульная база, инженерия и физический склад", "075,076,081,082,083,084,085",
                ("P0-SAVES","P2-VAN"), "Reposition physical racks, power failure, warehouse may be stale."),
    PlannedTask("P6-STAFF", "P6", "Вспомогательные NPC и делегирование", "075,076,077,078,079,080",
                ("P6-GARAGE",), "No autonomous NPC primary delivery; tasks respect budgets, fatigue."),
    PlannedTask("P6-SUPPLY", "P6", "Физические поставки, приёмка, закупки", "085,086,087",
                ("P6-GARAGE","P4-NPC"), "No virtual material spawning; delivery receipts and defects."),
    PlannedTask("P6-CRAFT", "P6", "Производство, R&D, тесты и переработка", "088,089,090,091",
                ("P6-STAFF","P6-SUPPLY"), "Blueprints, real components, tests, latent defects, qualified NPC work."),
    PlannedTask("P6-ECON", "P6", "Рынок фургонов, долги и страхование", "061,072,073,074",
                ("P5-CONTRACT","P6-GARAGE"), "Finances persist; insolvency doesn't destroy game."),
    PlannedTask("P7-LAW", "P7", "Документы, проверки, полиция, арест и конфискации", "066,067,068,069,070,071",
                ("P4-NPC","P6-ECON"), "Knowledge-limited enforcement; playable recovery from arrest."),
    PlannedTask("P7-STORY", "P7", "Нелинейная история и фракции", "015,016,047,048,093",
                ("P5-CONTRACT","P7-LAW"), "Branching outcomes keep existing company playable."),
    PlannedTask("P8-UX", "P8", "HUD, обучение, стилизация, пространственный звук", "004,044,045,057,095,096,097,098",
                ("P4-NET","P5-CONTRACT"), "Diegetic interface, optional tutorial, physical stereo cues."),
    PlannedTask("P8-ALPHA", "P8", "Сборка и регрессия большой альфы", "001,017,061,075,088,092,093,094,095,096,097,098,099,100",
                ("P3-KLETSKA","P3-DREMNIK","P3-MYLNIK","P3-SKLADEN",
                 "P3-ISKRJAK","P3-PECHNIK","P3-KORESHOK","P4-NET",
                 "P5-WEATHER","P6-CRAFT","P6-ECON","P7-STORY","P8-UX"),
                "Full seven-species, several-vans, multi-region, 1–4 co-op build with evidence."),
)


def _docs_path(root: Path | None = None) -> Path:
    return Path(root) if root is not None else resource_path("docs")


def load_documents(root: Path | None = None) -> dict[str, str]:
    """Read and validate bundled, already user-approved design artifacts."""
    docs = _docs_path(root)
    result = {}
    for name in DOCS:
        path = docs / "gdd" / name
        result[name] = path.read_text(encoding="utf-8")
        if not result[name].strip():
            raise ValueError("Empty approved design document: " + name)
    result[ROADMAP] = (docs / ROADMAP).read_text(encoding="utf-8")
    numbers = [int(n) for n in re.findall(
        r"^- \*\*GDD-(\d{3})\*\*", result[DOCS[0]], flags=re.MULTILINE)]
    if numbers != list(range(1, 101)):
        raise ValueError("Decision register must contain GDD-001 through GDD-100 exactly once.")
    keys = {t.key for t in PLAN}
    if len(keys) != len(PLAN) or any(
            dependency not in keys for item in PLAN for dependency in item.depends):
        raise ValueError("Invalid task plan or unresolved dependency.")
    seen = set()
    for item in PLAN:
        if not set(item.depends) <= seen:
            raise ValueError("Task dependencies must reference earlier tasks: " + item.key)
        seen.add(item.key)
    return result


def approved_baseline(documents: dict[str, str]) -> str:
    return (BASELINE_MARKER + "\n\n" + documents[DOCS[0]] +
            "\n\n---\n\n" + documents["01-MASTER-GDD.md"])


def seed_game_project(store: ProjectStore, docs_root: Path | None = None) -> dict:
    """Safely install a read-only baseline and queue tasks. Never execute agents.

    Refuses conflicting existing GDD/reference files; repeated calls are
    idempotent and do not change existing task states.
    """
    documents = load_documents(docs_root)
    approved = approved_baseline(documents)
    gdd_target = store.folder / "gdd" / "approved.md"
    if gdd_target.exists() and gdd_target.read_text(encoding="utf-8") != approved:
        raise ValueError("Existing approved GDD differs; refusing to overwrite it.")
    reference = store.folder / "gdd" / "reference"
    copies = {name: reference / name for name in DOCS}
    copies[ROADMAP] = reference / ROADMAP
    for name, path in copies.items():
        if path.exists() and path.read_text(encoding="utf-8") != documents[name]:
            raise ValueError("Existing reference differs; refusing overwrite: " + str(path))

    reference.mkdir(parents=True, exist_ok=True)
    for name, path in copies.items():
        if not path.exists():
            path.write_text(documents[name], encoding="utf-8")
    if not gdd_target.exists():
        store.approve_gdd(approved)

    existing: dict[str, dict] = {}
    for task in store.tasks:
        match = re.match(r"^\[DFTC:([A-Z0-9-]+)\]", task["text"])
        if match:
            if match.group(1) in existing:
                raise ValueError("Duplicate DFTC task tag: " + match.group(1))
            existing[match.group(1)] = task
    created = 0
    for spec in PLAN:
        if spec.key in existing:
            continue
        missing = [dep for dep in spec.depends if dep not in existing]
        if missing:
            raise ValueError(f"Missing dependencies for {spec.key}: {missing}")
        prompt = (f"[DFTC:{spec.key}] {spec.title}\n"
                  f"PHASE: {spec.phase}; APPROVED GDD REFERENCES: {spec.gdd}.\n"
                  "Implement one bounded Unity C# step in Assets/ (and Packages/"
                  "ProjectSettings only if necessary). Preserve GUIDs and other "
                  "contributors' work. GDD is fixed; propose deviations, never "
                  "silently change design. Add relevant EditMode/PlayMode tests. "
                  "Do not install, start Unity Editor, commit or push. "
                  "Report concrete tests run, remaining issues and Unity manual QA needs.\n"
                  f"ACCEPTANCE: {spec.acceptance}")
        item = store.add(prompt, depends=[existing[k]["id"] for k in spec.depends],
                         role="Unity Developer", route="codex")
        store.update(item["id"], phase=spec.phase,
                     gdd_refs=spec.gdd, seed_key=spec.key)
        existing[spec.key] = item
        created += 1
    return {"created": created, "total": len(PLAN), "documents": len(copies),
            "approved_file": str(gdd_target), "plan": "P0–P8", "started": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the approved game GDD & scoped Codex task queue.")
    parser.add_argument("--unity-project", required=True, help="Existing Unity project root containing Assets and ProjectSettings")
    parser.add_argument("--check", action="store_true", help="Validate bundled documents and report plan without modifying the project")
    args = parser.parse_args()
    docs = load_documents()
    if args.check:
        print(f"GDD validated: 100 approved decisions, {len(docs)} documents, {len(PLAN)} planned tasks.")
        return 0
    result = seed_game_project(ProjectStore(Path(args.unity_project)))
    print(f"Installed GDD and queued {result['created']} new tasks ({result['total']} total).")
    print("Nothing executed. Review tasks and run Unity/Codex from GameDev AI Office.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
