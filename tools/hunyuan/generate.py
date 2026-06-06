"""Batch image -> 3D generation for HabitBud (Hunyuan3D-2).

Run from inside a cloned Hunyuan3D-2 repo (so `hy3dgen` imports). The plain
Gemini background is removed with a PIL corner flood-fill -> RGBA, so the
pipeline skips its own rembg path (no onnxruntime needed).

Examples
--------
    # shape only, ~40k faces, fast (~6 GB VRAM)
    python generate.py --input <imgs> --out ./out

    # textured + capped at 30k faces (recommended for app/rig)
    python generate.py --input <imgs> --out ./out --texture --faces 30000

    # raw high detail (huge, ~500k faces) -> only if you'll decimate later
    python generate.py --input <imgs> --out ./out --octree 384 --faces 0

Options
-------
  --octree N    marching-cubes resolution; higher = more detail + more faces
                (256 fast / 320 detailed / 384 max). Default 256.
  --faces  N    cap final triangle count via quadric decimation (FaceReducer).
                0 disables reduction. Default 40000. Lower = smaller GLB.
  --texture     also bake a color texture (needs the texgen custom rasterizer).
  --steps  N    diffusion steps (quality vs speed). Default 30.

Tip: put the model cache on a big drive:  set HF_HOME=D:\\hf_cache
"""
import argparse
import glob
import os
import time

# Keep the multi-GB model cache off a full C: drive.
os.environ.setdefault('HF_HOME', 'D:\\hf_cache')
os.environ.setdefault('HF_HUB_CACHE', 'D:\\hf_cache\\hub')
os.environ.setdefault('HF_XET_CACHE', 'D:\\hf_cache\\xet')

import numpy as np
from PIL import Image, ImageDraw

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


def clean_mesh(mesh, max_faces):
    """Remove floaters/degenerate faces and decimate to `max_faces` triangles.
    Run BEFORE texturing so the texture is baked onto the light mesh."""
    try:
        from hy3dgen.shapegen import FloaterRemover, DegenerateFaceRemover, FaceReducer
        mesh = FloaterRemover()(mesh)
        mesh = DegenerateFaceRemover()(mesh)
        if max_faces and max_faces > 0:
            mesh = FaceReducer()(mesh, max_facenum=max_faces)
    except Exception as e:
        print("  clean_mesh warn:", e)
    return mesh


def matte_export(mesh, out_path):
    """Hunyuan exports materials metallic=1 with no normals -> dark in PBR
    viewers. Force matte, downscale the texture, ensure normals."""
    try:
        mat = getattr(mesh.visual, 'material', None)
        if mat is not None:
            if hasattr(mat, 'metallicFactor'):
                mat.metallicFactor = 0.0
            if hasattr(mat, 'roughnessFactor'):
                mat.roughnessFactor = 0.9
            tex = getattr(mat, 'baseColorTexture', None)
            if tex is not None and hasattr(tex, 'size') and max(tex.size) > 1024:
                mat.baseColorTexture = tex.convert('RGB').resize((1024, 1024), Image.LANCZOS)
    except Exception:
        pass
    try:
        _ = mesh.vertex_normals
    except Exception:
        pass
    mesh.export(out_path)


def generate_one(shape, paint, path, out_dir, steps, octree, faces, tag=''):
    import torch
    name = os.path.splitext(os.path.basename(path))[0].replace(' ', '_').lower()
    out_path = os.path.join(out_dir, f"{name}.glb")
    print(f"\n{tag}=== {name} ===")
    t = time.time()
    img = bg_to_alpha(path)
    mesh = shape(image=img, num_inference_steps=steps, octree_resolution=octree,
                 num_chunks=20000, generator=torch.manual_seed(42), output_type='trimesh')[0]
    mesh = clean_mesh(mesh, faces)
    try:
        print(f"{tag}  faces after reduce: {len(mesh.faces)}")
    except Exception:
        pass
    if paint is not None:
        mesh = paint(mesh, image=img)
    matte_export(mesh, out_path)
    print(f"{tag}  -> {out_path}  ({time.time() - t:.1f}s)")


def load_pipelines(texture):
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
    print("loading shape model tencent/Hunyuan3D-2mini ...")
    shape = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        'tencent/Hunyuan3D-2mini', subfolder='hunyuan3d-dit-v2-mini', variant='fp16')
    paint = None
    if texture:
        print("loading paint model tencent/Hunyuan3D-2 ...")
        from hy3dgen.texgen import Hunyuan3DPaintPipeline
        paint = Hunyuan3DPaintPipeline.from_pretrained('tencent/Hunyuan3D-2')
    return shape, paint


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help="Folder of input images")
    ap.add_argument('--out', default='./out', help="Output folder for GLBs")
    ap.add_argument('--steps', type=int, default=30)
    ap.add_argument('--octree', type=int, default=256)
    ap.add_argument('--faces', type=int, default=40000, help="Cap triangle count (0 = no reduction)")
    ap.add_argument('--texture', action='store_true', help="Also synthesize texture")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    images = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.webp'):
        images.extend(glob.glob(os.path.join(args.input, ext)))
    images.sort()
    if not images:
        print(f"No images in {args.input}")
        return

    shape, paint = load_pipelines(args.texture)
    for path in images:
        try:
            generate_one(shape, paint, path, args.out, args.steps, args.octree, args.faces)
        except Exception as exc:
            print(f"  FAILED {os.path.basename(path)}: {exc}")
    print(f"\nDone. GLBs in {os.path.abspath(args.out)}")


if __name__ == '__main__':
    main()
