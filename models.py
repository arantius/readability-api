from django.db import models

_MAX_ENTRIES_PER_FEED = 20

class Feed(models.Model):
  last_fetch_time = models.DateTimeField()
  link = models.URLField(max_length=1024)
  title = models.CharField(max_length=1024)
  url = models.URLField(max_length=1024)


class Entry(models.Model):
  feed = models.ForeignKey(Feed)

  content = models.TextField()
  created = models.DateTimeField(auto_now_add=True)
  link = models.URLField(max_length=1024)
  original_content = models.TextField()
  title = models.CharField(max_length=1024)
  updated = models.DateTimeField()
