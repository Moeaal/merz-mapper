# Exporting the detector to TensorRT

**Not yet verified on hardware.** Steps are from the Ultralytics TensorRT page (RESEARCH_INDEX [N10]). Commands may
differ with the Ultralytics version installed, so check `yolo export --help` output against this first.

## Rules
- **Build the engine on the Jetson itself.** Engines are tied to the GPU and TensorRT version, and are not a portable
  format. An engine built on another machine, or before a JetPack upgrade, is not valid.
- `.engine` and `.pt` files are ignored by git. Keep them on the NVMe, under `~/merz_data/models/`.
- Start with FP16. Only try INT8 with a calibration set, and report accuracy before and after.

## Steps (on the Jetson)
1. Install Ultralytics and a PyTorch build that matches JetPack (see the Ultralytics NVIDIA Jetson guide). Do not use a
   plain `pip install torch`, as that does not give a CUDA-enabled build for this hardware. Check first:
   ```bash
   python3 -c "import torch; print(torch.__version__, torch.cuda.is_available())"
   python3 -c "import tensorrt; print(tensorrt.__version__)"
   ```
2. Set the highest stable power mode, and record the mode in the logbook:
   ```bash
   sudo nvpmodel -q
   sudo jetson_clocks --show
   ```
3. Export FP16. Current Ultralytics uses `quantize=16`; older versions use `half=True`.
   ```bash
   cd ~/merz_data/models
   yolo export model=merz_yolo.pt format=engine imgsz=640 quantize=16
   ```
4. Try it directly:
   ```bash
   yolo predict model=merz_yolo.engine task=detect source=sample.jpg
   ```
5. Compare before and after, using the same validation set and the same power mode:
   ```bash
   yolo val model=merz_yolo.pt data=merz.yaml imgsz=640
   yolo val model=merz_yolo.engine task=detect data=merz.yaml imgsz=640
   ```
   Log mAP50, mAP50-95 and FPS for each one in the logbook, and watch `tegrastats` for thermal throttling.
6. Set this in `merz_perception/config/perception.yaml`, for both detector nodes:
   ```yaml
   engine: tensorrt
   weights: /home/<user>/merz_data/models/merz_yolo.engine
   ```

## INT8 (only if FP16 is too slow)
Current versions:
```bash
yolo export model=merz_yolo.pt format=engine imgsz=640 quantize=8 data=merz.yaml fraction=1.0
```
Older versions use `int8=True` in place of `quantize=8`. Run this on the same Jetson that will run the model.
