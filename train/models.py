from django.db import models

class Facet(models.Model):
  """Any facet that identifies an element as spam or ham."""
  spam = models.BooleanField()
  kind = models.CharField(max_length=16, db_index=True)
  data_char = models.CharField(max_length=128)
  data_int = models.IntegerField()
