"""extract_offset — save your Blender fix for ONE (avatar, item) into item_attach.json.

Why: you fix each item on each avatar ONCE. Hand and head items attach to
independent sockets, so every saved hand-fix composes with every saved head-fix
automatically — 10 hand fixes + 2 head fixes covers all 20 combinations.

How to use (inside Blender's Scripting tab):
  1. Open a combined GLB from attach_all (e.g. gen\\out\\fox__magic_wand.glb)
     or import avatar + item yourself.
  2. Move/rotate/scale the ITEM until it sits right.
  3. Select the item object, make sure AVATAR and ITEM names below are right,
     then Run Script. It writes avatar_overrides["fox"]["magic_wand"] into
     tools/rig/item_attach.json.
  4. Re-run attach_all.ps1 -Force (bakes) and/or `manage.py import_attach_tuning`
     (runtime) — the fix now applies to every combination with that item.

The offset is stored relative to the item's socket (its parent if parented,
else the nearest socket_* empty), in avatar units — the same space the app and
attach_socket.py use.
"""
import json
import math
import os

import bpy
from mathutils import Vector

# ---- EDIT THESE THREE LINES, THEN RUN ----------------------------------- #
AVATAR = 'fox'           # avatar base name (fox, cat, deer, panda, ...)
ITEM = 'magic_wand'      # item slug (matches item_attach.json / Item.slug)
CONFIG = r'C:\Users\ishak\habitbud-backend\tools\rig\item_attach.json'
# -------------------------------------------------------------------------- #


def find_socket(obj):
    if obj.parent and obj.parent.type == 'EMPTY':
        return obj.parent
    for o in bpy.data.objects:
        if o.type == 'EMPTY' and 'socket' in o.name.lower():
            return o
    raise RuntimeError('No socket Empty found — parent the item to the socket '
                       'or keep a socket_* Empty in the scene.')


def main():
    item = bpy.context.active_object
    if item is None or item.type != 'MESH':
        raise RuntimeError('Select the ITEM mesh first.')
    socket = find_socket(item)

    bpy.context.view_layer.update()
    sw = socket.matrix_world
    iw = item.matrix_world
    rel = sw.inverted() @ iw                 # item transform in socket space

    loc = [round(v, 4) for v in rel.to_translation()]
    rot = [round(math.degrees(a), 2) for a in rel.to_euler('XYZ')]
    scale = round(sum(rel.to_scale()) / 3.0, 4)   # uniform-ish

    with open(CONFIG, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    cfg.setdefault('avatar_overrides', {}).setdefault(AVATAR, {})[ITEM] = {
        'loc': loc, 'rot_deg': rot, 'scale': scale,
    }
    with open(CONFIG, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    print(f'[extract_offset] saved {AVATAR}/{ITEM}: loc={loc} rot={rot} scale={scale}')
    print(f'[extract_offset] -> {CONFIG}')


main()
