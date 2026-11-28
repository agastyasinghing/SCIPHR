"""
FTR-01B1 — prediction isolation.

Pins the model artifact, feature names/order, and every prediction-related
source file to the values recorded in docs/FTR-01_AUDIT.md (§7.1) and at the
FTR-01B1 start commit.  These tests are intentionally strict: a ticket that
legitimately changes one of these files must update the pin deliberately.
"""

import ast
import hashlib
import os
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

MODEL_SHA256 = "a465a75aebaafe3659232aeb83fdbafe04461dad139ebcf186baadc683274a44"
FEATURE_NAMES_SHA256 = "94ec2d88365fc070a9c117925b8f02e7121d1c6271c3528837791377b8a9f321"

# sha256 of file bytes with CRLF normalised to LF (Windows checkouts are CRLF).
SOURCE_PINS = {
    "src/golden_feature_calculator.py": "75574de573bd1e94214a27f50ec8df0963703b03cdfbef8a90507129c669aaaf",
    "src/predictor_golden.py": "eacaeec113b15e49dba1ee80bb4d6e6d1d930a4bebc87814e80b160e1b7110ba",
    "backend/intelligence/__init__.py": "11eb6350be505bb10684951d45d95fe26950a144bb852ee59e6aab72be569e11",
    "backend/intelligence/badge_engine.py": "1e68f0ba8ad47a3159b10d8466d149d52f9e9d81a21791a4d619da7e1f98b919",
    "backend/intelligence/chaos_scorer.py": "9a7930d449d02df74f767c6da8841745f540e10d0babf827d2bbda3ce7d8c34c",
    "backend/intelligence/cinematic_title.py": "774d86a13bf8efbda7bd750e4e9960f4a975070897a9e228bb7d3df496bcae86",
    "backend/intelligence/false_consensus.py": "26d8ffeec0dcbcc90dad2c45b3a84abfdb592c44905242617f1ea50fc7f5b825",
    "backend/intelligence/fight_dna.py": "f362020c3df53a029935b3e3814b89198d8e068e8736912e5ea2bf95571f51ae",
    "backend/intelligence/models.py": "f361154b33b45b4e0099b583cf7379c529c8fb4976d971719f3d198a740d0081",
    "backend/intelligence/narrative_trap.py": "580e777ff18e8f41711b2cfe31ee4b293100d31542c7f15789c3619cc80589c4",
    "backend/intelligence/nightmare_matchup.py": "7651a821ca37b5aed1099d24782be3d09d6c21e06ced124b08ddbf8ca40f71fb",
    "backend/intelligence/orchestrator.py": "b4276fd278ad381e9e87a446c5c538b344b3771f47ab118e4d9fd988d13075af",
    "backend/intelligence/perception_gap.py": "2b1207d0c0f4981f72f690fcd94cae4ef3cd27d59962070c1d6ad3284f63ab2a",
    "backend/intelligence/sharp_money.py": "ed37bc69bf02b39562907001bdad2e8d53481e6748c5c5ee843a6851e4152dd0",
    "backend/intelligence/upset_alert.py": "43c5533dff6ee44d35cadbad718e3a9000359cbbc0be1a5a1fb76a8a61e42397",
    "backend/intelligence/utils.py": "ed038765ab5f1871ab0d28e3f76efa0ab451dd3f72b45e77c1eccc52ce01de0d",
    "backend/intelligence/value_bet.py": "a863908c4e820f98926bd9a0699f4bd3c21c87abb2a37b8329fd841d4eca0fab",
    "backend/intelligence/win_path.py": "dde6fb37811330dfc54797bce6e81961666308dac1ccce23e4a9ecca9fda3be1",
}


def _sha_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


MODEL_PATH = REPO / "models" / "golden_model.pkl"


@pytest.mark.skipif(not MODEL_PATH.exists(), reason="model artifact not present")
class TestModelArtifact:
    def test_model_file_hash_unchanged(self):
        assert hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest() == MODEL_SHA256

    def test_feature_names_count_order_unchanged(self):
        with open(MODEL_PATH, "rb") as fh:
            data = pickle.load(fh)
        names = data["feature_names"]
        assert len(names) == 5401
        assert hashlib.sha256("\n".join(names).encode()).hexdigest() == FEATURE_NAMES_SHA256


@pytest.mark.parametrize("rel,expected", sorted(SOURCE_PINS.items()))
def test_prediction_related_sources_unchanged(rel, expected):
    assert _sha_lf(REPO / rel) == expected, f"{rel} changed — FTR-01B1 must not touch it"


def test_no_new_intelligence_files():
    present = {f"backend/intelligence/{p.name}" for p in (REPO / "backend" / "intelligence").glob("*.py")}
    assert present == {k for k in SOURCE_PINS if k.startswith("backend/intelligence/")}


FORBIDDEN_PREFIXES = (
    "xgboost", "pickle", "predictor", "predictor_golden", "golden_feature_calculator",
    "intelligence", "numpy", "pandas", "sklearn", "joblib",
)


def test_fighter_profile_package_does_not_import_model_or_intelligence():
    pkg = REPO / "backend" / "fighter_profile"
    files = list(pkg.glob("*.py"))
    assert files
    for f in files:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module]
            for m in mods:
                root = m.split(".")[0]
                assert root not in FORBIDDEN_PREFIXES, f"{f.name} imports {m}"


def _non_docstring_strings(tree):
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                doc_nodes.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_nodes]


def test_profile_package_never_references_latest_features_in_code_or_sql():
    for f in (REPO / "backend" / "fighter_profile").glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for value in _non_docstring_strings(tree):
            assert "latest_features" not in value, f"{f.name}: {value[:60]!r}"
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} |                 {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert "latest_features" not in names


def test_profile_package_has_no_write_statements():
    for f in (REPO / "backend" / "fighter_profile").glob("*.py"):
        up = f.read_text(encoding="utf-8").upper()
        for kw in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "CREATE TABLE", ".COMMIT(", "CREATE_ALL"):
            assert kw not in up, f"{f.name} contains {kw!r}"


def test_cprofile_still_importable_with_backend_first_on_path():
    """The package is named `profile` (per ticket); verify stdlib cProfile is unaffected."""
    code = (
        "import sys; sys.path.insert(0, r'%s'); import cProfile; print('ok')"
        % (REPO / "backend")
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0 and "ok" in out.stdout, out.stderr
