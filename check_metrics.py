#!/usr/bin/env python
"""Quick script to check model metrics after retraining."""

import json

with open('artifacts/metrics.json', 'r') as f:
    data = json.load(f)

print(f"Model: {data['model_name']}")
print(f"Accuracy: {data['metrics']['accuracy']:.4f} ({100*data['metrics']['accuracy']:.2f}%)")
print(f"F1-Score: {data['metrics']['f1']:.4f}")
print(f"Recall: {data['metrics']['recall']:.4f}")
print(f"Precision: {data['metrics']['precision']:.4f}")
print(f"ROC-AUC: {data['metrics']['roc_auc']:.4f}")
print(f"PR-AUC: {data['metrics']['pr_auc']:.4f}")

print("\nConfusion Matrix:")
cm = data['confusion_matrix']
print(f"  True Negatives: {cm['true_negative']}")
print(f"  False Positives: {cm['false_positive']}")
print(f"  False Negatives: {cm['false_negative']}")
print(f"  True Positives: {cm['true_positive']}")
