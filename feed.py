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

import clean
import models
import util


_EMPTY_ENTRY = {
    'key': {'name': ''},
    'title': 'Processing ...',
    'link': 'about:blank',
    'content': 'Please wait while this feed is fetched and processed.',
    'tags': [],
    }


def _CleanEntryBase(feed_entity, entry_feedparser, content, original_content):
  if entry_feedparser.updated_parsed:
    updated = datetime.datetime(*entry_feedparser.updated_parsed[:6])
  else:
    updated = datetime.datetime.now()

  try:
    tags = [c['term'] for c in entry_feedparser.tags]
  except (AttributeError, KeyError):
    tags = []

  try:
    title = entry_feedparser.title.replace('\n', '').replace('\r', '')
  except AttributeError:
    title = 'Unknown'

  try:
    link = entry_feedparser.link
  except AttributeError:
    link = 'Unknown'

  entry_entity = models.Entry(
      key_name=_EntryId(entry_feedparser),
      feed=feed_entity,
      title=title,
      link=link,
      updated=updated,
      content=content,
      original_content=original_content,
      tags=tags)
  entry_entity.put()


def _CleanEntryFailure(feed_entity, entry_feedparser, exception):
  _CleanEntryBase(feed_entity, entry_feedparser,
                  content='Error cleaning entry: %s' % exception,
                  original_content='')


# TODO: Retry somehow.
def _CleanEntry(feed_entity, entry_feedparser):
  """Given a parsed feed entry, turn it into a cleaned entry entity."""
  logging.info(
      'For feed %r, cleaning entry %r ...',
      feed_entity.key().id_or_name(),
      getattr(entry_feedparser, 'link', 'UNKNOWN'))

  if not hasattr(entry_feedparser, 'link'):
    logging.warn('Missing link attribute!?')
    return

  try:
    _CleanEntryBase(
        feed_entity, entry_feedparser,
        content=clean.Clean(entry_feedparser.link),
        original_content=util.GetFeedEntryContent(entry_feedparser))
  except:
    logging.info('Got error cleaning: %s', entry_feedparser.link)
    raise


def _EntryId(entry_feedparser):
  try:
    entry_id = entry_feedparser.id.encode('utf-8')
  except AttributeError:
    entry_id = entry_feedparser.link.encode('utf-8')
  entry_id = hashlib.sha256(entry_id).digest()
  return base64.b64encode(entry_id)


def CreateFeed(url):
  feed_feedparser = util.ParseFeedAtUrl(url)
  feed_entity = models.Feed(
      key_name=url,
      url=url,
      title=feed_feedparser.feed.title,
      link=feed_feedparser.feed.link)
  UpdateFeed(feed_entity, feed_feedparser)
  feed_entity.put()
  return feed_entity


def UpdateFeed(feed_entity, feed_feedparser=None):
  if isinstance(feed_entity, db.Key):
    feed_entity = db.get(feed_entity)
  logging.info('Updating feed %r ...', feed_entity.key().id_or_name())

  if not feed_feedparser:
    feed_feedparser = util.ParseFeedAtUrl(feed_entity.url)

  entry_keys = [db.Key.from_path('Entry', _EntryId(entry))
                for entry in feed_feedparser.entries]
  entry_entities = db.get(entry_keys)
  existing_keys = [entry.key().name() for entry in entry_entities if entry]

  delay = 0
  for entry_feedparser in feed_feedparser.entries:
    if _EntryId(entry_feedparser) not in existing_keys:
      #deferred.defer(_CleanEntry, feed_entity, entry_feedparser,
      #               _countdown=delay, _queue='fetch')
      #delay += 3
      # TODO: enqueue somehow
      return

  feed_entity.last_fetch_time = datetime.datetime.now()
  feed_entity.put()


def PrintFeed(feed_entity, include_original=False):
  if not feed_entity.entries:
    feed_entity = {
        'title': feed_entity.title,
        'link': feed_entity.title,
        'entries': [_EMPTY_ENTRY],
        }
  return util.RenderTemplate(
      'feed.xml', {'feed': feed_entity, 'include_original': include_original})
