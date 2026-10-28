from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratories', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='laboratory',
            name='accreditation_certificate',
            field=models.FileField(upload_to='accreditation_certificates/', blank=True, null=True),
        ),
    ]
