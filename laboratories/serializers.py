from rest_framework import serializers
from .models import AccreditationCertificate, Category, Laboratory, Review, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'email', 'role']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'category_name', 'slug', 'description']


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'rating', 'review_text', 'created_at']


class AccreditationCertificateSerializer(serializers.ModelSerializer):
    image_url = serializers.ImageField(source='image', read_only=True)

    class Meta:
        model = AccreditationCertificate
        fields = ['id', 'image_url']


class LaboratorySerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    certificates = AccreditationCertificateSerializer(many=True, read_only=True)
    average_rating = serializers.ReadOnlyField()

    class Meta:
        model = Laboratory
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'city',
            'state',
            'address',
            'phone',
            'email',
            'website',
            'accreditation',
            'certificates',
            'average_rating',
            'categories',
        ]
