"""h3d - HabitBud 3D production CLI (Hunyuan3D-2).

A small, fast command-line tool to turn 2D character images into app-ready
`.glb` models. Run from inside the Hunyuan3D-2 repo (so `hy3dgen` imports) and
on the GPU machine. The heavy mesh/texture helpers live in generate.py; this
file is just the CLI + a pipeline that loads the models ONCE.

Quick start
-----------
    # one image or a whole folder -> GLBs (balanced quality, textured)
    python h3d.py gen ./assets/t-poses
    python h3d.py gen fox.png -o ./out --quality high

    # keep models loaded and auto-build every new image dropped in a folder
    python h3d.py watch ./inbox -o ./out          # Ctrl-C to stop

    # inspect a result (faces / size / texture / material)
    python h3d.py info ./out/fox.glb

Commands
--------
  gen    INPUT [-o OUT]      build model(s) from an image file or a folder
  watch  FOLDER [-o OUT]     load once, then build each new image as it appears
  info   GLB...              print faces / file size / texture / metallic

Quality profiles  (-q / --quality)   set octree + steps + faces in one go
  fast       octree 256  steps 30  faces 20000   (~6 GB VRAM, quickest)
  balanced   octree 320  steps 50  faces 30000   (default, app-friendly)
  high       octree 384  steps 50  faces 60000   (most detail, bigger files)
Any of --octree/--steps/--faces override the profile. --faces 0 = no decimation.

Texture is ON by default; use --no-texture for a fast gray mesh (~6 GB VRAM).
"""
import argparse
import glob
import os
import sys
import time

# Model cache off the (full) C: drive. Set before importing torch/diffusers.
os.environ.setdefault('HF_HOME', 'D:\\hf_cache')
os.environ.setdefault('HF_HUB_CACHE', 'D:\\hf_cache\\hub')
os.environ.setdefault('HF_XET_CACHE', 'D:\\hf_cache\\xet')
os.environ.setdefault('PYTHONUTF8', '1')

# Reuse the battle-tested helpers (bg removal, decimation, matte export, loader).
import generate as G

IMG_EXTS = ('.png', '.jpg', '.jpeg', '.webp')

PROFILES = {
    'fast':     dict(octree=256, steps=30, faces=20000),
    'balanced': dict(octree=320, steps=50, faces=30000),
    'high':     dict(octree=384, steps=50, faces=60000),
}


# --------------------------------------------------------------------------- #
# Pipeline: load the shape (+paint) models once, then build many meshes.
# --------------------------------------------------------------------------- #
class Pipeline:
    def __init__(self, texture):
        self.texture = texture
        t = time.time()
        self.shape, self.paint = G.load_pipelines(texture)
        print(f"models ready in {time.time() - t:.0f}s "
              f"(texture {'on' if texture else 'off'})", flush=True)

    def build(self, img_path, out_dir, steps, octree, faces, tag=''):
        G.generate_one(self.shape, self.paint, img_path, out_dir,
                       steps, octree, faces, tag=tag)


def collect_images(path):
    """A single image file -> [it]; a folder -> all images inside (sorted)."""
    if os.path.isfile(path):
        return [path]
    imgs = []
    for ext in IMG_EXTS:
        imgs += glob.glob(os.path.join(path, '*' + ext))
        imgs += glob.glob(os.path.join(path, '*' + ext.upper()))
    return sorted(set(imgs))


def resolve_settings(args):
    """Profile defaults, then per-flag overrides."""
    p = PROFILES[args.quality]
    return (
        args.octree if args.octree is not None else p['octree'],
        args.steps  if args.steps  is not None else p['steps'],
        args.faces  if args.faces  is not None else p['faces'],
    )


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_gen(args):
    images = collect_images(args.input)
    if not images:
        print(f"no images in {args.input}")
        return 1
    octree, steps, faces = resolve_settings(args)
    os.makedirs(args.out, exist_ok=True)
    print(f"gen: {len(images)} image(s) | quality={args.quality} "
          f"octree={octree} steps={steps} faces={faces} "
          f"texture={'on' if not args.no_texture else 'off'} -> {args.out}",
          flush=True)
    pipe = Pipeline(texture=not args.no_texture)
    ok = 0
    for i, img in enumerate(images, 1):
        tag = f"[{i}/{len(images)}] "
        try:
            pipe.build(img, args.out, steps, octree, faces, tag=tag)
            ok += 1
        except Exception as exc:
            print(f"{tag}FAILED {os.path.basename(img)}: {exc}", flush=True)
    print(f"\ndone: {ok}/{len(images)} -> {os.path.abspath(args.out)}")
    return 0 if ok else 1


def cmd_watch(args):
    octree, steps, faces = resolve_settings(args)
    os.makedirs(args.out, exist_ok=True)
    print(f"watch: {args.input} -> {args.out} | quality={args.quality} "
          f"octree={octree} steps={steps} faces={faces} "
          f"texture={'on' if not args.no_texture else 'off'} "
          f"(poll {args.interval}s, Ctrl-C to stop)", flush=True)
    pipe = Pipeline(texture=not args.no_texture)
    seen = set()
    # Don't rebuild whatever is already there at startup.
    for img in collect_images(args.input):
        out = os.path.join(args.out, os.path.splitext(os.path.basename(img))[0].lower() + '.glb')
        if os.path.exists(out):
            seen.add(img)
    print("waiting for images... (drop files into the folder)", flush=True)
    try:
        while True:
            for img in collect_images(args.input):
                if img in seen:
                    continue
                # Wait until the file stops growing (finished copying).
                s1 = os.path.getsize(img)
                time.sleep(0.5)
                if os.path.getsize(img) != s1:
                    continue
                seen.add(img)
                try:
                    pipe.build(img, args.out, steps, octree, faces, tag='[watch] ')
                except Exception as exc:
                    print(f"[watch] FAILED {os.path.basename(img)}: {exc}", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nwatch stopped.")
    return 0


def cmd_info(args):
    import trimesh
    try:
        from pygltflib import GLTF2
    except Exception:
        GLTF2 = None
    for path in args.glb:
        if not os.path.exists(path):
            print(f"{path}: not found")
            continue
        size_mb = os.path.getsize(path) / 1e6
        try:
            m = trimesh.load(path, force='mesh')
            faces, verts = len(m.faces), len(m.vertices)
        except Exception as e:
            faces = verts = f"? ({e})"
        tex = metal = '?'
        if GLTF2 is not None:
            try:
                g = GLTF2().load(path)
                tex = len(g.textures)
                if g.materials:
                    metal = g.materials[0].pbrMetallicRoughness.metallicFactor
            except Exception:
                pass
        print(f"{os.path.basename(path)}: {size_mb:.2f} MB | faces={faces} "
              f"verts={verts} | textures={tex} | metallic={metal}")
    return 0


# --------------------------------------------------------------------------- #
def _add_common(sp):
    sp.add_argument('-o', '--out', default='./out', help='output folder (default ./out)')
    sp.add_argument('-q', '--quality', choices=list(PROFILES), default='balanced',
                    help='quality profile (default balanced)')
    sp.add_argument('--octree', type=int, default=None, help='override marching-cubes resolution')
    sp.add_argument('--steps', type=int, default=None, help='override diffusion steps')
    sp.add_argument('--faces', type=int, default=None, help='override face cap (0 = no decimation)')
    sp.add_argument('--no-texture', action='store_true', help='gray mesh only (faster, less VRAM)')


def main():
    ap = argparse.ArgumentParser(prog='h3d', description='HabitBud 3D production CLI (Hunyuan3D-2)')
    sub = ap.add_subparsers(dest='cmd', required=True)

    g = sub.add_parser('gen', help='build model(s) from an image file or folder')
    g.add_argument('input', help='image file or folder of images')
    _add_common(g)
    g.set_defaults(func=cmd_gen)

    w = sub.add_parser('watch', help='load once, build each new image dropped in a folder')
    w.add_argument('input', help='folder to watch')
    w.add_argument('--interval', type=float, default=2.0, help='poll seconds (default 2)')
    _add_common(w)
    w.set_defaults(func=cmd_watch)

    i = sub.add_parser('info', help='print faces / size / texture / metallic for GLB(s)')
    i.add_argument('glb', nargs='+', help='one or more .glb files')
    i.set_defaults(func=cmd_info)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == '__main__':
    main()
