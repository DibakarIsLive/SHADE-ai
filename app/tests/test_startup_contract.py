import importlib.util
import sys
from pathlib import Path

import pytest


MANAGE_PATH = Path(__file__).resolve().parents[1] / "manage.py"


@pytest.fixture
def manage_module():
    module_name = "shade_manage_for_startup_tests"
    spec = importlib.util.spec_from_file_location(module_name, MANAGE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_prepare_runserver_arguments_removes_force_only_from_runserver_options(manage_module):
    argv = ["manage.py", "runserver", "127.0.0.1:8000", "--force", "--noreload"]

    cleaned, force = manage_module._prepare_runserver_arguments(argv)

    assert cleaned == ["manage.py", "runserver", "127.0.0.1:8000", "--noreload"]
    assert force is True


def test_prepare_arguments_does_not_change_non_runserver_commands(manage_module):
    argv = ["manage.py", "check", "--force"]

    cleaned, force = manage_module._prepare_runserver_arguments(argv)

    assert cleaned == argv
    assert force is False


def test_require_mongodb_skips_database_lookup_in_force_mode(manage_module, monkeypatch):
    def should_not_be_called():
        raise AssertionError("force mode must not query MongoDB")

    monkeypatch.setattr("config.database.database_available", should_not_be_called)

    manage_module._require_mongodb(force=True)


def test_require_mongodb_fails_clearly_when_database_is_unavailable(manage_module, monkeypatch):
    monkeypatch.setattr("config.database.database_available", lambda: False)

    with pytest.raises(SystemExit, match="make dev -- --force"):
        manage_module._require_mongodb()


def test_require_mongodb_returns_when_database_is_available(manage_module, monkeypatch):
    monkeypatch.setattr("config.database.database_available", lambda: True)

    manage_module._require_mongodb()


def test_diagnostic_environment_variable_is_defined_for_reloader_handoff(manage_module):
    assert manage_module.DIAGNOSTIC_MODE_ENV == "SHADE_AI_DIAGNOSTIC_MODE"
