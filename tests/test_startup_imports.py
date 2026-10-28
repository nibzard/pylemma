"""The hosted game must not load the historical model player."""

import subprocess
import sys


def test_hosted_import_excludes_historical_player() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import pylemma.web.app; "
            "assert 'pylemma.player.model' not in sys.modules; "
            "assert 'pydantic_ai' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
