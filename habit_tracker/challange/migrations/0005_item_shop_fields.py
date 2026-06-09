from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("challange", "0004_item_slug"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="is_shop_item",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="item",
            name="price_points",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="item",
            name="shop_sort",
            field=models.PositiveSmallIntegerField(default=100),
        ),
    ]
