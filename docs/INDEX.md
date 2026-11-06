# Documentation index

Every document in `docs/`, one line each. Start with [`MERZ_MAPPER_STATE.md`](MERZ_MAPPER_STATE.md).
Status words (CONFIRMED, IMPLEMENTED, TESTED, PLANNED, PROPOSED, UNKNOWN) are defined at the top of the state file.

## State & memory
| Document | What it is for |
| --- | --- |
| [`MERZ_MAPPER_STATE.md`](MERZ_MAPPER_STATE.md) | Current phase, next tasks, blockers, key dates. Read first |
| [`decisions.md`](decisions.md) | Engineering decisions: reason, alternatives, evidence, status |
| [`OPEN_ISSUES.md`](OPEN_ISSUES.md) | Problems, severity and proposed fixes |
| [`CLAUDE_CODE_ROADMAP.md`](CLAUDE_CODE_ROADMAP.md) | The staged plan Claude Code followed to write the software |

## Planning
| Document | What it is for |
| --- | --- |
| [`planning/hardware-arrival-plan.md`](planning/hardware-arrival-plan.md) | Day-by-day plan from parts arrival to May 2027 (when, and why) |
| [`planning/experiments.md`](planning/experiments.md) | Procedure and pass rule for each objective O1-O8 |

## Hardware
| Document | What it is for |
| --- | --- |
| [`HARDWARE_REGISTER.md`](HARDWARE_REGISTER.md) | Confirmed specs, drivers, power and integration status of each part |

## Software
| Document | What it is for |
| --- | --- |
| [`SOFTWARE_ARCHITECTURE.md`](SOFTWARE_ARCHITECTURE.md) | ROS 2 packages, nodes, topics, TF and data flow |
| [`software/database-schema.md`](software/database-schema.md) | The SQLite building database the robot writes and the website reads |
| [`software/safety-review.md`](software/safety-review.md) | Safety and bug review of `ros2_ws` (2026-11-04), with open findings R1-R12 |
| [`website/design-brief.md`](website/design-brief.md) | Design brief for the website demonstrator; screenshots in [`website/screenshots/`](website/screenshots/) |

## Research
| Document | What it is for |
| --- | --- |
| [`RESEARCH_INDEX.md`](RESEARCH_INDEX.md) | Verified sources and key findings. Check here before searching |
| [`research/literature-base.md`](research/literature-base.md) | Literature base for the technical report (IEEE references, relevance) |
| [`research/lit-review-outline.md`](research/lit-review-outline.md) | PROPOSED structure of the report's literature review |
| [`research/distro-decision.md`](research/distro-decision.md) | JetPack, Ubuntu and ROS 2 distro options for the Jetson (OPEN_ISSUES #2) |
| [`research/perception-plan.md`](research/perception-plan.md) | PROPOSED plan for O3: landmark detection and door-sign OCR |

## Runbooks
| Document | What it is for |
| --- | --- |
| [`runbooks/o1-checklist.md`](runbooks/o1-checklist.md) | Checklist from parts arrival to the first manual map (G1 / O1) |
| [`runbooks/jetson-bringup.md`](runbooks/jetson-bringup.md) | Jetson Orin Nano from flashing to all sensors publishing |
| [`runbooks/build-guide.md`](runbooks/build-guide.md) | Commands for each hardware step: build, sensors, calibration, mapping, troubleshooting |

## Logbook & meetings
| Document | What it is for |
| --- | --- |
| [`logbook/`](logbook/) | One entry per day worked; copy [`logbook/TEMPLATE.md`](logbook/TEMPLATE.md) |
| [`meetings/`](meetings/) | Supervisor meeting minutes; copy [`meetings/TEMPLATE.md`](meetings/TEMPLATE.md) |
| [`figures/`](figures/) | Screenshots and plots referred to from logbook entries |

## Archive
| Document | What it is for |
| --- | --- |
| [`archive/`](archive/) | Finished or superseded documents, kept for the project's history; [`archive/README.md`](archive/README.md) says why each is there |
