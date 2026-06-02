"""Inspect GLB files for rigging and animation data.

Usage:
    python tools/hunyuan/inspect_glb_rig.py D:/RigAnything/outputs
    python tools/hunyuan/inspect_glb_rig.py D:/RigAnything/avatars_final --recursive

This intentionally has no third-party dependencies. It only reads the GLB JSON
chunk and reports whether the file contains glTF skins, joints, vertex weights,
and animation clips.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
from pathlib import Path


GLB_MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A


def read_glb_json(path: Path) -> dict:
    with path.open("rb") as fh:
        header = fh.read(12)
        if len(header) != 12:
            raise ValueError("file too small")
        magic, _version, length = struct.unpack("<III", header)
        if magic != GLB_MAGIC:
            raise ValueError("not a GLB file")

        offset = 12
        while offset < length:
            chunk_header = fh.read(8)
            if len(chunk_header) != 8:
                break
            chunk_length, chunk_type = struct.unpack("<II", chunk_header)
            chunk_data = fh.read(chunk_length)
            offset += 8 + chunk_length
            if chunk_type == JSON_CHUNK:
                return json.loads(chunk_data.decode("utf-8").rstrip("\x00 "))

    raise ValueError("missing JSON chunk")


def summarize(path: Path) -> dict:
    gltf = read_glb_json(path)
    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])
    skins = gltf.get("skins", [])
    animations = gltf.get("animations", [])
    primitives = [p for mesh in meshes for p in mesh.get("primitives", [])]
    has_weights = any(
        "JOINTS_0" in p.get("attributes", {}) or "WEIGHTS_0" in p.get("attributes", {})
        for p in primitives
    )
    skinned_nodes = [node for node in nodes if "skin" in node]
    joint_count = sum(len(skin.get("joints", [])) for skin in skins)

    return {
        "file": str(path),
        "size_mb": path.stat().st_size / 1_000_000,
        "nodes": len(nodes),
        "meshes": len(meshes),
        "skins": len(skins),
        "joints": joint_count,
        "skinned_nodes": len(skinned_nodes),
        "has_vertex_weights": has_weights,
        "animations": len(animations),
    }


def iter_glbs(root: Path, recursive: bool) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix.lower() == ".glb" else []
    pattern = "**/*.glb" if recursive else "*.glb"
    return sorted(root.glob(pattern))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="GLB file or folder containing GLBs")
    parser.add_argument("--recursive", action="store_true", help="Scan subfolders too")
    args = parser.parse_args()

    paths = iter_glbs(Path(args.path), args.recursive)
    if not paths:
        print("No .glb files found.")
        return

    for path in paths:
        try:
            row = summarize(path)
        except Exception as exc:
            print(f"ERR  {path} ({exc})")
            continue

        rig = "RIGGED" if row["skins"] and row["has_vertex_weights"] else "static"
        anim = f"{row['animations']} anim" if row["animations"] else "no anim"
        print(
            f"{rig:6} | {anim:7} | joints={row['joints']:3} | "
            f"skins={row['skins']} | {row['size_mb']:5.1f} MB | {row['file']}"
        )


if __name__ == "__main__":
    main()
