from rest_framework import serializers
from core.models import User, Quest, PromoCode, UserQuestProgress, Point, RoutePoint, Route, PointPhoto, PointAudio, PointVideo


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'telegram_id', 'name', 'phone_number', 'is_verified', 'created_at']


class QuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quest
        fields = ['id', 'name', 'description', 'location', 'created_at', 'is_active']


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ['id', 'code', 'quest', 'is_used', 'created_at']


class UserQuestProgressSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    quest = QuestSerializer(read_only=True)
    promo_code = PromoCodeSerializer(read_only=True)

    class Meta:
        model = UserQuestProgress
        fields = [
            'id', 'user', 'quest', 'photo', 'status',
            'promo_code', 'completed_at', 'admin_comment'
        ]


class PointPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointPhoto
        fields = ['id', 'image']

class PointAudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointAudio
        fields = ['id', 'file']

class PointVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointVideo
        fields = ['id', 'file']

class PointSerializer(serializers.ModelSerializer):
    photos = PointPhotoSerializer(many=True, read_only=True)
    audios = PointAudioSerializer(many=True, read_only=True)
    videos = PointVideoSerializer(many=True, read_only=True)
    class Meta:
        model = Point
        fields = (
            'id', 'name', 'description',
            'latitude', 'longitude',
            'text_content', 'photo',
            'audio_file', 'video_file',
            'photos', 'audios', 'videos'
        )

class RoutePointSerializer(serializers.ModelSerializer):
    point = PointSerializer()
    class Meta:
        model = RoutePoint
        fields = ('order', 'point')

class RouteSerializer(serializers.ModelSerializer):
    points = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ('id', 'name', 'description', 'points', 'created_at')

    def get_points(self, obj):
        # Берём все связанные точки в нужном порядке
        rps = RoutePoint.objects.filter(route=obj).order_by('order')
        return RoutePointSerializer(rps, many=True).data