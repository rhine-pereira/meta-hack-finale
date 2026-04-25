import json
from hashlib import sha256
from typing import Any, Dict

def canonical_payload(state: Any) -> bytes:
    """
    Serializes a subset of the WorldState into a canonical JSON byte string.
    Focuses on reproducibility-critical fields.
    """
    # Define fields to include in the hash
    # We use a stable subset to avoid noise from ephemeral fields
    payload = {
        "episode_id": state.episode_id,
        "day": state.day,
        "difficulty": int(state.difficulty),
        "seed": getattr(state, "seed", 0), # Fallback if not yet on state
        "cash": round(float(state.cash), 2),
        "mrr": round(float(state.mrr), 2),
        "burn_rate_daily": round(float(state.burn_rate_daily), 2),
        "valuation": round(float(state.valuation), 2),
        "cumulative_reward": round(float(state.cumulative_reward), 6),
        "product_maturity": round(float(state.product_maturity), 4),
        "tech_debt": round(float(state.tech_debt), 4),
        "features_shipped": state.features_shipped,
        "employee_count": len(state.employees),
        "customer_count": len(state.customers),
        "investor_count": len(state.investors),
        "competitor_count": len(state.competitors),
    }
    
    # Sort keys for stable JSON
    canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return canonical_json.encode('utf-8')

def hash_state(state: Any) -> bytes:
    """Computes SHA256 of the canonical state payload."""
    return sha256(canonical_payload(state)).digest()
