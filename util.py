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

import Cookie
import logging
import os
import re
import urlparse

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template

IS_DEV_APPSERVER = 'Development' in os.environ.get('SERVER_SOFTWARE', '')
MAX_SCORE_DEPTH = 5
RE_DOCTYPE = re.compile(r'<!DOCTYPE.*?>', re.S)
RE_HTML_COMMENTS = re.compile(r'<!--.*?-->', re.S)

_DEPTH_SCORE_DECAY = [(1 - d / 12.0) ** 5 for d in range(MAX_SCORE_DEPTH + 1)]


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


def ApplyScore(tag, score, depth=0, name=None):
  """Recursively apply a decaying score to each parent up the tree."""
  if not tag:
    return
  if depth > MAX_SCORE_DEPTH:
    return
  decayed_score = score * _DEPTH_SCORE_DECAY[depth]

  if not tag.has_key('score'): tag['score'] = 0.0
  tag['score'] = tag['score'] + decayed_score

  if IS_DEV_APPSERVER and name:
    name_key = 'score_%s' % name
    if not tag.has_key(name_key):
      tag[name_key] = 0
    tag[name_key] = float(tag[name_key]) + decayed_score

  ApplyScore(tag.parent, score, depth + 1, name=name)


@Memoize('Fetch_%s', 60*60*24)
def Fetch(url):
  """Fetch a URL, return its contents and any final-after-redirects URL."""
  error = None
  for _ in xrange(3):
    try:
      return _Fetch(url)
    except FetchError, e:
      error = e
      logging.exception(e)
  if error: raise error


class FetchError(Exception):
  pass


def _Fetch(orig_url):
  cookie = Cookie.SimpleCookie()
  redirect_limit = 10
  redirects = 0
  url = orig_url
  while url and redirects < redirect_limit:
    redirects += 1
    try:
      if IS_DEV_APPSERVER:
        logging.info('Fetching: %s', url)
      final_url = url
      response = urlfetch.fetch(
          url, allow_truncated=True, follow_redirects=False, deadline=3,
          headers={'Cookie': cookie.output(attrs=(), header='', sep='; ')})
      cookie.load(response.headers.get('Set-Cookie', ''))
      url = response.headers.get('Location')
    except urlfetch.DownloadError, e:
      raise FetchError(repr(e))
  final_url = urlparse.urljoin(orig_url, final_url)
  return (response.content, final_url)


def PreCleanHtml(html):
  # Remove all HTML comments, doctypes.
  html = re.sub(RE_HTML_COMMENTS, '', html)
  html = re.sub(RE_DOCTYPE, '', html)

  return html


def RenderTemplate(template_name, template_values):
  template_base = os.path.join(os.path.dirname(__file__), 'templates')
  return template.render(os.path.join(template_base, template_name),
                         template_values)


def SoupTagOnly(tag):
  return str(tag).split('>')[0] + '>'
