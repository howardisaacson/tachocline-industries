"""Locks the CI contract and the secret-file ignore rules.

These tests only read files in the checkout. They do not open sockets.
Parsing, validation, and upsert tests arrive with issue #27.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_ci_workflow_lints_and_tests_on_python_312() -> None:
    workflow = _text(".github/workflows/ci.yml")
    assert "name: CI" in workflow
    assert "name: lint" in workflow
    assert "name: test" in workflow
    assert 'python-version: "3.12"' in workflow
    assert "ruff check ." in workflow
    assert "ruff format --check ." in workflow
    assert "run: pytest" in workflow
    assert "pull_request:" in workflow
    assert "-r ingest/requirements.txt" in _text("requirements-dev.txt")


def test_env_files_stay_out_of_git() -> None:
    gitignore = _text(".gitignore")
    # `.env.*` would also hide the template, so the un-ignore must be present.
    assert ".env" in gitignore.splitlines()
    assert ".env.*" in gitignore.splitlines()
    assert "!.env.example" in gitignore.splitlines()
    assert gitignore.splitlines().index(".env.*") < gitignore.splitlines().index(
        "!.env.example"
    )
    assert (ROOT / ".env.example").is_file()
    assert not (ROOT / ".env").exists()
