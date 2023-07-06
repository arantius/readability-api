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
import operator
import time

from django import template
from huey.contrib.djhuey import  db_task

from readability import clean
from readability import models
from readability import util


_EMPTY_ENTRY = {
    'key': {'name': ''},
    'title': 'Processing ...',
    'link': 'about:blank',
    'content': 'Please wait while this feed is fetched and processed.',
    'tags': [],
    }

_MAX_UPDATE_INTERVAL = datetime.timedelta(days=3).total_seconds()
_MIN_UPDATE_INTERVAL = datetime.timedelta(hours=1).total_seconds()


def _CleanEntryBase(feed_entity, entry_feedparser, content, original_content):
  dt = entry_feedparser.updated_parsed or entry_feedparser.published_parsed
  if dt:
    updated = datetime.datetime(*dt[:6])
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
      key=_EntryId(entry_feedparser),
      feed=feed_entity,
      title=title,
      link=link,
      updated=updated,
      content=content,
      original_content=original_content,
      tags=tags)
  entry_entity.save()


def _CleanEntryFailure(feed_entity, entry_feedparser, ex):
  url = entry_feedparser.link
  truncate_url = url
  if len(url) > clean._MAX_URL_DISPLAY_LEN:
    truncate_url = url[0:60] + '…'
  content = '''
<p>Error cleaning entry at <a href="%s">%s</a>:</p>
<pre style="pre-wrap'>%s</pre>
''' % (url, truncate_url, ex)
  _CleanEntryBase(
      feed_entity, entry_feedparser,
      content=content, original_content='')


@db_task()
def _CleanEntry(feed_entity, entry_feedparser):
  """Given a parsed feed entry, turn it into a cleaned entry entity."""
  util.log.info(
      'For feed %r, cleaning entry %r ...',
      feed_entity.url,
      getattr(entry_feedparser, 'link', 'UNKNOWN'))
  if not hasattr(entry_feedparser, 'link'):
    util.log.warn('Missing link attribute!?')
    return

  i = 0
  while True:
    try:
      content = clean.Clean(entry_feedparser.link)
      _CleanEntryBase(
          feed_entity, entry_feedparser,
          content=content,
          original_content=util.GetFeedEntryContent(entry_feedparser))
    except Exception as ex:
      util.log.info(
          'Got error %d cleaning %s: %s', i, entry_feedparser.link, ex)
      time.sleep(15)
      i += 1
      if i < 3:
        continue
      else:
        _CleanEntryFailure(feed_entity, entry_feedparser, ex)
    break


def _EntryId(entry_feedparser):
  try:
    entry_id = entry_feedparser.id.encode('utf-8')
  except AttributeError:
    entry_id = entry_feedparser.link.encode('utf-8')
  entry_id = hashlib.sha256(entry_id).digest()
  return base64.b64encode(entry_id).decode('ascii')


def CreateFeed(url):
  feed_feedparser = util.ParseFeedAtUrl(url)
  feed_entity = models.Feed(
      url=url,
      title=feed_feedparser.feed.title,
      link=feed_feedparser.feed.link)
  feed_entity.save()
  UpdateFeed.call_local(feed_entity.url, feed_feedparser, local=True)
  return feed_entity


def RenderFeed(feed_entity, include_original=False):
  tpl = template.loader.get_template('feed.xml')
  return tpl.render({
      'feed': feed_entity,
      'entries': feed_entity.entries or [_EMPTY_ENTRY],
      'include_original': include_original,
   })


def _UpdateFeedInterval(feed_entity, had_new_items):
  f = feed_entity.fetch_interval_seconds
  f *= 0.9 if had_new_items else 1.1
  if f < _MIN_UPDATE_INTERVAL: f = _MIN_UPDATE_INTERVAL
  if f > _MAX_UPDATE_INTERVAL: f = _MAX_UPDATE_INTERVAL

  feed_entity.fetch_interval_seconds = f
  feed_entity.last_fetch_time = time.time()
  feed_entity.save()


@db_task()
def UpdateFeed(feed_url, feed_feedparser=None, local=False):
  util.log.info('Updating feed %r ...', feed_url)

  feed_entity = models.Feed.objects.get(url=feed_url)
  if not feed_feedparser:
    feed_feedparser = util.ParseFeedAtUrl(feed_entity.url)
  if not feed_feedparser:
    # Bad fetch, ignore.
    _UpdateFeedInterval(feed_entity, False)
    return

  entries = sorted(
      feed_feedparser.entries,
      key=operator.attrgetter('published_parsed'),
      reverse=True)
  entries = entries[:models.MAX_ENTRIES_PER_FEED]

  entry_keys = [_EntryId(e) for e in entries]
  existing_keys = models.Entry.objects.filter(feed__url=feed_url).values('key')
  existing_keys = set(x['key'] for x in existing_keys)

  util.log.info(
      'Downloaded %d entries, already have %d ...',
      len(entries), len(existing_keys))
  delay = 1
  new_entries = False
  for entry_feedparser in entries:
    if _EntryId(entry_feedparser) in existing_keys:
      continue
    new_entries = True
    args = (feed_entity, entry_feedparser)
    if local:
      _CleanEntry.call_local(*args)
      time.sleep(1)
    else:
      _CleanEntry.schedule(args, delay=delay)
    delay += 3

  _UpdateFeedInterval(feed_entity, new_entries)
