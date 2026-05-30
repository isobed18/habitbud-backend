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

# Force Hugging Face to use the D: drive cache folder (Windows C: drive has very low space)
os.environ['HF_HOME'] = 'D:\\hf_cache'
os.environ['HF_HUB_CACHE'] = 'D:\\hf_cache\\hub'
os.environ['HF_XET_CACHE'] = 'D:\\hf_cache\\xet'

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


def matte_export(mesh, out_path):
    """Hunyuan exports materials as metallic=1 with no vertex normals, which look
    dark in any PBR viewer (Three.js, Unity, Blender preview). Force matte plush
    materials and ensure normals so the baked colors read correctly everywhere."""
    try:
        mat = getattr(mesh.visual, 'material', None)
        if mat is not None:
            if hasattr(mat, 'metallicFactor'):
                mat.metallicFactor = 0.0
            if hasattr(mat, 'roughnessFactor'):
                mat.roughnessFactor = 0.9
            # Downscale the base-color texture for lighter mobile GLBs.
            tex = getattr(mat, 'baseColorTexture', None)
            if tex is not None and hasattr(tex, 'size') and max(tex.size) > 512:
                from PIL import Image as _Img
                mat.baseColorTexture = tex.convert('RGB').resize((512, 512), _Img.LANCZOS)
    except Exception:
        pass
    try:
        _ = mesh.vertex_normals  # triggers computation so they get exported
    except Exception:
        pass
    mesh.export(out_path)


def worker_main(queue, out_dir, steps, octree, texture, worker_id):
    import torch
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

    print(f"[Worker {worker_id}] Loading shape model tencent/Hunyuan3D-2mini ...")
    shape = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        'tencent/Hunyuan3D-2mini', subfolder='hunyuan3d-dit-v2-mini', variant='fp16'
    )
    paint = None
    if texture:
        print(f"[Worker {worker_id}] Loading paint model tencent/Hunyuan3D-2 ...")
        from hy3dgen.texgen import Hunyuan3DPaintPipeline
        paint = Hunyuan3DPaintPipeline.from_pretrained('tencent/Hunyuan3D-2')

    print(f"[Worker {worker_id}] Loaded successfully. Processing images...")

    while True:
        try:
            path = queue.get_nowait()
        except Exception:
            break

        name = os.path.splitext(os.path.basename(path))[0].replace(' ', '_').lower()
        out_path = os.path.join(out_dir, f"{name}.glb")
        print(f"\n[Worker {worker_id}] === Starting {name} ===")
        try:
            img = bg_to_alpha(path)
            t = time.time()
            mesh = shape(image=img, num_inference_steps=steps, octree_resolution=octree,
                         num_chunks=20000, generator=torch.manual_seed(42), output_type='trimesh')[0]
            if paint is not None:
                mesh = paint(mesh, image=img)
            matte_export(mesh, out_path)
            print(f"[Worker {worker_id}]   -> {out_path}  ({time.time() - t:.1f}s)")
        except Exception as exc:
            print(f"[Worker {worker_id}]   FAILED {name}: {exc}")

    print(f"[Worker {worker_id}] Worker finished.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help="Folder of input images")
    ap.add_argument('--out', default='./out', help="Output folder for GLBs")
    ap.add_argument('--steps', type=int, default=30)
    ap.add_argument('--octree', type=int, default=256)
    ap.add_argument('--texture', action='store_true', help="Also synthesize texture")
    ap.add_argument('--workers', type=int, default=None, help="Number of parallel worker processes (default: 2 for shape-only, 1 for texture)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    images = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.webp'):
        images.extend(glob.glob(os.path.join(args.input, ext)))
    images.sort()
    if not images:
        print(f"No images in {args.input}")
        return

    workers_count = args.workers
    if workers_count is None:
        workers_count = 1 if args.texture else 2

    if workers_count > 1:
        print(f"Starting {workers_count} parallel worker processes...")
        import multiprocessing
        ctx = multiprocessing.get_context('spawn')
        queue = ctx.Queue()
        for path in images:
            queue.put(path)

        processes = []
        for i in range(workers_count):
            p = ctx.Process(
                target=worker_main,
                args=(queue, args.out, args.steps, args.octree, args.texture, i)
            )
            p.start()
            processes.append(p)

        for p in processes:
            p.join()
        print(f"\nDone. GLBs in {os.path.abspath(args.out)}")
    else:
        # Fallback to single-process generation to avoid multiprocessing overhead and print output directly
        import torch
        from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

        print("loading shape model tencent/Hunyuan3D-2mini ...")
        shape = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            'tencent/Hunyuan3D-2mini', subfolder='hunyuan3d-dit-v2-mini', variant='fp16'
        )
        paint = None
        if args.texture:
            from hy3dgen.texgen import Hunyuan3DPaintPipeline
            paint = Hunyuan3DPaintPipeline.from_pretrained('tencent/Hunyuan3D-2')

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
                matte_export(mesh, out_path)
                print(f"  -> {out_path}  ({time.time() - t:.1f}s)")
            except Exception as exc:
                print(f"  FAILED {name}: {exc}")

        print(f"\nDone. GLBs in {os.path.abspath(args.out)}")


if __name__ == '__main__':
    main()
