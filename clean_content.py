#!/usr/bin/env python
"""Originally "Hacker News" feed rewriter by Nirmal Patel.

Now: General purpose "page cleaner".  Given the *content* of a page, at a URL,
attempts to convert it into the smallest subset of markup that contains the
entire body of important content.

Original license text:

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

# Use default membership test instead of 'has_key'
# pylint: disable-msg=C6401
# -- this doesn't work with BeautifulSoup objects.  Disable check.

# Standard library imports.
import HTMLParser
import logging
import re
import sys
import urlparse

# Packaged third-party imports.
from third_party import BeautifulSoup

import util

logging.basicConfig(level=logging.DEBUG)

BLOCK_TAG_NAMES = set((
    'blockquote', 'dl', 'div', 'ol', 'p', 'pre', 'table', 'ul',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    ))
RE_DISPLAY_NONE = re.compile(r'display\s*:\s*none', re.I)
RE_DOUBLE_BR = re.compile(r'<br[ /]*>\s*<br[ /]*>', re.I)
RE_NEGATIVE = re.compile(
    r'(_|\b)comment'
    r'|disqus_thread|dsq-brlink'
    r'|(_|\b)foot'
    r'|(_|\b)(sub)?head'
    r'|(_|\b)hid(den|e)(_|\b)'
    r'|(_|\b)nav'
    r'|(_|\b)neighbor'
    r'|(_|\b)read-more'
    r'|(_|\b)related'
    r'|(_|\b)shar(e|ing)'
    r'|(_|\b)side'
    r'|sponsor'
    r'|twitter'
    r'|widget',
    re.I)
RE_POSITIVE = re.compile(r'article|body|content|entry|post|text', re.I)
STRIP_ATTRS = set((
    'class',
    'id',
    'onblur',
    'onchange ',
    'onclick',
    'ondblclick',
    'onfocus',
    'onkeydown',
    'onkeypress',
    'onkeyup',
    'onload',
    'onmousedown',
    'onmousemove',
    'onmouseout',
    'onmouseover',
    'onmouseup',
    'onreset',
    'onselect',
    'onsubmit',
    'onunload',
    'style',
    ))
STRIP_TAG_NAMES = set((
    'head',
    'iframe',
    'link',
    'meta',
    'noscript',
    'script',
    'style',
    ))


def CleanUrl(url):
  url = url.encode('utf-8')
  try:
    html, _ = util.Fetch(url)
    return CleanContent(url, html)
  except IOError, e:
    logging.exception(e)
    return ''


def CleanContent(url, html):
  """Given a string of HTML, remove nasty bits, score and pick bit to keep."""
  # Remove all HTML comments.
  html = re.sub(r'<!--.*?-->', '', html)
  # Turn double-linebreaks into faked-up paragraphs before parsing.
  html = re.sub(RE_DOUBLE_BR, '</p><p>', html)

  try:
    soup = BeautifulSoup.BeautifulSoup(html)
  except HTMLParser.HTMLParseError, e:
    logging.exception(e)
    return ''

  # Strip all these tags before any other processing.
  def UnwantedTag(tag):
    if tag.name == 'form':
      if tag.has_key('id') and (tag['id'] == 'aspnetForm'):
        return False
      if tag.has_key('name') and (tag['name'] == 'aspnetForm'):
        return False
      return True
    if tag.name in STRIP_TAG_NAMES:
      return True
    if tag.has_key('class') and RE_NEGATIVE.search(tag['class']):
      return True
    if tag.has_key('id') and RE_NEGATIVE.search(tag['id']):
      return True
    if tag.has_key('style') and RE_DISPLAY_NONE.search(tag['style']):
      return True
    return False
  for tag in soup.findAll(UnwantedTag):
    tag.extract()

  # Transform "text-only" (doesn't contain blocks) <div>s to <p>s.
  for tag in soup.findAll('div'):
    if not tag.find(BLOCK_TAG_NAMES):
      tag.name = 'p'

  # Count score for all ancestors-of-paragraphs.
  parents = []
  parent_scores = {
      'p': 5.0,
      'div': 1.5,
      'td': 1.0,
      }
  for container in soup.findAll(parent_scores):
    # Skip e.g. divs with nested divs.  We'll consider the nested one directly,
    # so skip to avoid double-counting.
    if container.find(container.name):
      continue
    parent = container.parent
    score = 0
    if parent not in parents:
      parents.append(parent)
      base_score = parent_scores[container.name]
      id_class = parent.get('id', '') + ' ' + parent.get('class', '')
      if RE_POSITIVE.search(id_class):
        score += base_score * 10
      _ApplyScore(parent, score)

    if len(container.text) > 20:
      _ApplyScore(parent, base_score)
    _ApplyScore(parent, container.text.count(',') * base_score)

  top_parent = None
  for parent in soup.findAll(attrs={'score': True}):
    if (not top_parent) or (parent['score'] > top_parent['score']):
      top_parent = parent

#  for parent in sorted(soup.findAll(attrs={'score': True}),
#                       key=lambda x: x['score'])[-5:]:
#    logging.info('%10.2f %s', parent['score'], util.SoupTagOnly(parent))
#    #logging.info(parent.text[0:59])

  if not top_parent:
    return ''

  # Remove unwanted attributes from all tags (e.g. events, styles).
  for tag in soup.findAll(True):
    for attr in STRIP_ATTRS:
      del tag[attr]

  _FixUrls(top_parent, url)

  return top_parent.renderContents()


def _ApplyScore(tag, score, depth=0):
  """Recursively apply a decaying score to each parent up the tree."""
  if not tag:
    return
  if (tag.name == 'body') and (depth > 0):
    return
  decayed_score = score * ( ( 1 - (depth / float(5)) ) ** 2.5 )
  if decayed_score < 1:
    return
  if not tag.has_key('score'):
    tag['score'] = 0
  tag['score'] = float(tag['score']) + decayed_score
  _ApplyScore(tag.parent, score, depth + 1)  # TODO: Remove magic number.


def _FixUrls(parent, base_url):
  for tag in parent.findAll():
    if tag.has_key('href'):
      tag['href'] = urlparse.urljoin(base_url, tag['href'])
    if tag.has_key('src'):
      tag['src'] = urlparse.urljoin(base_url, tag['src'])


if __name__ == '__main__':
  # For debugging, assume file on command line.
  print CleanContent('http://www.example.com', open(sys.argv[1]).read())
