"""Figure 2 of the EEE3094 project proposal: Merz Mapper Gantt chart.

Run from any directory:
    python docs/proposal/figures/gantt.py

Writes gantt.png (300 dpi) and gantt.pdf next to this script, sized to fit an
A4 landscape page (297 x 210 mm) inside 20 mm margins, with room for a caption.

Fixed dates (deliverables D1-D4, gateways G1-G4, objective deadlines O1-O8,
planned leave) come from docs/MERZ_MAPPER_STATE.md. Start dates of O2-O8 are
planning choices and may overlap. Easter is shown as a working period; its
dates are approximate (EASTER below) and should be checked against the
university calendar.
"""

from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent

# --- Page geometry --------------------------------------------------------
MM = 1 / 25.4
FIG_W = (297 - 2 * 20) * MM  # 257 mm: full text width on A4 landscape
FIG_H = 150 * MM  # leaves ~20 mm for the caption inside 170 mm

# --- Colours (print-friendly; validated categorical order) -----------------
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#d9d8d4"
PHASE_COLOURS = {
    "research": "#2a78d6",
    "hardware": "#eb6834",
    "poster": "#1baf7a",
    "autonomy": "#eda100",
    "semantic": "#e87ba4",
    "evaluation": "#6250d6",
    "continuous": "#8a8984",
}

# --- Calendar -------------------------------------------------------------
START = date(2026, 10, 1)
END = date(2027, 6, 1)
X_MAX = date(2027, 6, 14)  # room for end-of-May labels
LEAVE = (date(2026, 12, 19), date(2027, 2, 4))  # inclusive
EASTER = (date(2027, 3, 20), date(2027, 4, 18))  # APPROX. - confirm dates

# --- Schedule -------------------------------------------------------------
# Each row: (label, start, end, phase, marker) where marker is None or
# (kind, code) with kind "G" (gateway) or "D" (deliverable), placed at `end`.
# tbc=True draws a hatched bar for dates not yet confirmed.
PHASES = [
    ("Phase 1: Research and proposal", [
        ("Background research and literature review", date(2026, 10, 1), date(2026, 11, 13), None, False),
        ("Project proposal (D1)", date(2026, 10, 19), date(2026, 11, 13), ("D", "D1"), False),
    ], "research"),
    ("Phase 2: Hardware integration (O1)", [
        ("Rover inspection, mast and sensor mounts", date(2026, 11, 9), date(2026, 12, 4), None, False),
        ("Sensor bring-up: LIDAR, D455 + IMU, camera", date(2026, 11, 16), date(2026, 12, 11), None, False),
        ("O1 First manual map and rosbags", date(2026, 12, 1), date(2026, 12, 18), ("G", "G1"), False),
    ], "hardware"),
    ("Phase 3: Poster", [
        ("Poster preparation (D2)", date(2027, 2, 5), date(2027, 2, 23), ("D", "D2"), False),
    ], "poster"),
    ("Phase 4: Autonomy and perception", [
        ("O2 Autonomous mapping (frontier exploration)", date(2027, 2, 5), date(2027, 3, 5), None, False),
        ("O3 Landmark detection + OCR", date(2027, 2, 15), date(2027, 3, 12), None, False),
        ("O4 Fused localisation (EKF)", date(2027, 2, 22), date(2027, 3, 19), ("G", "G2"), False),
    ], "autonomy"),
    ("Phase 5: Semantic map and demonstrator", [
        ("O5 Access zones", date(2027, 3, 8), date(2027, 4, 2), None, False),
        ("O6 Building database + API", date(2027, 3, 15), date(2027, 4, 9), None, False),
        ("O7 Website demonstrator", date(2027, 3, 29), date(2027, 4, 23), ("G", "G3"), False),
    ], "semantic"),
    ("Phase 6: Evaluation and reporting", [
        ("O8 Evaluation: fused vs single-sensor", date(2027, 4, 5), date(2027, 5, 7), ("G", "G4"), False),
        ("Demonstration (D3, date TBC)", date(2027, 5, 3), date(2027, 5, 21), ("D", "D3"), True),
        ("Final report writing (D4, date TBC)", date(2027, 4, 19), date(2027, 5, 28), ("D", "D4"), True),
    ], "evaluation"),
    ("Continuous", [
        ("Logbook + supervisor meetings", date(2026, 10, 1), date(2027, 5, 31), None, False),
    ], "continuous"),
]


def num(d):
    return mdates.date2num(d)


def build():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 7.5,
        "axes.edgecolor": INK_2,
        "axes.linewidth": 0.6,
        "pdf.fonttype": 42,  # embed TrueType so text stays selectable
    })
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    # Build rows top to bottom: phase header, then its tasks.
    rows = []  # (label, kind, payload)
    for title, tasks, phase in PHASES:
        rows.append((title, "header", phase))
        for t in tasks:
            rows.append((t[0], "task", (t, phase)))
    n = len(rows)
    y_of = {i: n - 1 - i for i in range(n)}

    # Background spans: leave (unavailable) and Easter (working).
    ax.axvspan(num(LEAVE[0]), num(LEAVE[1] + timedelta(days=1)), facecolor="#e6e5e1",
               hatch="////", edgecolor="#b3b2ad", linewidth=0, zorder=0)
    ax.axvspan(num(EASTER[0]), num(EASTER[1] + timedelta(days=1)), facecolor="#f3f2ee",
               edgecolor="none", zorder=0)
    mid_leave = LEAVE[0] + (LEAVE[1] - LEAVE[0]) / 2
    ax.text(num(mid_leave), n - 0.35, "Unavailable –\nplanned leave",
            ha="center", va="top", fontsize=7, color=INK, fontweight="bold",
            bbox=dict(facecolor="white", edgecolor="#b3b2ad", linewidth=0.5, pad=2), zorder=5)
    mid_easter = EASTER[0] + (EASTER[1] - EASTER[0]) / 2
    ax.text(num(mid_easter), n - 0.35, "Easter vacation\n(working period)",
            ha="center", va="top", fontsize=6.5, color=INK_2, zorder=5)

    bar_h = 0.56
    for i, (label, kind, payload) in enumerate(rows):
        y = y_of[i]
        if kind == "header":
            continue
        (name, s, e, marker, tbc), phase = payload
        colour = PHASE_COLOURS[phase]
        left, width = num(s), num(e + timedelta(days=1)) - num(s)
        if tbc:
            ax.barh(y, width, left=left, height=bar_h, color="white", edgecolor=colour,
                    hatch="xxxx", linewidth=0.9, zorder=3)
        else:
            ax.barh(y, width, left=left, height=bar_h, color=colour, edgecolor=INK,
                    linewidth=0.5, zorder=3)
        # End-date label for objective rows, and leave break on the continuous bar.
        if name.startswith("O"):
            dx_date = 4.5 if marker else 1.2  # clear the gateway diamond
            ax.text(num(e + timedelta(days=1)) + dx_date, y, f"{e.day} {e:%b}",
                    va="center", ha="left", fontsize=6.3, color=INK_2, zorder=6)
        if marker:
            mk, code = marker
            x = num(e + timedelta(days=1))
            if mk == "G":
                ax.plot(x, y, marker="D", markersize=7.5, color=INK, markeredgecolor="white",
                        markeredgewidth=0.8, zorder=7)
            else:
                ax.plot(x, y, marker="v", markersize=8.5, color="white", markeredgecolor=INK,
                        markeredgewidth=1.2, zorder=7)
            dx = 17 if name.startswith("O") else 3.0
            txt = code + (" TBC" if tbc else "")
            ax.text(x + dx, y, txt, va="center", ha="left", fontsize=7, fontweight="bold",
                    color=INK, zorder=7)

    # Y axis: task names, phase headers in bold.
    ax.set_yticks([y_of[i] for i in range(n)])
    ax.set_yticklabels([r[0] for r in rows])
    for i, tick in enumerate(ax.get_yticklabels()):
        if rows[i][1] == "header":
            tick.set_fontweight("bold")
            tick.set_color(INK)
        else:
            tick.set_color(INK_2)
    for i, r in enumerate(rows):
        if r[1] == "header" and i > 0:
            ax.axhline(y_of[i] + 0.5, color=GRID, linewidth=0.6, zorder=1)
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(-0.7, n - 0.2)

    # X axis: months, with week minor ticks.
    ax.set_xlim(num(START), num(X_MAX))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.tick_top()
    ax.grid(axis="x", which="major", color=GRID, linewidth=0.7, zorder=1)
    ax.grid(axis="x", which="minor", color=GRID, linewidth=0.3, linestyle=":", zorder=1)
    for side in ("right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # Legend.
    handles = [
        Patch(facecolor=PHASE_COLOURS["research"], edgecolor=INK, linewidth=0.5, label="Research + proposal"),
        Patch(facecolor=PHASE_COLOURS["hardware"], edgecolor=INK, linewidth=0.5, label="Hardware (O1)"),
        Patch(facecolor=PHASE_COLOURS["poster"], edgecolor=INK, linewidth=0.5, label="Poster"),
        Patch(facecolor=PHASE_COLOURS["autonomy"], edgecolor=INK, linewidth=0.5, label="Autonomy + perception (O2–O4)"),
        Patch(facecolor=PHASE_COLOURS["semantic"], edgecolor=INK, linewidth=0.5, label="Semantic map + website (O5–O7)"),
        Patch(facecolor=PHASE_COLOURS["evaluation"], edgecolor=INK, linewidth=0.5, label="Evaluation + report (O8)"),
        Patch(facecolor="white", edgecolor=PHASE_COLOURS["evaluation"], hatch="xxxx", label="Date to be confirmed (TBC)"),
        Patch(facecolor="#e6e5e1", edgecolor="#b3b2ad", hatch="////", label="Unavailable – planned leave"),
        Patch(facecolor="#f3f2ee", edgecolor="#d9d8d4", label="Easter vacation (working)"),
        Line2D([], [], marker="D", linestyle="none", color=INK, markeredgecolor="white", markersize=7, label="Gateway (G1–G4)"),
        Line2D([], [], marker="v", linestyle="none", color="white", markeredgecolor=INK, markeredgewidth=1.2, markersize=8, label="Deliverable (D1–D4)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=6.6,
               handlelength=1.6, columnspacing=1.2, bbox_to_anchor=(0.5, 0.0))

    fig.subplots_adjust(left=0.27, right=0.985, top=0.9, bottom=0.15)
    for ext, kw in (("png", {"dpi": 300}), ("pdf", {})):
        fig.savefig(OUT_DIR / f"gantt.{ext}", facecolor="white", **kw)
    plt.close(fig)


if __name__ == "__main__":
    build()
    print(f"Wrote {OUT_DIR / 'gantt.png'} and {OUT_DIR / 'gantt.pdf'}")
