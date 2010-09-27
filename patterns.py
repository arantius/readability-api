#!/usr/bin/env python
"""Pattern-based heuristics for BeautifulSoup objects.

Applies positive/negative scores to identify content, and completely removes
notes that are known to be unwanted.

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
import re

import util


def _ReAny(pattern):
  return re.compile(pattern, re.I)


def _ReWhole(pattern):
  return re.compile(r'(^|!!!)%s($|!!!)' % pattern, re.I)


def _ReWord(pattern):
  return re.compile(r'(_|\b)%s(_|\b)' % pattern, re.I)

ATTR_POINTS = (
    (-20, 'classid', _ReAny(r'facebook')),
    (-20, 'classid', _ReWord(r'ad(block)?')),
    (-20, 'classid', _ReWord(r'author')),
    (-20, 'classid', _ReWord(r'bottom')),
    (-20, 'classid', _ReWord(r'delicious')),
    (-20, 'classid', _ReWord(r'featured')),
    (-20, 'classid', _ReWord(r'meta')),
    (-20, 'classid', _ReWord(r'module')),
    (-20, 'classid', _ReWord(r'post-meta')),
    (-20, 'classid', _ReWord(r'widget')),
    (-15, 'classid', _ReWord(r'twitter')),
    (-10, 'classid', _ReWord(r'print')),
    (1, 'classid', _ReWord(r'container')),
    (1, 'classid', _ReWord(r'main')),
    (5, 'classid', _ReWord(r'body')),
    (5, 'classid', _ReWord(r'content')),
    (5, 'classid', _ReWord(r'single')),
    (10, 'classid', _ReWhole(r'main')),
    (10, 'classid', _ReWord(r'player')),
    (20, 'classid', _ReAny(r'^article_?body')),
    (20, 'classid', _ReWhole(r'(story)?body')),
    (20, 'classid', _ReWhole(r'page')),
    (20, 'classid', _ReWhole(r'permalink')),
    (20, 'classid', _ReWhole(r'player')),
    (20, 'classid', _ReWhole(r'story')),
    (20, 'classid', _ReWord(r'post(id)?[-_]?(\d+|body|content)')),
    (20, 'classid', _ReWord(r'h?entry(?!-title)')),
    (20, 'classid', _ReWord(r'text')),
    )
ATTR_STRIP = (
    # any '^topic' broke cracked.com
    ('classid', _ReAny(r'add(this|toany)')),
    ('classid', _ReAny(r'comment')),
    ('classid', _ReAny(r'functions')),
    ('classid', _ReAny(r'popular')),
    ('classid', _ReAny(r'share(box|this)')),
    ('classid', _ReAny(r'socia(ble|l)')),
    ('classid', _ReAny(r'tool(box|s)')),

    ('classid', _ReWord(r'postmetadata')),

    ('classid', _ReWhole(r'author_info')),
    ('classid', _ReWhole(r'blippr-nobr')),
    ('classid', _ReWhole(r'byline')),
    ('classid', _ReWhole(r'more_stories')),
    ('classid', _ReWhole(r'pagination')),
    ('classid', _ReWhole(r'post(-info|ed_on)')),
    ('classid', _ReWhole(r'prevnext')),
    ('classid', _ReWhole(r'recent-posts')),
    ('classid', _ReWhole(r'respond')),
    ('classid', _ReWhole(r'share')),

    # tumblr comments
    ('classid', _ReWhole(r'notes(-container)?')),
    ('classid', _ReWhole(r'post-notes')),

    # word 'share' breaks twitter
    # word 'head(er)?' breaks some sites that put _all_ content there
    ('classid', _ReWord(r'ads?')),
    ('classid', _ReWord(r'categor(ies|y)')),
    ('classid', _ReWord(r'cnn_stry(btmcntnt|btntoolsbottom|cbftrtxt|lctcqrelt)')),
    ('classid', _ReWord(r'foot(er)?')),
    ('classid', _ReWord(r'hid(den|e)')),
    ('classid', _ReWord(r'inset')),
    ('classid', _ReWord(r'nav')),
    ('classid', _ReWord(r'post_share')),
    #('classid', _ReWord(r'print')),  # too much
    ('classid', _ReWord(r'related\d*')),
    ('classid', _ReWord(r'sidebar')),
    ('classid', _ReWord(r'tag(ged|s)')),
    ('classid', _ReWord(r'talkback')),

    ('href', _ReAny(r'(delicious\.com|del\.icio\.us)/post')),
    ('href', _ReAny(r'(digg|reddit|stumbleupon)\.com/submit')),
    ('href', _ReAny(r'(facebook|linkedin)\.com/share')),
    ('href', _ReAny(r'(newsvine|yahoo)\.com/buzz')),
    ('href', _ReAny(r'^javascript:')),
    ('href', _ReAny(r'addtoany\.com')),
    ('href', _ReAny(r'api\.tweetmeme\.com')),
    ('href', _ReAny(r'fusion\.google\.com/add')),
    ('href', _ReAny(r'twitter\.com/home\?status')),
    ('href', _ReWord(r'share')),
    ('href', _ReWord(r'sponsor')),

    ('src', _ReAny(r'reddit\.com')),
    ('src', _ReAny(r'stumbleupon\.com')),

    ('style', _ReAny(r'display\s*:\s*none')),

    # Feed tracking noise.
    ('href', _ReAny(r'^https?://feed[^/]+/(~.{1,3}|1\.0)/')),
    ('src', _ReAny(r'^https?://feed[^/]+/(~.{1,3}|1\.0)/')),
    )
STRIP_TAGS = ('form', 'iframe', 'link', 'meta', 'noscript', 'script', 'style')


def _Score(tag):
  for points, attr, pattern in ATTR_POINTS:
    if not tag.has_key(attr): continue
    if pattern.search(tag[attr]):
      util.ApplyScore(tag, points, name=attr)


def _Strip(tag):
  if tag.has_key('score') and tag['score'] > 0:
    # Do not strip positively-scored tags.
    return False

  if tag.name in STRIP_TAGS:
    tag.extract()
    return True

  for attr, pattern in ATTR_STRIP:
    if not tag.has_key(attr): continue
    if pattern.search(tag[attr]):
      if util.IS_DEV_APPSERVER:
        logging.info('Strip for %s: %s', attr, util.SoupTagOnly(tag))
      tag.extract()
      return True
  return False


def Process(soup):
  """Process an entire soup, without recursing into stripped nodes."""
  # Make a single "class and id" attribute that everything else can test.
  soup['classid'] = '!!!'.join([soup.get('class', '').strip(),
                                soup.get('id', '').strip()])

  _Score(soup)
  if _Strip(soup): return
  for tag in soup.findAll(True, recursive=False):
    Process(tag)
