#!/usr/bin/env python
"""Feed re-syndicator functionality.

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

import base64
import datetime
import hashlib
import logging
import re
import urlparse

from google.appengine.ext import deferred

from third_party import feedparser

import clean
import models
import util

_EMPTY_ENTRY = {
    'key': {'name': ''},
    'title': 'Processing ...',
    'link': 'about:blank',
    'content': 'Please wait while this feed is fetched and processed.'}


@util.DeferredRetryLimit()
def _CleanEntry(feed_entity, entry_feedparser):
  """Given a parsed feed entry, turn it into a cleaned entry entity."""
  entry_entity = models.Entry(
    key_name = _EntryId(entry_feedparser),
    feed = feed_entity,
    title = entry_feedparser.title,
    link = entry_feedparser.link,
    updated = datetime.datetime(*entry_feedparser.updated_parsed[:6]),
    content = clean.Clean(entry_feedparser.link))
  entry_entity.put()


def _EntryId(entry_feedparser):
  entry_id = entry_feedparser.id or entry_feedparser.link
  entry_id = hashlib.sha256(entry_id).digest()
  return base64.b64encode(entry_id)


def CreateFeed(url):
  feed_feedparser = util.ParseFeedAtUrl(url)
  feed_entity = models.Feed(
      key_name = url,
      url = url,
      title = feed_feedparser.feed.title,
      link = feed_feedparser.feed.link)
  UpdateFeed(feed_entity, feed_feedparser)
  feed_entity.put()
  return feed_entity


@util.DeferredRetryLimit()
def UpdateFeed(feed_entity, feed_feedparser=None):
  if not feed_feedparser:
    feed_feedparser = util.ParseFeedAtUrl(feed_entity.url)
  for entry_feedparser in feed_feedparser.entries:
    if not models.Entry.get_by_key_name(_EntryId(entry_feedparser)):
      deferred.defer(_CleanEntry, feed_entity, entry_feedparser, _queue='fetch')
  feed_entity.last_fetch_time = datetime.datetime.now()
  feed_entity.put()


def PrintFeed(feed_entity):
  if not feed_entity.entries:
    feed_entity = {
        'title': feed_entity.title,
        'link': feed_entity.title,
        'entries': [_EMPTY_ENTRY],
        }
  return util.RenderTemplate('feed.xml', {'feed': feed_entity})
