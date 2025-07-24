from django.db import migrations, models
import uuid
import yandex_s3_storage
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_route_photo'),
    ]

    operations = [
        migrations.CreateModel(
            name='PointPhoto',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('image', models.ImageField(storage=yandex_s3_storage.ClientDocsStorage(), upload_to=core.models.get_photo_path)),
                ('point', models.ForeignKey(on_delete=models.CASCADE, related_name='photos', to='core.point')),
            ],
        ),
        migrations.CreateModel(
            name='PointAudio',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(storage=yandex_s3_storage.ClientDocsStorage(), upload_to=core.models.get_audio_path)),
                ('point', models.ForeignKey(on_delete=models.CASCADE, related_name='audios', to='core.point')),
            ],
        ),
        migrations.CreateModel(
            name='PointVideo',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(storage=yandex_s3_storage.ClientDocsStorage(), upload_to=core.models.get_video_path)),
                ('point', models.ForeignKey(on_delete=models.CASCADE, related_name='videos', to='core.point')),
            ],
        ),
    ]
