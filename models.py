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

from google.appengine.ext import db
from google.appengine.ext.blobstore import blobstore


class Feed(db.Model):
  url = db.StringProperty(required=True)
  title = db.StringProperty(required=True)
  link = db.StringProperty(required=True)

  last_fetch_time = db.DateTimeProperty()

  @property
  def entries(self):
    return sorted(self.entry_set.fetch(20),
                  key=lambda entry: entry.updated,
                  reverse=True)

  @property
  def updated(self):
    try:
      return self.entries[-1].updated
    except IndexError:
      return None


class Entry(db.Model):
  feed = db.ReferenceProperty(Feed)
  title = db.StringProperty(required=True)
  link = db.StringProperty(required=True)
  updated = db.DateTimeProperty()
  content = db.TextProperty()
