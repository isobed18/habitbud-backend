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
    """fox2 / bear_(2) / fox_socketed -> 'fox' / 'bear' / 'fox' (alpha only, minus rig suffixes)."""
    s = re.sub(r'[^a-z]', '', name.lower())
    for suffix in ('socketed', 'tpose', 'rigged'):
        s = s.replace(suffix, '')
    return s


def _face_crop_bytes(path):
    """Simple face-close snapshot: a centered square from the top half of the
    image (the head sits in the upper-center of these centered plush renders)."""
    import io
    from PIL import Image
    img = Image.open(path).convert('RGB')
    w, h = img.size
    side = min(w, int(h * 0.55))     # ~top half height, capped to width
    left = (w - side) // 2           # horizontally centered
    top = int(h * 0.05)              # small headroom from the top
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
        parser.add_argument('--replace', action='store_true',
                            help="Deactivate (is_active=False) any AvatarModel whose slug "
                                 "was not in this import batch — retires old high-poly models.")

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
                    thumbs[_base_key(tb)] = os.path.join(tdir, tf)  # 'fox2'/'bear (2)' -> 'fox'/'bear'

        created, updated = 0, 0
        imported_slugs = []
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
            tpath = thumbs.get(base)
            if tpath:
                try:
                    buf = _face_crop_bytes(tpath)
                    obj.thumbnail.save(f"{slug}_face.png", File(buf), save=True)
                except Exception:
                    with open(tpath, 'rb') as th:  # fallback: full image
                        obj.thumbnail.save(os.path.basename(tpath), File(th), save=True)
            imported_slugs.append(slug)
            created += was_created
            updated += not was_created
            try:
                self.stdout.write(f"  {'+' if was_created else '~'} {emoji} {name}")
            except Exception:
                self.stdout.write(f"  {'+' if was_created else '~'} {name}")

        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(glbs)} GLB(s): {created} new, {updated} updated."
        ))

        if options.get('replace'):
            stale = AvatarModel.objects.exclude(slug__in=imported_slugs).filter(is_active=True)
            n = stale.update(is_active=False)
            self.stdout.write(self.style.WARNING(f"Deactivated {n} stale avatar(s) not in this batch."))
