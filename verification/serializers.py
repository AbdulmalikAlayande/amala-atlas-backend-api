from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from places.models import Candidate, PhotoURL, Submission
from . import models
from .models import Verification

class PhotoURLSerializer(serializers.ModelSerializer):

    class Meta:
        model = PhotoURL
        fields = ['id', 'url']

class VerificationSerializer(serializers.ModelSerializer):
    candidate_id = serializers.CharField(source="candidate.id")
    # user_id = ModelField(model_field=User)

    class Meta:
        model = models.Verification
        fields = ('candidate', 'action', 'notes', 'by_user', 'created_at', 'last_modified_at')
        read_only_fields = ("id", "public_id", "created_at")


class VerificationActionSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=[x.value for x in Verification.Actions])
    notes = serializers.CharField(required=False, allow_blank=True)
    merge_into_spot_id = serializers.IntegerField(required=False)


class CandidateQueueSerializer(serializers.ModelSerializer):
    kind = serializers.ChoiceField(choices=Submission.Kind.choices, default=Submission.Kind.MANUAL)
    photo_urls = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = ("id", "name", "city", "state", "country", "score", "source_kind", "source_channel",
                  "evidence", "photo_urls", "price_band", "tags", "phone", "kind", "email", "website",
                  "signals", "lat", "lng", "raw_address")

    def get_photo_urls(self, obj):
        print(self)
        all_photo_urls = []
        if obj.photo_urls and obj.photo_urls.count() > 0:
            all_photo_urls = obj.photo_urls.all()
            print("1. All photo URLs:: ", all_photo_urls)
        else:
            candidate_ct = ContentType.objects.get_for_model(obj)
            all_photo_urls = PhotoURL.objects.filter(content_type=candidate_ct, object_id=obj.id)
            print("2. All photo URLs:: ", all_photo_urls)

        return PhotoURLSerializer(all_photo_urls, many=True).data