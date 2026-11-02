# Merz Mapper - current state

> Read this first in every new chat. Update it at the end of significant work.
> Status words: **CONFIRMED** (verified/agreed), **IMPLEMENTED** (code in repo),
> **TESTED** (measured result logged), **PLANNED** (in proposal), **PROPOSED**
> (suggested, not agreed), **UNKNOWN**.

**Last updated:** 2026-11-02 | **Phase:** Proposal + hardware procurement (pre-O1)

## Where things stand
- Repo: folder skeleton, templates, memory docs, Claude Code config (PR #1 merged 2026-11-02). **No ROS 2 code yet.**
- Claude setup: 4 skills enabled on claude.ai (brain, navigation-estimation, perception-jetson, ros2-engineering-skills); Context7 + Consensus connected.
- Nothing is IMPLEMENTED or TESTED. Every robot capability is PLANNED.
- Hardware: chosen (see `HARDWARE_REGISTER.md`), not yet received/integrated.
- Rover model: **UNKNOWN** - blocks URDF, odometry source, power and mounting.

## Key dates
| What | Date | Notes |
| --- | --- | --- |
| D1 proposal | Fri 13 Nov 2026, 14:00 | 3 pages, third person, IEEE |
| G1 / O1 sensors + first manual map | Fri 18 Dec 2026 | last working day before leave |
| Leave (unavailable) | 19 Dec 2026 - ~4 Feb 2027 | |
| D2 poster | 23 Feb 2027 | a Tuesday; slides say "Friday" - confirm |
| O2-O8, G2-G4 | 5 Mar - 7 May 2027 | see proposal Table 1 |
| D3 demo, D4 report | May 2027 | TBC |

## Immediate next tasks (to G1)
1. Confirm rover model + what it includes (encoders? battery? existing computer?).
2. Decide JetPack/ROS 2 distro with supervisor (see OPEN_ISSUES #2).
3. Fix proposal issues before D1 (OPEN_ISSUES #6, #7, #8).
4. Order remaining parts (parts list is missing gamepad, mast, mounts, checkerboard).
5. Flash Jetson, install ROS 2, bring up each sensor one at a time, record bags.

## Active blockers
- Rover model unknown (OPEN_ISSUES #1).
- ROS 2 distro / JetPack undecided (OPEN_ISSUES #2).

## Memory files
`docs/decisions.md` (engineering decisions) | `docs/HARDWARE_REGISTER.md` |
`docs/SOFTWARE_ARCHITECTURE.md` | `docs/OPEN_ISSUES.md` | `docs/RESEARCH_INDEX.md` |
`docs/logbook/` | `docs/meetings/`
