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

import datetime
import http.cookies
import io
import functools
import logging
import os
import re
import urllib.parse

import bs4
from django import template
import feedparser
import requests
import requests.exceptions
import requests_cache

from readability import settings


DEBUG = settings.DEBUG
RE_CNN_HACK = re.compile(r'<!-- with(out)? htc -->')
RE_DOCTYPE = re.compile(r'<!DOCTYPE.*?>', re.S)
TAG_NAMES_BLOCK = set(('blockquote', 'div', 'li', 'p', 'pre', 'td', 'th'))
TAG_NAMES_HEADER = set(('h1', 'h2', 'h3', 'h4', 'h5', 'h6'))

BR_TO_P_STOP_TAGS = set(list(TAG_NAMES_BLOCK) + list(TAG_NAMES_HEADER) + ['br'])

MAX_SCORE_DEPTH = 5
_DEPTH_SCORE_DECAY = [(1 - d / 12.0) ** 5 for d in range(MAX_SCORE_DEPTH + 1)]

################################################################################

log = logging.Logger('readability')
_lh = logging.StreamHandler()
_lh.setFormatter(logging.Formatter('%(asctime)s:readability:%(message)s'))
log.addHandler(_lh)

################################### HELPERS ####################################

def ApplyScore(tag, score, depth=0, name=None):
  """Recursively apply a decaying score to each parent up the tree."""
  if not tag:
    return
  if depth > MAX_SCORE_DEPTH:
    return
  if tag.name == 'li' and score > 0:
    # Don't score list items positively.  Too likely to be false positives.
    return
  decayed_score = score * _DEPTH_SCORE_DECAY[depth]

  if not tag.has_attr('score'): tag['score'] = 0.0
  tag['score'] += decayed_score

  if DEBUG and name:
    name_key = 'score_%s' % name
    if not tag.has_attr(name_key):
      tag[name_key] = 0
    tag[name_key] = float(tag[name_key]) + decayed_score
    if not tag.has_attr('all_scores'):
      tag['all_scores'] = ''
    tag['all_scores'] += '%s=%s ' % (name_key, decayed_score)

  ApplyScore(tag.parent, score, depth + 1, name=name)


def CleanUrl(url):
  url = re.sub(r'utm_[a-z]+=[^&]+(&?)', r'\1', url)
  url = re.sub(r'[?&]+$', '', url)
  return url


def CommentStrip(soup):
  comments = soup.findAll(text=lambda t: isinstance(t, bs4.Comment))
  for comment in comments:
    comment.extract()


def Fetch(orig_url, deadline=6, do_cache=True):
  cookie = http.cookies.SimpleCookie()
  redirect_limit = 5
  redirects = 0
  url = orig_url
  while url and redirects < redirect_limit:
    redirects += 1
    url = CleanUrl(url)
    if settings.DEBUG:
      log.info('Fetching %r after %d redirects', url, redirects - 1)
    final_url = url
    session = requests
    if do_cache:
      session = RequestsCacheSession()
    response = session.get(
        url,
        timeout=deadline,
        headers={
          'Cookie': cookie.output(attrs=(), header='', sep='; '),
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        })
    try:
      cookie.load(response.headers.get('Set-Cookie', ''))
    except cookie.CookieError:
      log.exception('Ignoring cookie problem!')
    previous_url = url
    url = response.headers.get('Location')
    if url:
      url = urllib.parse.urljoin(previous_url, url)
  final_url = urllib.parse.urljoin(orig_url, final_url)
  return (response, final_url)


def GetFeedEntryContent(entry):
  """Figure out the best content for this entry."""
  # Prefer "content".
  if 'content' in entry:
    # If there's only one, use it.
    if len(entry.content) == 1:
      return entry.content[0]['value']
    # Or, use the text/html type if there's more than one.
    for content in entry.content:
      if ('type' in content) and ('text/html' == content['type']):
        return content['value']
  # Otherwise try "summary_detail" and "summary".
  if 'summary_detail' in entry:
    return entry.summary_detail['value']
  if 'summary' in entry:
    return entry.summary
  return ''


def ParseFeedAtUrl(url):
  """Fetch a URL's contents, and parse it as a feed."""
  try:
    response, _ = Fetch(url, deadline=20, do_cache=False)
  except requests.exceptions.ConnectionError as e:
    print('Remote disconnected while fetching %r!' % url)
    return None
  try:
    feed_feedparser = feedparser.parse(response.content)
  except LookupError:
    return None
  else:
    return feed_feedparser


def PreCleanHtml(html):
  html = re.sub(RE_DOCTYPE, '', html)
  html = html.replace('&nbsp;', ' ')
  return html


def RenderTemplate(template_name, template_values=None):
  template_values = template_values or {}
  tpl = template.loader.get_template(template_name)
  return tpl.render(template_values)


def RequestsCacheSession():
  return requests_cache.CachedSession(
      str(settings.DB_DIR / 'requests_cache'), extension='.db',
      expire_after=datetime.timedelta(days=2))


def SoupTagOnly(tag):
  return str(tag).split('>')[0] + '>'


def Strip(tag, reason=None):
  if settings.DEBUG:
    tag['style'] = 'outline: 2px dotted red'
    if reason: tag['strip_reason'] = reason
  else:
    tag.extract()


def TagSize(tag):
  if tag.has_attr('width') and tag.has_attr('height'):
    w = tag['width']
    h = tag['height']
  elif tag.has_attr('style'):
    try:
      w = re.search(r'width:\s*(\d+)px', tag['style']).group(1)
      h = re.search(r'height:\s*(\d+)px', tag['style']).group(1)
    except AttributeError:
      return None
  else:
    return None

  if w == '100%': w = 600
  if h == '100%': h = 400

  return w, h
