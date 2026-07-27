"""Architectural guard: broker vocabulary must not leak outside scalpr/brokers.

Outside the broker layer, instruments are identified only by canonical
symbol + exchange. security_id construction and Dhan wire-segment literals
are broker-internal. import-linter enforces module imports; this test
enforces string vocabulary, which import graphs cannot see.
"""

from pathlib import Path

SCALPR_ROOT = Path(__file__).resolve().parents[2] / "scalpr"

# Files allowed to speak broker vocabulary
_ALLOWED = ("scalpr/brokers/", "scalpr/domain/instrument.py")

# Broker wire segments + security_id construction — must stay inside brokers
_FORBIDDEN = (
    'security_id=',
    '"NSE_EQ"', '"BSE_EQ"', '"IDX_I"', '"MCX_COMM"', '"NSE_FNO"', '"BSE_FNO"',
)


def test_no_broker_vocabulary_outside_brokers():
    violations = []
    for path in SCALPR_ROOT.rglob("*.py"):
        rel = path.relative_to(SCALPR_ROOT.parent).as_posix()
        if any(rel.startswith(a) or rel == a for a in _ALLOWED):
            continue
        text = path.read_text(encoding="utf-8")
        for token in _FORBIDDEN:
            if token in text:
                violations.append(f"{rel}: contains {token}")
    assert not violations, (
        "Broker vocabulary leaked outside scalpr/brokers "
        "(use canonical symbol+exchange; brokers own security_id/wire segments):\n"
        + "\n".join(violations)
    )
