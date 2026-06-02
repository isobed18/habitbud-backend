"""Convert GLB assets to Mixamo-friendly interchange formats.

Mixamo does not accept GLB. The fastest upload path is usually FBX. OBJ and DAE
are exported too for fallback testing.

Usage:
    D:/conda_envs/UniRig/python.exe tools/hunyuan/convert_for_mixamo.py input.glb out_dir
"""
from __future__ import annotations

import argparse
from pathlib import Path

import bpy


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def normalize_scene() -> None:
    for obj in bpy.context.scene.objects:
        obj.select_set(obj.type in {"MESH", "ARMATURE"})
    bpy.context.view_layer.objects.active = next(
        (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
        None,
    )
    # Apply mesh transforms so uploaded scale/orientation is less surprising.
    try:
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    except Exception:
        pass


def export_obj(path: Path) -> None:
    if hasattr(bpy.ops.wm, "obj_export"):
        bpy.ops.wm.obj_export(
            filepath=str(path),
            export_selected_objects=False,
            export_materials=True,
        )
    else:
        bpy.ops.export_scene.obj(
            filepath=str(path),
            use_selection=False,
            use_materials=True,
        )


def convert(input_glb: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = input_glb.stem

    reset_scene()
    bpy.ops.import_scene.gltf(filepath=str(input_glb))
    normalize_scene()

    fbx_path = out_dir / f"{stem}.fbx"
    obj_path = out_dir / f"{stem}.obj"
    dae_path = out_dir / f"{stem}.dae"

    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=False,
        path_mode="COPY",
        embed_textures=True,
        add_leaf_bones=False,
        bake_space_transform=False,
    )
    export_obj(obj_path)
    bpy.ops.wm.collada_export(
        filepath=str(dae_path),
        selected=False,
        apply_global_orientation=True,
    )

    print(f"FBX: {fbx_path}")
    print(f"OBJ: {obj_path}")
    print(f"DAE: {dae_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_glb")
    parser.add_argument("out_dir")
    args = parser.parse_args()
    convert(Path(args.input_glb).resolve(), Path(args.out_dir).resolve())


if __name__ == "__main__":
    main()
