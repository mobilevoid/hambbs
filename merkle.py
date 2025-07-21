from __future__ import annotations
from hashlib import sha256
from typing import Iterable, List


def merkle_root(leaves: Iterable[bytes]) -> bytes:
    """Return the Merkle root of *leaves* using SHA-256."""
    nodes = [sha256(l).digest() for l in leaves]
    if not nodes:
        return b"\x00" * 32
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        nodes = [sha256(nodes[i] + nodes[i + 1]).digest() for i in range(0, len(nodes), 2)]
    return nodes[0]


def diff_indices(local: List[bytes], remote_root: bytes) -> List[int]:
    """Return indices of leaves that differ from *remote_root*.
    This is a naive implementation for small trees.
    """
    mismatched = []
    for idx, leaf in enumerate(local):
        if merkle_root([leaf]) != remote_root:
            mismatched.append(idx)
    return mismatched
