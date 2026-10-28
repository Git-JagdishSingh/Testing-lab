from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('laboratories', '0003_create_accreditation_certificate_model'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='laboratory',
            name='profile_image',
        ),
    ]
