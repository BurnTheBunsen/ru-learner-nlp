def _is_aligned(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """True if one span fully contains the other, or they're equal."""
    return (a_start <= b_start and a_end >= b_end) or (b_start <= a_start and b_end >= a_end)


def find_aligned_boundary_tokens(target_token: dict, boundary_tokens: list[dict]) -> list[dict]:
    """
    Returns every boundary token whose span fully contains, or is
    contained by, target_token's span (order preserved from boundary_tokens).
    """
    t_start, t_end = target_token["start_char"], target_token["end_char"]

    matches = [
        b for b in boundary_tokens
        if _is_aligned(t_start, t_end, b["start_char"], b["end_char"])
    ]

    if not matches:
        raise ValueError(
            f"No boundary token aligns with target {target_token.get('text')!r} "
            f"at [{t_start}:{t_end}). Check both adapters ran on the same text."
        )

    return matches


def align_tokens(target_tokens: list[dict], boundary_tokens: list[dict]) -> list[dict]:
    """
    Aligns each target token to its boundary token(s). Returns, in
    target_tokens order: [{"target": ..., "boundary_tokens": [...]}, ...]
    boundary_tokens may contain more than one entry (see find_aligned_boundary_tokens).
    """
    return [
        {"target": t, "boundary_tokens": find_aligned_boundary_tokens(t, boundary_tokens)}
        for t in target_tokens
    ]