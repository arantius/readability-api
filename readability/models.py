#!/usr/bin/env python
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


_MAX_ENTRIES_PER_FEED = 20


class Feed(models.Model):
  class Meta:
    app_label = 'readability'

  url = models.TextField(blank=False, default=None)
  title = models.TextField(blank=False, default=None)
  link = models.TextField(blank=False, default=None)

  last_fetch_time = models.DateTimeField()

  @property
  def entries(self):
    """List of active entries in the feed."""
    return self.entry_set.order('-updated').fetch(_MAX_ENTRIES_PER_FEED)

  @property
  def stale_entries(self):
    """List of stale entries that should be removed."""
    return self.entry_set.order('-updated').fetch(999, _MAX_ENTRIES_PER_FEED)

  @property
  def updated(self):
    try:
      return self.entries[-1].updated
    except IndexError:
      return None


class Entry(models.Model):
  class Meta:
    app_label = 'readability'

  feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
  title = models.TextField(blank=False, default=None)
  link = models.TextField(blank=False, default=None)
  updated = models.DateTimeField(auto_now=True)
  content = models.TextField(blank=False, default=None)
  original_content = models.TextField()
  #tags = db.ListProperty(item_type=str)

  created = models.DateTimeField(auto_now_add=True)
