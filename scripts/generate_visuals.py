"""
Generate visual assets for README and documentation.

Creates:
  - ROC curve plot
  - Precision-Recall curve plot
  - Confusion matrix heatmap
  - Feature importance chart (from notebook summary)
  - Churn distribution chart

Usage:
    python scripts/generate_visuals.py
"""

import json
import os
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Paths ──
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_PATH = os.path.join(ROOT, "artifacts", "metrics.json")
SUMMARY_PATH = os.path.join(ROOT, "notebooks", "artifacts", "notebook_summary.json")
OUT_DIR = os.path.join(ROOT, "docs", "images")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Style ──
COLORS = {
    "primary": "#2563EB",
    "secondary": "#7C3AED",
    "accent": "#059669",
    "danger": "#DC2626",
    "warning": "#D97706",
    "bg": "#FAFBFC",
    "grid": "#E5E7EB",
    "text": "#1F2937",
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 12,
    "figure.facecolor": COLORS["bg"],
    "axes.facecolor": "white",
    "axes.edgecolor": COLORS["grid"],
    "axes.grid": True,
    "grid.color": COLORS["grid"],
    "grid.alpha": 0.5,
})


def load_metrics():
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_summary():
    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ───────────────────────────────────────────────
# 1. ROC Curve
# ───────────────────────────────────────────────
def plot_roc_curve(data):
    curves = data.get("curves", {})
    roc = curves.get("roc", {})
    fpr = roc.get("fpr", [])
    tpr = roc.get("tpr", [])
    auc_val = data["metrics"]["roc_auc"]
    model_name = data["model_name"]

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(fpr, tpr, color=COLORS["primary"], linewidth=2.5,
            label=f"{model_name} (AUC = {auc_val:.4f})")
    ax.plot([0, 1], [0, 1], color=COLORS["grid"], linewidth=1.5,
            linestyle="--", label="Random (AUC = 0.50)")
    ax.fill_between(fpr, tpr, alpha=0.08, color=COLORS["primary"])

    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve")
    ax.legend(loc="lower right", frameon=True, fancybox=True, shadow=False)
    ax.set_xlim([-0.01, 1.01])
    ax.set_ylim([-0.01, 1.01])

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "roc_curve.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path}")


# ───────────────────────────────────────────────
# 2. Precision-Recall Curve
# ───────────────────────────────────────────────
def plot_pr_curve(data):
    curves = data.get("curves", {})
    pr = curves.get("pr", {})
    precision = pr.get("precision", [])
    recall = pr.get("recall", [])
    pr_auc = data["metrics"]["pr_auc"]
    model_name = data["model_name"]

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(recall, precision, color=COLORS["secondary"], linewidth=2.5,
            label=f"{model_name} (PR-AUC = {pr_auc:.4f})")
    ax.axhline(y=data.get("churn_rate", 0.265), color=COLORS["warning"],
               linewidth=1.5, linestyle="--", label=f"Baseline (churn rate ≈ 26.5%)")
    ax.fill_between(recall, precision, alpha=0.08, color=COLORS["secondary"])

    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve")
    ax.legend(loc="upper right", frameon=True, fancybox=True, shadow=False)
    ax.set_xlim([-0.01, 1.01])
    ax.set_ylim([0, 1.05])

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "pr_curve.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path}")


# ───────────────────────────────────────────────
# 3. Confusion Matrix
# ───────────────────────────────────────────────
def plot_confusion_matrix(data):
    cm = data["confusion_matrix"]
    matrix = np.array(cm["matrix"])
    labels = ["No Churn", "Churn"]
    total = matrix.sum()

    fig, ax = plt.subplots(figsize=(6, 5))
    cmap = plt.cm.Blues
    im = ax.imshow(matrix, interpolation="nearest", cmap=cmap, aspect="auto")

    thresh = matrix.max() / 2.0
    for i in range(2):
        for j in range(2):
            count = matrix[i, j]
            pct = count / total * 100
            ax.text(j, i, f"{count}\n({pct:.1f}%)",
                    ha="center", va="center", fontsize=13, fontweight="bold",
                    color="white" if count > thresh else COLORS["text"])

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted Label", fontsize=12)
    ax.set_ylabel("True Label", fontsize=12)
    ax.set_title("Confusion Matrix")

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "confusion_matrix.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path}")


# ───────────────────────────────────────────────
# 4. Feature Importance (from Welch t-test)
# ───────────────────────────────────────────────
def plot_feature_importance(summary):
    welch = summary.get("top_welch_ttest", [])
    if not welch:
        print("  ⚠ No Welch t-test data found")
        return

    features = [w["feature"] for w in welch][:10]
    t_stats = [abs(w["t_stat"]) for w in welch][:10]

    # Normalize
    max_t = max(t_stats) if t_stats else 1
    importance = [t / max_t for t in t_stats]

    # Reverse for horizontal bar chart (top feature at top)
    features = features[::-1]
    importance = importance[::-1]

    # Color gradient
    colors = [plt.cm.Blues(0.4 + 0.6 * v) for v in importance]

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.barh(features, importance, color=colors, edgecolor="white", height=0.6)

    for bar, val in zip(bars, importance):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=10, color=COLORS["text"])

    ax.set_xlabel("Relative Importance (normalized |t-stat|)")
    ax.set_title("Top 10 Features — Statistical Significance")
    ax.set_xlim([0, 1.15])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "feature_importance.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path}")


# ───────────────────────────────────────────────
# 5. Churn Distribution
# ───────────────────────────────────────────────
def plot_churn_distribution(summary):
    churn_rate = summary.get("churn_rate", 0.265)
    no_churn = 1 - churn_rate

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(
        ["No Churn", "Churn"],
        [no_churn * 100, churn_rate * 100],
        color=[COLORS["primary"], COLORS["danger"]],
        width=0.5,
        edgecolor="white",
    )

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height + 1,
                f"{height:.1f}%", ha="center", va="bottom",
                fontsize=14, fontweight="bold", color=COLORS["text"])

    ax.set_ylabel("Percentage (%)")
    ax.set_title("Target Distribution — Imbalanced Dataset")
    ax.set_ylim([0, 100])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "churn_distribution.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path}")


# ───────────────────────────────────────────────
# 6. Model Metrics Summary Card
# ───────────────────────────────────────────────
def plot_metrics_card(data):
    metrics = data["metrics"]
    model_name = data["model_name"]

    names = ["Accuracy", "Precision", "Recall", "F1 Score", "ROC-AUC", "PR-AUC"]
    values = [
        metrics["accuracy"],
        metrics["precision"],
        metrics["recall"],
        metrics["f1"],
        metrics["roc_auc"],
        metrics["pr_auc"],
    ]

    fig, ax = plt.subplots(figsize=(8, 4))

    colors_list = [COLORS["primary"], COLORS["secondary"], COLORS["accent"],
                   COLORS["danger"], COLORS["warning"], "#6366F1"]
    bars = ax.barh(names[::-1], [v * 100 for v in values[::-1]],
                   color=colors_list[::-1], height=0.55, edgecolor="white")

    for bar, val in zip(bars, values[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{val * 100:.1f}%", va="center", fontsize=11,
                fontweight="bold", color=COLORS["text"])

    ax.set_xlim([0, 105])
    ax.set_title(f"Model Performance — {model_name}")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "model_metrics.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path}")


# ───────────────────────────────────────────────
# 7. Pipeline Architecture Diagram
# ───────────────────────────────────────────────
def plot_architecture():
    """Create a clean pipeline architecture diagram."""
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Title
    ax.text(6, 7.5, "Churn Risk Platform — System Architecture",
            ha="center", va="center", fontsize=16, fontweight="bold",
            color=COLORS["text"])

    # ── Pipeline boxes ──
    boxes = [
        # (x, y, w, h, label, sublabel, color)
        (0.3, 5.5, 2.2, 1.2, "Data\nIngestion", "CSV / NPZ\nTrain-Test Split", COLORS["primary"]),
        (3.2, 5.5, 2.2, 1.2, "Data\nTransformation", "Cleaning\nFeature Eng.", COLORS["secondary"]),
        (6.1, 5.5, 2.2, 1.2, "Model\nTraining", "GridSearchCV\n4 Algorithms", COLORS["accent"]),
        (9.0, 5.5, 2.2, 1.2, "Model\nEvaluation", "Metrics\nCurves", COLORS["warning"]),
        (0.3, 2.5, 2.2, 1.2, "Drift\nDetection", "KS Test\nPSI", "#8B5CF6"),
        (3.2, 2.5, 2.2, 1.2, "Prediction\nLogger", "JSONL Logs\nStatistics", "#EC4899"),
        (6.1, 2.5, 2.2, 1.2, "FastAPI\nService", "REST API\n11 Endpoints", COLORS["danger"]),
        (9.0, 2.5, 2.2, 1.2, "Retrain\nPipeline", "Auto / Manual\nScheduled", "#14B8A6"),
    ]

    for (x, y, w, h, label, sublabel, color) in boxes:
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.1",
            facecolor=color, alpha=0.15, edgecolor=color, linewidth=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.65, label, ha="center", va="center",
                fontsize=10, fontweight="bold", color=color)
        ax.text(x + w / 2, y + h * 0.2, sublabel, ha="center", va="center",
                fontsize=8, color=COLORS["text"], alpha=0.7)

    # ── Arrows (top row) ──
    arrow_props = dict(arrowstyle="->", color=COLORS["text"], lw=1.5)
    for x_start in [2.5, 5.4, 8.3]:
        ax.annotate("", xy=(x_start + 0.7, 6.1), xytext=(x_start, 6.1),
                     arrowprops=arrow_props)

    # ── Vertical arrows ──
    ax.annotate("", xy=(7.2, 5.5), xytext=(7.2, 3.7),
                arrowprops=dict(arrowstyle="<->", color=COLORS["text"], lw=1.5))

    # ── Labels for layers ──
    ax.text(6, 7.0, "Training Pipeline", ha="center", va="center",
            fontsize=11, color=COLORS["primary"], fontstyle="italic")
    ax.text(6, 4.1, "Production Services", ha="center", va="center",
            fontsize=11, color=COLORS["danger"], fontstyle="italic")

    # ── Dashed connection lines (bottom row) ──
    for x_start in [2.5, 5.4, 8.3]:
        ax.plot([x_start, x_start + 0.7], [3.1, 3.1],
                color=COLORS["grid"], linewidth=1.5, linestyle="--")

    # ── Tech stack footer ──
    ax.text(6, 0.7, "Python  ·  FastAPI  ·  scikit-learn  ·  XGBoost  ·  Docker  ·  GitHub Actions",
            ha="center", va="center", fontsize=10, color=COLORS["text"],
            alpha=0.6, fontstyle="italic")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "architecture.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    print(f"  ✅ {path}")


# ───────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────
if __name__ == "__main__":
    print("🎨 Generating visual assets for README...\n")

    data = load_metrics()
    summary = load_summary()

    # Add churn rate to data for PR curve baseline
    data["churn_rate"] = summary.get("churn_rate", 0.265)

    plot_roc_curve(data)
    plot_pr_curve(data)
    plot_confusion_matrix(data)
    plot_feature_importance(summary)
    plot_churn_distribution(summary)
    plot_metrics_card(data)
    plot_architecture()

    print(f"\n✅ All visuals saved to {OUT_DIR}")
