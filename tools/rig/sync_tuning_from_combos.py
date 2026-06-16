"""Read the TRUE item->socket transform from the baked combined GLBs (which are
Blender's own correct Y-up export) and write it to item_attach.json as a raw
matrix in the app's frame. This sidesteps every Blender->glTF axis/euler
conversion guess: the app applies the matrix verbatim and reproduces the combo
exactly.

    python tools/rig/sync_tuning_from_combos.py --dir D:\\blenderprojects\\gen\\out

For each <avatar>__<item>.glb it finds the mesh node parented to a socket_* node,
computes rel = socketWorld^-1 @ itemWorld (raw glTF, Y-up), and stores
avatar_overrides[avatar][item] = { "mat": [16 floats, column-major] }.
"""
import argparse
import glob
import json
import os

import numpy as np
from pygltflib import GLTF2

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, 'item_attach.json')


def node_local(n):
    T = np.eye(4); R = np.eye(4); S = np.eye(4)
    if n.translation:
        T[:3, 3] = n.translation
    if n.scale:
        S[:3, :3] = np.diag(n.scale)
    if n.rotation:
        x, y, z, w = n.rotation
        R[:3, :3] = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    return T @ R @ S


def world_matrices(g):
    parent = {}
    for i, n in enumerate(g.nodes):
        for c in (n.children or []):
            parent[c] = i

    def world(i):
        M = node_local(g.nodes[i])
        while i in parent:
            i = parent[i]
            M = node_local(g.nodes[i]) @ M
        return M
    return world, parent


def rel_from_combo(path):
    g = GLTF2().load(path)
    world, parent = world_matrices(g)
    # item = mesh node whose parent is a socket_* node
    for i, n in enumerate(g.nodes):
        p = parent.get(i)
        if n.mesh is not None and p is not None and 'socket' in (g.nodes[p].name or '').lower():
            rel = np.linalg.inv(world(p)) @ world(i)
            return rel
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--avatars', default='', help='comma list to limit (e.g. pinkcat)')
    args = ap.parse_args()

    only = {a.strip() for a in args.avatars.split(',') if a.strip()}
    with open(CONFIG, encoding='utf-8') as f:
        cfg = json.load(f)
    cfg.setdefault('avatar_overrides', {})

    n = 0
    for path in sorted(glob.glob(os.path.join(args.dir, '*__*.glb'))):
        stem = os.path.splitext(os.path.basename(path))[0]
        avatar, item = stem.split('__', 1)
        avatar = ''.join(ch for ch in avatar.lower().replace('socketed', '') if ch.isalpha())
        if only and avatar not in only:
            continue
        rel = rel_from_combo(path)
        if rel is None:
            print(f'  skip {stem} (no socket-parented mesh)')
            continue
        # numpy row-major -> three.js Matrix4 column-major flat array
        mat = rel.T.flatten().round(6).tolist()
        cfg['avatar_overrides'].setdefault(avatar, {})[item] = {'mat': mat}
        n += 1
        print(f'  {avatar}/{item}: synced')

    with open(CONFIG, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f'Synced {n} overrides (raw matrix) -> {CONFIG}')


if __name__ == '__main__':
    main()
