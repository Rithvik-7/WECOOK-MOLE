"""Copy the local database and evidence files. This does not publish them."""
from __future__ import annotations

import json
import shutil
from pathlib import Path


def backup(database: Path, evidence: Path, destination: Path) -> dict:
    if not database.is_file():
        raise FileNotFoundError(database)
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(database, destination / "mole.db")
    files = []
    if evidence.is_dir():
        target = destination / "evidence"
        shutil.copytree(evidence, target)
        files = sorted(path.name for path in target.iterdir() if path.is_file())
    manifest = {"database": "mole.db", "evidence": files}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def restore(source: Path, database: Path, evidence: Path) -> dict:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    saved = source / manifest["database"]
    if not saved.is_file():
        raise FileNotFoundError(saved)
    database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(saved, database)
    if evidence.exists():
        shutil.rmtree(evidence)
    stored = source / "evidence"
    if stored.is_dir():
        shutil.copytree(stored, evidence)
    return manifest
