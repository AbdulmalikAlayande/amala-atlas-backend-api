"""
URL configuration for amala_atlas project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include
from django.contrib import admin
from rest_framework import routers

import ingestion.views
import places.views
import verification.views

router = routers.DefaultRouter()
router.register(r'spots', places.views.SpotViewSet)


urlpatterns = router.urls

urlpatterns += [
    path('admin/', admin.site.urls),
    # Not an endpoint, just for learning:: path('spot/create-spot', places.views.SpotApiView.as_view()),
    path('verify/queue/', verification.views.GetVerificationCandidateQueue.as_view()),
    path('verify/action/', verification.views.VerificationActionView.as_view()),
    path('ingest/', ingestion.views.IngestCandidateView.as_view()),
    path('submit-candidate/', places.views.CandidateSubmissionView.as_view()),
    path("health/", places.views.HealthCheckView.as_view(), name="health"),
]