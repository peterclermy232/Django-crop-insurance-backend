import uuid

from django.db import migrations, models

MODELS = [
    'claim', 'crop', 'cropvariety', 'farm', 'farmer', 'inspection', 'insuranceproduct', 'invoice',
    'lossassessor', 'organization', 'productcategory', 'quotation', 'roletype', 'season', 'subsidy', 'user',
]


def fill_public_ids(apps, schema_editor):
    # A plain AddField would give every existing row the same default, so each row gets its own
    for name in MODELS:
        Model = apps.get_model('insurance', name)
        rows = list(Model.objects.filter(public_id__isnull=True).only('pk'))
        for row in rows:
            row.public_id = uuid.uuid4()
        Model.objects.bulk_update(rows, ['public_id'], batch_size=1000)


class Migration(migrations.Migration):

    dependencies = [
        ('insurance', '0010_administrative_units'),
    ]

    operations = (
        [migrations.AddField(model_name=name, name='public_id', field=models.UUIDField(null=True, editable=False))
         for name in MODELS]
        + [migrations.RunPython(fill_public_ids, migrations.RunPython.noop)]
        + [migrations.AlterField(model_name=name, name='public_id',
                                 field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False))
           for name in MODELS]
    )
