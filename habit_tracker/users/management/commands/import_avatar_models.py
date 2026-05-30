"""Import Hunyuan3D-generated GLB files into the AvatarModel catalog.

After running tools/hunyuan/generate.py (which writes GLBs to tools/hunyuan/out/),
run this to copy them into media/ and register them so they appear in the app's
Avatar Studio (3D mode):

    python manage.py import_avatar_models                 # default folder
    python manage.py import_avatar_models --dir path/to/glbs --scale 1.0

Emoji/scale are guessed from the filename when possible.
"""
import os
import shutil

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from users.models import AvatarModel

EMOJI = {
    'fox': '🦊', 'cat': '🐱', 'bear': '🐻', 'panda': '🐼', 'rabbit': '🐰',
    'frog': '🐸', 'koala': '🐨', 'deer': '🦌', 'chick': '🐤', 'hamster': '🐹',
}


class Command(BaseCommand):
    help = "Import GLB files into the AvatarModel catalog (for Avatar Studio 3D)."

    def add_arguments(self, parser):
        default_dir = os.path.join(settings.BASE_DIR, '..', 'tools', 'hunyuan', 'out')
        parser.add_argument('--dir', default=default_dir, help="Folder containing .glb files")
        parser.add_argument('--scale', type=float, default=1.0, help="Render scale hint")

    def handle(self, *args, **options):
        folder = os.path.abspath(options['dir'])
        if not os.path.isdir(folder):
            self.stdout.write(self.style.ERROR(f"Folder not found: {folder}"))
            return

        glbs = [f for f in os.listdir(folder) if f.lower().endswith('.glb')]
        if not glbs:
            self.stdout.write(self.style.WARNING(f"No .glb files in {folder}"))
            return

        created, updated = 0, 0
        for order, fname in enumerate(sorted(glbs)):
            name = os.path.splitext(fname)[0]
            slug = slugify(name)
            emoji = EMOJI.get(name.lower(), '')
            obj, was_created = AvatarModel.objects.get_or_create(
                slug=slug,
                defaults={'name': name.capitalize(), 'emoji': emoji,
                          'scale': options['scale'], 'sort_order': order, 'is_active': True},
            )
            with open(os.path.join(folder, fname), 'rb') as fh:
                obj.glb.save(fname, File(fh), save=True)
            created += was_created
            updated += not was_created
            try:
                self.stdout.write(f"  {'+' if was_created else '~'} {emoji} {name}")
            except Exception:
                self.stdout.write(f"  {'+' if was_created else '~'} {name}")

        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(glbs)} GLB(s): {created} new, {updated} updated."
        ))
