"""Publish tools/rig/item_attach.json to media so the app can fetch it.

The app composes avatar + items at runtime using sockets; this JSON carries the
per-item and per-(avatar,item) placement fixes (made once in Blender via
extract_offset.py). Re-run after every fix:

    python manage.py import_attach_tuning
    python manage.py import_attach_tuning --file path\\to\\item_attach.json
"""
import json
import os
import shutil

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Copy the rig attachment tuning JSON into media/models/."

    def add_arguments(self, parser):
        default = os.path.join(settings.BASE_DIR, '..', 'tools', 'rig', 'item_attach.json')
        parser.add_argument('--file', default=default)

    def handle(self, *args, **opts):
        src = os.path.abspath(opts['file'])
        if not os.path.isfile(src):
            self.stdout.write(self.style.ERROR(f'Not found: {src}')); return
        with open(src, encoding='utf-8') as f:
            cfg = json.load(f)  # validate before publishing

        dst_dir = os.path.join(settings.MEDIA_ROOT, 'models')
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dst_dir, 'attach_tuning.json'))
        cache.delete('attach_tuning')
        n_over = sum(len(v) for k, v in cfg.get('avatar_overrides', {}).items() if not k.startswith('_'))
        self.stdout.write(self.style.SUCCESS(
            f'Published attach tuning ({len(cfg.get("socket_tuning", {}))-1} items, '
            f'{n_over} avatar overrides) -> media/models/attach_tuning.json'))
