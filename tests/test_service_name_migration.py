import json
from pathlib import Path
import runpy
from unittest.mock import patch

import pytest

migrate = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                            "deploy" / "migrate-service-names.py"))["migrate"]


def responses():
    return [
        json.dumps({"name": "deploy"}),
        "legacy-container\n",
        json.dumps([{
            "Mounts": [
                {"Destination": "/app/data", "Type": "volume", "Name": "existing-index"},
                {"Destination": "/app/.cache", "Type": "volume", "Name": "existing-cache"},
            ],
            "Config": {"Env": ["MS2_EVENTS_QUEUE=custom-events"]},
        }]),
    ]


def test_preserves_existing_resources_and_credentials_idempotently(tmp_path):
    environment = tmp_path / ".env"
    environment.write_text("POSTGRES_PASSWORD=fixture-only\n")
    with patch("subprocess.check_output", side_effect=responses()):
        migrate(Path("deploy/compose.yaml"), environment)
    saved = environment.read_text()
    assert "POSTGRES_PASSWORD=fixture-only\n" in saved
    assert "RAG_DATA_VOLUME=existing-index\n" in saved
    assert "RAG_CACHE_VOLUME=existing-cache\n" in saved
    assert "RAG_EVENTS_QUEUE=custom-events\n" in saved
    assert "RAG_EVENTS_DEAD_LETTER_QUEUE=ms2.note-events.dlq\n" in saved
    with patch("subprocess.check_output", side_effect=responses()):
        migrate(Path("deploy/compose.yaml"), environment)
    assert environment.read_text() == saved


def test_conflicting_override_aborts_without_changing_environment(tmp_path):
    environment = tmp_path / ".env"
    environment.write_text("RAG_DATA_VOLUME=different-index\n")
    with patch("subprocess.check_output", side_effect=responses()), pytest.raises(RuntimeError, match="conflicts"):
        migrate(Path("deploy/compose.yaml"), environment)
    assert environment.read_text() == "RAG_DATA_VOLUME=different-index\n"


def test_fresh_install_does_not_create_environment_overrides(tmp_path):
    environment = tmp_path / ".env"
    with patch("subprocess.check_output", side_effect=[json.dumps({"name": "fresh"}), ""]):
        migrate(Path("compose.yaml"), environment)
    assert not environment.exists()
