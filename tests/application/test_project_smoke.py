from pathlib import Path
import tomllib

from apk_hacker import __version__


ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_VERSION = tomllib.loads(ROOT.joinpath("pyproject.toml").read_text())["project"][
    "version"
]


def test_project_version_string() -> None:
    assert __version__ == "0.1.0"


def test_project_version_matches_pyproject() -> None:
    assert PYPROJECT_VERSION == __version__
