r"""attach_item - bind a HabitBud item GLB to a rigged avatar's hand bone (Blender).

Runs headless inside Blender:
    blender --background --python attach_item.py -- \
        --avatar D:\blenderprojects\foxrigged.fbx \
        --item   habit_tracker\media\models\items\magic_wand.glb \
        --out    D:\blenderprojects\out\fox_magic_wand.glb \
        [--hand R] [--config tools\rig\item_attach.json]

What it does
------------
1. Imports the rigged avatar (FBX or GLB). Blender 5.1's FBX importer crashes on
   embedded lights, so we monkeypatch the light reader.
2. Finds the *deforming* armature (the one driving the mesh via an Armature
   modifier) and its hand bone (`hand.R` / `hand.L`).
3. Imports the item, bakes its import transform, recenters its origin, and
   auto-scales it to a sensible size for the hand.
4. **Bone-parents** the item to the hand bone, so it follows the hand in every
   pose/animation. Position/rotation/scale come from a per-item config (with
   tweakable defaults) so placement is deterministic and easy to fine-tune.
5. Cleans the scene (drops camera/lights/stray rigs) and exports one GLB.

Only the HAND is supported for now (head attachment distorts the mesh).

Per-item config (item_attach.json)
-----------------------------------
    {
      "_default": {"fit": 0.35, "scale": 1.0, "loc": [0,0,0], "rot_deg": [0,0,0]},
      "magic_wand": {"rot_deg": [90,0,0], "loc": [0,0.02,0]}
    }
`fit` = target max-dimension in Blender units before `scale` multiplier.
`loc`/`rot_deg`/`scale` are RELATIVE TO THE BONE TAIL (Y axis = along the bone).
Tweak the numbers, re-run — no Blender clicking needed.
"""
import argparse
import json
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector


# --------------------------------------------------------------------------- #
def parse_args():
    argv = sys.argv
    argv = argv[argv.index('--') + 1:] if '--' in argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--avatar', required=True, help='rigged avatar FBX or GLB')
    ap.add_argument('--item', required=True, help='item GLB to attach')
    ap.add_argument('--out', required=True, help='output GLB path')
    ap.add_argument('--hand', default='R', choices=['R', 'L'], help='which hand (default R)')
    ap.add_argument('--config', default=None, help='per-item JSON config')
    # Direct overrides (win over config); useful for quick iteration.
    ap.add_argument('--fit', type=float, default=None)
    ap.add_argument('--scale', type=float, default=None)
    ap.add_argument('--loc', type=float, nargs=3, default=None)
    ap.add_argument('--rot', type=float, nargs=3, default=None, help='degrees XYZ')
    return ap.parse_args(argv)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Blender 5.1 FBX importer crashes on lights -> bypass the light reader.
    try:
        import io_scene_fbx.import_fbx as imp
        imp.blen_read_light = lambda *a, **k: bpy.data.lights.new(name='l', type='POINT')
    except Exception as e:
        print('  (light patch skipped:', e, ')')


def import_any(path):
    """Import a model, return the list of objects it added."""
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    if ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext in ('.glb', '.gltf'):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        raise SystemExit(f'unsupported format: {ext}')
    return [o for o in bpy.data.objects if o not in before]


def find_deform_armature(objs):
    """The armature that actually drives a mesh (via an Armature modifier)."""
    for o in objs:
        if o.type == 'MESH':
            for m in o.modifiers:
                if m.type == 'ARMATURE' and m.object:
                    return m.object
    # Fallback: prefer a Rigify-style metarig, else first armature.
    arms = [o for o in objs if o.type == 'ARMATURE']
    for a in arms:
        if any(b.name in ('hand.R', 'hand.L') for b in a.data.bones):
            return a
    return arms[0] if arms else None


def pick_hand_bone(arm, hand):
    names = [f'hand.{hand}', f'Hand.{hand}', f'hand_{hand}', 'hand', 'Hand']
    bone_names = {b.name for b in arm.data.bones}
    for n in names:
        if n in bone_names:
            return n
    # Loose match: any bone containing 'hand' and the side letter.
    for b in arm.data.bones:
        if 'hand' in b.name.lower() and b.name.lower().rstrip('.').endswith(hand.lower()):
            return b.name
    raise SystemExit(f'no hand bone found in {arm.name}; bones: {sorted(bone_names)}')


def consolidate_item(item_objs):
    """Join the item's meshes into one object with a baked, centered transform."""
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
    # Bake the importer's axis-conversion rotation into the mesh data, then
    # move the origin to the geometry center so offsets are predictable.
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    return item


def max_dimension(obj):
    return max(obj.dimensions) or 1.0


def cleanup(keep):
    keep_set = set(keep)
    for o in list(bpy.data.objects):
        if o not in keep_set and o.type in ('CAMERA', 'LIGHT', 'EMPTY', 'ARMATURE'):
            bpy.data.objects.remove(o, do_unlink=True)


def main():
    args = parse_args()
    cfg = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    item_key = os.path.splitext(os.path.basename(args.item))[0].lower()
    settings = dict(cfg.get('_default', {}))
    settings.update(cfg.get(item_key, {}))
    fit   = args.fit   if args.fit   is not None else settings.get('fit', 0.35)
    scale = args.scale if args.scale is not None else settings.get('scale', 1.0)
    loc   = args.loc   if args.loc   is not None else settings.get('loc', [0, 0, 0])
    rot   = args.rot   if args.rot   is not None else settings.get('rot_deg', [0, 0, 0])

    reset_scene()

    print(f'avatar: {args.avatar}')
    avatar_objs = import_any(args.avatar)
    arm = find_deform_armature(avatar_objs)
    if arm is None:
        raise SystemExit('no armature in avatar')
    bone = pick_hand_bone(arm, args.hand)
    mesh = next((o for o in avatar_objs if o.type == 'MESH'), None)
    print(f'  armature={arm.name}  bone={bone}  mesh={mesh.name if mesh else "?"}')

    print(f'item: {args.item}  (config key: {item_key})')
    item = consolidate_item(import_any(args.item))

    # Auto-fit the item to the hand, then apply the per-item multiplier.
    base = (fit / max_dimension(item)) * scale
    item.scale = (base, base, base)
    bpy.context.view_layer.update()

    # Bone-parent: item space origin = bone tail, Y axis along the bone.
    item.parent = arm
    item.parent_type = 'BONE'
    item.parent_bone = bone
    item.matrix_parent_inverse = Matrix()  # deterministic: no leftover offset
    item.location = Vector(loc)
    item.rotation_mode = 'XYZ'
    item.rotation_euler = Euler([__import__('math').radians(a) for a in rot], 'XYZ')
    print(f'  attached: fit={fit} scale={scale} loc={loc} rot_deg={rot} (final s={base:.4f})')

    cleanup(keep=[arm, mesh, item])

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=args.out, export_format='GLB',
        use_selection=True, export_yup=True,
        export_apply=False,            # keep the armature modifier live
        export_animations=True,
    )
    print(f'OK -> {args.out}  ({os.path.getsize(args.out)/1e6:.2f} MB)')


if __name__ == '__main__':
    main()
