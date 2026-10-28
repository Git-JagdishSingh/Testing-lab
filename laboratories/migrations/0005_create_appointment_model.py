from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('laboratories', '0004_remove_laboratory_profile_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=150)),
                ('contact_number', models.CharField(max_length=30)),
                ('email_address', models.EmailField(max_length=254)),
                ('appointment_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('laboratory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appointments', to='laboratories.laboratory')),
            ],
            options={
                'ordering': ['-appointment_date', '-created_at'],
            },
        ),
    ]
