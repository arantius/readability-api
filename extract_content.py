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

import HTMLParser
import logging
import re
import sys
import urlparse

from third_party import BeautifulSoup

import util

logging.basicConfig(level=logging.DEBUG)

BLOCK_TAG_NAMES = set((
    'blockquote', 'dl', 'div', 'ol', 'p', 'pre', 'table', 'ul',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    ))
DEV_FLAG = True
MAX_SCORE_DEPTH = 5
RE_DISPLAY_NONE = re.compile(r'display\s*:\s*none', re.I)
RE_DOUBLE_BR = re.compile(r'<br[ /]*>\s*<br[ /]*>', re.I)
RE_CLASS_ID_STRIP = re.compile(
    r'addtoany'
    r'|(_|\b)comment'
    r'|disqus_thread|dsq-brlink'
    r'|fb-like'
    r'|(_|\b)foot'
    r'|(_|\b)(sub)?head'
    r'|(_|\b)hid(den|e)(_|\b)'
    r'|(_|\b)nav'
    r'|(_|\b)neighbor'
    r'|(_|\b)read-more'
    r'|(_|\b)recent-post'
    r'|(_|\b)related'
    r'|(_|\b)shar(e|ing)'
    r'|(_|\b)side'
    r'|share'
    r'|social'
    r'|sponsor'
    r'|tool(box)?s?\d?(_|\b)'
    r'|twitter'
    r'|widget',
    re.I)
RE_CLASS_ID_POSITIVE = re.compile(
    r'article|artTe?xt|body|content|entry|post|snap_preview|story|text', re.I)
STRIP_TAG_NAMES = set((
    'iframe',
    'link',
    'meta',
    'noscript',
    'script',
    'style',
    ))
TAG_BASE_SCORES = {
    'p': 5.0,
    'div': 1.5,
    'td': 1.0,
    }
TAG_BASE_SCORE_MAX = max(TAG_BASE_SCORES.values())


def ExtractFromUrl(url):
  url = url.encode('utf-8')
  try:
    html, _ = util.Fetch(url)
    return ExtractFromHtml(url, html)
  except IOError, e:
    logging.exception(e)
    return ''


def ExtractFromHtml(url, html):
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

  _StripUnwanted(soup)

  # Transform "text-only" (doesn't contain blocks) <div>s to <p>s.
  for tag in soup.findAll('div'):
    if not tag.find(BLOCK_TAG_NAMES):
      tag.name = 'p'

  # Count score for all ancestors-of-paragraphs.
  parents = []
  for container in soup.findAll(TAG_BASE_SCORES):
    # Skip e.g. divs with nested divs.  We'll consider the nested one directly,
    # so skip to avoid double-counting.
    if container.find(container.name):
      continue

    # Score each parent-of-containers once.
    parent = container.parent
    if parent not in parents:
      parents.append(parent)
      base_score = TAG_BASE_SCORES[container.name]
      _ApplyScore(parent, _ScoreForParent(parent, base_score))

    _ApplyScore(parent, container.text.count(',') * 3)

  top_parent = None
  for parent in soup.findAll(attrs={'score': True}):
    if (not top_parent) or (parent['score'] > top_parent['score']):
      top_parent = parent

  if DEV_FLAG:
    for parent in sorted(soup.findAll(attrs={'score': True}),
                         key=lambda x: x['score']):
      logging.info('%10.2f %s', parent['score'], util.SoupTagOnly(parent))

  if not top_parent:
    return ''

  # Strip pieces with negative scores here?

  _FixUrls(top_parent, url)

  return top_parent.renderContents()


def _FixUrls(parent, base_url):
  for tag in parent.findAll():
    if tag.has_key('href'):
      tag['href'] = urlparse.urljoin(base_url, tag['href'])
    if tag.has_key('src'):
      tag['src'] = urlparse.urljoin(base_url, tag['src'])


def _ScoreForParent(parent, base_score):
  score = 0
  # Add points for certain id and class values.
  if util.IdOrClassMatches(parent, RE_CLASS_ID_POSITIVE):
    # If this parent's siblings also have an interesting id/class,
    # don't score it well because of the match -- it's probably a false
    # positive among a group of them.
    siblings = (parent.findPreviousSiblings(name=True, limit=1)
                + parent.findNextSiblings(name=True, limit=1))
    sibling_matches = [util.IdOrClassMatches(s, RE_CLASS_ID_POSITIVE)
                       for s in siblings]
    if not filter(None, sibling_matches):
      score += base_score * 20

  # Remove points for links, especially those in lists.
  for link in parent.findAll('a'):
    score -= TAG_BASE_SCORE_MAX / base_score
    try:
      if link.findParents('li')[0].findParents('ul')[0]:
        score -= TAG_BASE_SCORE_MAX
    except IndexError:
      # Item did not exist.
      pass

  # Remove points for previous nodes, earlier = lose fewer points; break ties.
  score -= len(parent.findAllPrevious(True)) / 2

  return score


def _StripUnwanted(soup):
  """Breadth-first recursively strip unwanted tags out of the soup."""
  for tag in soup.findAll(_UnwantedTag, recursive=False):
    if DEV_FLAG:
      logging.info('Stripped unwanted tag: %s', util.SoupTagOnly(tag))
    tag.extract()
  for tag in soup.findAll(recursive=False):
    _StripUnwanted(tag)


def _ApplyScore(tag, score, depth=0):
  """Recursively apply a decaying score to each parent up the tree."""
  if not tag:
    return
  if (tag.name == 'body') and (depth > 0):
    return
  if depth > MAX_SCORE_DEPTH:
    return
  # Let me put spaces where I want them: pylint: disable-msg=C6007
  decayed_score = score * ( ( 1 - (depth / float(MAX_SCORE_DEPTH)) ) ** 2.5 )
  if not tag.has_key('score'):
    tag['score'] = 0
  tag['score'] = float(tag['score']) + decayed_score
  _ApplyScore(tag.parent, score, depth + 1)


def _UnwantedTag(tag):
  """Given a soup tag, filter out (return False for) tags to be stripped."""
  if tag.name == 'form':
    if tag.has_key('id') and (tag['id'] == 'aspnetForm'):
      return False
    if tag.has_key('name') and (tag['name'] == 'aspnetForm'):
      return False
    return True
  if tag.name in STRIP_TAG_NAMES:
    return True
  if util.IdOrClassMatches(tag, RE_CLASS_ID_STRIP):
    return True
  if tag.has_key('style') and RE_DISPLAY_NONE.search(tag['style']):
    return True
  return False


if __name__ == '__main__':
  # For debugging, assume file on command line.
  print ExtractFromHtml('http://www.example.com', open(sys.argv[1]).read())
