# Item → Hand attachment (rigged avatars)

Automatically binds a HabitBud item GLB to a **rigged** avatar's hand bone so the
item follows the hand in every pose/animation, then exports one combined GLB.

> Only the **hand** is supported for now — head attachment distorts the mesh.

## Quick start (Windows)
```powershell
# one item (defaults: right hand, fox avatar, out in D:\blenderprojects\out)
tools\rig\attach.ps1 -Item magic_wand

# left hand
tools\rig\attach.ps1 -Item coffee_mug -Hand L

# every hand item listed in item_attach.json
tools\rig\attach.ps1 -All
```
`-Item` takes a name (looked up in `habit_tracker\media\models\items\<name>.glb`)
or a full path. Override `-Avatar`, `-Out`, `-OutDir`, `-Blender` as needed.

## How it works (`attach_item.py`, run inside Blender)
1. Imports the rigged avatar (FBX/GLB). *Blender 5.1's FBX importer crashes on
   embedded lights, so the light reader is monkeypatched.*
2. Finds the **deforming** armature (the one driving the mesh via an Armature
   modifier) and its hand bone (`hand.R` / `hand.L`).
3. Imports the item, bakes its transform, recenters its origin, **auto-scales**
   it to the hand.
4. **Bone-parents** the item to the hand bone (deterministic placement).
5. Drops camera/lights/stray rigs and exports a clean GLB.

## Tuning placement — `item_attach.json`
Per-item offsets relative to the **hand-bone tail** (Y axis runs along the bone):
```json
{
  "_default":   { "fit": 0.35, "scale": 1.0, "loc": [0,0,0], "rot_deg": [0,0,0] },
  "magic_wand": { "fit": 0.45, "rot_deg": [90,0,0], "loc": [0,0.05,0] }
}
```
- `fit` — target max dimension (Blender units) before `scale`.
- `scale` — extra multiplier.
- `loc` / `rot_deg` — position / rotation (degrees) relative to the bone.

Edit numbers, re-run — no Blender clicking. For fast trial-and-error you can also
pass `--fit/--scale/--loc/--rot` directly to `attach_item.py` (they override the JSON).

## Direct call (any avatar)
```powershell
& "D:\Blender Foundation\Blender 5.1\blender.exe" --background `
  --python tools\rig\attach_item.py -- `
  --avatar D:\blenderprojects\foxrigged.fbx `
  --item   habit_tracker\media\models\items\magic_wand.glb `
  --out    D:\blenderprojects\out\fox_magic_wand.glb `
  --hand R --config tools\rig\item_attach.json
```

## Notes
- The exported GLB contains the avatar mesh + armature + the item node parented to
  the hand bone. (Re-importing into Blender may show a phantom `Icosphere`
  placeholder — it is **not** in the file and won't appear in the app/three.js.)
- Hand items so far: `magic_wand`, `dumbell`, `coffee_mug`, `water_bottle`,
  `book`, `balloons`. Head items (cap, crown, glasses, …) are intentionally
  skipped for now.
