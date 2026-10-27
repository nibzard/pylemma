"""Check that the installed distribution exposes the package contract."""

from importlib.metadata import metadata, version

import pylemma


def test_installed_version_matches_package() -> None:
    assert version("pylemma") == pylemma.__version__


def test_distribution_declares_supported_python() -> None:
    assert metadata("pylemma")["Requires-Python"] == ">=3.12"
