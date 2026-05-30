"""Batch image->3D generation for HabitBud (no rembg/onnxruntime needed).

Run from inside a cloned Hunyuan3D-2 repo (so `hy3dgen` imports). Background is
removed with a PIL corner flood-fill (the Gemini plush images have a plain,
edge-touching background) -> RGBA, so the pipeline skips its own rembg path.

Examples:
    # all images in a folder -> ./out/<name>.glb  (shape only, ~6 GB VRAM)
    python generate.py --input <path>/animals_gemini_2d --out ./out

    # with texture (~16 GB; needs the texgen custom rasterizer built)
    python generate.py --input <path> --out ./out --texture

Tip: put the model cache on a big drive:  set HF_HOME=D:\hf_cache
"""
import argparse
import glob
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw
import torch

from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

SENTINEL = (255, 0, 255)


def bg_to_alpha(path):
    """Plain background -> transparent via corner flood-fill; crop + square pad."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    flood = img.copy()
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        try:
            ImageDraw.floodfill(flood, corner, SENTINEL, thresh=40)
        except Exception:
            pass
    arr = np.array(flood).astype(int)
    mask_bg = np.all(np.abs(arr - np.array(SENTINEL)) < 12, axis=-1)
    rgba = np.array(img.convert("RGBA"))
    rgba[mask_bg, 3] = 0
    out = Image.fromarray(rgba, "RGBA")
    bbox = out.split()[-1].getbbox()
    if bbox:
        out = out.crop(bbox)
    cw, ch = out.size
    side = int(max(cw, ch) * 1.15)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(out, ((side - cw) // 2, (side - ch) // 2), out)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help="Folder of input images")
    ap.add_argument('--out', default='./out', help="Output folder for GLBs")
    ap.add_argument('--steps', type=int, default=30)
    ap.add_argument('--octree', type=int, default=256)
    ap.add_argument('--texture', action='store_true', help="Also synthesize texture")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    print("loading shape model tencent/Hunyuan3D-2mini ...")
    shape = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        'tencent/Hunyuan3D-2mini', subfolder='hunyuan3d-dit-v2-mini', variant='fp16'
    )
    paint = None
    if args.texture:
        from hy3dgen.texgen import Hunyuan3DPaintPipeline
        paint = Hunyuan3DPaintPipeline.from_pretrained('tencent/Hunyuan3D-2')

    images = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.webp'):
        images.extend(glob.glob(os.path.join(args.input, ext)))
    images.sort()
    if not images:
        print(f"No images in {args.input}")
        return

    for path in images:
        name = os.path.splitext(os.path.basename(path))[0].replace(' ', '_').lower()
        out_path = os.path.join(args.out, f"{name}.glb")
        print(f"\n=== {name} ===")
        try:
            img = bg_to_alpha(path)
            t = time.time()
            mesh = shape(image=img, num_inference_steps=args.steps, octree_resolution=args.octree,
                         num_chunks=20000, generator=torch.manual_seed(42), output_type='trimesh')[0]
            if paint is not None:
                mesh = paint(mesh, image=img)
            mesh.export(out_path)
            print(f"  -> {out_path}  ({time.time() - t:.1f}s)")
        except Exception as exc:
            print(f"  FAILED {name}: {exc}")

    print(f"\nDone. GLBs in {os.path.abspath(args.out)}")


if __name__ == '__main__':
    main()
