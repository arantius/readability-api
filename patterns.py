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
import urllib
import urlparse

import util

# If one pattern matched this many tags, consider it a false positive, and
# subtract its points back out.
FALSE_POSITIVE_THRESHOLD = 5

def _ReAny(pattern):
  return re.compile(pattern, re.I)


def _ReWhole(pattern):
  return re.compile(r'(^|!!!)%s($|!!!)' % pattern, re.I)


def _ReWord(pattern):
  return re.compile(r'(_|\b)%s(_|\b)' % pattern, re.I)

ATTR_POINTS = (
    (-20, 'classid', _ReWord(r'delicious')),
    (-20, 'classid', _ReWord(r'featured?')),
    (-20, 'classid', _ReWord(r'post-(details|label|meta|ratings)')),
    (-20, 'classid', _ReWord(r'widget')),
    (-15, 'classid', _ReWhole(r'side')),
    (-15, 'classid', _ReWord(r'email')),
    (-15, 'classid', _ReWord(r'twitter')),
    (-10, 'classid', _ReWord(r'ghost')),
    (-10, 'classid', _ReWord(r'overlay')),
    (-10, 'classid', _ReWord(r'print')),
    (-10, 'classid', _ReWord(r'topics?')),
    (-5, 'classid', _ReAny(r'menu')),
    (-5, 'classid', _ReAny(r'social')),
    (-5, 'classid', _ReWord(r'(?<!padding-)bottom')),
    (-5, 'classid', _ReWord(r'footer')),
    (-5, 'classid', _ReWord(r'hotspot')),  # tmz
    (-5, 'classid', _ReWord(r'icons')),
    (-5, 'classid', _ReWord(r'lightbox')),
    (-5, 'classid', _ReWord(r'links')),
    (-5, 'classid', _ReWord(r'meta(data)?')),
    (-5, 'classid', _ReWord(r'more')),
    (-5, 'classid', _ReWord(r'post-date')),
    (-3, 'classid', _ReAny(r'embed')),  # usually "embed this" code
    (1, 'classid', _ReWord(r'main')),
    (2, 'classid', _ReWord(r'text')),
    (4, 'classid', _ReWord(r'article(?!_tool)')),
    (5, 'classid', _ReAny(r'^article')),
    (5, 'classid', _ReAny(r'gallery')),
    (5, 'classid', _ReAny(r'photo')),
    (5, 'classid', _ReWhole(r'main')),
    (5, 'classid', _ReWhole(r'permalink')),
    (5, 'classid', _ReWhole(r'page')),
    (5, 'classid', _ReWord(r'body(text)?')),
    (5, 'classid', _ReWord(r'content')),
    (5, 'classid', _ReWord(r'primary-column')),
    (5, 'classid', _ReWord(r'single')),
    (10, 'classid', _ReAny(r'^article_?body')),
    (10, 'classid', _ReWhole(r'story')),
    (10, 'classid', _ReWord(r'player')),
    (10, 'classid', _ReWord(r'post(id)?[-_]?(\d+|body|content)?')),
    (10, 'classid', _ReWord(r'snap_preview')),
    (10, 'classid', _ReWord(r'video')),
    (10, 'classid', _ReWord(r'wide')),
    (10, 'classid', _ReWhole(r'meat')),
    (10, 'classid', _ReWhole(r'post(-\d+)?')),
    (12, 'classid', _ReWhole(r'article span image')),  # nytimes
    (12, 'classid', _ReWord(r'h?entry(?!-title)')),
    (20, 'classid', _ReWhole(r'large-image')),  # imgur.com
    (20, 'classid', _ReWhole(r'story(body|block)')),
    (20, 'classid', _ReWhole(r'player')),
    )
ATTR_STRIP = (
    # any '^topic' broke cracked.com
    ('classid', _ReAny(r'adsense')),
    ('classid', _ReAny(r'add(this|toany)')),
    ('classid', _ReAny(r'comment')),
    ('classid', _ReAny(r'disqus')),
    ('classid', _ReAny(r'functions')),
    ('classid', _ReAny(r'popular')),
    ('classid', _ReAny(r'^post_(\d+_)?info')),
    ('classid', _ReAny(r'reportabuse')),
    ('classid', _ReAny(r'share(bar|box|this)')),
    ('classid', _ReAny(r'signin')),
    ('classid', _ReAny(r'(controls?|tool)(box|s)')),

    # word 'share' breaks twitter
    # word 'head(er)?' breaks some sites that put _all_ content there
    ('classid', _ReWord(r'(in)?categor(ies|y)')),
    ('classid', _ReWord(r'(left|right)?nav(igation)?')),
    ('classid', _ReWord(r'(post)?author|authdesc')),
    ('classid', _ReWord(r'ad(block|tag)')),
    ('classid', _ReWord(r'cnn(_ftrcntnt|Footer)')),
    ('classid', _ReWord(r'cnn_stry(btmcntnt|btntoolsbottom|cbftrtxt|lctcqrelt)')),
    ('classid', _ReWord(r'foot(er)?(feature)?')),
    ('classid', _ReWord(r'hid(den|e)')),
    ('classid', _ReWord(r'horizontal_posts')),  # mashable
    ('classid', _ReWord(r'icons')),
    ('classid', _ReWord(r'ilikethis')),
    ('classid', _ReWord(r'inset')),
    ('classid', _ReWord(r'metavalue')),
    ('classid', _ReWord(r'post-labels?')),
    ('classid', _ReWord(r'post_share')),
    ('classid', _ReWord(r'postmetadata')),
    ('classid', _ReWord(r'related\d*')),
    ('classid', _ReWord(r'replies')),
    ('classid', _ReWord(r'retweet')),
    ('classid', _ReWord(r'shopbox')),
    ('classid', _ReWord(r'snap_nopreview')),
    ('classid', _ReWord(r'social')),
    ('classid', _ReWord(r'tag(ged|s)')),
    ('classid', _ReWord(r'talkback')),
    ('classid', _ReWord(r'wdt_button')),

    ('classid', _ReWhole(r'ads?')),
    ('classid', _ReWhole(r'article inline runaround left')),  # nytimes junk
    ('classid', _ReWhole(r'a(uthor_)?info')),
    ('classid', _ReWhole(r'blippr-nobr')),
    ('classid', _ReWhole(r'breadcrumb')),
    ('classid', _ReWhole(r'byline')),
    ('classid', _ReWhole(r'catsandtags')),
    ('classid', _ReWhole(r'dontPrint')),
    ('classid', _ReWhole(r'facebook-like')),
    ('classid', _ReWhole(r'more_stories')),
    ('classid', _ReWhole(r'pagination')),
    ('classid', _ReWhole(r'post(-date|-info|ed_on|edby)')),
    ('classid', _ReWhole(r'prevnext')),
    ('classid', _ReWhole(r'previously\d?')),  # boing boing
    ('classid', _ReWhole(r'promoColumn')),
    ('classid', _ReWhole(r'(recent|related)-posts')),
    ('classid', _ReWhole(r'respon(d|ses)')),
    ('classid', _ReWhole(r'rightrail')),
    ('classid', _ReWhole(r'search(bar)?')),
    ('classid', _ReWhole(r'sexy-bookmarks')),
    ('classid', _ReWhole(r'share')),
    ('classid', _ReWhole(r'side(bar)?\d*')),  # word matches too much
    ('classid', _ReWhole(r'sociable')),
    ('classid', _ReWhole(r'story-date')),
    ('classid', _ReWhole(r'notes(-container)?')),  # tumblr comments
    ('classid', _ReWhole(r'post-(details|notes)')),

    ('href', _ReAny(r'(delicious\.com|del\.icio\.us)/post')),
    ('href', _ReAny(r'(digg|reddit|stumbleupon)\.com/submit')),
    ('href', _ReAny(r'(facebook|linkedin)\.com/share')),
    ('href', _ReAny(r'(newsvine|yahoo)\.com/buzz')),
    ('href', _ReAny(r'^javascript:')),
    ('href', _ReAny(r'add(this|toany)\.com')),
    ('href', _ReAny(r'api\.tweetmeme\.com')),
    ('href', _ReAny(r'digg\.com/tools/diggthis')),
    ('href', _ReAny(r'fusion\.google\.com/add')),
    ('href', _ReAny(r'google\.com/reader/link')),
    ('href', _ReAny(r'pheedo\.com')),
    ('href', _ReAny(r'twitter\.com/home\?status')),
    ('href', _ReWord(r'share')),
    ('href', _ReWord(r'sponsor')),

    ('src', _ReAny(r'invitemedia\.com')),
    ('src', _ReAny(r'quantserve\.com')),
    ('src', _ReAny(r'leenks\.com/webmasters')),
    ('src', _ReAny(r'reddit\.com')),
    ('src', _ReAny(r'stumbleupon\.com')),

    ('style', _ReAny(r'display\s*:\s*none')),

    # Feed tracking noise.
    ('href', _ReAny(r'^https?://feed[^/]+/(~.{1,3}|1\.0)/')),
    ('src', _ReAny(r'^https?://feed[^/]+/(~.{1,3}|1\.0)/')),
    )
RE_RELATED_HEADER = re.compile(
    r'\b('
    r'also on'
    r'|(for|read) more'
    r'|more.*(coverage|news|resources)'
    r'|most popular'
    r'|(popular|similar) (articles?|entries|posts?|stories)'
    r'|related'
    r'|see also'
    r'|suggested links'
    r')\b'
    r'|more\.\.\.', re.I)

DO_NOT_STRIP_TAGS = ('html', 'body')
STRIP_TAGS = ('form', 'iframe', 'link', 'meta', 'script', 'style',
              'fb:share-button')


def _CamelCaseToSpace(str):
  return re.sub('([a-z0-9])([A-Z])', r'\1 \2',
                re.sub('(.)([A-Z][a-z]+)', r'\1 \2', str)
               ).lower()

def _FindPreviousHeader(tag):
  # Find the "header" immediately previous to this tag.  Search among a few
  # possibilities for it.

  # If tag, and nothing else, is wrapped by e.g. a <div>, pop up.
  while len(tag.parent.findAll(name=True, recursive=False)) == 1:
    tag = tag.parent

  # First, try the immediately previous sibling node, skipping breaks.
  header = tag.findPreviousSibling(lambda tag: tag.name not in ('br', 'hr'))
  if header: return (header, header.getText(separator=u' '))

  # Otherwise, look for text just before this tag.
  header = tag.findPreviousSiblings(text=True)
  if header: return (header[0], header[0])

  return (None, '')


def _IsList(tag):
  if tag.name == 'ul': return True
  if tag.name == 'ol': return True
  if 'blockquote' == tag.name:
    if re.search(r'(<br.*?> - .*){2,}', unicode(tag)):
      return True
  if 'center' == tag.name:
    tags_links = tag.findAll(name='a', recursive=False)
    if tags_links and len(tags_links) >= 8:
      return True
  return False


def _Score(tag, url, hit_counter):
  if tag.name == 'body': return
  for points, attr, pattern in ATTR_POINTS:
    if not tag.has_key(attr): continue
    if pattern.search(tag[attr]):
      util.ApplyScore(tag, points, name=attr)

      key = (points, attr, pattern.pattern)
      hit_counter.setdefault(key, [])
      hit_counter[key].append(tag)

  if tag.name == 'a' and tag.has_key('href'):
    that_url = urlparse.urljoin(url, tag['href'])
    if url in that_url or url in urllib.unquote(tag['href']):
      # Special case: score down AND strip links to this page.  (Including
      # "social media" links.)
      util.ApplyScore(tag, -1.5, name='self_link')
      tag.extract()
    # TODO: host name -> domain name
    elif urlparse.urlparse(url)[1] == urlparse.urlparse(that_url)[1]:
      # Score up links to _other_ domains.
      util.ApplyScore(tag, 1.0, name='out_link')


def _Strip(tag):
  if tag.name in DO_NOT_STRIP_TAGS:
    return False

  if tag.name in STRIP_TAGS:
    if tag.name == 'form':
      if 'aspnetForm' in [attr[1] for attr in tag.attrs]: return False
      if tag.find('input', id='__VIEWSTATE'): return False
    if tag.name == 'iframe':
      if tag.has_key('src'):
        if 'youtube.com' in tag['src']: return False
        if 'vimeo.com' in tag['src']: return False
    tag.extract()
    return True

  # Strip "related" lists.
  if _IsList(tag):
    header, header_text = _FindPreviousHeader(tag)
    # Too-long text means this must not be a header, false positive!
    if len(header_text) < 100 and RE_RELATED_HEADER.search(header_text):
      tag.extract()
      header.extract()
      return True

  if tag.has_key('score') and tag['score'] > 0:
    # Do not strip positively-scored tags.
    return False

  for attr, pattern in ATTR_STRIP:
    if not tag.has_key(attr): continue
    if pattern.search(tag[attr]):
      if util.IS_DEV_APPSERVER:
        logging.info('Strip for %s: %s', attr, util.SoupTagOnly(tag))
        logging.info('  (Match %s against %s)',
                     pattern.search(tag[attr]).group(0), pattern.pattern);
      tag.extract()
      return True

  return False


def Process(root_tag, url, hit_counter=None):
  """Process an entire soup, without recursing into stripped nodes."""
  # Make a single "class and id" attribute that everything else can test.
  root_tag['classid'] = '!!!'.join([
      _CamelCaseToSpace(root_tag.get('class', '')).strip(),
      _CamelCaseToSpace(root_tag.get('id', '')).strip()
      ]).strip('!')

  top_run = False
  if hit_counter is None:
    hit_counter = {}
    top_run = True

  _Score(root_tag, url, hit_counter)
  if _Strip(root_tag): return
  for tag in root_tag.findAll(True, recursive=False):
    Process(tag, url, hit_counter)

  # Look for too-frequently-matched false-positive patterns.
  if top_run:
    for key, tags in hit_counter.iteritems():
      if len(tags) >= FALSE_POSITIVE_THRESHOLD:
        points, attr, unused_pattern = key
        if points < 0:
          # Only reverse false _positives_.  Negatives probably aren't false.
          continue
        for tag in tags:
          util.ApplyScore(tag, -1 * points, name=attr)
