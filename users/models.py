from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    whatsapp_phone = models.CharField(max_length=20, blank=True, unique=True, null=True)
    spots_contributed = models.PositiveIntegerField(default=0)
