"""Import pre-baked combined avatar+item GLBs (Blender attach_all.ps1 output)
into media/models/combos/, where they serve as preview/fallback for the 3D
viewer (the primary path is runtime socket attachment).

Files are named <avatarbase>__<itemslug>.glb (e.g. fox__magic_wand.glb) and are
served as-is; the /users/api/combos/ endpoint lists them keyed by that stem.

    python manage.py import_combos --dir D:\\blenderprojects\\gen\\out
"""
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Copy combined avatar+item GLBs into media/models/combos/."

    def add_arguments(self, parser):
        parser.add_argument('--dir', required=True, help="Folder with <avatar>__<item>.glb files")
        parser.add_argument('--clean', action='store_true', help="Remove existing combos first")

    def handle(self, *args, **opts):
        src = os.path.abspath(opts['dir'])
        if not os.path.isdir(src):
            self.stdout.write(self.style.ERROR(f"Folder not found: {src}")); return

        dst = os.path.join(settings.MEDIA_ROOT, 'models', 'combos')
        os.makedirs(dst, exist_ok=True)
        if opts.get('clean'):
            for f in os.listdir(dst):
                if f.lower().endswith('.glb'):
                    os.remove(os.path.join(dst, f))

        glbs = [f for f in os.listdir(src) if f.lower().endswith('.glb') and '__' in f]
        if not glbs:
            self.stdout.write(self.style.WARNING("No <avatar>__<item>.glb files found.")); return

        for f in sorted(glbs):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f.lower()))
        self.stdout.write(self.style.SUCCESS(f"Copied {len(glbs)} combo GLB(s) -> {dst}"))
