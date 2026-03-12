from rest_framework import serializers

from . import models
from .models import Submission


class PhotoURLSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PhotoURL
        fields = ['id', 'url']


class SpotSerializer(serializers.ModelSerializer):
    photo_urls = PhotoURLSerializer(many=True, read_only=True)

    class Meta:
        model = models.Spot
        fields = ('id', 'public_id', 'created_at', 'last_modified_at', 'name', 'address', 'city', 'state', 'lat', 'lng',
                  'photo_urls')


class GetSpotSerializer(serializers.ModelSerializer):
    photo_urls = PhotoURLSerializer(many=True, read_only=True)

    class Meta:
        model = models.Spot
        fields = (
            'id', 'public_id', 'created_at', 'last_modified_at', 'name', 'address', 'city', 'state', 'lat', 'lng',
            'country',
            'zipcode', 'price_band', 'tags', 'photos', "email", "photo_urls", "phone", "website", 'open_hours', 'source'
        )


class CandidateSubmissionSerializer(serializers.ModelSerializer):
    kind = serializers.ChoiceField(choices=Submission.Kind.choices, default=Submission.Kind.MANUAL)
    photo_urls = serializers.ListField(child=serializers.URLField(), write_only=True)

    class Meta:
        model = Submission
        fields = (
            'id', 'public_id', 'created_at', 'last_modified_at', "kind", "name", "address", "city", "country",
            "lat", "lng", "price_band", "tags", "hours_text", "email", "photo_urls", "phone", "website", "transcript", "raw_payload"
        )

    def validate(self, attrs):
        lat, lng = attrs['lat'], attrs['lng']
        if (lat is not None) ^ (lng is not None):
            raise serializers.ValidationError("Provide both lat and lng together, or leave both empty.")
        return attrs

    def create(self, validated_data):
        photo_urls = validated_data.pop("photo_urls", [])
        submission = Submission.objects.create(**validated_data)
        for url in photo_urls:
            models.PhotoURL.objects.create(url=url, content_object=submission)
        return submission
