# HabitBud — 3D Model Creation (Hunyuan3D-2)

This is the team guide for turning a 2D character image into a 3D `.glb` model
for the app (avatars, dress-up items). It is **offline tooling** — it does not
run in the backend server; you run it on the GPU machine and drop the resulting
GLBs into the app.

> TL;DR
> ```powershell
> # 1) put a clean, front-facing PNG in habit_tracker/assets/t-poses/
> # 2) run the wrapper (textured, ~30k faces):
> powershell -ExecutionPolicy Bypass -File tools\hunyuan\make_model.ps1 -Input habit_tracker\assets\t-poses -Texture -Faces 30000
> # 3) GLBs appear in D:\Hunyuan3D-2\out_tpose\
> ```

---

## 1. What it does

`generate.py` takes each image in a folder and produces a textured 3D mesh:

1. **Background removal** — a PIL corner flood-fill turns the plain background
   transparent (works for the Gemini plush renders; no rembg/onnxruntime).
2. **Shape generation** — Hunyuan3D-2mini (image → 3D mesh).
3. **Clean-up** — remove floating bits + degenerate faces, then **decimate** to a
   target triangle count (this is the size fix — see §4).
4. **Texture** (optional) — Hunyuan3D-2 paint pipeline bakes a color texture.
5. **Export** — matte material (metalness 0) + normals + GLB.

**Input tips:** one centered character, plain background, front-facing. For
rigging, use a **T-pose** (arms/legs spread) so the skeleton fits cleanly.

---

## 2. Environment (already set up on this machine)

| Thing | Location |
|---|---|
| Hunyuan3D-2 repo | `D:\Hunyuan3D-2` (symlinked into `tools/rig/Hunyuan3D-2`) |
| Python | conda **base** → `C:\Users\ishak\anaconda3\python.exe` (torch + CUDA) |
| Model cache | `D:\hf_cache` (set via `HF_HOME`; keep off the full C: drive) |
| Texture C++ ext | `custom_rasterizer`, `mesh_processor` (editable installs in base) |

**Fresh-machine setup** (only if recreating):
```bash
conda activate base                       # needs CUDA-enabled torch
pip install diffusers transformers accelerate trimesh pymeshlab pygltflib \
            scikit-image omegaconf einops opencv-python
# texture extensions (need MSVC + CUDA toolkit):
cd D:\Hunyuan3D-2\hy3dgen\texgen\custom_rasterizer       && pip install -e .
cd D:\Hunyuan3D-2\hy3dgen\texgen\differentiable_renderer && pip install -e .
```

> ⚠️ If you ever **move** the repo, the editable installs above break (their
> recorded path is stale → `ModuleNotFoundError: custom_rasterizer`). Fix the
> path inside `…\site-packages\__editable__.custom_rasterizer-*.pth` and
> `__editable___mesh_processor_*_finder.py`, or just re-run `pip install -e .`.

---

## 3. How to run

**Wrapper (recommended):**
```powershell
powershell -ExecutionPolicy Bypass -File tools\hunyuan\make_model.ps1 `
  -Input habit_tracker\assets\t-poses -Texture -Faces 30000 -Octree 320
```

**Or call generate.py directly** (from inside `D:\Hunyuan3D-2`):
```powershell
& "C:\Users\ishak\anaconda3\python.exe" generate.py `
  --input "<folder of images>" --out "D:\Hunyuan3D-2\out_tpose" `
  --texture --faces 30000 --octree 320 --steps 50
```

It processes every image in the folder and writes `<name>.glb`.

---

## 4. Options (the "too many faces / too big" fix)

| Flag | Default | Meaning |
|---|---|---|
| `--faces N` | `40000` | **Cap triangle count** via quadric decimation. This is what keeps GLBs small. `0` = no reduction (raw, can be 500k+ faces / 25 MB+). Good values: 15k–40k. |
| `--octree N` | `256` | Marching-cubes resolution. Higher = more surface detail **and** more faces (256 fast · 320 detailed · 384 max). |
| `--steps N` | `30` | Diffusion steps; more = crisper shape, slower. |
| `--texture` | off | Bake a color texture (else plain gray mesh, ~6 GB VRAM vs ~16 GB). |

**Size cheat-sheet** (fox example): raw octree 320 ≈ **570k faces / 25 MB**;
with `--faces 30000` ≈ **30k faces / ~2–4 MB** — same look, app-friendly.
The texture is also downscaled to 1024px on export.

---

## 5. What else Hunyuan3D-2 can do (beyond face count)

The repo ships several pipelines (see `D:\Hunyuan3D-2\examples\`):

- **Image → 3D** — what we use (`Hunyuan3D-2mini`, 0.6B; or `Hunyuan3D-2`, 1.1B for higher quality).
- **Multiview → 3D** (`Hunyuan3D-2mv`) — feed **front + back + side** images for
  much better geometry (great for asymmetric characters / accessories).
- **Text → 3D** — `text2image` (Hunyuan-DiT) makes an image from a prompt, then
  image→3D. Lets us generate items from text without drawing them.
- **Texture-only** — run just the paint pipeline to (re)texture an existing mesh
  (e.g. after manual edits/rigging in Blender).
- **FlashVDM fast variants** (`examples/fast_*`, `mini-turbo`) — faster shape gen.
- **Post-processors** — `FaceReducer` (decimate), `FloaterRemover`,
  `DegenerateFaceRemover`, `MeshSimplifier` (we apply the first three).
- **Shape knobs** — `guidance_scale`, `num_chunks`, `mc_level`, `mc_algo`
  (`mc` = scikit-image marching cubes, default; `dmc` = differentiable, needs `diso`).

Ideas this unlocks for us: text-prompted dress-up items, multiview hero avatars,
re-texturing after rigging, batch item packs.

---

## 6. After generation: rigging & app import

- **Rig (T-pose models):** open the GLB in **Blender**, or use **RigAnything**
  (`D:\RigAnything`, env `D:\conda_envs\UniRig`) which auto-rigs + simplifies:
  `sh scripts/inference.sh <mesh.glb> 1 8192`.
- **Avatars → app:** `python manage.py import_avatar_models --dir <glb folder> --thumbs-dir <2d source>`
- **Items → app:** `python manage.py import_items --dir <glb folder> --thumbs-dir <2d source> --assign-to <user>`

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: custom_rasterizer` | Editable path stale after moving repo — fix the `__editable__*` files in base `site-packages` (§2 warning). |
| `DLL load failed … custom_rasterizer_kernel` | `import torch` first (generate.py already does). |
| `not enough space on disk` | Model cache must be on D: — `set HF_HOME=D:\hf_cache`. |
| Model renders dark | metalness=1 from Hunyuan; `matte_export` sets it to 0 (app also forces matte). |
| Can't rig (limbs merged) | Use a **T-pose** input image. |
