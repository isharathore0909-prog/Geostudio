# -*- coding: utf-8 -*-
"""
GeoStudio - Forestry Cartographic Visualizer
Renders executive high-resolution 300-DPI summary maps with glassmorphic count badges.
"""

from typing import List, Dict, Any, Tuple
import numpy as np


def render_tree_count_png(
    chm: np.ndarray,
    gt: Tuple[float, ...],
    tree_records: List[Dict[str, Any]],
    total_count: int,
    forest_area_ha: float,
    density_per_ha: float,
    mean_height: float,
    max_height: float,
    label_style: str,
    output_png: str
) -> str:
    """Renders an executive 300-DPI PNG map graphic with floating total count badge."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 10), dpi=300)

    # 1. Extent in coordinates
    h, w = chm.shape
    x_min = gt[0]
    x_max = gt[0] + w * gt[1]
    y_max = gt[3]
    y_min = gt[3] + h * gt[5]

    # 2. Render colorized CHM canopy background
    masked_chm = np.ma.masked_where(chm <= 0.5, chm)
    im = ax.imshow(
        masked_chm,
        extent=[x_min, x_max, y_min, y_max],
        cmap="YlGn",
        origin="upper",
        interpolation="bilinear"
    )

    # 3. Plot Tree Apex Markers
    xs = [t["x"] for t in tree_records]
    ys = [t["y"] for t in tree_records]
    ax.scatter(xs, ys, c="#ef4444", s=18, edgecolors="#ffffff", linewidths=0.5, zorder=4, label="Tree Apex")

    # 4. Individual tree labels with cartographic halo and collision avoidance
    if label_style in ("number", "number_height"):
        import matplotlib.patheffects as pe

        span_x = max(1e-6, x_max - x_min)
        span_y = max(1e-6, y_max - y_min)
        # Minimum spatial separation between label anchors to prevent overlapping
        min_dx = span_x * 0.024
        min_dy = span_y * 0.018

        halo = [pe.withStroke(linewidth=1.8, foreground="#ffffff")]
        placed_positions: List[Tuple[float, float]] = []

        # Prioritize dominant / tallest trees for labeling when dense
        sorted_trees = sorted(tree_records, key=lambda t: t.get("height", 0.0), reverse=True)

        for t in sorted_trees:
            tx, ty = t["x"], t["y"]

            # Check collision with already placed labels
            collides = False
            for px, py in placed_positions:
                if abs(tx - px) < min_dx and abs(ty - py) < min_dy:
                    collides = True
                    break

            if not collides:
                placed_positions.append((tx, ty))
                lbl = f"#{t['id']}" if label_style == "number" else f"#{t['id']} ({t['height']:.1f}m)"
                ax.annotate(
                    lbl,
                    xy=(tx, ty),
                    xytext=(3, 3),
                    textcoords="offset points",
                    fontsize=5.5,
                    fontweight="bold",
                    color="#0f172a",
                    path_effects=halo,
                    zorder=5
                )

    # 5. Floating Executive Total Count Card (Glassmorphic dark aesthetic)
    badge_text = (
        f"PRECISION FORESTRY INVENTORY\n"
        f"-------------------------------------\n"
        f"- Total Tree Count:   {total_count:,} trees\n"
        f"- Survey Stand Area:  {forest_area_ha:.2f} hectares\n"
        f"- Stand Density:      {density_per_ha:.0f} trees / ha\n"
        f"- Mean Canopy Height: {mean_height:.1f} m\n"
        f"- Maximum Tree Height:{max_height:.1f} m"
    )
    ax.text(
        0.03, 0.95, badge_text,
        transform=ax.transAxes,
        fontsize=8.5,
        family="monospace",
        fontweight="bold",
        color="#f8fafc",
        verticalalignment="top",
        bbox=dict(
            boxstyle="round,pad=0.8,rounding_size=0.3",
            facecolor="#0f172a",
            alpha=0.88,
            edgecolor="#38bdf8",
            linewidth=1.5
        ),
        zorder=6
    )

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.032, pad=0.03)
    cbar.set_label("Canopy Height (meters)", fontsize=8, fontweight="bold", color="#0f172a")
    cbar.ax.tick_params(labelsize=7)

    # Styling & Margins
    ax.set_title("GeoStudio - Individual Tree Detection & Stand Inventory", fontsize=11, fontweight="bold", pad=12, color="#0f172a")
    ax.set_xlabel("Easting (X)", fontsize=8, color="#475569")
    ax.set_ylabel("Northing (Y)", fontsize=8, color="#475569")
    ax.tick_params(labelsize=7)
    ax.grid(True, linestyle="--", alpha=0.3, color="#64748b")

    plt.tight_layout()
    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_png
