#!/usr/bin/env python
"""Check if optimal threshold is stored in model."""

from src.utils.common import load_object

model = load_object('artifacts/model.pkl')
optimal_threshold = getattr(model, 'optimal_threshold', None)

print(f"Model type: {type(model).__name__}")
print(f"Optimal threshold: {optimal_threshold}")
print(f"Has optimal_threshold attribute: {hasattr(model, 'optimal_threshold')}")
