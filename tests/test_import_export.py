from __future__ import annotations

from pathlib import Path
import sys

from app.config.settings import get_settings
from app.repositories.fixtures import FixtureRepository
from app.utils.hashing import generate_request_hash
import export_fixtures as export_module
import import_fixtures as import_module
import clear_fixtures as clear_module


def test_fixture_export_works(tmp_path: Path, monkeypatch, sample_payload) -> None:
    db_path = tmp_path / "fixtures.db"
    output_dir = tmp_path / "fixtures"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    request_hash = generate_request_hash(sample_payload)
    FixtureRepository(db_path).upsert(
        request_hash=request_hash,
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response={"exported": True},
    )

    count = export_module.export_fixtures(output_dir)

    assert count == 1
    assert (output_dir / f"{request_hash}.json").exists()


def test_fixture_import_works(tmp_path: Path, monkeypatch, sample_payload) -> None:
    db_path = tmp_path / "fixtures.db"
    output_dir = tmp_path / "fixtures"
    output_dir.mkdir()
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    request_hash = generate_request_hash(sample_payload)
    (output_dir / f"{request_hash}.json").write_text(
        """
        {
          "request_hash": "%s",
          "model": "llama-test",
          "request": {"model": "llama-test", "messages": []},
          "response": {"imported": true}
        }
        """
        % request_hash,
        encoding="utf-8",
    )

    count = import_module.import_fixtures(output_dir)

    assert count == 1
    assert FixtureRepository(db_path).get(request_hash).response == {"imported": True}


def test_export_main_prints_count(tmp_path: Path, monkeypatch, capsys, sample_payload) -> None:
    db_path = tmp_path / "fixtures.db"
    output_dir = tmp_path / "fixtures"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    request_hash = generate_request_hash(sample_payload)
    FixtureRepository(db_path).upsert(
        request_hash=request_hash,
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response={"exported": True},
    )
    monkeypatch.setattr(sys, "argv", ["export_fixtures.py", "--output-dir", str(output_dir)])

    export_module.main()

    assert "Exported 1 fixtures." in capsys.readouterr().out


def test_import_main_prints_count(tmp_path: Path, monkeypatch, capsys, sample_payload) -> None:
    db_path = tmp_path / "fixtures.db"
    input_dir = tmp_path / "fixtures"
    input_dir.mkdir()
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    request_hash = generate_request_hash(sample_payload)
    (input_dir / f"{request_hash}.json").write_text(
        """
        {
          "request_hash": "%s",
          "provider": "openai",
          "model": "llama-test",
          "request": {"model": "llama-test", "messages": []},
          "response": {"imported": true}
        }
        """
        % request_hash,
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["import_fixtures.py", "--input-dir", str(input_dir), "--provider", "groq"])

    import_module.main()

    assert "Imported 1 fixtures." in capsys.readouterr().out


def test_clear_fixtures_command_deletes_sqlite_rows(tmp_path: Path, monkeypatch, capsys, sample_payload) -> None:
    db_path = tmp_path / "fixtures.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    FixtureRepository(db_path).upsert(
        request_hash=generate_request_hash(sample_payload),
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response={"clear": True},
    )
    monkeypatch.setattr(sys, "argv", ["clear_fixtures.py"])

    clear_module.main()

    assert FixtureRepository(db_path).count() == 0
    assert "Deleted 1 fixtures." in capsys.readouterr().out
