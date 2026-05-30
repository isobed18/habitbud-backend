"""Import accessory GLBs (Hunyuan output) into the Item catalog as 3D dress-up
items, with an attach anchor guessed from the filename. Optionally grant them
all to a user for testing.

    python manage.py import_items --dir C:\\Users\\ishak\\Hunyuan3D-2\\out_items
    python manage.py import_items --dir <...> --assign-to runner
"""
import os
import re

from django.core.files import File
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from challange.models import Item, UserItem

User = get_user_model()

# base filename -> (Turkish name, anchor, scale)
META = {
    'cap': ('Şapka', 'head', 0.45),
    'beanie': ('Bere', 'head', 0.45),
    'crown': ('Taç', 'head', 0.45),
    'pink_headphones': ('Kulaklık', 'head', 0.5),
    'round_glasses': ('Yuvarlak Gözlük', 'face', 0.42),
    'pink_sunglasses': ('Güneş Gözlüğü', 'face', 0.42),
    'face_mask': ('Maske', 'face', 0.42),
    'book': ('Kitap', 'hand', 0.45),
    'dumbell': ('Dambıl', 'hand', 0.45),
    'coffee_mug': ('Kahve', 'hand', 0.4),
    'water_bottle': ('Su Şişesi', 'hand', 0.45),
    'magic_wand': ('Sihirli Değnek', 'hand', 0.5),
    'balloons': ('Balon', 'hand', 0.6),
}


def _base(name):
    return re.sub(r'[^a-z_]', '', name.lower()).strip('_')


class Command(BaseCommand):
    help = "Import accessory GLBs as 3D dress-up Items."

    def add_arguments(self, parser):
        parser.add_argument('--dir', required=True)
        parser.add_argument('--assign-to', default=None, help="Username to grant all items to")

    def handle(self, *args, **opts):
        folder = os.path.abspath(opts['dir'])
        if not os.path.isdir(folder):
            self.stdout.write(self.style.ERROR(f"Folder not found: {folder}")); return

        glbs = [f for f in os.listdir(folder) if f.lower().endswith('.glb')]
        if not glbs:
            self.stdout.write(self.style.WARNING("No .glb files")); return

        created = []
        for fname in sorted(glbs):
            base = _base(os.path.splitext(fname)[0])
            name, anchor, scale = META.get(base, (base.replace('_', ' ').title(), 'hand', 0.45))
            obj, was_new = Item.objects.get_or_create(
                name=name,
                defaults={'description': f'{name} aksesuarı', 'rarity': 'rare',
                          'anchor': anchor, 'item_scale': scale},
            )
            obj.anchor = anchor
            obj.item_scale = scale
            with open(os.path.join(folder, fname), 'rb') as fh:
                obj.model_glb.save(fname, File(fh), save=True)
            created.append(obj)
            self.stdout.write(f"  {'+' if was_new else '~'} {name} [{anchor}]")

        self.stdout.write(self.style.SUCCESS(f"Imported {len(created)} items."))

        uname = opts.get('assign_to')
        if uname:
            u = User.objects.filter(username=uname).first()
            if not u:
                self.stdout.write(self.style.ERROR(f"User '{uname}' not found")); return
            n = 0
            for it in created:
                _, made = UserItem.objects.get_or_create(user=u, item=it)
                n += made
            self.stdout.write(self.style.SUCCESS(f"Granted {len(created)} items to {uname} ({n} new)."))
