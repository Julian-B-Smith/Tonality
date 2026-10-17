"""Every script in examples/ runs to completion.

The README's first runnable command (examples/quickstart_engine_demo.py) was
broken for months: RE-6e removed a helper it imported, and nothing ran
examples/. Found by the 2026-10-17 docs-vs-code drift audit. This is the gate
that makes a documented example a contract.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "examples").glob("*.py"))


def test_there_are_examples_to_run():
    assert EXAMPLES, "examples/ is empty; the README's quickstart points into it"


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.name)
def test_example_runs(script):
    # PYTHONPATH pins the working tree: the venv's installed copy of mts can lag
    # it, and an example passing against stale code proves nothing.
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    r = subprocess.run([sys.executable, str(script)], cwd=ROOT, env=env, capture_output=True,
                       text=True, timeout=60, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.strip(), "an example that prints nothing demonstrates nothing"
