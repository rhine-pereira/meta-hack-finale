from hashlib import sha256
from typing import List

def sha256_leaf(data: bytes) -> bytes:
    """Computes SHA256(0x00 || data) to prevent second-preimage attacks."""
    return sha256(b"\x00" + data).digest()

def sha256_node(left: bytes, right: bytes) -> bytes:
    """Computes SHA256(0x01 || left || right) with sorted pairing."""
    # Sort children to ensure deterministic root regardless of order
    if left > right:
        left, right = right, left
    return sha256(b"\x01" + left + right).digest()

def build_merkle_root(leaves: List[bytes]) -> bytes:
    """
    Builds a Merkle tree from a list of leaf hashes and returns the root.
    If leaves is empty, returns 32 bytes of zeros.
    """
    if not leaves:
        return b"\x00" * 32
    
    # Work on a copy of the leaf hashes
    current_layer = list(leaves)
    
    while len(current_layer) > 1:
        next_layer = []
        for i in range(0, len(current_layer), 2):
            left = current_layer[i]
            if i + 1 < len(current_layer):
                right = current_layer[i+1]
                next_layer.append(sha256_node(left, right))
            else:
                # If odd number of nodes, promote the last one (or duplicate/pair with self)
                # Here we follow the simple strategy of pairing with self or just promoting
                # Standard practice in Solana (e.g. SPL-Token) is often promoting or specific padding.
                # We'll pair with self for simplicity in this implementation.
                next_layer.append(sha256_node(left, left))
        current_layer = next_layer
        
    return current_layer[0]
