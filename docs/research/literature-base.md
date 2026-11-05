# Literature base for the EEE3094 technical report

**Compiled:** 2026-11-05 on branch `lit-review`. **Status:** sources verified at metadata level (see "How each
source was checked"); none of the papers below has been read in full for this file. Read the paper before quoting
a result from it in the report.

Objectives referred to (from `docs/planning/experiments.md`):
**O1** sensors + first manual map | **O2** autonomous exploration: coverage and wall accuracy | **O3** door-sign
reading | **O4** landmark position error | **O5** entrance access zones | **O6** query time | **O7** route
correctness | **O8** fused against single-sensor comparison.

## How each source was checked
- This session's network blocked direct fetches of doi.org, arXiv, Crossref, OpenAlex and publisher pages, so every
  entry was checked through web-search results that quote publisher pages (IEEE Xplore, Springer, Elsevier, MDPI,
  SAGE, ACM, CVF, AAAI), dblp, institutional repositories, PubMed/PMC or the arXiv listing, plus the Consensus paper
  index. Where two such sources agreed on authors, venue, volume, pages and DOI, the entry is treated as verified.
- **UNVERIFIED** marks any field that no source confirmed, or where sources disagreed. Fill these in from the DOI
  landing page before submission. No field has been guessed.
- Summaries are written from abstracts and search snippets, in my own words. They describe what each paper claims,
  not what this project has reproduced.
- Accessed: 2026-11-05 for every entry.
- Tags `LB-x.y` are used in `docs/RESEARCH_INDEX.md`. Topic numbers follow the task brief.

---

## 1. 2D LIDAR SLAM (graph-based; SLAM Toolbox, Cartographer, GMapping)

**LB-1.1** G. Grisetti, C. Stachniss, and W. Burgard, "Improved techniques for grid mapping with Rao-Blackwellized
particle filters," *IEEE Trans. Robot.*, vol. 23, no. 1, pp. 34–46, 2007.
DOI: [10.1109/TRO.2006.889486](https://doi.org/10.1109/TRO.2006.889486)
- *Summary:* The GMapping paper. A Rao-Blackwellised particle filter builds an occupancy grid; the proposal
  distribution uses the latest scan as well as odometry, and adaptive resampling keeps the particle count low.
- *Relevance:* The standard filter-based baseline that graph-based SLAM Toolbox is usually compared with. GMapping
  leans on odometry for its proposal, which matters for a rover with no wheel encoders.
- *Supports:* O1, O2.

**LB-1.2** G. Grisetti, R. Kümmerle, C. Stachniss, and W. Burgard, "A tutorial on graph-based SLAM," *IEEE Intell.
Transp. Syst. Mag.*, vol. 2, no. 4, pp. 31–43, 2010.
DOI: [10.1109/MITS.2010.939925](https://doi.org/10.1109/MITS.2010.939925)
- *Summary:* Explains SLAM as a pose graph: nodes are poses, edges are constraints from odometry or scan matching,
  and the map comes from a sparse least-squares solve. Written so readers can implement it.
- *Relevance:* The clearest citation for the graph-based formulation that SLAM Toolbox and Cartographer both use;
  good for the background paragraph.
- *Supports:* O1, O2.

**LB-1.3** K. Konolige, G. Grisetti, R. Kümmerle, W. Burgard, B. Limketkai, and R. Vincent, "Efficient sparse pose
adjustment for 2D mapping," in *Proc. IEEE/RSJ Int. Conf. Intell. Robots Syst. (IROS)*, Taipei, Taiwan, 2010,
pp. 22–29. DOI: [10.1109/IROS.2010.5649043](https://doi.org/10.1109/IROS.2010.5649043)
- *Summary:* Introduces Sparse Pose Adjustment (SPA), a fast way to build and solve the linear system in 2D pose-graph
  optimisation, and reports faster convergence than indirect methods.
- *Relevance:* SPA is the optimiser behind Karto SLAM, from which SLAM Toolbox was developed; links the tool used in
  this project to the peer-reviewed method.
- *Supports:* O1, O2.

**LB-1.4** W. Hess, D. Kohler, H. Rapp, and D. Andor, "Real-time loop closure in 2D LIDAR SLAM," in *Proc. IEEE Int.
Conf. Robot. Autom. (ICRA)*, Stockholm, Sweden, 2016, pp. 1271–1278.
DOI: [10.1109/ICRA.2016.7487258](https://doi.org/10.1109/ICRA.2016.7487258)
- *Summary:* The Cartographer paper. Scans are matched to local submaps, and loop closures are found in real time by
  branch-and-bound scan-to-submap matching; maps at 5 cm resolution are reported.
- *Relevance:* The main alternative to SLAM Toolbox in ROS 2; needed to justify the choice of SLAM Toolbox.
- *Supports:* O1, O2.

**LB-1.5** S. Macenski and I. Jambrecic, "SLAM Toolbox: SLAM for the dynamic world," *J. Open Source Softw.*,
vol. 6, no. 61, Art. no. 2783, 2021. DOI: [10.21105/joss.02783](https://doi.org/10.21105/joss.02783)
- *Summary:* Describes SLAM Toolbox: graph-based 2D SLAM with synchronous and asynchronous modes, map serialisation,
  continued mapping on a saved map, and lifelong mapping. It became the default SLAM package for ROS 2 Navigation.
- *Relevance:* The SLAM package used on the rover (`merz_bringup/config/slam.yaml`). Cite this, not the GitHub page.
- *Supports:* O1, O2, O5.

**LB-1.6** J. M. Santos, D. Portugal, and R. P. Rocha, "An evaluation of 2D SLAM techniques available in Robot
Operating System," in *Proc. IEEE Int. Symp. Safety, Security, Rescue Robot. (SSRR)*, Linköping, Sweden, 2013,
pp. 1–6. DOI: [10.1109/SSRR.2013.6719348](https://doi.org/10.1109/SSRR.2013.6719348)
- *Summary:* Compares HectorSLAM, GMapping, KartoSLAM, CoreSLAM and LagoSLAM in ROS, in simulation and on a real
  robot, by comparing maps with ground truth.
- *Relevance:* A widely cited ROS 1 comparison; shows the map-to-ground-truth method this project reuses for O2.
  Predates SLAM Toolbox and Cartographer.
- *Supports:* O2.

**LB-1.7** R. Yagfarov, M. Ivanou, and I. Afanasyev, "Map comparison of lidar-based 2D SLAM algorithms using precise
ground truth," in *Proc. 15th Int. Conf. Control, Autom., Robot. Vis. (ICARCV)*, Singapore, 2018, pp. 1979–1983.
DOI: [10.1109/ICARCV.2018.8581131](https://doi.org/10.1109/ICARCV.2018.8581131)
- *Summary:* Compares 2D LIDAR SLAM packages (including GMapping, Hector and Cartographer) against a ground-truth map
  built with a FARO laser tracker, rather than against a floor plan.
- *Relevance:* Shows how to build a trustworthy ground truth for map error, directly relevant to the O2 wall-error
  test and to OPEN_ISSUES #14 (floor plan or laser survey).
- *Supports:* O2.

**LB-1.8** C. Cadena *et al.*, "Past, present, and future of simultaneous localization and mapping: Toward the
robust-perception age," *IEEE Trans. Robot.*, vol. 32, no. 6, pp. 1309–1332, 2016.
DOI: [10.1109/TRO.2016.2624754](https://doi.org/10.1109/TRO.2016.2624754)
- *Summary:* A broad survey of SLAM: the factor-graph formulation, robustness, scalability, and semantic SLAM as an
  open direction.
- *Relevance:* The standard survey citation; frames semantic mapping (topics 3 and 7) as a recognised open problem.
- *Supports:* O1, O2, O4.

**LB-1.9** S. Kohlbrecher, O. von Stryk, J. Meyer, and U. Klingauf, "A flexible and scalable SLAM system with full 3D
motion estimation," in *Proc. IEEE Int. Symp. Safety, Security, Rescue Robot. (SSRR)*, Kyoto, Japan, 2011.
Pages: UNVERIFIED. DOI: UNVERIFIED. Author PDF:
<https://web.sim.informatik.tu-darmstadt.de/publ/download/2011_SSRR_KohlbrecherMeyerStrykKlingauf_Flexible_SLAM_System.pdf>
- *Summary:* Hector SLAM: matches each scan directly to the occupancy grid, so it needs no wheel odometry, and
  combines this with a full 3D motion estimate (as the title states).
  (Method details not yet checked against the paper.)
- *Relevance:* Proof that 2D LIDAR SLAM can run without wheel odometry; useful context for decisions #10 (no
  encoders). Fix the DOI and pages before citing.
- *Supports:* O1, O8.

**Gap noted:** no peer-reviewed real-robot comparison of SLAM Toolbox against Cartographer was found. The ones found
are a 2025 ResearchGate preprint ("From simulation to reality: Comparative performance analysis of SLAM Toolbox and
Cartographer in ROS 2", venue UNVERIFIED) and an Authorea preprint. Do not cite either as peer-reviewed. LB-6.8 is the
nearest peer-reviewed real-robot study that includes SLAM Toolbox.

---

## 2. Frontier-based and other autonomous exploration

**LB-2.1** B. Yamauchi, "A frontier-based approach for autonomous exploration," in *Proc. IEEE Int. Symp. Comput.
Intell. Robot. Autom. (CIRA)*, Monterey, CA, USA, 1997, pp. 146–151.
DOI: [10.1109/CIRA.1997.613851](https://doi.org/10.1109/CIRA.1997.613851)
- *Summary:* Defines frontiers as boundaries between known free space and unknown space in an occupancy grid, and
  explores by repeatedly driving to the nearest frontier; tested on a real robot in offices and corridors.
- *Relevance:* The method that `explore_lite` (m-explore-ros2) implements; the founding citation for O2.
- *Supports:* O2.

**LB-2.2** D. Holz, N. Basilico, F. Amigoni, and S. Behnke, "Evaluating the efficiency of frontier-based exploration
strategies," in *Proc. ISR/ROBOTIK 2010*, Munich, Germany, 2010, pp. 36–43. (dblp lists pp. 1–8; the proceedings
running head shows p. 36.) DOI: none found.
URL: <https://www.vde-verlag.de/proceedings-en/453273006.html>
- *Summary:* Compares frontier-based exploration strategies in simulated indoor environments, measuring how
  efficiently each explores against the ideal path.
  (Details beyond the abstract not yet checked.)
- *Relevance:* Gives metrics (distance travelled against explored area) for comparing exploration runs in O2.
- *Supports:* O2.

**LB-2.3** M. Juliá, A. Gil, and Ó. Reinoso, "A comparison of path planning strategies for autonomous exploration and
mapping of unknown environments," *Auton. Robots*, vol. 33, no. 4, pp. 427–444, 2012.
DOI: [10.1007/s10514-012-9298-8](https://doi.org/10.1007/s10514-012-9298-8)
- *Summary:* Surveys the main autonomous exploration and mapping methods, then compares a representative subset
  under one experimental setup, setting out the strengths and weaknesses of each.
- *Relevance:* Peer-reviewed justification for choosing a frontier method over alternatives.
- *Supports:* O2.

**LB-2.4** A. Bircher, M. Kamel, K. Alexis, H. Oleynikova, and R. Siegwart, "Receding horizon 'next-best-view'
planner for 3D exploration," in *Proc. IEEE Int. Conf. Robot. Autom. (ICRA)*, Stockholm, Sweden, 2016,
pp. 1462–1468. DOI: [10.1109/ICRA.2016.7487281](https://doi.org/10.1109/ICRA.2016.7487281)
- *Summary:* A sampling-based alternative to frontiers: grows a random tree from the robot, scores branches by unseen
  volume, executes only the first step, and replans.
- *Relevance:* Represents the information-gain family; useful for explaining why a simpler 2D frontier method suits a
  student rover.
- *Supports:* O2.

**LB-2.5** H. Umari and S. Mukhopadhyay, "Autonomous robotic exploration based on multiple rapidly-exploring
randomized trees," in *Proc. IEEE/RSJ Int. Conf. Intell. Robots Syst. (IROS)*, Vancouver, BC, Canada, 2017,
pp. 1396–1402. DOI: [10.1109/IROS.2017.8202319](https://doi.org/10.1109/IROS.2017.8202319)
- *Summary:* Uses local and global RRTs to find frontier points quickly in a 2D occupancy grid; released as the ROS
  `rrt_exploration` package.
- *Relevance:* A well-known ROS alternative to `explore_lite`; a natural fallback if frontier clustering struggles.
- *Supports:* O2.

**LB-2.6** J. Oršulić, D. Miklić, and Z. Kovačić, "Efficient dense frontier detection for 2-D graph SLAM based on
occupancy grid submaps," *IEEE Robot. Autom. Lett.*, vol. 4, no. 4, pp. 3569–3576, 2019.
DOI: [10.1109/LRA.2019.2928203](https://doi.org/10.1109/LRA.2019.2928203)
- *Summary:* Detects frontiers only in active submaps of a graph-SLAM system, so frontier detection stays fast and
  stays correct after loop closures move the map.
- *Relevance:* Addresses a real interaction in this stack: SLAM Toolbox loop closures shift the map that
  `explore_lite` reads. A good point for the discussion section.
- *Supports:* O2.

**LB-2.7** I. Lluvia, E. Lazkano, and A. Ansuategi, "Active mapping and robot exploration: A survey," *Sensors*,
vol. 21, no. 7, Art. no. 2445, 2021. DOI: [10.3390/s21072445](https://doi.org/10.3390/s21072445)
- *Summary:* Open-access survey of active SLAM and exploration for indoor mobile robots, covering frontier,
  information-theoretic and learning-based methods.
- *Relevance:* A recent survey to anchor the exploration subsection.
- *Supports:* O2.

**LB-2.8** C. Liu *et al.*, "Enhancing autonomous exploration for robotics via real time map optimization and improved
frontier costs," *Sci. Rep.*, vol. 15, Art. no. 12261, 2025.
DOI: [10.1038/s41598-025-97231-9](https://doi.org/10.1038/s41598-025-97231-9) (article number taken from a citing
record; check on the DOI page)
- *Summary:* Filters the grid map in real time to remove useless frontiers, scores frontiers by path length, sensor
  range and information gain, and orders them with a travelling-salesman variant; reports 10–30% better exploration
  efficiency in simulation and on a real ground robot.
- *Relevance:* A recent, peer-reviewed improvement on the nearest-frontier rule used by `explore_lite`; supports a
  discussion of how O2 could be improved.
- *Supports:* O2.

**LB-2.9** S. Macenski, F. Martín, R. White, and J. Ginés Clavero, "The Marathon 2: A navigation system," in *Proc.
IEEE/RSJ Int. Conf. Intell. Robots Syst. (IROS)*, Las Vegas, NV, USA (virtual), 2020, pp. 2718–2725.
DOI: [10.1109/IROS45743.2020.9341207](https://doi.org/10.1109/IROS45743.2020.9341207)
- *Summary:* Introduces Nav2: behaviour-tree navigation, lifecycle-managed servers, and layered costmaps, tested over
  long runs on a university campus.
- *Relevance:* The navigation stack that exploration goals and keep-out zones run through. Cite this for Nav2.
- *Supports:* O2, O5.

Optional (3D, for context only): C. Cao, H. Zhu, H. Choset, and J. Zhang, "TARE: A hierarchical framework for
efficiently exploring complex 3D environments," in *Proc. Robot.: Sci. Syst. (RSS)*, 2021.
DOI: [10.15607/RSS.2021.XVII.018](https://doi.org/10.15607/RSS.2021.XVII.018). Supports O2 (state of the art).

---

## 3. Semantic mapping, room and landmark labelling

**LB-3.1** I. Kostavelis and A. Gasteratos, "Semantic mapping for mobile robotics tasks: A survey," *Robot. Auton.
Syst.*, vol. 66, pp. 86–103, 2015. DOI: [10.1016/j.robot.2014.12.006](https://doi.org/10.1016/j.robot.2014.12.006)
- *Summary:* Classifies semantic-mapping methods by scalability, inference, temporal coherence and use of topological
  maps, and reviews applications and datasets.
- *Relevance:* The core survey for the semantic-mapping subsection.
- *Supports:* O3, O4, O5.

**LB-3.2** X. Song, X. Liang, and H. Zhou, "Semantic mapping techniques for indoor mobile robots: Review and
prospect," *Meas. Control*, vol. 58, 2025 (online 2024). Issue and pages: UNVERIFIED. Author name order: UNVERIFIED
(DOAJ lists the third author as "Zhou Huaidong").
DOI: [10.1177/00202940241259903](https://doi.org/10.1177/00202940241259903)
- *Summary:* Reviews indoor semantic mapping, grouped by the kind of information used to extract semantics, and lists
  open problems.
- *Relevance:* A recent review to show the field is current. Already in RESEARCH_INDEX as L3, which gives the year as
  2024; the volume year is 2025.
- *Supports:* O3, O4.

**LB-3.3** Ó. Martínez Mozos, C. Stachniss, and W. Burgard, "Supervised learning of places from range data using
AdaBoost," in *Proc. IEEE Int. Conf. Robot. Autom. (ICRA)*, Barcelona, Spain, 2005. Pages: UNVERIFIED (sources give
1730–1735 and 1742–1747). DOI: [10.1109/ROBOT.2005.1570363](https://doi.org/10.1109/ROBOT.2005.1570363)
- *Summary:* Labels places as corridor, room or doorway from 2D laser features with AdaBoost.
- *Relevance:* Early proof that a 2D LIDAR alone can support room and corridor labels, relevant to splitting the map
  into regions for access zones.
- *Supports:* O5.

**LB-3.4** R. Bormann, F. Jordan, W. Li, J. Hampp, and M. Hägele, "Room segmentation: Survey, implementation, and
analysis," in *Proc. IEEE Int. Conf. Robot. Autom. (ICRA)*, Stockholm, Sweden, 2016, pp. 1019–1026.
DOI: [10.1109/ICRA.2016.7487234](https://doi.org/10.1109/ICRA.2016.7487234)
- *Summary:* Implements and compares morphological, distance-transform, Voronoi and feature-based room segmentation of
  2D grid maps, with open-source ROS code.
- *Relevance:* Directly relevant to O5: segmenting the corridor map into rooms and regions before computing which
  rooms each entrance reaches.
- *Supports:* O5, O7.

**LB-3.5** N. Sünderhauf, T. T. Pham, Y. Latif, M. Milford, and I. Reid, "Meaningful maps with object-oriented
semantic mapping," in *Proc. IEEE/RSJ Int. Conf. Intell. Robots Syst. (IROS)*, Vancouver, BC, Canada, 2017,
pp. 5079–5085. DOI: [10.1109/IROS.2017.8206392](https://doi.org/10.1109/IROS.2017.8206392)
- *Summary:* Builds a map of individual object instances from a CNN detector, RGB-D segmentation and data association,
  rather than labelling every point.
- *Relevance:* The object-level map design that `landmark_node` follows (one record per landmark, merged across
  observations).
- *Supports:* O4, O8.

**LB-3.6** C. Case, B. Suresh, A. Coates, and A. Y. Ng, "Autonomous sign reading for semantic mapping," in *Proc. IEEE
Int. Conf. Robot. Autom. (ICRA)*, Shanghai, China, 2011, pp. 3297–3303.
DOI: [10.1109/ICRA.2011.5980523](https://doi.org/10.1109/ICRA.2011.5980523)
- *Summary:* Adds text detection and recognition to a laser-mapping robot so room numbers and names on wall signs
  become map labels; the robot found user-named places in 84% of trials.
- *Relevance:* The closest prior work to this project (RESEARCH_INDEX L1). The 84% figure is a fair benchmark next to
  the O3 target of 85%.
- *Supports:* O3, O4.

**LB-3.7** D. Balaban and J. Hart, "Automatic sign reading and localization for semantic mapping with an office
robot," arXiv:2209.11432, 2022. [Online]. Available: <https://arxiv.org/abs/2209.11432>
- *Summary:* Detects door placards with YOLOv5, reads them with a text pipeline, and places them in a map built from
  RGB-D video (Azure Kinect on a BWIBot) using a modified ORB-SLAM.
- *Relevance:* The most recent close match (RESEARCH_INDEX L2, which wrongly gives "et al."; there are two authors).
  A preprint: say so in the report.
- *Supports:* O3, O4.

**LB-3.8** R. Alqobali, R. Alnasser, A. Rashidi, M. Alshmrani, and T. Alhmiedat, "A real-time semantic map production
system for indoor robot navigation," *Sensors*, vol. 24, no. 20, Art. no. 6691, 2024.
DOI: [10.3390/s24206691](https://doi.org/10.3390/s24206691)
- *Summary:* Combines LIDAR mapping with YOLOv3 detection in ROS on low-cost computers to place objects on a 2D map,
  reporting object localisation error and 78.86% map construction accuracy, in simulation.
- *Relevance:* Same sensor pattern as this project (LIDAR map + YOLO); its error figures are a comparison point for
  O4, but note they come from simulation.
- *Supports:* O4.

---

## 4. Scene text detection and recognition (door signs; PaddleOCR and alternatives)

**LB-4.1** S. Long, X. He, and C. Yao, "Scene text detection and recognition: The deep learning era," *Int. J. Comput.
Vis.*, vol. 129, no. 1, pp. 161–184, 2021. DOI: [10.1007/s11263-020-01369-0](https://doi.org/10.1007/s11263-020-01369-0)
- *Summary:* Survey of deep scene-text detection, recognition and end-to-end spotting, with datasets and metrics.
- *Relevance:* The survey to open the OCR subsection.
- *Supports:* O3.

**LB-4.2** B. Shi, X. Bai, and C. Yao, "An end-to-end trainable neural network for image-based sequence recognition
and its application to scene text recognition," *IEEE Trans. Pattern Anal. Mach. Intell.*, vol. 39, no. 11,
pp. 2298–2304, 2017. DOI: [10.1109/TPAMI.2016.2646371](https://doi.org/10.1109/TPAMI.2016.2646371)
- *Summary:* CRNN: convolutional features, a recurrent layer and CTC loss read a whole word without segmenting
  characters.
- *Relevance:* The recogniser family used inside PP-OCR; explains how a cropped door sign becomes text.
- *Supports:* O3.

**LB-4.3** M. Liao, Z. Wan, C. Yao, K. Chen, and X. Bai, "Real-time scene text detection with differentiable
binarization," in *Proc. AAAI Conf. Artif. Intell.*, vol. 34, no. 7, 2020, pp. 11474–11481.
DOI: [10.1609/aaai.v34i07.6812](https://doi.org/10.1609/aaai.v34i07.6812)
- *Summary:* DBNet: a segmentation detector with a learnable binarisation threshold, accurate and fast enough for
  real time.
- *Relevance:* The text detector used in PP-OCR's pipeline.
- *Supports:* O3.

**LB-4.4** Y. Du *et al.*, "PP-OCR: A practical ultra lightweight OCR system," arXiv:2009.09941, 2020. [Online].
Available: <https://arxiv.org/abs/2009.09941>
- *Summary:* Baidu's lightweight OCR pipeline (DB detector, direction classifier, CRNN recogniser) with tricks that
  shrink the model to a few megabytes for mobile and embedded use.
- *Relevance:* The technical basis of PaddleOCR, the OCR engine chosen for `sign_reader_node`. A preprint.
- *Supports:* O3.

**LB-4.5** C. Cui *et al.*, "PaddleOCR 3.0 technical report," arXiv:2507.05595, 2025. [Online]. Available:
<https://arxiv.org/abs/2507.05595>
- *Summary:* Describes PaddleOCR 3.0, including the PP-OCRv5 multilingual recogniser, document parsing and key
  information extraction.
- *Relevance:* The current version of the toolkit; cite this for the version actually installed on the Jetson. A
  preprint.
- *Supports:* O3.

**LB-4.6** J. Baek *et al.*, "What is wrong with scene text recognition model comparisons? Dataset and model
analysis," in *Proc. IEEE/CVF Int. Conf. Comput. Vis. (ICCV)*, Seoul, South Korea, 2019, pp. 4715–4723.
DOI: [10.1109/ICCV.2019.00481](https://doi.org/10.1109/ICCV.2019.00481)
- *Summary:* Shows that text-recognition papers used inconsistent training and test data, and compares modules
  (transformation, features, sequence, prediction) under one setup for accuracy, speed and memory.
- *Relevance:* Supports the O3 method: fix the test set first and keep training signs out of it (experiments.md O3
  threats).
- *Supports:* O3.

**LB-4.7** R. Smith, "An overview of the Tesseract OCR engine," in *Proc. 9th Int. Conf. Document Anal. Recognit.
(ICDAR)*, Curitiba, Brazil, 2007, pp. 629–633. DOI: [10.1109/ICDAR.2007.56](https://doi.org/10.1109/ICDAR.2007.56)
(DOI seen in one bibliography record; pages confirmed by two.)
- *Summary:* Describes Tesseract's pipeline, designed for scanned documents.
- *Relevance:* The obvious alternative to PaddleOCR; its document focus explains why it is weaker on photographed
  signs.
- *Supports:* O3.

**LB-4.8** E. D. Fajrianti, Y. Y. F. Panduman, N. Funabiki, A. L. Haz, K. C. Brata, and S. Sukaridhoto, "A user
location reset method through object recognition in indoor navigation system using Unity and a smartphone (INSUS),"
*Network*, vol. 4, no. 3, pp. 295–312, 2024. DOI: [10.3390/network4030014](https://doi.org/10.3390/network4030014)
- *Summary:* Detects room signs with YOLOv8, reads them with PaddleOCR, and matches the text to a room database by
  Levenshtein distance; reports mAP@0.5 of 0.995 and character error under 10% in two university buildings.
- *Relevance:* The same YOLO + PaddleOCR + fuzzy-match pipeline as `sign_reader_node`, peer-reviewed, on room signs.
  Strong support for the O3 design and for normalising text before matching.
- *Supports:* O3, O6.

---

## 5. Object detection on embedded GPUs (YOLO, TensorRT on Jetson)

**LB-5.1** J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, "You only look once: Unified, real-time object
detection," in *Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR)*, Las Vegas, NV, USA, 2016, pp. 779–788.
DOI: [10.1109/CVPR.2016.91](https://doi.org/10.1109/CVPR.2016.91)
- *Summary:* Treats detection as a single regression from image to boxes and classes, giving real-time detection.
- *Relevance:* The original YOLO paper.
- *Supports:* O3, O4.

**LB-5.2** J. Terven, D.-M. Córdova-Esparza, and J.-A. Romero-González, "A comprehensive review of YOLO architectures
in computer vision: From YOLOv1 to YOLOv8 and YOLO-NAS," *Mach. Learn. Knowl. Extr.*, vol. 5, no. 4, pp. 1680–1716,
2023. DOI: [10.3390/make5040083](https://doi.org/10.3390/make5040083)
- *Summary:* Traces each YOLO version's changes to backbone, neck, head, loss and training.
- *Relevance:* Peer-reviewed source for the YOLO family; avoids citing blog posts.
- *Supports:* O3, O4.

**LB-5.3** A. Wang *et al.*, "YOLOv10: Real-time end-to-end object detection," in *Adv. Neural Inf. Process. Syst.
(NeurIPS)*, vol. 37, 2024. Pages: UNVERIFIED. arXiv: [2405.14458](https://arxiv.org/abs/2405.14458)
- *Summary:* Removes non-maximum suppression with consistent dual label assignment and slims the architecture, cutting
  latency at equal accuracy.
- *Relevance:* NMS-free detection matters on a Jetson because NMS runs on the CPU after the TensorRT engine.
- *Supports:* O3, O4.

**LB-5.4** G. Jocher and J. Qiu, "Ultralytics YOLO11," version 11.0.0, 2024. [Online]. Available:
<https://github.com/ultralytics/ultralytics>. DOI: none issued (Ultralytics states it is pending).
- *Summary:* Software citation recommended by Ultralytics; there is no YOLO11 paper. YOLOv8 has the equivalent entry
  (G. Jocher, A. Chaurasia, and J. Qiu, "Ultralytics YOLOv8," version 8.0.0, 2023).
- *Relevance:* Cite whichever version `detector_node` actually runs; record the version in the logbook.
- *Supports:* O3, O4.

**LB-5.5** D. G. Lema, R. Usamentiaga, and D. F. García, "Quantitative comparison and performance evaluation of deep
learning-based object detection models on edge computing devices," *Integration*, vol. 95, Art. no. 102127, 2024.
DOI: [10.1016/j.vlsi.2023.102127](https://doi.org/10.1016/j.vlsi.2023.102127)
- *Summary:* Benchmarks YOLOv3, YOLOv5 and YOLOX on Jetson Nano, Jetson AGX Xavier and Coral, over twenty input sizes
  and three runtimes (PyTorch, TensorRT, TensorFlow Lite), with FPS-per-watt and FPS-per-cost.
- *Relevance:* Peer-reviewed evidence that TensorRT and input size dominate speed on Jetson boards; supports the
  TensorRT export plan.
- *Supports:* O3, O4.

**LB-5.6** B. Shakya, O. F. El-Gayar, J. Kaabi, and K. M. Ahmed, "Small-object detection at the edge: A
Pareto-efficient benchmark of lightweight YOLO models on UAV and overhead datasets," *IEEE Access*, vol. UNVERIFIED,
pp. 528–548, 2026. DOI: [10.1109/ACCESS.2025.3648968](https://doi.org/10.1109/ACCESS.2025.3648968)
- *Summary:* Benchmarks eight lightweight YOLO variants (YOLOX-Nano, YOLOv6–v12) on a Jetson Orin Nano with PyTorch
  and TensorRT FP16; reports 3–5× speed-up from TensorRT and 7.6–10.4 W power draw, with no model best on every
  measure.
- *Relevance:* Uses the same board as this project (Orin Nano); its numbers help set expectations for the detector
  rate and power budget.
- *Supports:* O3, O4.

**LB-5.7** D. K. Alqahtani, A. Cheema, and A. N. Toosi, "Benchmarking deep learning models for object detection on
edge computing devices," arXiv:2409.16808, 2024. [Online]. Available: <https://arxiv.org/abs/2409.16808>
(v2 retitled "A comprehensive evaluation of deep learning object detection models on heterogeneous edge devices"
and adds M. A. Rodriguez as an author; cite the version you read.)
- *Summary:* Compares YOLOv8, EfficientDet Lite and SSD on Raspberry Pi boards (with and without accelerators),
  Jetson Nano and Jetson Orin Nano, for latency, energy and accuracy; Orin Nano gives the best overall balance.
- *Relevance:* Includes Orin Nano and the Raspberry Pi 5 the student already uses; useful for justifying the Jetson.
  A preprint.
- *Supports:* O3, O4.

---

## 6. Sensor fusion for mobile robots; laser scan-matching odometry without wheel encoders

**LB-6.1** S. Thrun, W. Burgard, and D. Fox, *Probabilistic Robotics*. Cambridge, MA, USA: MIT Press, 2005,
ISBN 978-0-262-20162-9.
- *Summary:* The standard text on Bayes filters, the EKF, motion and sensor models, and SLAM.
- *Relevance:* Background citation for the EKF and for why an IMU alone cannot give distance travelled.
- *Supports:* O1, O8.

**LB-6.2** T. Moore and D. Stouch, "A generalized extended Kalman filter implementation for the Robot Operating
System," in *Intelligent Autonomous Systems 13* (Advances in Intelligent Systems and Computing, vol. 302),
E. Menegatti, N. Michael, K. Berns, and H. Yamaguchi, Eds. Cham, Switzerland: Springer, 2016, pp. 335–348.
DOI: [10.1007/978-3-319-08338-4_25](https://doi.org/10.1007/978-3-319-08338-4_25)
- *Summary:* The `robot_localization` paper: an EKF that fuses any number of odometry, IMU and pose sources in 3D,
  with per-sensor masks for which state variables each measures.
- *Relevance:* The fusion node configured in `ekf.yaml`; the basis of the O8 comparison.
- *Supports:* O1, O8.

**LB-6.3** M. Jaimez, J. G. Monroy, and J. Gonzalez-Jimenez, "Planar odometry from a radial laser scanner. A range
flow-based approach," in *Proc. IEEE Int. Conf. Robot. Autom. (ICRA)*, Stockholm, Sweden, 2016, pp. 4479–4485.
DOI: [10.1109/ICRA.2016.7487647](https://doi.org/10.1109/ICRA.2016.7487647)
- *Summary:* RF2O: estimates planar motion from consecutive scans by dense range-flow alignment, with no point
  correspondences, in about 1 ms per scan on one CPU core.
- *Relevance:* The method behind `rf2o_laser_odometry`, which replaces wheel odometry on this rover (decisions #10,
  #14). The core citation for encoder-free odometry.
- *Supports:* O1, O8.

**LB-6.4** A. Censi, "An ICP variant using a point-to-line metric," in *Proc. IEEE Int. Conf. Robot. Autom. (ICRA)*,
Pasadena, CA, USA, 2008, pp. 19–25. DOI: [10.1109/ROBOT.2008.4543181](https://doi.org/10.1109/ROBOT.2008.4543181)
- *Summary:* PLICP: point-to-line ICP with a closed-form step; more precise and needs fewer iterations than
  point-to-point ICP, but is less robust to large initial errors.
- *Relevance:* The main alternative scan-matching odometry (`laser_scan_matcher`); a fallback if rf2o fails.
- *Supports:* O1, O8.

**LB-6.5** E. B. Olson, "Real-time correlative scan matching," in *Proc. IEEE Int. Conf. Robot. Autom. (ICRA)*, Kobe,
Japan, 2009, pp. 4387–4393. DOI: [10.1109/ROBOT.2009.5152375](https://doi.org/10.1109/ROBOT.2009.5152375)
- *Summary:* Finds the best scan alignment by searching over candidate poses rather than iterating from one initial
  guess, made fast enough for real time; this makes it robust to poor initial estimates.
  (Implementation details not yet checked against the paper.)
- *Relevance:* The scan-matching approach SLAM Toolbox uses internally; explains why SLAM can tolerate weak odometry.
- *Supports:* O1, O2.

**LB-6.6** J. Zhang, M. Kaess, and S. Singh, "On degeneracy of optimization-based state estimation problems," in
*Proc. IEEE Int. Conf. Robot. Autom. (ICRA)*, Stockholm, Sweden, 2016, pp. 809–816.
DOI: [10.1109/ICRA.2016.7487211](https://doi.org/10.1109/ICRA.2016.7487211)
- *Summary:* Shows how to detect directions in which a scan-matching problem is poorly constrained (for example along
  a featureless corridor) and to stop updates in those directions.
- *Relevance:* Gives a formal basis for OPEN_ISSUES #17 (long plain corridors defeating scan matching without
  encoders). Written for 3D LIDAR; the idea carries over.
- *Supports:* O1, O2, O8.

**LB-6.7** C. Li, S. Wang, Y. Zhuang, and F. Yan, "Deep sensor fusion between 2D laser scanner and IMU for mobile robot
localization," *IEEE Sensors J.*, vol. 21, no. 6, pp. 8501–8509, 2021.
DOI: [10.1109/JSEN.2019.2910826](https://doi.org/10.1109/JSEN.2019.2910826)
- *Summary:* A recurrent CNN fuses 2D laser scans and IMU data for scan-to-scan pose estimates, refined by
  scan-to-submap optimisation; tested on a real robot.
- *Relevance:* The same sensor pair as this rover (2D LIDAR + IMU, no encoders); motivated by IMU fusion helping in
  large rotations, where the authors say laser-only methods are fragile; that is the case the O8 pose comparison
  tests.
- *Supports:* O8.

**LB-6.8** A. Kudriashov, J. Koszyk, B. Hyla, and Ł. Ambroziński, "A real-world benchmark of Monte Carlo-assisted EKF
odometry for online pose estimation in 2D LiDAR SLAM," *Sensors*, vol. 26, no. 13, Art. no. 4264, 2026.
DOI: UNVERIFIED. Repository record: <https://badap.agh.edu.pl/publikacja/168814>
- *Summary:* Fuses LIDAR odometry, IMU and AMCL in an EKF and feeds the result to Cartographer, GMapping and SLAM
  Toolbox on two real robots in three buildings (720 runs); the benefit depends on the environment and backend, and
  fusion made results worse in repetitive corridors.
- *Relevance:* Recent, real-robot, includes SLAM Toolbox, and uses run-to-run repeatability (map IoU, ATE spread) as
  metrics. Directly informs O1, O2 and O8 and supports reporting a null O8 result honestly.
- *Supports:* O2, O8.

**LB-6.9** S. Macenski, T. Moore, D. V. Lu, A. Merzlyakov, and M. Ferguson, "From the desks of ROS maintainers: A
survey of modern & capable mobile robotics algorithms in the Robot Operating System 2," *Robot. Auton. Syst.*,
vol. 168, Art. no. 104493, 2023. DOI: [10.1016/j.robot.2023.104493](https://doi.org/10.1016/j.robot.2023.104493)
(full author list: UNVERIFIED; the search confirmed title, journal, volume and DOI)
- *Summary:* Surveys ROS 2 navigation, localisation, SLAM and perception packages, written by their maintainers,
  with benchmarks of planners and controllers.
- *Relevance:* One citation covering the whole ROS 2 software stack (Nav2, SLAM Toolbox, robot_localization).
- *Supports:* O1, O2, O8.

---

## 7. Landmark/object localisation by fusing detections with depth and pose

Cross-listed from above: **LB-3.5** (Sünderhauf, object-level maps), **LB-3.7** (Balaban and Hart, placards
placed with RGB-D), **LB-3.8** (Alqobali, LIDAR + YOLO object error).

**LB-7.1** R. Martins, D. Bersan, M. F. M. Campos, and E. R. Nascimento, "Extending maps with semantic and contextual
object information for robot navigation: A learning-based framework using visual and depth cues," *J. Intell. Robot.
Syst.*, 2020. Volume and pages: UNVERIFIED.
DOI: [10.1007/s10846-019-01136-5](https://doi.org/10.1007/s10846-019-01136-5)
- *Summary:* YOLO detections plus depth-based 3D segmentation place doors, fire extinguishers, benches and water
  fountains on a metric map, with one Kalman filter per object to merge observations; data and ROS code released.
- *Relevance:* Close to `landmark_node` (fire extinguishers and doors are likely Merz Court landmarks), and its
  per-object filtering is the same idea as the O8 single-against-merged comparison.
- *Supports:* O4, O8.

**LB-7.2** F. Rollo, G. Raiola, A. Zunino, N. Tsagarakis, and A. Ajoudani, "Artifacts mapping: Multi-modal semantic
mapping for object detection and 3D localization," in *Proc. Eur. Conf. Mobile Robots (ECMR)*, 2023. Pages:
UNVERIFIED. DOI: [10.1109/ECMR59166.2023.10256373](https://doi.org/10.1109/ECMR59166.2023.10256373)
- *Summary:* Detects and localises known objects by fusing RGB-D and LIDAR depth, then filters repeated measurements;
  98% of objects mapped with fusion against 85% (RGB-D only) and 80% (RGB + LIDAR).
- *Relevance:* A direct fused-against-single-sensor comparison for object mapping: a template for presenting O8.
- *Supports:* O4, O8.

**LB-7.3** L. Nicholson, M. Milford, and N. Sünderhauf, "QuadricSLAM: Dual quadrics from object detections as
landmarks in object-oriented SLAM," *IEEE Robot. Autom. Lett.*, vol. 4, no. 1, pp. 1–8, 2019.
DOI: [10.1109/LRA.2018.2866205](https://doi.org/10.1109/LRA.2018.2866205)
- *Summary:* Treats 2D bounding boxes from several views as measurements of a 3D ellipsoid per object, estimated
  jointly with camera poses.
- *Relevance:* Shows the stronger option (objects inside the SLAM optimisation) that this project does not take;
  useful for the limitations section.
- *Supports:* O4.

**LB-7.4** L. Keselman, J. I. Woodfill, A. Grunnet-Jepsen, and A. Bhowmik, "Intel RealSense stereoscopic depth
cameras," in *Proc. IEEE Conf. Comput. Vis. Pattern Recognit. Workshops (CVPRW)*, Honolulu, HI, USA, 2017,
pp. 1267–1276. DOI: [10.1109/CVPRW.2017.167](https://doi.org/10.1109/CVPRW.2017.167)
- *Summary:* Describes the design of Intel's RealSense stereo depth cameras and their depth performance.
  (Check the D455-relevant error figures in the paper itself.)
- *Relevance:* Peer-reviewed source for the D455 depth-error term in the O4 error budget (alongside the datasheet,
  RESEARCH_INDEX H2).
- *Supports:* O4.

**LB-7.5** Z. Zhang, "A flexible new technique for camera calibration," *IEEE Trans. Pattern Anal. Mach. Intell.*,
vol. 22, no. 11, pp. 1330–1334, 2000. DOI: [10.1109/34.888718](https://doi.org/10.1109/34.888718)
- *Summary:* Calibrates a camera from several views of a planar pattern; the basis of OpenCV and ROS checkerboard
  calibration.
- *Relevance:* Cite for the C920/D455 intrinsic calibration with the checkerboard; extrinsic error is part of the O4
  error budget.
- *Supports:* O1, O4.

---

## 8. Indoor navigation for visitors without positioning infrastructure

**LB-8.1** N. Fallah, I. Apostolopoulos, K. Bekris, and E. Folmer, "Indoor human navigation systems: A survey,"
*Interact. Comput.*, vol. 25, no. 1, pp. 21–33, 2013. DOI: [10.1093/iwc/iws010](https://doi.org/10.1093/iwc/iws010)
- *Summary:* Reviews indoor navigation aids for people under four headings: locating the user, planning a path,
  representing the environment, and interacting with the user.
- *Relevance:* A framework for describing the website: QR at the entrance locates the user, the database plans the
  route, the robot map represents the building, photos are the interface.
- *Supports:* O6, O7.

**LB-8.2** J. Kunhoth, A. Karkar, S. Al-Maadeed, and A. Al-Ali, "Indoor positioning and wayfinding systems: A survey,"
*Hum.-centric Comput. Inf. Sci.*, vol. 10, Art. no. UNVERIFIED, 2020.
DOI: [10.1186/s13673-020-00222-0](https://doi.org/10.1186/s13673-020-00222-0)
- *Summary:* Surveys computer-vision, dead-reckoning and radio (Wi-Fi, BLE, RFID, UWB, visible light) indoor
  positioning, and proposes criteria for judging wayfinding systems.
- *Relevance:* Places the QR + image approach among alternatives that need installed infrastructure.
- *Supports:* O6, O7.

**LB-8.3** F. Zafari, A. Gkelias, and K. K. Leung, "A survey of indoor localization systems and technologies," *IEEE
Commun. Surveys Tuts.*, vol. 21, no. 3, pp. 2568–2599, 2019.
DOI: [10.1109/COMST.2019.2911558](https://doi.org/10.1109/COMST.2019.2911558)
- *Summary:* Technical survey of indoor localisation techniques (RSSI, ToF, AoA, fingerprinting) and technologies,
  with their accuracy and cost.
- *Relevance:* The authoritative source for why the project avoids radio positioning: it needs installed hardware or
  a site survey.
- *Supports:* O6, O7.

**LB-8.4** A. Mulloni, D. Wagner, I. Barakonyi, and D. Schmalstieg, "Indoor positioning and navigation with camera
phones," *IEEE Pervasive Comput.*, vol. 8, no. 2, pp. 22–31, 2009.
DOI: [10.1109/MPRV.2009.30](https://doi.org/10.1109/MPRV.2009.30)
- *Summary:* Phones locate themselves by photographing printed markers placed around a venue; used by over 2,000
  people at four large events.
- *Relevance:* Early large-scale evidence that marker scanning on ordinary phones works for visitors; the precedent
  for QR posters at entrances.
- *Supports:* O6, O7.

**LB-8.5** A. K. Beeharee and A. Steed, "A natural wayfinding exploiting photos in pedestrian navigation systems," in
*Proc. 8th Conf. Hum.-Comput. Interact. Mobile Devices Serv. (MobileHCI)*, Helsinki, Finland, 2006, pp. 81–88.
DOI: [10.1145/1152215.1152233](https://doi.org/10.1145/1152215.1152233)
- *Summary:* Adds photos of the route to pedestrian directions so users can match what they see with what to do.
- *Relevance:* The closest precedent for the image-to-image directions on the website (decisions #12).
- *Supports:* O7.

**LB-8.6** A. J. May, T. Ross, S. H. Bayer, and M. J. Tarkiainen, "Pedestrian navigation aids: Information
requirements and design implications," *Pers. Ubiquitous Comput.*, vol. 7, no. 6, pp. 331–338, 2003.
DOI: [10.1007/s00779-003-0248-5](https://doi.org/10.1007/s00779-003-0248-5)
- *Summary:* Found that landmarks were the most used navigation cue and that distances and street names were rarely
  used; people also use directions to build confidence.
- *Relevance:* Justifies photographing junctions and landmarks rather than giving distances.
- *Supports:* O7.

**LB-8.7** S. Garrido-Jurado, R. Muñoz-Salinas, F. J. Madrid-Cuevas, and M. J. Marín-Jiménez, "Automatic generation
and detection of highly reliable fiducial markers under occlusion," *Pattern Recognit.*, vol. 47, no. 6,
pp. 2280–2292, 2014. DOI: [10.1016/j.patcog.2014.01.005](https://doi.org/10.1016/j.patcog.2014.01.005)
- *Summary:* The ArUco marker system: dictionary generation, detection with error correction, and occlusion handling,
  for camera pose estimation.
- *Relevance:* The fiducial alternative to plain QR codes, if the website ever needs the phone's pose rather than an
  entrance ID. Context only.
- *Supports:* O6.

**LB-8.8** Ç. Tünger and Ç. İmamoğlu, "Using quick response (QR) codes as an indoor wayfinding tool: Benefits and
limitations," *METU J. Fac. Archit.*, vol. 39, no. 2, pp. 201–220, 2022.
DOI: [10.4305/METU.JFA.2022.2.4](https://doi.org/10.4305/METU.JFA.2022.2.4) (author order differs between
repositories; METU's record lists Tünger first)
- *Summary:* A 38-person study in a complex university building: with QR codes people walked more slowly but rated the
  experience better, suggesting QR codes as a cheap alternative to "you are here" maps.
- *Relevance:* Peer-reviewed user evidence for QR-based wayfinding in a university building, and a warning that QR
  scanning adds time; relevant to how O6 and the informal user test are reported.
- *Supports:* O6, O7.

**LB-8.9** E. D. Fajrianti *et al.*, "INSUS: Indoor navigation system using Unity and smartphone for user ambulation
assistance," *Information*, vol. 14, no. 7, Art. no. 359, 2023.
DOI: [10.3390/info14070359](https://doi.org/10.3390/info14070359)
- *Summary:* Phone AR navigation that starts from a QR code and tracks the user with phone visual SLAM, using a 3D
  model of the building made in advance.
- *Relevance:* A contrast: it needs a hand-made 3D building model, which is what a robot-built map could replace.
  Pair with LB-4.8 (same group, signs instead of QR).
- *Supports:* O6, O7.

---

## 9. Evaluation methods: map accuracy, coverage, localisation error

Cross-listed: **LB-1.6** and **LB-1.7** (map against ground truth), **LB-2.2** (exploration efficiency),
**LB-6.8** (repeatability metrics).

**LB-9.1** R. Kümmerle *et al.*, "On measuring the accuracy of SLAM algorithms," *Auton. Robots*, vol. 27, no. 4,
pp. 387–407, 2009. DOI: [10.1007/s10514-009-9155-6](https://doi.org/10.1007/s10514-009-9155-6)
- *Summary:* Proposes measuring SLAM error from relative relations between poses, so no global ground-truth frame is
  needed, and publishes relation sets for common datasets.
- *Relevance:* Justifies measuring wall error locally after aligning the plan, and warns that global alignment can
  hide or inflate error (experiments.md O2 threats).
- *Supports:* O2, O8.

**LB-9.2** J. Sturm, N. Engelhard, F. Endres, W. Burgard, and D. Cremers, "A benchmark for the evaluation of RGB-D SLAM
systems," in *Proc. IEEE/RSJ Int. Conf. Intell. Robots Syst. (IROS)*, Vilamoura, Portugal, 2012, pp. 573–580.
DOI: [10.1109/IROS.2012.6385773](https://doi.org/10.1109/IROS.2012.6385773)
- *Summary:* The TUM RGB-D benchmark; defines absolute trajectory error (ATE) and relative pose error (RPE) with
  tools to compute them.
- *Relevance:* The standard definitions to use if the O8 pose comparison reports trajectory error.
- *Supports:* O8.

**LB-9.3** Z. Zhang and D. Scaramuzza, "A tutorial on quantitative trajectory evaluation for visual(-inertial)
odometry," in *Proc. IEEE/RSJ Int. Conf. Intell. Robots Syst. (IROS)*, Madrid, Spain, 2018, pp. 7244–7251.
DOI: [10.1109/IROS.2018.8593941](https://doi.org/10.1109/IROS.2018.8593941)
- *Summary:* Explains how trajectory alignment choices change ATE and RPE, and which alignment fits which sensor
  setup; releases an evaluation toolbox.
- *Relevance:* Guidance on aligning estimate to ground truth before computing error, as in the O2 rigid transform from
  named corners and the O4 frame alignment.
- *Supports:* O2, O4, O8.

**LB-9.4** A. Filatov, A. Filatov, K. Krinkin, B. Chen, and D. Molodan, "2D SLAM quality evaluation methods," in
*Proc. 21st Conf. Open Innov. Assoc. (FRUCT)*, Helsinki, Finland, 2017, pp. 120–126.
DOI: [10.23919/FRUCT.2017.8250173](https://doi.org/10.23919/FRUCT.2017.8250173)
- *Summary:* Proposes quantitative measures of 2D laser-SLAM map quality for data sets that have no ground truth.
  (The individual measures are not yet checked against the paper.)
- *Relevance:* A second check on map quality alongside the floor plan; useful if the floor plan turns out not to match
  the building (O2 threats).
- *Supports:* O2.

**LB-9.5** S. Schwertfeger and A. Birk, "Map evaluation using matched topology graphs," *Auton. Robots*, 2016 (online
2015). Volume and pages: UNVERIFIED. DOI: [10.1007/s10514-015-9493-5](https://doi.org/10.1007/s10514-015-9493-5)
- *Summary:* Compares maps by extracting and matching their topology graphs (rooms, corridors, junctions) rather than
  cell by cell.
- *Relevance:* A topological measure is closer to what visitors need (O7 junction sequences, O5 reachability) than
  wall error.
- *Supports:* O2, O5, O7.

**LB-9.6** F. Amigoni, M. Reggiani, and V. Schiaffonati, "An insightful comparison between experiments in mobile
robotics and in science," *Auton. Robots*, vol. 27, pp. 313–325, 2009. Issue: UNVERIFIED.
DOI: [10.1007/s10514-009-9137-8](https://doi.org/10.1007/s10514-009-9137-8)
- *Summary:* Compares how experiments are done in mobile robotics with experimental practice in the sciences, and
  argues that robotics experimentation has not yet reached comparable maturity.
- *Relevance:* Supports the experiments.md rules: fix pass rules before the runs, repeat runs, publish bags and
  parameters.
- *Supports:* O2–O8.

**LB-9.7** Joint Committee for Guides in Metrology, *Evaluation of Measurement Data – Guide to the Expression of
Uncertainty in Measurement*, JCGM 100:2008, 2008. DOI:
[10.59161/JCGM100-2008E](https://doi.org/10.59161/JCGM100-2008E)
- *Summary:* The GUM: how to combine and state measurement uncertainty.
- *Relevance:* Supports the "ground truth 3–5 times more accurate than the target" rule and the uncertainty stated
  with laser-meter landmark positions in O4.
- *Supports:* O2, O4.

---

## Candidates found but not yet verifiable (do not cite until checked)
- C. Merrick *et al.*, "Evaluating the impact of extended Kalman filter odometry on the performance of 2D LiDAR SLAM
  algorithms," listed by Consensus as *Sensors*, 2026; a not-yet-peer-reviewed version is on preprints.org. Journal
  version, volume and DOI: UNVERIFIED. Very relevant to O8 (EKF odometry into GMapping, Karto and SLAM Toolbox,
  absolute pose error).
- "From simulation to reality: Comparative performance analysis of SLAM Toolbox and Cartographer in ROS 2," on
  ResearchGate (2025). Authors and venue: UNVERIFIED.
- The proposal's own references [1]–[10] were not in the repository, so they could not be checked here (see the
  pull request description).
