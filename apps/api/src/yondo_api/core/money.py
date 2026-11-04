"""Integer minor-unit money helpers. Floating point is never used for money."""

BPS_DENOMINATOR = 10_000


def apply_bps(amount_minor: int, bps: int) -> int:
    """Return ``amount * bps / 10000`` rounded half up, using integer arithmetic only."""
    if amount_minor < 0 or bps < 0:
        raise ValueError('Amount and basis points must be nonnegative')
    return (amount_minor * bps + BPS_DENOMINATOR // 2) // BPS_DENOMINATOR
