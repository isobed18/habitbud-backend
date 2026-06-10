r"""attach_socket - drop a HabitBud item GLB onto an avatar's hand SOCKET (Blender).

The artist adds an Empty (a "socket") at the hand in Blender, named with
'soket'/'socket' (e.g. `sagel_soket` = right-hand socket). This script imports
the item, scales it sensibly relative to the socket, parents it to the socket,
and exports one clean GLB. No skeleton needed — way simpler than bone parenting.

Run headless:
    blender --background --python attach_socket.py -- \
        --avatar D:\blenderprojects\sagelsoket_pinkcat.glb \
        --item   habit_tracker\media\models\items\magic_wand.glb \
        --out    D:\blenderprojects\out\pinkcat_magic_wand.glb \
        [--socket sagel_soket] [--config tools\rig\item_attach.json]

Scaling: item max-dimension = socket_display_size * fit_ratio * scale.
The socket's on-screen size (set by the artist) is the reference, so different
avatars/sockets auto-scale proportionally. Tune per item in the config.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector


def parse_args():
    argv = sys.argv
    argv = argv[argv.index('--') + 1:] if '--' in argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--avatar', required=True)
    ap.add_argument('--item', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--socket', default=None, help='socket empty name (auto-detect if omitted)')
    ap.add_argument('--config', default=None)
    ap.add_argument('--fit-ratio', type=float, default=None, help='item size / socket size')
    ap.add_argument('--scale', type=float, default=None)
    ap.add_argument('--loc', type=float, nargs=3, default=None)
    ap.add_argument('--rot', type=float, nargs=3, default=None, help='degrees XYZ')
    return ap.parse_args(argv)


def import_glb(path):
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    if ext == '.fbx':
        try:
            import io_scene_fbx.import_fbx as imp
            imp.blen_read_light = lambda *a, **k: bpy.data.lights.new(name='l', type='POINT')
        except Exception:
            pass
        bpy.ops.import_scene.fbx(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def find_socket(objs, name):
    if name:
        s = bpy.data.objects.get(name)
        if s and s.type == 'EMPTY':
            return s
        print(f'  (socket "{name}" not found, falling back to auto-detect)')
    for o in objs:
        if o.type == 'EMPTY' and ('soket' in o.name.lower() or 'socket' in o.name.lower()):
            return o
    raise SystemExit(f'no socket empty found (expected an Empty named "{name or "socket_r"}" '
                     'or one containing "socket"/"soket")')


def consolidate_item(item_objs):
    meshes = [o for o in item_objs if o.type == 'MESH']
    if not meshes:
        raise SystemExit('item has no mesh')
    bpy.ops.object.select_all(action='DESELECT')
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    item = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    return item


def ancestors(obj):
    out = []
    p = obj.parent
    while p:
        out.append(p)
        p = p.parent
    return out


def main():
    args = parse_args()
    cfg = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    key = os.path.splitext(os.path.basename(args.item))[0].lower()
    tuning = cfg.get('socket_tuning', {})
    s = dict(tuning.get('_default', {}))
    s.update(tuning.get(key, {}))
    # Per-avatar fix (from extract_offset.py) wins over the generic item tuning.
    import re as _re
    avatar_base = _re.sub(r'[^a-z]', '', os.path.splitext(os.path.basename(args.avatar))[0].lower().replace('socketed', ''))
    s.update(cfg.get('avatar_overrides', {}).get(avatar_base, {}).get(key, {}))
    fit_ratio = args.fit_ratio if args.fit_ratio is not None else s.get('fit_ratio', 1.6)
    scale     = args.scale     if args.scale     is not None else s.get('scale', 1.0)
    loc       = args.loc       if args.loc       is not None else s.get('loc', [0, 0, 0])
    rot       = args.rot       if args.rot       is not None else s.get('rot_deg', [0, 0, 0])

    bpy.ops.wm.read_factory_settings(use_empty=True)

    print(f'avatar: {args.avatar}')
    avatar_objs = import_glb(args.avatar)
    socket = find_socket(avatar_objs, args.socket)
    avatar_mesh = socket.parent
    while avatar_mesh and avatar_mesh.type != 'MESH':
        avatar_mesh = avatar_mesh.parent
    # Scale reference = the avatar's size, NOT the socket's display size.
    # glTF does not preserve an Empty's display size across export/import (it
    # comes back ~0.001), so we size the item as a fraction of the avatar.
    avatar_dim = max(avatar_mesh.dimensions) if avatar_mesh else 2.0
    print(f'  socket={socket.name}  parent_mesh={avatar_mesh.name if avatar_mesh else "?"}  avatar_dim={avatar_dim:.3f}')

    print(f'item: {args.item}  (config key: {key})')
    item = consolidate_item(import_glb(args.item))

    target = avatar_dim * fit_ratio * scale
    base = target / (max(item.dimensions) or 1.0)
    item.scale = (base, base, base)
    bpy.context.view_layer.update()

    # Parent to the socket: item origin lands on the socket origin, inheriting
    # the socket's world position + orientation. Offsets are socket-relative.
    item.parent = socket
    item.parent_type = 'OBJECT'
    item.matrix_parent_inverse = Matrix()
    item.location = Vector(loc)
    item.rotation_mode = 'XYZ'
    item.rotation_euler = Euler([math.radians(a) for a in rot], 'XYZ')
    print(f'  placed: fit_ratio={fit_ratio} scale={scale} -> max_dim={target:.3f} '
          f'(s={base:.4f}) loc={loc} rot_deg={rot}')

    # Keep only the socket's avatar hierarchy + item; drop stray meshes/empties.
    keep = {socket, item}
    if avatar_mesh:
        keep.add(avatar_mesh)
        keep.update(ancestors(avatar_mesh))
        keep.update(ancestors(socket))
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=args.out, export_format='GLB',
                              use_selection=True, export_yup=True)
    print(f'OK -> {args.out}  ({os.path.getsize(args.out)/1e6:.2f} MB)')


if __name__ == '__main__':
    main()
