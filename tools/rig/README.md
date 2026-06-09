# Item → Hand attachment

Automatically drops a HabitBud item GLB into an avatar's hand and exports one
combined GLB. Two modes — **socket** (recommended) and **bone**.

> Only the **hand** is supported for now — head attachment distorts the mesh.

## How the app uses this (socket → app)
The app's 3D viewer (`components/Avatar3D.js`) attaches items **at runtime** by
reading the socket Empty's position straight from the avatar GLB — no per-combo
file needed. The baked combined GLBs are kept as a preview/fallback.

1. **Generate low-poly models** (already 20k faces — see `tools/hunyuan`):
   `h3d gen <imgs> -q fast` → avatars + items.
2. **Socket the avatars** in Blender (Empty named `socket_r` / `socket_head`),
   export to `gen\avatars_socketed`.
3. **(Optional) bake combos** for preview/fallback: `tools\rig\attach_all.ps1`.
4. **Import into the backend** (run from `habit_tracker\`):
   ```
   python manage.py import_avatar_models --dir D:\blenderprojects\gen\avatars_socketed \
       --thumbs-dir ..\habit_tracker\assets\animals_gemini_2d_v2 --replace
   python manage.py import_items   --dir D:\blenderprojects\gen\items
   python manage.py import_combos  --dir D:\blenderprojects\gen\out --clean
   ```
   `--replace` retires old high-poly avatars (`is_active=False`).
5. The frontend maps each item's **anchor → socket**: `hand→socket_r`,
   `head/face/neck→socket_head`, `back→socket_back` (see `ANCHOR_SOCKET` in
   `challange/serializers.py` and `ANCHOR_TO_SOCKET` in `Avatar3D.js`). If an
   avatar has no matching socket, it falls back to the old approximate anchor.

### "faces 0" in Blender's Decimate panel
Not a corruption — Decimate only counts faces when a **mesh** is selected. If you
have the **Empty/socket** (or armature) selected it shows 0. These models are
already decimated to 20k faces in `h3d` (`-q fast`); no Blender decimation needed.
Lighter still: `h3d gen -q fast --faces <fewer>`.

### Performance
The big win is already done: old high-poly avatars (some 25 MB+) → 20k-face /
2-7 MB. Runtime socket means the app downloads only the base avatar + small items
(no N×M combined files). GLBs are disk-cached (`useCachedGlb`). Further levers if
needed: lower `h3d --faces`, downscale item textures, or Draco — but Draco needs a
decoder configured in the RN GLTF loader, so test before enabling.

## Socket mode (recommended) ⭐

### The socket (what YOU do in Blender, once per avatar)
Add an **Empty** at the right hand:
- **Name it exactly `socket_r`** (this is the default the scripts look for).
  Any name containing `socket`/`soket` also works as a fallback.
- Parent it to the body, place it at the right hand.
- **Size the Empty** (its display size) — this is the reference for item scale.
- Export the avatar as `.glb`.

You only ever define the **right hand**. All hand items attach automatically.

### Sockets & items are fully configurable (`item_attach.json`)
```json
"sockets": {
  "socket_r":    ["magic_wand","dumbell","coffee_mug","water_bottle","book","balloons"],
  "socket_head": ["beanie","cap","crown","face_mask","pink_headphones","pink_sunglasses","round_glasses"]
}
```
Each key is a socket **Empty name**; its list is the items that attach there.
Add/remove items by editing the lists; add new sockets (e.g. `socket_l`) freely.
Per-item scale/offset lives in `socket_tuning` (`fit_ratio` = item size as a
fraction of the avatar; `loc`/`rot_deg` are socket-relative).

### Attach everything (batch) — the main workflow
Socketed avatars in one folder, item GLBs in another:
```powershell
tools\rig\attach_all.ps1                                  # ALL sockets, all their items
tools\rig\attach_all.ps1 -Sockets socket_r               # hand only
tools\rig\attach_all.ps1 -Sockets socket_head            # head only
tools\rig\attach_all.ps1 -Sockets socket_r,socket_head   # hand + head
tools\rig\attach_all.ps1 -Items magic_wand,coffee_mug    # only these items
tools\rig\attach_all.ps1 -Avatars fox,cat                # only these avatars
tools\rig\attach_all.ps1 -Force                          # overwrite (see below)
```
Output: `<avatar>__<item>.glb` in `-OutDir`. **Existing files are kept by
default** so manual fixes (saved under the same filename) survive a re-run —
pass `-Force` to regenerate. Dirs default to
`D:\blenderprojects\gen\{avatars_socketed,items,out}` (override with
`-AvatarsDir`/`-ItemsDir`/`-OutDir`).

### Attach one (quick test)
```powershell
tools\rig\attach.ps1 -Socket -Item magic_wand                       # default avatar
tools\rig\attach.ps1 -Socket -Item dumbell -Avatar D:\...\mycat.glb # your GLB
tools\rig\attach.ps1 -Socket -All                                   # all socket items, one avatar
```
Each item is auto-scaled to `socket_size * fit_ratio * scale`, parented to the
socket (inherits its position + rotation); stray meshes/empties are dropped.

## Bone mode (rigged skeletons)
For fully rigged avatars (FBX with an armature): binds the item to the hand bone
so it follows animation.
```powershell
tools\rig\attach.ps1 -Item magic_wand          # fox skeleton, right hand
tools\rig\attach.ps1 -Item coffee_mug -Hand L  # left hand
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
