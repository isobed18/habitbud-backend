# Hunyuan3D → HabitBud avatar pipeline

Turn the 2D plush-animal images (`habit_tracker/assets/animals_gemini_2d/`) into
textured 3D GLB characters with Hunyuan3D-2, then import them into the app's
Avatar Studio (3D mode).

**Why image→3D:** Hunyuan3D-2's strongest path is a single clean image of one
centered subject on a plain background — exactly what the Gemini images are.
`generate.py` runs background removal (which also drops the corner watermark),
tight-crops to the subject, then generates shape + texture.

**VRAM:** shape ≈ 6 GB, shape+texture ≈ 16 GB → an RTX 3090 (24 GB) is plenty.
Use the `2mini` model for faster iteration.

---

## 1. Set up Hunyuan3D-2 (on the 3090 box)

```bash
git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2
cd Hunyuan3D-2

# (recommended) fresh env, CUDA-enabled torch matching your driver
conda create -n hy3d python=3.10 -y && conda activate hy3d
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
pip install -e .

# texture pipeline native bits (needed only if you want textures):
cd hy3dgen/texgen/custom_rasterizer && pip install -e . && cd ../../..
cd hy3dgen/texgen/differentiable_renderer && pip install -e . && cd ../../..

# preprocessing helpers
pip install rembg pillow trimesh
```

Models download automatically from Hugging Face on first run
(`tencent/Hunyuan3D-2` or `tencent/Hunyuan3D-2mini`). Accept the model card terms
on HF and `huggingface-cli login` if prompted.

## 2. Generate the GLBs

Copy `generate.py` (next to this README) into the cloned `Hunyuan3D-2/` folder so
it can import `hy3dgen`, then:

```bash
# fast, no texture (6 GB):
python generate.py --input /path/to/habitbud-backend/habit_tracker/assets/animals_gemini_2d --out ./out --mini --no-texture

# full quality with texture (16 GB):
python generate.py --input /path/to/.../animals_gemini_2d --out ./out
```

Output: `./out/fox.glb`, `./out/cat.glb`, … one per input image.

## 3. Import into HabitBud

```bash
cd /path/to/habitbud-backend/habit_tracker
python manage.py import_avatar_models --dir /path/to/Hunyuan3D-2/out --scale 1.0
```

This copies the GLBs into `media/models/avatars/` and registers them as
`AvatarModel` rows. They immediately appear in the app: **Profil → avatar → 3B**.
(`--scale` is a render-size hint for the RN viewer; tweak per model if needed.)

## Notes / tuning

- If a character imports too big/small in the app, set its `scale` in Django
  admin (Users → Avatar models) — no re-generation needed.
- `--steps` controls quality vs speed (default 30; 50 = crisper, slower).
- Licensing: Tencent Hunyuan 3D 2.0 license — commercial OK under 1M MAU, but the
  license does **not** apply in EU/UK/South Korea. Generate & use within the
  permitted territory.
