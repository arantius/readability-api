"""Datastore models for Readability API project.

--------------------------------------------------------------------------------

Readability API - Clean up pages and feeds to be readable.
Copyright (C) 2010  Anthony Lieuallen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from django.db import models


MAX_ENTRIES_PER_FEED = 50


class Feed(models.Model):
  class Meta:
    app_label = 'readability'

  url = models.TextField(primary_key=True)
  title = models.TextField(blank=False, default=None)
  link = models.TextField(blank=False, default=None)
  last_fetch_time = models.FloatField(default=0)  # UTC seconds.
  fetch_interval_seconds = models.IntegerField(default=4*60*60)

  @property
  def entries(self):
    """List of active entries in the feed."""
    return Entry.objects.filter(feed__url=self.url) \
        .order_by('-updated')[:MAX_ENTRIES_PER_FEED]

  @property
  def stale_entries(self):
    """List of stale entries that should be removed."""
    return Entry.objects.filter(feed__url=self.url) \
        .order_by('-updated')[MAX_ENTRIES_PER_FEED:]

  @property
  def updated(self):
    try:
      return self.entries[0].updated
    except IndexError:
      return None


class Entry(models.Model):
  class Meta:
    app_label = 'readability'

  key = models.TextField(primary_key=True)
  feed = models.ForeignKey(Feed, on_delete=models.CASCADE)

  title = models.TextField(blank=False, default=None)
  link = models.TextField(blank=False, default=None)
  updated = models.DateTimeField()
  content = models.TextField(blank=False, default=None)
  original_content = models.TextField()
  tags = models.JSONField(default=list)
