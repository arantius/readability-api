from django.db import models


class Facet(models.Model):
  """Any facet that identifies an element as spam or ham."""
  kind = models.CharField(db_index=True, max_length=16)
  data_char = models.CharField(db_index=True, max_length=128, null=True)
  data_int = models.IntegerField(db_index=True, null=True)
  ham_count = models.IntegerField(default=0)
  spam_count = models.IntegerField(default=0)


class Page(models.Model):
  url = models.CharField(db_index=True, max_length=255)
