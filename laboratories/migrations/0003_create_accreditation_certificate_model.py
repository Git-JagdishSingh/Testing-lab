from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('laboratories', '0002_add_accreditation_certificate'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccreditationCertificate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='accreditation_certificates/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])])),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('laboratory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to='laboratories.laboratory')),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
