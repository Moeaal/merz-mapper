"""Figure 1 of the EEE3094 project proposal: Merz Mapper system architecture.

Run from any directory:
    python docs/proposal/figures/architecture.py

Writes architecture.png (300 dpi) and architecture.pdf next to this script,
sized to the 170 mm text width of an A4 portrait page with 20 mm margins.

Blocks follow docs/SOFTWARE_ARCHITECTURE.md (data flow). The odometry source is
deliberately left open: OPEN_ISSUES #15 / decisions #10 are unresolved, so it is
drawn with a dashed border and labelled TBC.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
MM = 1 / 25.4
W, H = 170, 118  # mm; drawing units are millimetres

INK = "#0b0b0b"
INK_2 = "#52514e"
SENSOR = "#dbe8f8"   # light blue: sensors
ROS = "#ffffff"      # white: ROS 2 nodes
DATA = "#f3f2ee"     # warm grey: data store
WEB = "#ffffff"
ROBOT_EDGE = "#1c5cab"
DEMO_EDGE = "#8a8984"

FS = 6.1  # body font size (pt)


def box(ax, x, y, w, h, text, fc=ROS, ec=INK, lw=0.7, ls="-", bold_first=True, fs=FS):
    """Rounded box centred on (x, y). First line bold."""
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0,rounding_size=1.2",
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=3))
    lines = text.split("\n")
    if bold_first and len(lines) > 1:
        nb = len(lines) - 1
        top = y + (nb * 2.3 + 2.6) / 2  # centre the title + body block
        ax.text(x, top, lines[0], ha="center", va="top",
                fontsize=fs, fontweight="bold", color=INK, zorder=4)
        ax.text(x, top - 3.0, "\n".join(lines[1:]), ha="center", va="top",
                fontsize=fs - 0.8, color=INK_2, zorder=4, linespacing=1.15)
    else:
        ax.text(x, y, text, ha="center", va="center", fontsize=fs, fontweight="bold",
                color=INK, zorder=4)
    return dict(x=x, y=y, w=w, h=h)


def side(b, where, t=0.5):
    """Point on a box edge: where in l/r/t/b, t = fraction along the edge."""
    x0, y0 = b["x"] - b["w"] / 2, b["y"] - b["h"] / 2
    if where == "l":
        return (x0, y0 + t * b["h"])
    if where == "r":
        return (x0 + b["w"], y0 + t * b["h"])
    if where == "t":
        return (x0 + t * b["w"], y0 + b["h"])
    return (x0 + t * b["w"], y0)


def arrow(ax, p, q, label=None, rad=0.0, ls="-", lpos=0.5, loff=(0, 1.2), color=INK, fs=5.4):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7, lw=0.7,
                                 color=color, ls=ls, shrinkA=0.5, shrinkB=0.5,
                                 connectionstyle=f"arc3,rad={rad}", zorder=2))
    if label:
        mx = p[0] + (q[0] - p[0]) * lpos + loff[0]
        my = p[1] + (q[1] - p[1]) * lpos + loff[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=fs, color=INK_2,
                style="italic", zorder=5,
                bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.9))


def container(ax, x0, y0, x1, y1, title, ec, lw, ls="-", fc="none", title_fs=7.0, title_x=None,
              bottom=False):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                                boxstyle="round,pad=0,rounding_size=2.0",
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=1))
    ax.text(title_x if title_x is not None else x0 + 2.5, y0 + 2.2 if bottom else y1 - 2.2, title,
            ha="left", va="bottom" if bottom else "top",
            fontsize=title_fs, fontweight="bold", color=ec if ec != INK else INK, zorder=4)


def build():
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})
    fig = plt.figure(figsize=(W * MM, H * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")

    # --- Containers -------------------------------------------------------
    container(ax, 1.0, 22.0, 132.0, 116.5,
              "ROBOT  –  main contribution (autonomous mapping rover)",
              ROBOT_EDGE, 1.8)
    ax.text(3.5, 108.6, "Sensors", fontsize=6.8, fontweight="bold", color=INK_2, va="center")
    container(ax, 40.0, 26.0, 130.0, 111.0, "ROS 2 on Jetson Orin Nano", INK, 0.8,
              fc="#fafaf8", title_fs=6.8, bottom=True)
    container(ax, 135.5, 3.0, 169.5, 55.0, "Demonstrator", DEMO_EDGE, 1.2, ls=(0, (4, 2)),
              title_fs=6.4, title_x=137.0)

    # --- Sensors (x centre 21) --------------------------------------------
    sw, sh = 30, 11.5
    lidar = box(ax, 19, 95, sw, sh, "RPLIDAR S2\n2D laser scanner, 360°", fc=SENSOR)
    odom = box(ax, 19, 78, sw, 13.5,
               "Odometry\nwheel encoders or LIDAR\nscan matching – TBC", fc="white", ls=(0, (3, 1.5)))
    d455 = box(ax, 19, 59, sw, 13.5, "RealSense D455\ndepth + colour camera,\nbuilt-in IMU", fc=SENSOR)
    cam = box(ax, 19, 39, sw, 11.5, "Sign camera\n1080p USB camera", fc=SENSOR)

    # --- ROS 2 nodes (3 columns) -------------------------------------------
    c1, c2, c3 = 55, 85, 115
    nw, nh = 26, 13
    slam = box(ax, c1, 95, nw, nh, "SLAM Toolbox\n2D occupancy map\n+ robot pose")
    nav = box(ax, c2, 95, nw, nh, "Nav2 + frontier\nexploration;\nmotor commands")
    zones = box(ax, c3, 95, nw, nh, "Access-zone builder\nreachable rooms\nper entrance")
    ekf = box(ax, c1, 72, nw, nh, "robot_localization\nEKF: fuses\nodometry + IMU")
    fuse = box(ax, c3, 72, nw, nh, "Landmark fusion\nmerges repeated\nsightings (map frame)")
    yolo = box(ax, c1, 42, nw, nh, "YOLO (TensorRT)\nsign / door / landmark\ndetection")
    ocr = box(ax, c2, 42, nw, nh, "PaddleOCR\nroom-number and\nsign text")

    # --- Data + demonstrator ----------------------------------------------
    db = box(ax, 152.5, 80, 30, 16, "Building database\nSQLite: map, rooms,\nlandmarks, zones,\njunction photos", fc=DATA)
    api = box(ax, 152.5, 31, 29, 11, "FastAPI\nroute + room queries")
    web = box(ax, 152.5, 13, 29, 13, "Website\nphone map, opened\nby entrance QR code")

    # --- Arrows -------------------------------------------------------------
    arrow(ax, side(lidar, "r"), side(slam, "l"), "scans", loff=(0, 1.6))
    arrow(ax, side(lidar, "b", 0.85), side(odom, "t", 0.85), ls=(0, (2, 1.5)))
    ax.text(side(lidar, "b", 0.85)[0] - 1.8, 86.6, "if scan\nmatching", fontsize=4.9, color=INK_2,
            ha="right", va="center", style="italic")
    arrow(ax, side(odom, "r"), side(ekf, "l", 0.7), "velocity", loff=(0, 1.5))
    arrow(ax, side(d455, "r", 0.75), side(ekf, "l", 0.25), "IMU", lpos=0.45, loff=(0, 1.4))
    arrow(ax, side(d455, "r", 0.25), side(yolo, "l", 0.75), "colour\n+ depth", lpos=0.5, loff=(0.5, 2.3))
    arrow(ax, side(cam, "r"), side(yolo, "l", 0.25), "images", lpos=0.5, loff=(0, -1.8))
    arrow(ax, side(ekf, "t"), side(slam, "b"), "odom → base_link", loff=(0, 0))
    arrow(ax, side(slam, "r"), side(nav, "l"), "map", loff=(0, 1.8), fs=4.9)
    arrow(ax, side(slam, "t", 0.75), side(zones, "t", 0.25), "saved map", rad=-0.35, lpos=0.5, loff=(0, 5.3))
    arrow(ax, side(slam, "b", 0.85), side(fuse, "l", 0.75), "robot pose", lpos=0.55, loff=(0, 1.6))
    arrow(ax, side(yolo, "r"), side(ocr, "l"), "crops", loff=(0, 1.8), fs=4.9)
    arrow(ax, side(yolo, "t", 0.85), side(fuse, "l", 0.2), "3D detections", lpos=0.55, loff=(0, -1.8))
    arrow(ax, side(ocr, "r"), side(fuse, "b", 0.5), "text", lpos=0.5, loff=(2.5, -1.0))
    arrow(ax, side(zones, "r"), side(db, "l", 0.8), None)
    arrow(ax, side(fuse, "r"), side(db, "l", 0.2), None)
    arrow(ax, side(db, "b", 0.78), side(api, "t", 0.78), "after\neach run", lpos=0.25, loff=(-8.0, 0))
    arrow(ax, side(api, "b"), side(web, "t"), None)

    # --- Key ----------------------------------------------------------------
    ky = 12.0
    ax.add_patch(FancyBboxPatch((3, ky - 1.6), 7, 3.2, boxstyle="round,pad=0,rounding_size=0.8",
                                fc="none", ec=ROBOT_EDGE, lw=1.8))
    ax.text(12, ky, "Robot: main contribution", fontsize=5.8, va="center", color=INK)
    ax.add_patch(FancyBboxPatch((52, ky - 1.6), 7, 3.2, boxstyle="round,pad=0,rounding_size=0.8",
                                fc="none", ec=DEMO_EDGE, lw=1.2, ls=(0, (4, 2))))
    ax.text(61, ky, "Demonstrator", fontsize=5.8, va="center", color=INK)
    ax.add_patch(FancyBboxPatch((3, ky - 8.6), 7, 3.2, boxstyle="round,pad=0,rounding_size=0.8",
                                fc=SENSOR, ec=INK, lw=0.7))
    ax.text(12, ky - 7, "Sensor", fontsize=5.8, va="center", color=INK)
    ax.add_patch(FancyBboxPatch((29, ky - 8.6), 7, 3.2, boxstyle="round,pad=0,rounding_size=0.8",
                                fc="white", ec=INK, lw=0.7, ls=(0, (3, 1.5))))
    ax.text(38, ky - 7, "Not yet decided (TBC)", fontsize=5.8, va="center", color=INK)
    ax.add_patch(FancyBboxPatch((76, ky - 8.6), 7, 3.2, boxstyle="round,pad=0,rounding_size=0.8",
                                fc="white", ec=INK, lw=0.7))
    ax.text(85, ky - 7, "ROS 2 node / software", fontsize=5.8, va="center", color=INK)

    for ext, kw in (("png", {"dpi": 300}), ("pdf", {})):
        fig.savefig(OUT_DIR / f"architecture.{ext}", facecolor="white", **kw)
    plt.close(fig)


if __name__ == "__main__":
    build()
    print(f"Wrote {OUT_DIR / 'architecture.png'} and {OUT_DIR / 'architecture.pdf'}")
