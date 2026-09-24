# ============================================================
# GOOGLE DRIVE -> GITHUB ACTIONS -> MOVIEPY
# REACTION + ANIMATION SHORTS MAKER
#
# FINAL VIDEO:
#   720 x 1280
#   9:16 vertical
#   SOURCE FPS PRESERVED
#   NO 30 -> 60 FPS CONVERSION
#   NO FPS INTERPOLATION
#   NO SHARPENING
#   NO AI UPSCALING
#   NO QUALITY ENHANCEMENT
#   NO YOUTUBE UI
#   NO ANDROID UI
#
# DRIVE:
#   ASSETS FOLDER:
#   https://drive.google.com/drive/folders/1l9ayaXiRBwUr1Hrjag7r3CycVDiN24fh
#
#   CLIPS FOLDER:
#   https://drive.google.com/drive/folders/10DSjb9etdFzQTg_rftRJpJkC5jKBjsNT
#
# EXPECTED INSIDE ASSETS:
#   assets/
#      Bg_Pic/
#      top_clips/
#
# EXPECTED INSIDE CLIPS:
#   clips/
#      multiple folders...
#
# OUTPUT:
#   output/reaction_720p/
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import os
import csv
import math
import random
import shutil
import subprocess
import sys
import time

from pathlib import Path

import numpy as np

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter
)

from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    CompositeVideoClip
)


# ============================================================
# GOOGLE DRIVE LINKS
# ============================================================

ASSETS_URL = (
    "https://drive.google.com/drive/folders/"
    "1l9ayaXiRBwUr1Hrjag7r3CycVDiN24fh"
)

CLIPS_URL = (
    "https://drive.google.com/drive/folders/"
    "10DSjb9etdFzQTg_rftRJpJkC5jKBjsNT"
)


# ============================================================
# LOCAL WORKING DIRECTORIES
# ============================================================

BASE_DIR = Path.cwd()

DOWNLOAD_ROOT = BASE_DIR / "downloaded"

ASSETS_DIR = DOWNLOAD_ROOT / "assets"

CLIPS_DIR = DOWNLOAD_ROOT / "clips"

OUTPUT_ROOT = BASE_DIR / "output" / "reaction_720p"

LOG_FILE = OUTPUT_ROOT / "processing_log.csv"


# ============================================================
# CREATE DIRECTORIES
# ============================================================

OUTPUT_ROOT.mkdir(
    parents=True,
    exist_ok=True
)

DOWNLOAD_ROOT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# FINAL VIDEO SIZE
# ============================================================

OUT_W = 720
OUT_H = 1280


# ============================================================
# ENCODING
# ============================================================
#
# CRF 26:
#   Smaller file
#   Lower bitrate
#   Lower output quality than CRF 18/20
#
# This is compression, NOT quality enhancement.
# ============================================================

CRF = "26"

ENCODE_PRESET = "veryfast"

AUDIO_BITRATE = "96k"


# ============================================================
# PROCESSING OPTIONS
# ============================================================

# smart:
#   same relative path/name
#   then same filename
#   then sequential
#
# sequential:
#   top[0] + bottom[0]
#   top[1] + bottom[1]

PAIR_MODE = "smart"


# shortest:
#   final duration = shorter clip
#
# loop_shorter:
#   shorter video repeats until longer ends

DURATION_MODE = "shortest"


# Audio:
#   top    = reaction audio first
#   bottom = animation audio first
#   none   = no audio

AUDIO_SOURCE = "top"


# Background:
#   cycle = different background per output
#   first = always first image

BG_MODE = "cycle"


# ============================================================
# OPTIONAL OUTPUT LIMIT
# ============================================================
#
# 0 = process all
# 5 = only first 5
# 10 = only first 10
#
# Useful for testing GitHub Actions first.
# ============================================================

MAX_OUTPUTS = 0


# ============================================================
# INPUT FILE TYPES
# ============================================================

VIDEO_EXTS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
    ".m4v"
}

IMAGE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp"
}


# ============================================================
# SCREEN LAYOUT
# ============================================================


# ------------------------------------------------------------
# TOP REACTION
# ------------------------------------------------------------

TOP_X = 72
TOP_Y = 78

TOP_W = 576
TOP_H = 500


# ------------------------------------------------------------
# BOTTOM ANIMATION
# ------------------------------------------------------------

BOT_X = 17
BOT_Y = 595

BOT_W = 686
BOT_H = 493


# ============================================================
# BORDER
# ============================================================


# TOP
TOP_BORDER = 7
TOP_RADIUS = 23

TOP_BORDER_RGBA = (
    190,
    0,
    255,
    255
)


# BOTTOM
BOT_BORDER = 9
BOT_RADIUS = 27

BOT_BORDER_RGBA = (
    255,
    205,
    0,
    255
)


# ============================================================
# SHADOW
# ============================================================

SHADOW_RGBA = (
    0,
    0,
    0,
    145
)


# ============================================================
# BACKGROUND
# ============================================================

BG_BLUR_RADIUS = 18

BG_DARKEN_ALPHA = 28


# ============================================================
# CROP FOCUS
# ============================================================

# Reaction:
TOP_FOCUS_X = 0.50
TOP_FOCUS_Y = 0.42


# Animation:
BOT_FOCUS_X = 0.50
BOT_FOCUS_Y = 0.50


# ============================================================
# LABELS
# ============================================================

LEFT_LABEL = "HardToonz"

PART_MIN = 1
PART_MAX = 99

LABEL_FONT_SIZE = 35

LABEL_STROKE = 3

LABEL_SHADOW_OFFSET = 3


# ============================================================
# RANDOM PART GENERATOR
# ============================================================

def random_part_label():

    number = random.randint(
        PART_MIN,
        PART_MAX
    )

    return f"Part {number}"


# ============================================================
# RUN COMMAND
# ============================================================

def run_command(
    command,
    title
):

    print("")
    print("=" * 60)
    print(title)
    print("=" * 60)
    print("")

    print(
        " ".join(
            str(x)
            for x in command
        )
    )

    subprocess.run(
        command,
        check=True
    )


# ============================================================
# GOOGLE DRIVE DOWNLOAD
# ============================================================

def download_drive_folder(
    url,
    destination
):

    destination = Path(
        destination
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    # --------------------------------------------------------
    # Don't keep stale partial data.
    # Every GitHub runner is fresh anyway.
    # --------------------------------------------------------

    if destination.exists():

        print(
            "Removing old directory:",
            destination
        )

        shutil.rmtree(
            destination
        )


    destination.mkdir(
        parents=True,
        exist_ok=True
    )


    # --------------------------------------------------------
    # gdown:
    #
    # --folder
    #   folder download
    #
    # --continue
    #   resume partial files
    #
    # --retries 3
    #   retry transient failures
    # --------------------------------------------------------

    command = [

        "gdown",

        "--folder",

        "--continue",

        "--retries",
        "3",

        url,

        "-O",
        str(destination)

    ]


    try:

        run_command(
            command,
            "DOWNLOADING GOOGLE DRIVE FOLDER"
        )

    except subprocess.CalledProcessError as error:

        print("")
        print(
            "Google Drive download failed."
        )

        print(
            "Check that the folder is shared as:"
        )

        print(
            "Anyone with the link -> Viewer"
        )

        raise error


# ============================================================
# DOWNLOAD ASSETS
# ============================================================

download_drive_folder(
    ASSETS_URL,
    ASSETS_DIR
)


# ============================================================
# DOWNLOAD CLIPS
# ============================================================

download_drive_folder(
    CLIPS_URL,
    CLIPS_DIR
)


# ============================================================
# FIND NAMED DIRECTORIES
# ============================================================

def find_named_directories(
    root,
    directory_name
):

    root = Path(root)

    results = []

    if not root.exists():
        return results


    for path in root.rglob("*"):

        if not path.is_dir():
            continue

        if (
            path.name.lower()
            ==
            directory_name.lower()
        ):

            results.append(path)


    return sorted(
        results,
        key=lambda x: str(x).lower()
    )


# ============================================================
# FIND ASSET SUBDIRECTORIES
# ============================================================

bg_dirs = find_named_directories(
    ASSETS_DIR,
    "Bg_Pic"
)

top_dirs = find_named_directories(
    ASSETS_DIR,
    "top_clips"
)


# ============================================================
# FALLBACK:
# If exact folders were not found, scan whole assets folder.
# ============================================================

if not bg_dirs:

    bg_dirs = [
        ASSETS_DIR
    ]


if not top_dirs:

    top_dirs = [
        ASSETS_DIR
    ]


# ============================================================
# SCAN FILES INSIDE MULTIPLE DIRECTORIES
# ============================================================

def scan_dirs(
    directories,
    extensions
):

    found = []

    seen = set()


    for directory in directories:

        directory = Path(
            directory
        )

        if not directory.exists():
            continue


        for file in directory.rglob("*"):

            if not file.is_file():
                continue


            if file.suffix.lower() not in extensions:
                continue


            key = str(
                file.resolve()
            )


            if key in seen:
                continue


            seen.add(key)

            found.append(file)


    return sorted(
        found,
        key=lambda x: str(x).lower()
    )


# ============================================================
# INPUT FILES
# ============================================================

bg_files = scan_dirs(
    bg_dirs,
    IMAGE_EXTS
)


top_files = scan_dirs(
    top_dirs,
    VIDEO_EXTS
)


bottom_files = scan_dirs(
    [CLIPS_DIR],
    VIDEO_EXTS
)


# ============================================================
# PRINT SCAN
# ============================================================

print("")
print("=" * 60)
print("INPUT FILE SCAN")
print("=" * 60)
print("")

print(
    "Background images:",
    len(bg_files)
)

print(
    "Top reaction clips:",
    len(top_files)
)

print(
    "Bottom animation clips:",
    len(bottom_files)
)

print("")


# ============================================================
# VALIDATION
# ============================================================

if not bg_files:

    raise FileNotFoundError(
        "No background image found in Google Drive assets folder."
    )


if not top_files:

    raise FileNotFoundError(
        "No top reaction videos found in Google Drive assets folder."
    )


if not bottom_files:

    raise FileNotFoundError(
        "No animation videos found in Google Drive clips folder."
    )


# ============================================================
# NORMALIZE FILE KEY
# ============================================================

def file_stem_key(
    path
):

    return Path(
        path
    ).stem.lower().strip()


# ============================================================
# SMART PAIRING
# ============================================================

def make_pairs(
    top_list,
    bottom_list
):

    # --------------------------------------------------------
    # SEQUENTIAL
    # --------------------------------------------------------

    if PAIR_MODE == "sequential":

        count = min(
            len(top_list),
            len(bottom_list)
        )

        return [

            (
                top_list[i],
                bottom_list[i]
            )

            for i in range(count)

        ]


    # --------------------------------------------------------
    # INDEX BOTTOM BY STEM
    # --------------------------------------------------------

    bottom_by_stem = {}

    for bottom in bottom_list:

        stem = file_stem_key(
            bottom
        )

        bottom_by_stem.setdefault(
            stem,
            []
        ).append(
            bottom
        )


    pairs = []

    used_bottom = set()

    unmatched_top = []


    # --------------------------------------------------------
    # SAME STEM FIRST
    # --------------------------------------------------------

    for top in top_list:

        stem = file_stem_key(
            top
        )

        candidates = (
            bottom_by_stem.get(
                stem,
                []
            )
        )


        selected = None


        for candidate in candidates:

            if (
                str(candidate)
                not in
                used_bottom
            ):

                selected = candidate

                break


        if selected is not None:

            pairs.append(
                (
                    top,
                    selected
                )
            )

            used_bottom.add(
                str(selected)
            )

        else:

            unmatched_top.append(
                top
            )


    # --------------------------------------------------------
    # SEQUENTIAL FALLBACK
    # --------------------------------------------------------

    remaining_bottom = [

        bottom

        for bottom in bottom_list

        if (
            str(bottom)
            not in
            used_bottom
        )

    ]


    for top, bottom in zip(

        unmatched_top,

        remaining_bottom

    ):

        pairs.append(
            (
                top,
                bottom
            )
        )


    # --------------------------------------------------------
    # RESTORE TOP ORDER
    # --------------------------------------------------------

    order_map = {

        str(path): index

        for index, path

        in enumerate(
            top_list
        )

    }


    pairs.sort(

        key=lambda item:
            order_map.get(
                str(item[0]),
                999999999
            )

    )


    return pairs


# ============================================================
# CREATE PAIRS
# ============================================================

pairs = make_pairs(
    top_files,
    bottom_files
)


# ============================================================
# APPLY LIMIT
# ============================================================

if (
    MAX_OUTPUTS > 0
    and
    len(pairs) > MAX_OUTPUTS
):

    pairs = pairs[
        :MAX_OUTPUTS
    ]


# ============================================================
# PAIR STATUS
# ============================================================

print(
    "Video pairs:",
    len(pairs)
)


if not pairs:

    raise RuntimeError(
        "No top/bottom video pairs available."
    )


# ============================================================
# FONT
# ============================================================

def find_font():

    font_candidates = [

        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSansCondensed-Bold.ttf",

        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans-Bold.ttf",

        "/usr/share/fonts/truetype/liberation2/"
        "LiberationSans-Bold.ttf"

    ]


    for font in font_candidates:

        if os.path.exists(font):

            return font


    return None


FONT_PATH = find_font()


def load_font(
    size
):

    if FONT_PATH:

        return ImageFont.truetype(
            FONT_PATH,
            size
        )

    return ImageFont.load_default()


# ============================================================
# ROUNDED MASK
# ============================================================

def rounded_mask(
    width,
    height,
    radius
):

    width = int(
        width
    )

    height = int(
        height
    )


    mask = Image.new(

        "L",

        (
            width,
            height
        ),

        0

    )


    draw = ImageDraw.Draw(
        mask
    )


    draw.rounded_rectangle(

        (
            0,
            0,
            width - 1,
            height - 1
        ),

        radius=int(
            radius
        ),

        fill=255

    )


    return (
        np.asarray(
            mask,
            dtype=np.float32
        )
        /
        255.0
    )


# ============================================================
# PANEL OVERLAY
# ============================================================

def make_panel_overlay(

    width,
    height,

    border_width,
    radius,

    border_rgba,

    show_labels=False

):

    width = int(
        width
    )

    height = int(
        height
    )


    canvas = Image.new(

        "RGBA",

        (
            width,
            height
        ),

        (
            0,
            0,
            0,
            0
        )

    )


    # ========================================================
    # SHADOW
    # ========================================================

    shadow = Image.new(

        "RGBA",

        (
            width,
            height
        ),

        (
            0,
            0,
            0,
            0
        )

    )


    shadow_draw = ImageDraw.Draw(
        shadow
    )


    shadow_draw.rounded_rectangle(

        (
            5,
            7,
            width - 1,
            height - 1
        ),

        radius=radius,

        fill=SHADOW_RGBA

    )


    shadow = shadow.filter(

        ImageFilter.GaussianBlur(
            11
        )

    )


    canvas.alpha_composite(
        shadow
    )


    # ========================================================
    # BORDER
    # ========================================================

    draw = ImageDraw.Draw(
        canvas
    )


    draw.rounded_rectangle(

        (
            1,
            1,
            width - 2,
            height - 2
        ),

        radius=radius,

        outline=border_rgba,

        width=border_width

    )


    # ========================================================
    # LABELS
    # ========================================================

    if show_labels:

        font = load_font(
            LABEL_FONT_SIZE
        )


        right_label = (
            random_part_label()
        )


        left_x = 14

        top_y = 7

        right_x = width - 14


        # ----------------------------------------------------
        # LEFT SHADOW
        # ----------------------------------------------------

        draw.text(

            (
                left_x + LABEL_SHADOW_OFFSET,
                top_y + LABEL_SHADOW_OFFSET
            ),

            LEFT_LABEL,

            font=font,

            fill=(
                0,
                0,
                0,
                180
            ),

            stroke_width=(
                LABEL_STROKE + 2
            ),

            stroke_fill=(
                0,
                0,
                0,
                180
            ),

            anchor="la"

        )


        # ----------------------------------------------------
        # RIGHT SHADOW
        # ----------------------------------------------------

        draw.text(

            (
                right_x + LABEL_SHADOW_OFFSET,
                top_y + LABEL_SHADOW_OFFSET
            ),

            right_label,

            font=font,

            fill=(
                0,
                0,
                0,
                180
            ),

            stroke_width=(
                LABEL_STROKE + 2
            ),

            stroke_fill=(
                0,
                0,
                0,
                180
            ),

            anchor="ra"

        )


        # ----------------------------------------------------
        # LEFT LABEL
        # ----------------------------------------------------

        draw.text(

            (
                left_x,
                top_y
            ),

            LEFT_LABEL,

            font=font,

            fill=(
                255,
                255,
                255,
                255
            ),

            stroke_width=LABEL_STROKE,

            stroke_fill=(
                0,
                160,
                205,
                255
            ),

            anchor="la"

        )


        # ----------------------------------------------------
        # RIGHT LABEL
        # ----------------------------------------------------

        draw.text(

            (
                right_x,
                top_y
            ),

            right_label,

            font=font,

            fill=(
                255,
                255,
                255,
                255
            ),

            stroke_width=LABEL_STROKE,

            stroke_fill=(
                0,
                160,
                205,
                255
            ),

            anchor="ra"

        )


    return np.asarray(
        canvas
    )


# ============================================================
# BACKGROUND
# ============================================================

def prepare_background(
    image_path
):

    image = Image.open(
        image_path
    ).convert(
        "RGB"
    )


    src_w, src_h = image.size


    target_ratio = (
        OUT_W /
        OUT_H
    )


    source_ratio = (
        src_w /
        src_h
    )


    # --------------------------------------------------------
    # CROP TO 9:16
    # --------------------------------------------------------

    if source_ratio > target_ratio:

        new_w = int(
            src_h *
            target_ratio
        )

        left = (
            src_w -
            new_w
        ) // 2


        image = image.crop(

            (
                left,
                0,
                left + new_w,
                src_h
            )

        )

    else:

        new_h = int(
            src_w /
            target_ratio
        )

        top = (
            src_h -
            new_h
        ) // 2


        image = image.crop(

            (
                0,
                top,
                src_w,
                top + new_h
            )

        )


    # --------------------------------------------------------
    # FINAL CANVAS SIZE
    # --------------------------------------------------------

    image = image.resize(

        (
            OUT_W,
            OUT_H
        ),

        Image.Resampling.LANCZOS

    )


    # --------------------------------------------------------
    # BLUR
    # --------------------------------------------------------

    image = image.filter(

        ImageFilter.GaussianBlur(
            BG_BLUR_RADIUS
        )

    )


    # --------------------------------------------------------
    # DARK OVERLAY
    # --------------------------------------------------------

    image = image.convert(
        "RGBA"
    )


    overlay = Image.new(

        "RGBA",

        (
            OUT_W,
            OUT_H
        ),

        (
            0,
            0,
            0,
            BG_DARKEN_ALPHA
        )

    )


    image.alpha_composite(
        overlay
    )


    return np.asarray(
        image
    )


# ============================================================
# VIDEO COVER CROP
# ============================================================

def cover_crop(

    clip,

    target_w,
    target_h,

    focus_x=0.5,
    focus_y=0.5

):

    target_w = int(
        target_w
    )

    target_h = int(
        target_h
    )


    # --------------------------------------------------------
    # SCALE UNTIL AREA IS FILLED
    # --------------------------------------------------------

    scale = max(

        target_w /
        float(clip.w),

        target_h /
        float(clip.h)

    )


    new_w = max(

        target_w,

        int(
            round(
                clip.w *
                scale
            )
        )

    )


    new_h = max(

        target_h,

        int(
            round(
                clip.h *
                scale
            )
        )

    )


    # --------------------------------------------------------
    # RESIZE
    # --------------------------------------------------------

    resized = clip.resize(

        newsize=(
            new_w,
            new_h
        )

    )


    # --------------------------------------------------------
    # CROP
    # --------------------------------------------------------

    max_x = max(

        0,

        new_w -
        target_w

    )


    max_y = max(

        0,

        new_h -
        target_h

    )


    x1 = (
        max_x *
        float(focus_x)
    )


    y1 = (
        max_y *
        float(focus_y)
    )


    x2 = (
        x1 +
        target_w
    )


    y2 = (
        y1 +
        target_h
    )


    return resized.crop(

        x1=x1,
        y1=y1,

        x2=x2,
        y2=y2

    )


# ============================================================
# LOOP SHORTER CLIP
# ============================================================

def loop_or_cut(
    clip,
    duration
):

    duration = float(
        duration
    )


    if (
        clip.duration is None
        or
        clip.duration >= duration
    ):

        return clip.subclip(
            0,
            duration
        )


    count = int(

        math.ceil(

            duration /
            max(
                clip.duration,
                0.001
            )

        )

    )


    return (

        clip
        .loop(
            n=count
        )
        .subclip(
            0,
            duration
        )

    )


# ============================================================
# ROUND MASK
# ============================================================

def apply_round_mask(

    clip,

    width,
    height,

    radius

):

    mask_array = rounded_mask(

        width,
        height,
        radius

    )


    mask = ImageClip(

        mask_array,

        ismask=True

    ).set_duration(
        clip.duration
    )


    return clip.set_mask(
        mask
    )


# ============================================================
# STRICT SOURCE FPS
# ============================================================
#
# No artificial fallback.
# If FPS metadata is unavailable, the video fails instead of
# silently converting to 30 FPS.
# ============================================================

def get_source_fps(
    clip
):

    fps = None


    try:

        fps = clip.fps

    except Exception:

        fps = None


    if not fps:

        try:

            fps = clip.reader.fps

        except Exception:

            fps = None


    if not fps:

        raise ValueError(
            "Source FPS metadata is missing."
        )


    fps = float(
        fps
    )


    if fps <= 0:

        raise ValueError(
            "Invalid source FPS."
        )


    return fps


# ============================================================
# OUTPUT PATH
# ============================================================

def make_output_path(

    index,
    top_path

):

    top_path = Path(
        top_path
    )


    safe_name = "".join(

        char

        if (
            char.isalnum()
            or
            char in "._-"
        )

        else "_"

        for char
        in top_path.stem

    )


    return (

        OUTPUT_ROOT
        /
        f"{index:04d}_"
        f"{safe_name}_720p.mp4"

    )


# ============================================================
# PROCESS ONE PAIR
# ============================================================

def process_one(

    index,
    top_path,
    bottom_path

):

    start_time = time.time()


    top = None
    bottom = None
    final = None


    try:

        print("")
        print("=" * 60)
        print(
            f"PROCESSING "
            f"{index}/{len(pairs)}"
        )
        print("=" * 60)


        print(
            "Top:",
            top_path
        )


        print(
            "Bottom:",
            bottom_path
        )


        # ====================================================
        # LOAD
        # ====================================================

        top = VideoFileClip(
            str(top_path),
            audio=True
        )


        bottom = VideoFileClip(
            str(bottom_path),
            audio=True
        )


        # ====================================================
        # FPS
        # ====================================================

        source_fps = get_source_fps(
            top
        )


        print(
            "Source FPS:",
            source_fps
        )


        # ====================================================
        # DURATIONS
        # ====================================================

        top_duration = float(
            top.duration or 0
        )


        bottom_duration = float(
            bottom.duration or 0
        )


        if top_duration <= 0:

            raise ValueError(
                "Top video duration is invalid."
            )


        if bottom_duration <= 0:

            raise ValueError(
                "Bottom video duration is invalid."
            )


        # ====================================================
        # DURATION
        # ====================================================

        if DURATION_MODE == "loop_shorter":

            duration = max(

                top_duration,

                bottom_duration

            )


            top_use = loop_or_cut(
                top,
                duration
            )


            bottom_use = loop_or_cut(
                bottom,
                duration
            )


        else:

            duration = min(

                top_duration,

                bottom_duration

            )


            top_use = top.subclip(

                0,
                duration

            )


            bottom_use = bottom.subclip(

                0,
                duration

            )


        # ====================================================
        # INTERIOR SIZES
        # ====================================================

        top_inner_w = (

            TOP_W -
            (
                TOP_BORDER *
                2
            )

        )


        top_inner_h = (

            TOP_H -
            (
                TOP_BORDER *
                2
            )

        )


        bot_inner_w = (

            BOT_W -
            (
                BOT_BORDER *
                2
            )

        )


        bot_inner_h = (

            BOT_H -
            (
                BOT_BORDER *
                2
            )

        )


        # ====================================================
        # TOP REACTION
        # ====================================================

        top_use = cover_crop(

            top_use,

            top_inner_w,
            top_inner_h,

            TOP_FOCUS_X,
            TOP_FOCUS_Y

        )


        top_use = apply_round_mask(

            top_use,

            top_inner_w,
            top_inner_h,

            TOP_RADIUS -
            TOP_BORDER

        )


        top_use = top_use.set_position(

            (
                TOP_X +
                TOP_BORDER,

                TOP_Y +
                TOP_BORDER
            )

        )


        # ====================================================
        # BOTTOM ANIMATION
        # ====================================================

        bottom_use = cover_crop(

            bottom_use,

            bot_inner_w,
            bot_inner_h,

            BOT_FOCUS_X,
            BOT_FOCUS_Y

        )


        bottom_use = apply_round_mask(

            bottom_use,

            bot_inner_w,
            bot_inner_h,

            BOT_RADIUS -
            BOT_BORDER

        )


        bottom_use = bottom_use.set_position(

            (
                BOT_X +
                BOT_BORDER,

                BOT_Y +
                BOT_BORDER
            )

        )


        # ====================================================
        # BACKGROUND
        # ====================================================

        if BG_MODE == "cycle":

            bg_path = bg_files[

                (
                    index -
                    1
                )
                %
                len(bg_files)

            ]

        else:

            bg_path = bg_files[0]


        background_array = (
            prepare_background(
                str(bg_path)
            )
        )


        background = ImageClip(
            background_array
        ).set_duration(
            duration
        )


        # ====================================================
        # TOP FRAME
        # ====================================================

        top_frame_array = (
            make_panel_overlay(

                TOP_W,
                TOP_H,

                TOP_BORDER,
                TOP_RADIUS,

                TOP_BORDER_RGBA,

                show_labels=False

            )
        )


        top_frame = ImageClip(

            top_frame_array,

            transparent=True

        ).set_duration(
            duration
        )


        top_frame = top_frame.set_position(

            (
                TOP_X,
                TOP_Y
            )

        )


        # ====================================================
        # BOTTOM FRAME + LABEL
        # ====================================================

        bottom_frame_array = (
            make_panel_overlay(

                BOT_W,
                BOT_H,

                BOT_BORDER,
                BOT_RADIUS,

                BOT_BORDER_RGBA,

                show_labels=True

            )
        )


        bottom_frame = ImageClip(

            bottom_frame_array,

            transparent=True

        ).set_duration(
            duration
        )


        bottom_frame = bottom_frame.set_position(

            (
                BOT_X,
                BOT_Y
            )

        )


        # ====================================================
        # FINAL COMPOSITION
        # ====================================================
        #
        # This contains ONLY our video layers.
        #
        # No Android UI
        # No YouTube UI
        # No status bar
        # No navigation buttons
        # No app controls
        # ====================================================

        final = CompositeVideoClip(

            [

                background,

                top_use,

                bottom_use,

                top_frame,

                bottom_frame

            ],

            size=(
                OUT_W,
                OUT_H
            )

        ).set_duration(
            duration
        )


        # ====================================================
        # AUDIO
        # ====================================================

        if (

            AUDIO_SOURCE == "top"
            and
            top.audio is not None

        ):

            final = final.set_audio(

                top.audio.subclip(
                    0,
                    duration
                )

            )


        elif (

            AUDIO_SOURCE == "bottom"
            and
            bottom.audio is not None

        ):

            final = final.set_audio(

                bottom.audio.subclip(
                    0,
                    duration
                )

            )


        elif (

            top.audio is not None

        ):

            # Automatic fallback
            final = final.set_audio(

                top.audio.subclip(
                    0,
                    duration
                )

            )


        elif (

            bottom.audio is not None

        ):

            # Automatic fallback
            final = final.set_audio(

                bottom.audio.subclip(
                    0,
                    duration
                )

            )


        else:

            final = final.without_audio()


        # ====================================================
        # OUTPUT
        # ====================================================

        output_file = make_output_path(

            index,

            top_path

        )


        # ====================================================
        # WRITE VIDEO
        # ====================================================
        #
        # FPS = source_fps
        #
        # This preserves source FPS.
        #
        # Example:
        #   24 -> 24
        #   25 -> 25
        #   29.97 -> 29.97
        #   30 -> 30
        #   60 -> 60
        #
        # Resolution:
        #   720x1280
        # ====================================================

        final.write_videofile(

            str(output_file),

            fps=source_fps,

            codec="libx264",

            audio=(
                final.audio is not None
            ),

            audio_codec=(
                "aac"
                if final.audio is not None
                else None
            ),

            audio_bitrate=(
                AUDIO_BITRATE
                if final.audio is not None
                else None
            ),

            preset=ENCODE_PRESET,

            ffmpeg_params=[

                "-crf",
                CRF,

                "-pix_fmt",
                "yuv420p",

                "-movflags",
                "+faststart"

            ],

            threads=max(

                1,

                min(
                    8,
                    os.cpu_count() or 2
                )

            ),

            logger=None

        )


        elapsed = (
            time.time()
            -
            start_time
        )


        print("")
        print(
            "SUCCESS"
        )

        print(
            "Output:",
            output_file
        )

        print(
            "Resolution:",
            f"{OUT_W}x{OUT_H}"
        )

        print(
            "FPS:",
            source_fps
        )

        print(
            "Duration:",
            round(
                duration,
                2
            ),
            "sec"
        )

        print(
            "Time:",
            round(
                elapsed,
                2
            ),
            "sec"
        )


        return {

            "index":
                index,

            "status":
                "DONE",

            "top":
                str(
                    top_path
                ),

            "bottom":
                str(
                    bottom_path
                ),

            "output":
                str(
                    output_file
                ),

            "fps":
                source_fps,

            "width":
                OUT_W,

            "height":
                OUT_H,

            "duration":
                round(
                    duration,
                    2
                ),

            "seconds":
                round(
                    elapsed,
                    2
                ),

            "error":
                ""

        }


    except Exception as error:

        print("")
        print(
            "FAILED:"
        )

        print(
            repr(error)
        )


        return {

            "index":
                index,

            "status":
                "ERROR",

            "top":
                str(
                    top_path
                ),

            "bottom":
                str(
                    bottom_path
                ),

            "output":
                "",

            "fps":
                "",

            "width":
                OUT_W,

            "height":
                OUT_H,

            "duration":
                "",

            "seconds":
                round(
                    time.time()
                    -
                    start_time,
                    2
                ),

            "error":
                repr(
                    error
                )

        }


    finally:

        # ====================================================
        # FREE MEMORY
        # ====================================================

        try:

            if final is not None:

                final.close()

        except Exception:

            pass


        try:

            if top is not None:

                top.close()

        except Exception:

            pass


        try:

            if bottom is not None:

                bottom.close()

        except Exception:

            pass


# ============================================================
# START PROCESSING
# ============================================================

results = []


print("")
print("=" * 60)
print("STARTING VIDEO PROCESSING")
print("=" * 60)


for index, (

    top_path,
    bottom_path

) in enumerate(

    pairs,

    start=1

):

    result = process_one(

        index,

        top_path,

        bottom_path

    )


    results.append(
        result
    )


# ============================================================
# SAVE CSV
# ============================================================

with open(

    LOG_FILE,

    "w",

    newline="",

    encoding="utf-8"

) as csv_file:

    writer = csv.DictWriter(

        csv_file,

        fieldnames=[

            "index",
            "status",
            "top",
            "bottom",
            "output",
            "fps",
            "width",
            "height",
            "duration",
            "seconds",
            "error"

        ]

    )


    writer.writeheader()


    for result in results:

        writer.writerow({

            "index":
                result.get(
                    "index",
                    ""
                ),

            "status":
                result.get(
                    "status",
                    ""
                ),

            "top":
                result.get(
                    "top",
                    ""
                ),

            "bottom":
                result.get(
                    "bottom",
                    ""
                ),

            "output":
                result.get(
                    "output",
                    ""
                ),

            "fps":
                result.get(
                    "fps",
                    ""
                ),

            "width":
                result.get(
                    "width",
                    ""
                ),

            "height":
                result.get(
                    "height",
                    ""
                ),

            "duration":
                result.get(
                    "duration",
                    ""
                ),

            "seconds":
                result.get(
                    "seconds",
                    ""
                ),

            "error":
                result.get(
                    "error",
                    ""
                )

        )


# ============================================================
# SUMMARY
# ============================================================

success_count = sum(

    1

    for result in results

    if (
        result["status"]
        ==
        "DONE"
    )

)


failed_count = sum(

    1

    for result in results

    if (
        result["status"]
        ==
        "ERROR"
    )

)


print("")
print("")
print("=" * 60)
print("PROCESSING FINISHED")
print("=" * 60)
print("")

print(
    "Successful:",
    success_count
)

print(
    "Failed:",
    failed_count
)

print(
    "Output:",
    OUTPUT_ROOT
)

print(
    "Log:",
    LOG_FILE
)

print("")
print(
    "FINAL VIDEO:"
)

print(
    "720 x 1280"
)

print(
    "SOURCE FPS PRESERVED"
)

print(
    "NO ANDROID UI"
)

print(
    "NO YOUTUBE UI"
)

print("=" * 60)
