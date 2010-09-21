#!/usr/bin/env python
"""General utility helper functions.

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

import logging
import os
import re
import urlparse

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template

IS_DEV_APPSERVER = 'Development' in os.environ.get('SERVER_SOFTWARE', '')
RE_DOCTYPE = re.compile(r'<!DOCTYPE.*?>', re.S)
RE_DOUBLE_BR = re.compile(r'<br[ /]*>\s*<br[ /]*>', re.I)
RE_HTML_COMMENTS = re.compile(r'<!--.*?-->', re.S)


def Memoize(formatted_key, time=60*60):
  """Decorator to store a function call result in App Engine memcache."""

  def Decorator(func):
    def InnerDecorator(*args, **kwargs):
      key = formatted_key % args[0:formatted_key.count('%')]
      result = memcache.get_multi([key])
      if key in result:
        return result[key]
      result = func(*args, **kwargs)
      memcache.set(key, result, time)
      return result
    return InnerDecorator
  return Decorator


@Memoize('Fetch_%s', 60*60*24)
def Fetch(url):
  """Fetch a URL, return its contents and any final-after-redirects URL."""
  error = None
  for _ in xrange(2):
    try:
      return _Fetch(url)
    except _FetchError, e:
      error = e
      logging.exception(e)
  return (repr(error), url)


class _FetchError(Exception):
  pass


def _Fetch(url):
  try:
    if IS_DEV_APPSERVER:
      logging.info('Fetching: %s', url)
    response = urlfetch.fetch(url, allow_truncated=True, deadline=3)
  except urlfetch.DownloadError, e:
    raise _FetchError(repr(e))
  else:
    final_url = (response.final_url or url)
    final_url = urlparse.urljoin(url, final_url)
    return (response.content, final_url)


def IdOrClassMatches(tag, regex):
  if not tag:
    return False
  if tag.name in ('body', 'html'):
    return False
  if tag.has_key('class') and regex.search(tag['class']):
    return True
  if tag.has_key('id') and regex.search(tag['id']):
    return True
  return False


def PreCleanHtml(html):
  # Remove all HTML comments, doctypes.
  html = re.sub(RE_HTML_COMMENTS, '', html)
  html = re.sub(RE_DOCTYPE, '', html)
  # Turn double-linebreaks into faked-up paragraphs.
  html = re.sub(RE_DOUBLE_BR, '</p><p>', html)

  return html


def RenderTemplate(template_name, template_values):
  template_base = os.path.join(os.path.dirname(__file__), 'templates')
  return template.render(os.path.join(template_base, template_name),
                         template_values)


def SoupTagOnly(tag):
  return str(tag).split('>')[0] + '>'
