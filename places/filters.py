import django_filters
import logging
from django.db.models import Q
from places.models import Spot

logger = logging.getLogger(__name__)

class GetSpotsFilter(django_filters.FilterSet):
    bbox = django_filters.CharFilter(method='filter_bbox')
    city = django_filters.CharFilter(field_name='city', lookup_expr='iexact')
    price_band = django_filters.CharFilter(field_name='price_band', lookup_expr='iexact')
    tags = django_filters.CharFilter(method='filter_tags')
    query = django_filters.CharFilter(method='filter_query')

    def filter_bbox(self, queryset, name, value):
        """Filter by bounding box: bbox=minLng,minLat,maxLng,maxLat"""
        logger.info(f"Filter by bounding box: bbox={value}, name={name}")
        try:
            min_lng, min_lat, max_lng, max_lat = map(float, value.split(","))
            print(min_lng, min_lat, max_lng, max_lat)
            # sanity guard
            if min_lng > max_lng or min_lat > max_lat:
                return queryset.none()
            return queryset.filter(
                lng__gte=min_lng, lng__lte=max_lng,
                lat__gte=min_lat, lat__lte=max_lat,
            )
        except Exception as exc:
            print(f"[GetSpotsFilter] Invalid bbox '{value}': {exc}")
            return queryset.none()

    def filter_tags(self, queryset, name, value):
        """Filter by one or more comma-separated tags"""
        logger.info(f"Filter by one or more comma-separated tags: tags={value}, name={name}")
        tags = [t.strip() for t in value.split(",") if t.strip()]
        if not tags:
            return queryset
        q = Q()
        for t in tags:
            q |= Q(tags__icontains=t)
        return queryset.filter(q)

    def filter_query(self, queryset, name, value):
        """Loose search over name / city / address"""
        logger.info(f"Loose search over name / city / address: query={value}, name={name}")
        v = (value or "").strip()
        if not v:
            return queryset
        return queryset.filter(
            Q(name__icontains=v)
            | Q(city__icontains=v)
            | Q(address__icontains=v)
        )

    class Meta:
        model = Spot
        fields = ["bbox", "city", "price_band", "tags", "query"]
