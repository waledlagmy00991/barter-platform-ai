"""Safety regression tests, not independent data-quality certification."""
import hashlib
import subprocess
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
VISION=ROOT/'vision'
sys.path.insert(0,str(VISION))
from integrity_guard import verify_snapshot, require_authorized_execution

PROTECTED=[]
for pattern in ('train*.py','resume*.py','harvest*.py','build_dataset*.py','download_opensooq.py','fill_openverse.py','prepare_data.py','val*.py','finish.py'):
    PROTECTED.extend(VISION.glob(pattern))


def test_snapshot_and_deployed_weight_hashes():
    manifest=verify_snapshot()
    assert len(manifest['records'])==62


def test_execution_fails_closed():
    with pytest.raises(RuntimeError,match='paused'):
        require_authorized_execution()


@pytest.mark.parametrize('script',sorted(set(PROTECTED)))
def test_mutating_entrypoint_is_blocked_before_action(script):
    result=subprocess.run([sys.executable,str(script)],cwd=VISION,capture_output=True,text=True,timeout=30)
    assert result.returncode!=0
    assert 'Vision execution paused' in result.stderr


def test_cleanup_apply_is_blocked():
    result=subprocess.run([sys.executable,str(VISION/'cleanup_review.py'),'--apply'],cwd=VISION,capture_output=True,text=True,timeout=30)
    assert result.returncode!=0
    assert 'Vision execution paused' in result.stderr


def test_snapshot_unchanged_after_guards():
    verify_snapshot()
