"""Shrink textured GLBs for fast mobile loading: downscale the base-color
texture to <=512px and force matte material. Re-exports into an output folder.

    python shrink_glb.py <in_dir> <out_dir> [max_px]
"""
import os
import sys
import glob
import trimesh
from PIL import Image

MAX_PX = int(sys.argv[3]) if len(sys.argv) > 3 else 512


def shrink(path, out_path):
    mesh = trimesh.load(path, force='mesh', process=False)
    try:
        mat = mesh.visual.material
        if hasattr(mat, 'metallicFactor'):
            mat.metallicFactor = 0.0
        if hasattr(mat, 'roughnessFactor'):
            mat.roughnessFactor = 0.9
        tex = getattr(mat, 'baseColorTexture', None)
        if tex is not None and hasattr(tex, 'size') and max(tex.size) > MAX_PX:
            mat.baseColorTexture = tex.convert('RGB').resize((MAX_PX, MAX_PX), Image.LANCZOS)
    except Exception as e:
        print('  material warn:', e)
    try:
        _ = mesh.vertex_normals
    except Exception:
        pass
    mesh.export(out_path)


def main():
    in_dir = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(in_dir, '*.glb'))):
        name = os.path.basename(p)
        out = os.path.join(out_dir, name)
        try:
            before = os.path.getsize(p) / 1e6
            shrink(p, out)
            after = os.path.getsize(out) / 1e6
            print(f"  {name}: {before:.1f}MB -> {after:.1f}MB")
        except Exception as e:
            print(f"  FAILED {name}: {e}")


if __name__ == '__main__':
    main()
