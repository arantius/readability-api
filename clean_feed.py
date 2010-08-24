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

import logging
import urllib2

from third_party import autorss
from third_party import feedparser


logging.basicConfig(level=logging.DEBUG)


class RssError(Exception):
  pass


class NoRssError(RssError):
  pass


class NoRssItemError(RssError):
  pass


class NoRssContentError(RssError):
  pass


def TrimQuery(url):
  return url.split('?')[0]


class FeedCleaner(object):
  """Clean a page to its readable part by extracting from the site's feed."""

  def __init__(self, url=None, final_url=None, html=None):
    self.clean_content = None

    assert url, 'URL must be provided.'
    self.url = url

    if final_url or html:
      assert (final_url and html), ('If either is, both final_url and '
                                    'html must be provided')
      self.final_url = final_url
      self.html = html
    else:
      response = urllib2.urlopen(url)
      self.final_url = response.geturl()
      self.html = response.read()

    feed_url = self._DetectFeed()
    self.feed = feedparser.parse(feed_url)
    self._FindEntry()

    self.content = self._EntryBestContent()

#    # Now, we've found content.  Check if it's legit.
#    soup = BeautifulSoup(content)
#    for tag in soup.findAll(('a', 'script', 'noscript')):
#      tag.extract()
#    logging.info('found content html: %s', soup)
#    logging.info('found content text: %s', soup.text)

  def _DetectFeed(self):
    """Find the URL to a feed for this page."""
    rss_link = autorss.getRSSLinkFromHTMLSource(self.html)
    if not rss_link:
      raise NoRssError()
    return rss_link

  def _FindEntry(self):
    """Find the entry in the feed, if any, which matches this url."""
    entry = (self._FindEntryMatching(self.url)
             or self._FindEntryMatching(self.final_url)
             or self._FindEntryMatching(TrimQuery(self.url), True)
             or self._FindEntryMatching(TrimQuery(self.final_url), True)
            )
    if not entry:
      raise NoRssItemError()
    self.entry = entry

  def _FindEntryMatching(self, url, trim_query=False):
    for entry in self.feed.entries:
      if self._UrlsMatch(entry.link, url, trim_query):
        return entry
      if entry.feedburner_origlink:
        if self._UrlsMatch(entry.feedburner_origlink, url, trim_query):
          return entry

  def _UrlsMatch(self, url1, url2, trim_query):
    if trim_query:
      url1 = TrimQuery(url1)
    logging.info('match? %s %s', url1, url2)
    return url1 == url2

  def _EntryBestContent(self):
    """Figure out the best content for this entry."""
    # Prefer "content".  Use it if there's only one, or ..
    if 'content' in self.entry:
      if len(self.entry.content) == 1:
        return self.entry.content[0]
      # .. use the text/html type if there's more than one.
      for content in self.entry.content:
        if 'text/html' == content.type:
          return content.value
    # Otherwise try "summary_detail" and "summary".
    if 'summary_detail' in self.entry:
      return self.entry.summary_detail.value
    if 'summary' in self.entry:
      return self.entry.summary
