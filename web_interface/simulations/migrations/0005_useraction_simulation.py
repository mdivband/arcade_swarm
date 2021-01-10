# Generated by Django 3.1.3 on 2021-01-03 13:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('simulations', '0004_simulationplayer'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraction',
            name='simulation',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, related_name='actions', to='simulations.simulation'),
            preserve_default=False,
        ),
    ]
