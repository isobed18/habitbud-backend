"""Generate textured 3D GLB characters from the 2D plush-animal images.

Run this from inside a cloned Hunyuan3D-2 repo (so `hy3dgen` is importable).
See README.md for setup. Example:

    python generate.py --input /path/to/animals_gemini_2d --out ./out --mini --no-texture

For each <name>.png it writes ./out/<name>.glb.

Pipeline per image:
  1. background removal (rembg) — also drops the corner watermark
  2. tight crop to the subject + square pad (Hunyuan likes a centered subject)
  3. shape generation (Hunyuan3D DiT)
  4. optional texture synthesis (Hunyuan3D Paint)
"""
import argparse
import os
import glob

from PIL import Image


def preprocess(image_path, rembg):
    """Isolate subject, crop to alpha bbox, pad to a centered square (RGBA)."""
    img = Image.open(image_path).convert("RGBA")
    # Remove background (drops the plain bg + bottom-right watermark).
    img = rembg(img)

    # Crop to the non-transparent bounding box.
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Pad to a square with transparent margin (~8%).
    w, h = img.size
    side = int(max(w, h) * 1.16)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2), img)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help="Folder of input PNG/JPG images")
    ap.add_argument('--out', default='./out', help="Output folder for GLBs")
    ap.add_argument('--mini', action='store_true', help="Use the faster 2mini model")
    ap.add_argument('--no-texture', action='store_true', help="Shape only (~6 GB VRAM)")
    ap.add_argument('--steps', type=int, default=30, help="Diffusion steps (quality/speed)")
    ap.add_argument('--save-prepared', action='store_true', help="Also save preprocessed PNGs")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    from hy3dgen.rembg import BackgroundRemover
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

    rembg = BackgroundRemover()

    shape_repo = 'tencent/Hunyuan3D-2mini' if args.mini else 'tencent/Hunyuan3D-2'
    print(f"Loading shape model: {shape_repo}")
    shape_pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(shape_repo)

    paint_pipe = None
    if not args.no_texture:
        from hy3dgen.texgen import Hunyuan3DPaintPipeline
        print("Loading texture model: tencent/Hunyuan3D-2")
        paint_pipe = Hunyuan3DPaintPipeline.from_pretrained('tencent/Hunyuan3D-2')

    images = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.webp'):
        images.extend(glob.glob(os.path.join(args.input, ext)))
    images.sort()
    if not images:
        print(f"No images found in {args.input}")
        return

    for path in images:
        name = os.path.splitext(os.path.basename(path))[0].replace(' ', '_')
        print(f"\n=== {name} ===")
        try:
            img = preprocess(path, rembg)
            if args.save_prepared:
                img.save(os.path.join(args.out, f"{name}_prepared.png"))

            mesh = shape_pipe(image=img, num_inference_steps=args.steps)[0]
            if paint_pipe is not None:
                print("  texturing...")
                mesh = paint_pipe(mesh, image=img)

            out_path = os.path.join(args.out, f"{name}.glb")
            mesh.export(out_path)
            print(f"  -> {out_path}")
        except Exception as exc:
            print(f"  FAILED {name}: {exc}")

    print(f"\nDone. GLBs in {args.out}")
    print("Next: python manage.py import_avatar_models --dir", os.path.abspath(args.out))


if __name__ == '__main__':
    main()
