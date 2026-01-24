from django.db import models
from django.contrib.auth import get_user_model
# Create your models here.
class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(get_user_model(), related_name='group_members')