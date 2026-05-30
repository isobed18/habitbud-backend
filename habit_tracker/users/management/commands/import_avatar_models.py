"""Import Hunyuan3D-generated GLB files into the AvatarModel catalog.

After running tools/hunyuan/generate.py (which writes GLBs to tools/hunyuan/out/),
run this to copy them into media/ and register them so they appear in the app's
Avatar Studio (3D mode):

    python manage.py import_avatar_models                 # default folder
    python manage.py import_avatar_models --dir path/to/glbs --scale 1.0

Emoji/scale are guessed from the filename when possible.
"""
import os
import re
import shutil

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from users.models import AvatarModel

# Keyed by the alpha-only base of the filename (digits/underscores/parens stripped).
EMOJI = {
    'fox': '🦊', 'cat': '🐱', 'pinkcat': '🐱', 'bear': '🐻', 'panda': '🐼',
    'rabbit': '🐰', 'frog': '🐸', 'koala': '🐨', 'deer': '🦌', 'chick': '🐤',
    'hamster': '🐹',
}
NAME_TR = {
    'fox': 'Tilki', 'cat': 'Kedi', 'pinkcat': 'Pembe Kedi', 'bear': 'Ayı',
    'panda': 'Panda', 'rabbit': 'Tavşan', 'frog': 'Kurbağa', 'koala': 'Koala',
    'deer': 'Geyik', 'chick': 'Civciv', 'hamster': 'Hamster',
}


def _base_key(name):
    """fox2 / bear_(2) / pinkcat2 -> 'fox' / 'bear' / 'pinkcat' (alpha only)."""
    return re.sub(r'[^a-z]', '', name.lower())


def _face_crop_bytes(path):
    """Return a square, face-close PNG (top of the subject) for use as a snapshot.
    Finds the subject via a corner flood-fill, then crops the top square (head)."""
    import io
    from PIL import Image, ImageDraw, ImageChops
    img = Image.open(path).convert('RGB')
    w, h = img.size
    flood = img.copy()
    for c in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        try:
            ImageDraw.floodfill(flood, c, (255, 0, 255), thresh=40)
        except Exception:
            pass
    sentinel = Image.new('RGB', (w, h), (255, 0, 255))
    mask = ImageChops.difference(flood, sentinel).convert('L').point(lambda p: 255 if p > 12 else 0)
    bbox = mask.getbbox() or (0, 0, w, h)
    l, t, r, b = bbox
    sw, sh = r - l, b - t
    side = max(40, min(sw, sh))          # top square ≈ head + shoulders
    cx = (l + r) // 2
    left = max(0, min(cx - side // 2, w - side))
    top = max(0, t - int(side * 0.04))   # tiny headroom
    crop = img.crop((left, top, left + side, top + side)).resize((256, 256), Image.LANCZOS)
    buf = io.BytesIO()
    crop.save(buf, 'PNG')
    buf.seek(0)
    return buf


class Command(BaseCommand):
    help = "Import GLB files into the AvatarModel catalog (for Avatar Studio 3D)."

    def add_arguments(self, parser):
        default_dir = os.path.join(settings.BASE_DIR, '..', 'tools', 'hunyuan', 'out')
        parser.add_argument('--dir', default=default_dir, help="Folder containing .glb files")
        parser.add_argument('--scale', type=float, default=1.0, help="Render scale hint")
        parser.add_argument('--thumbs-dir', default=None,
                            help="Folder of 2D source images to use as face snapshots "
                                 "(matched by base filename). E.g. the Gemini PNGs.")

    def handle(self, *args, **options):
        folder = os.path.abspath(options['dir'])
        if not os.path.isdir(folder):
            self.stdout.write(self.style.ERROR(f"Folder not found: {folder}"))
            return

        glbs = [f for f in os.listdir(folder) if f.lower().endswith('.glb')]
        if not glbs:
            self.stdout.write(self.style.WARNING(f"No .glb files in {folder}"))
            return

        # Build a {base_filename: path} map of 2D source images for thumbnails.
        thumbs = {}
        tdir = options.get('thumbs_dir')
        if tdir and os.path.isdir(tdir):
            for tf in os.listdir(tdir):
                tb, te = os.path.splitext(tf)
                if te.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
                    thumbs[tb.replace(' ', '_').lower()] = os.path.join(tdir, tf)

        created, updated = 0, 0
        for order, fname in enumerate(sorted(glbs)):
            name = os.path.splitext(fname)[0]
            slug = slugify(name)
            base = _base_key(name)
            emoji = EMOJI.get(base, '')
            display = NAME_TR.get(base, base.capitalize() or name)
            obj, was_created = AvatarModel.objects.get_or_create(
                slug=slug,
                defaults={'name': display, 'emoji': emoji,
                          'scale': options['scale'], 'sort_order': order, 'is_active': True},
            )
            # Refresh metadata on re-import too.
            obj.name = display
            obj.emoji = emoji
            obj.sort_order = order
            obj.is_active = True
            with open(os.path.join(folder, fname), 'rb') as fh:
                obj.glb.save(fname, File(fh), save=True)
            # Attach the matching 2D source image as a face snapshot/thumbnail.
            tpath = thumbs.get(name.replace(' ', '_').lower())
            if tpath:
                try:
                    buf = _face_crop_bytes(tpath)
                    obj.thumbnail.save(f"{slug}_face.png", File(buf), save=True)
                except Exception:
                    with open(tpath, 'rb') as th:  # fallback: full image
                        obj.thumbnail.save(os.path.basename(tpath), File(th), save=True)
            created += was_created
            updated += not was_created
            try:
                self.stdout.write(f"  {'+' if was_created else '~'} {emoji} {name}")
            except Exception:
                self.stdout.write(f"  {'+' if was_created else '~'} {name}")

        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(glbs)} GLB(s): {created} new, {updated} updated."
        ))
