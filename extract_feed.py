#!/usr/bin/env python
"""Extract a page's relevant content, via RSS parsing.

Theory: given a URL, likely from a content aggregation site, and the content
located at that URL, A) detect if the site advertises an RSS feed of its
contents, B) if so, and if possible, find the content from the feed for _this_
URL, and C) evaluate whether it is a "good" piece of content (i.e. from a
full feed and not truncated).

Usage example:
  feed_extractor = FeedExtractor(url='http://....',
                final_url='http://...',
                html='<html>...</html>')
  if feed_extractor.FindContents():
  pass

Note that the html argument to the constructor is optional, but can be provided
to avoid a second URL fetch in the case that it is already known.  If it is
provided, the "final" URL (after possible redirects) should also be provided.
"""

"""
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

import re

from third_party import BeautifulSoup
from third_party import autorss
from third_party import feedparser

import util


# Minimum length of text in feed entry content to accept.
MIN_FEED_TEXT_LEN = 512


class RssError(Exception):
  pass


class UnsupportedRssError(RssError):
  pass


class NoRssError(RssError):
  pass


class NoRssItemError(RssError):
  pass


class NoRssContentError(RssError):
  pass


def TrimQuery(url):
  return url.split('?')[0]


class FeedExtractor(object):
  """Clean a page to its readable part by extracting from the site's feed."""

  def __init__(self, url=None, final_url=None, html=None):
    assert url, 'URL must be provided.'
    self.url = url

    if re.search(r'^https?://(docs|spreadsheets)\.google\.', url, re.I):
      raise UnsupportedRssError('skip google docs')

    if final_url or html:
      assert (final_url and html), ('If either is, both final_url and '
                                    'html must be provided')
      self.final_url = final_url
      self.html = html
    else:
      self.html, self.final_url = util.Fetch(url)

    feed_url = self._DetectFeed()
    feed_source, _ = util.Fetch(feed_url)
    self.feed = feedparser.parse(feed_source)
    self._FindEntry()

    self.content = util.EntryContent(self.entry)

    # Now, we've found content.  Check if it's legit.
    soup = BeautifulSoup.BeautifulSoup(self.content)
    for tag in soup.findAll(('a', 'script', 'noscript')):
      tag.extract()
    text = soup.text
    if re.search(r'\[?\.\.\.\]?\s*$', text):
      raise NoRssContentError('trailing ellipsis')
    if len(text) < MIN_FEED_TEXT_LEN:
      raise NoRssContentError('text too short (%d)' % len(text))

  def _DetectFeed(self):
    """Find the URL to a feed for this page."""
    rss_link = autorss.getRSSLinkFromHTMLSource(self.html)
    if not rss_link:
      raise NoRssError('no feed link')
    return rss_link

  def _FindEntry(self):
    """Find the entry in the feed, if any, which matches this url."""
    entry = (self._FindEntryMatching(self.url)
             or self._FindEntryMatching(self.final_url)
             or self._FindEntryMatching(TrimQuery(self.url), True)
             or self._FindEntryMatching(TrimQuery(self.final_url), True)
            )
    if not entry:
      raise NoRssItemError('found no matching item')
    self.entry = entry

  def _FindEntryMatching(self, url, trim_query=False):
    for entry in self.feed.entries:
      if self._UrlsMatch(entry.link, url, trim_query):
        return entry
      if 'feedburner_origlink' in entry:
        if self._UrlsMatch(entry.feedburner_origlink, url, trim_query):
          return entry

  def _UrlsMatch(self, url1, url2, trim_query):
    if trim_query:
      url1 = TrimQuery(url1)
    return url1 == url2
