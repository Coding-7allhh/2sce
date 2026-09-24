# 720x1280 MoviePy Reaction Video Generator

GitHub Actions + MoviePy project for a 9:16, 720x1280 reaction/animation layout.

## Features
- Public Google Drive folders downloaded with `gdown`; no Drive mount.
- Recursive nested-folder clip discovery.
- Background images from `assets/Bg_Pic/`.
- Top reaction and bottom animation clips in rounded bordered windows.
- Blurred 720x1280 background.
- `HardToonz` label and random `Part 1..99`.
- Output duration = shortest source clip.
- Source FPS preserved: no 30->60 conversion/interpolation.
- No 1080p upscale or AI enhancement.
- H.264/AAC MP4 output.
- GitHub Actions artifact upload.

## Drive folders
Top: `https://drive.google.com/drive/folders/1l9ayaXiRBwUr1Hrjag7r3CycVDiN24fh`

Bottom: `https://drive.google.com/drive/folders/10DSjb9etdFzQTg_rftRJpJkC5jKBjsNT`

Both folders must be publicly accessible to the GitHub runner.

## Backgrounds
Put PNG/JPG/WebP files in `assets/Bg_Pic/`.

## Local
```bash
pip install -r requirements.txt
python main.py --max-outputs 2
```
Dry run:
```bash
python main.py --max-outputs 5 --dry-run
```

## GitHub Actions
Open **Actions -> Generate 720p Reaction Videos -> Run workflow**. `max_outputs=0` means all top clips. Rendered videos and `processing_log.csv` are uploaded as `reaction-720p-output`.

## Layout
Canvas 720x1280. Top window approximately `(72,78,576,500)`, bottom window `(17,595,686,493)`. Top border is purple/magenta; bottom border is yellow/gold.
