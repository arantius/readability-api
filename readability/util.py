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

import http.cookies
import io
import functools
import logging
import os
import re
import urllib.parse

from django import template
import requests

import bs4
import feedparser

from readability import settings


DEBUG = settings.DEBUG
EMBED_NAMES = set(('embed', 'object'))
RE_CNN_HACK = re.compile(r'<!-- with(out)? htc -->')
RE_DOCTYPE = re.compile(r'<!DOCTYPE.*?>', re.S)
TAG_NAMES_BLOCK = set(('blockquote', 'div', 'li', 'p', 'pre', 'td', 'th'))
TAG_NAMES_HEADER = set(('h1', 'h2', 'h3', 'h4', 'h5', 'h6'))

BR_TO_P_STOP_TAGS = set(list(TAG_NAMES_BLOCK) + list(TAG_NAMES_HEADER) + ['br'])

MAX_SCORE_DEPTH = 5
_DEPTH_SCORE_DECAY = [(1 - d / 12.0) ** 5 for d in range(MAX_SCORE_DEPTH + 1)]

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


def Fetch(orig_url, deadline=6):
  cookie = http.cookies.SimpleCookie()
  redirect_limit = 10
  redirects = 0
  url = orig_url
  while url and redirects < redirect_limit:
    redirects += 1
    url = CleanUrl(url)
    if settings.DEBUG:
      logging.info('Fetching: %s', url)
    final_url = url
    response = requests.get(
        url,
        #, allow_truncated=True, follow_redirects=False, deadline=deadline,
        headers={
          'Cookie': cookie.output(attrs=(), header='', sep='; '),
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        })
    try:
      cookie.load(response.headers.get('Set-Cookie', ''))
    except cookie.CookieError:
      logging.exception('Ignoring cookie problem!')
    previous_url = url
    url = response.headers.get('Location')
    if url:
      url = urllib.parse.urljoin(previous_url, url)
  final_url = urllib.parse.urljoin(orig_url, final_url)
  return (response, final_url)


def FindEmbeds(root_tag):
  if root_tag.name in EMBED_NAMES:
    yield root_tag
  for tag in root_tag.findAll(EMBED_NAMES):
    if tag.findParent(EMBED_NAMES):
      continue
    yield tag


def GetFeedEntryContent(entry):
  """Figure out the best content for this entry."""
  # Prefer "content".
  if 'content' in entry:
    # If there's only one, use it.
    if len(entry.content) == 1:
      return entry.content[0]['value']
    # Or, use the text/html type if there's more than one.
    for content in entry.content:
      if (content.has_attr('type')) and ('text/html' == content.type):
        return content['value']
  # Otherwise try "summary_detail" and "summary".
  if 'summary_detail' in entry:
    return entry.summary_detail['value']
  if 'summary' in entry:
    return entry.summary
  return ''


def OEmbedFixup(soup):
  oembed_links = soup.findAll(
      'a', {'onclick': re.compile(r'^oEmbedManagerVideoLoader')})
  for oembed_link in oembed_links:
    cont = oembed_link.parent
    embed = cont.find('iframe')
    if not embed:
      ta = cont.find('textarea')
      if not ta: return
      s = bs4.BeautifulSoup(ta.text, 'html.parser')
      embed = s.find('iframe')
    embed['src'] = re.sub(r'\?.*', '', embed['src'])
    div = bs4.Tag(soup, 'div')
    div.insert(0, embed)
    cont.replaceWith(div)


def ParseFeedAtUrl(url):
  """Fetch a URL's contents, and parse it as a feed."""
  response, _ = Fetch(url, deadline=20)
  try:
    feed_feedparser = feedparser.parse(response.text)
  except LookupError:
    return None
  else:
    return feed_feedparser


def PreCleanHtml(html):
  html = re.sub(RE_DOCTYPE, '', html)
  html = html.replace('&nbsp;', ' ')
  return html


def PreCleanSoup(soup):
  CommentStrip(soup)
  SwfObjectFixup(soup)
  OEmbedFixup(soup)


def RenderTemplate(template_name, template_values=None):
  template_values = template_values or {}
  template_file = os.path.join(
      os.path.dirname(__file__), 'templates', template_name)
  return template.render(template_file, template_values)


def SoupTagOnly(tag):
  return str(tag).split('>')[0] + '>'


def Strip(tag, reason=None):
  # Switch this for dev.
  if 1:
    tag['style'] = 'outline: 2px dotted red'
    if reason: tag['strip_reason'] = reason
  else:
    tag.extract()


def SwfObjectFixup(soup):
  # SWFObject 1 style
  script_txts = soup.findAll(
      'script_txt', text=re.compile(r'\bnew SWFObject\b'))
  for script_txt in script_txts:
    m = re.search(r'new\s+SWFObject.*?\((.*)\)', str(script_txt))
    src, name, width, height, _, bgcolor = [
        x for _, x in re.findall(r"""(['"])(.*?)\1""", m.group(1))]
    embed = bs4.Tag(soup, 'embed')
    embed['src'] = src
    embed['name'] = name
    embed['width'] = width
    embed['height'] = height
    embed['bgcolor'] = bgcolor
    for m in re.findall(
        r"""\.\s*addParam\s*\(\s*(['"])(.*)\1\s*,\s*(['"])(.*)\3\s*\)""",
        str(script_txt)):
      embed[m[1]] = m[3]
    script_txt.parent.replaceWith(embed)


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
