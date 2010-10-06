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
    (-20, 'classid', _ReWord(r'delicious')),
    (-20, 'classid', _ReWord(r'featured?')),
    (-20, 'classid', _ReWord(r'meta')),
    (-20, 'classid', _ReWord(r'module')),
    (-20, 'classid', _ReWord(r'post-(meta|ratings)')),
    (-20, 'classid', _ReWord(r'widget')),
    (-20, 'classid', _ReWhole(r'post_(\d+_)?info')),
    (-15, 'classid', _ReAny(r'comment')),
    (-15, 'classid', _ReWord(r'twitter')),
    (-10, 'classid', _ReWord(r'print')),
    (-10, 'classid', _ReWord(r'topics?')),
    (-5, 'classid', _ReAny(r'menu')),
    (-5, 'classid', _ReAny(r'socia(ble|l)')),
    (-5, 'classid', _ReWord(r'bottom')),
    (-5, 'classid', _ReWord(r'links')),
    (-2, 'classid', _ReAny(r'right')),
    (1, 'classid', _ReWord(r'container')),
    (1, 'classid', _ReWord(r'main')),
    (2, 'classid', _ReWord(r'text')),
    (5, 'classid', _ReWhole(r'permalink')),
    (5, 'classid', _ReWhole(r'main')),
    (5, 'classid', _ReWord(r'body(text)?')),
    (5, 'classid', _ReWord(r'content')),
    (5, 'classid', _ReWord(r'single')),
    (10, 'classid', _ReAny(r'^article_?body')),
    (10, 'classid', _ReWhole(r'story')),
    (10, 'classid', _ReWord(r'article(?!_tool)')),
    (10, 'classid', _ReWord(r'h?entry(?!-title)')),
    (10, 'classid', _ReWord(r'player')),
    (10, 'classid', _ReWord(r'post(id)?[-_]?(\d+|body|content)?')),
    (10, 'classid', _ReWord(r'snap_preview')),
    (10, 'classid', _ReWord(r'video')),
    (10, 'classid', _ReWord(r'wide')),
    (10, 'classid', _ReWhole(r'post-\d+')),
    (20, 'classid', _ReWhole(r'large-image')),  # imgur.com
    (20, 'classid', _ReWhole(r'story(body|block)')),
    (20, 'classid', _ReWhole(r'page')),
    (20, 'classid', _ReWhole(r'player')),
    )
ATTR_STRIP = (
    # any '^topic' broke cracked.com
    ('classid', _ReAny(r'add(this|toany)')),
    ('classid', _ReAny(r'comment')),
    ('classid', _ReAny(r'functions')),
    ('classid', _ReAny(r'popular')),
    ('classid', _ReAny(r'share(bar|box|this)')),
    ('classid', _ReAny(r'(controls?|tool)(box|s)')),

    ('classid', _ReWord(r'ad(block|tag)?')),
    ('classid', _ReWord(r'(post)?author')),
    ('classid', _ReWord(r'postmetadata')),
    ('classid', _ReWord(r'replies')),
    ('classid', _ReWord(r'shopbox')),
    ('classid', _ReWord(r'snap_nopreview')),
    ('classid', _ReWord(r'wdt_button')),

    ('classid', _ReWhole(r'a(uthor_)?info')),
    ('classid', _ReWhole(r'blippr-nobr')),
    ('classid', _ReWhole(r'byline')),
    ('classid', _ReWhole(r'facebook-like')),
    ('classid', _ReWhole(r'more_stories')),
    ('classid', _ReWhole(r'pagination')),
    ('classid', _ReWhole(r'post(-info|ed_on|edby)')),
    ('classid', _ReWhole(r'post_(\d+_)?info')),
    ('classid', _ReWhole(r'prevnext')),
    ('classid', _ReWhole(r'recent-posts')),
    ('classid', _ReWhole(r'respond')),
    ('classid', _ReWhole(r'rightrail')),
    ('classid', _ReWhole(r'share')),
    ('classid', _ReWhole(r'sidebar\d*')),  # word matches too much

    # tumblr comments
    ('classid', _ReWhole(r'notes(-container)?')),
    ('classid', _ReWhole(r'post-notes')),

    # word 'share' breaks twitter
    # word 'head(er)?' breaks some sites that put _all_ content there
    ('classid', _ReWord(r'ads?')),
    ('classid', _ReWord(r'(in)?categor(ies|y)')),
    ('classid', _ReWord(r'cnn_stry(btmcntnt|btntoolsbottom|cbftrtxt|lctcqrelt)')),
    ('classid', _ReWord(r'cnn(_ftrcntnt|Footer)')),
    ('classid', _ReWord(r'foot(er)?')),
    ('classid', _ReWord(r'hid(den|e)')),
    ('classid', _ReWord(r'inset')),
    ('classid', _ReWord(r'post-labels?')),
    ('classid', _ReWord(r'(left|right)?nav(igation)?')),
    ('classid', _ReWord(r'post_share')),
    #('classid', _ReWord(r'print')),  # too much
    ('classid', _ReWord(r'related\d*')),
    ('classid', _ReWord(r'tag(ged|s)')),
    ('classid', _ReWord(r'talkback')),

    ('href', _ReAny(r'(delicious\.com|del\.icio\.us)/post')),
    ('href', _ReAny(r'(digg|reddit|stumbleupon)\.com/submit')),
    ('href', _ReAny(r'(facebook|linkedin)\.com/share')),
    ('href', _ReAny(r'(newsvine|yahoo)\.com/buzz')),
    ('href', _ReAny(r'^javascript:')),
    ('href', _ReAny(r'addtoany\.com')),
    ('href', _ReAny(r'api\.tweetmeme\.com')),
    ('href', _ReAny(r'digg.com/tools/diggthis')),
    ('href', _ReAny(r'fusion\.google\.com/add')),
    ('href', _ReAny(r'google.com/reader/link')),
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
RE_RELATED_HEADER = re.compile(
    r'\b('
    r'for more'
    r'|more.*(coverage|resources)'
    r'|most popular'
    r'|read more'
    r'|related (articles?|entries|posts?)'
    r'|see also'
    r'|suggested links'
    r')\b'
    r'|more\.\.\.', re.I)
STRIP_TAGS = ('form', 'iframe', 'link', 'meta', 'noscript', 'script', 'style',
              'fb:share-button')


def _IsList(tag):
  if tag.name == 'ul': return True
  if tag.name == 'ol': return True
  if 'blockquote' == tag.name:
    if re.search(r'(<br.*?> - .*){2,}', unicode(tag)):
      return True
  return False


def _Score(tag):
  for points, attr, pattern in ATTR_POINTS:
    if not tag.has_key(attr): continue
    if pattern.search(tag[attr]):
      util.ApplyScore(tag, points, name=attr)


def _Strip(tag):
  # Seen: wanted to strip "post-labels" but it has score 5.
  if tag.has_key('score') and tag['score'] > 0:
    # Do not strip positively-scored tags.
    return False

  if tag.name in STRIP_TAGS:
    if tag.name == 'form' and 'aspnetForm' in [attr[1] for attr in tag.attrs]:
      return False
    tag.extract()
    return True

  # Strip "related" lists.
  if _IsList(tag):
    previous = tag.findPreviousSibling(True)
    search_text = ''
    if previous:
      if previous.name == 'hr':
        previous = previous.findPreviousSibling(True)
      search_text = previous.getText(separator=u' ')
      strip_node = previous
    elif tag.parent:
      search_text = tag.parent.getText(separator=u' ')
      strip_node = tag.parent
    # Too-long text means this must not be a header, false positive!
    if len(search_text) < 100:
      if RE_RELATED_HEADER.search(search_text):
        _StripAfter(strip_node)
        return True


  for attr, pattern in ATTR_STRIP:
    if not tag.has_key(attr): continue
    if pattern.search(tag[attr]):
      if util.IS_DEV_APPSERVER:
        logging.info('Strip for %s: %s', attr, util.SoupTagOnly(tag))
      tag.extract()
      return True
  return False


def _StripAfter(strip_tag):
  if util.IS_DEV_APPSERVER:
    logging.info('Strip after: %s', util.SoupTagOnly(strip_tag))
  for tag in strip_tag.findAllNext():
    tag.extract()
  strip_tag.extract()


def Process(soup):
  """Process an entire soup, without recursing into stripped nodes."""
  # Make a single "class and id" attribute that everything else can test.
  soup['classid'] = '!!!'.join([soup.get('class', '').strip(),
                                soup.get('id', '').strip()]).strip('!')

  _Score(soup)
  if _Strip(soup): return
  for tag in soup.findAll(True, recursive=False):
    Process(tag)
