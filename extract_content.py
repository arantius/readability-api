#!/usr/bin/env python
"""Originally "Hacker News" feed rewriter by Nirmal Patel.

Now: General purpose "page cleaner".  Given the *content* of a page, at a URL,
attempts to convert it into the smallest subset of markup that contains the
entire body of important content.

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

import HTMLParser
import logging
import re
import sys

from third_party import BeautifulSoup

import util

EMBED_NAMES = set(('embed', 'object'))
MAX_CLASS_ID_STRIP_PERCENTAGE = 0.25
MAX_SCORE_DEPTH = 5
RE_CLASS_ID_NEGATIVE_ANY = ('facebook',)
#RE_CLASS_ID_NEGATIVE_WHOLE = ()
RE_CLASS_ID_NEGATIVE_WORDS = (
    'ad(block)?', 'author', 'bottom', 'delicious', 'featured', 'meta', 'module',
    'post-meta', 'twitter', 'widget')
RE_CLASS_ID_NEGATIVE = re.compile(
    r'(' + '|'.join(RE_CLASS_ID_NEGATIVE_ANY) + r')'
    r'|(_|\b)(' + '|'.join(RE_CLASS_ID_NEGATIVE_WORDS) + r')(_|\b)',
    #r'|^(' + '|'.join(RE_CLASS_ID_NEGATIVE_WHOLE) + r')$',
    re.I)
RE_CLASS_ID_STRIP_ANY = (
    '^add(this|toany)', '^comment', 'functions', 'popular', '^related',
    'tool(box|s)', '^topic', 'sharethis', 'socia(ble|l)',
    )
RE_CLASS_ID_STRIP_WHOLE = (
    'author_info', 'byline', 'more_stories', 'pagination', 'posted_on',
    'prevnext', 'recent-posts', 'respond',
    'notes', 'notes-container', 'post-notes',  # tumblr comments
    )
RE_CLASS_ID_STRIP_WORDS = (
    'ad', '(article)?comments?', 'categor(ies|y)', 'dd_post_share', 'head(er)?',
    'hid(den|e)', 'foot(er)?', 'inset', 'nav', 'post_share', 'print', 'sidebar',
    'sprite', 'tag(ged|s)', 'talkback',
    'cnn_stry(btmcntnt|btntoolsbottom|cbftrtxt|lctcqrelt)',  # CNN Junk
    # NOT: 'share' -- breaks twitter
    )
RE_CLASS_ID_STRIP = re.compile(
    r'(' + '|'.join(RE_CLASS_ID_STRIP_ANY) + r')'
    r'|(_|\b)(' + '|'.join(RE_CLASS_ID_STRIP_WORDS) + r')(_|\b)'
    r'|^(' + '|'.join(RE_CLASS_ID_STRIP_WHOLE) + r')$',
    re.I)
RE_CLASS_ID_POSITIVE_ANY = ('^article_?(body)',)
RE_CLASS_ID_POSITIVE_WHOLE = (
    'page', 'permalink', 'player', 'post[-_]?(\d+|body|content)?', '(story)?body'
    # Test: removed 'content' as it often matches too much
    )
RE_CLASS_ID_POSITIVE_WORDS = ('h?entry', 'text')
RE_CLASS_ID_POSITIVE = re.compile(
    r'(' + '|'.join(RE_CLASS_ID_POSITIVE_ANY) + r')'
    r'|(_|\b)(' + '|'.join(RE_CLASS_ID_POSITIVE_WORDS) + r')(_|\b)'
    r'|^(' + '|'.join(RE_CLASS_ID_POSITIVE_WHOLE) + r')$',
    re.I)
RE_DISPLAY_NONE = re.compile(r'display\s*:\s*none', re.I)
RE_DOUBLE_BR = re.compile(r'<br[ /]*>\s*<br[ /]*>', re.I)
TAG_NAMES_BLOCK = set(('blockquote', 'div', 'li', 'p', 'pre', 'td', 'th'))
TAG_NAMES_HEADER = set(('h1', 'h2', 'h3', 'h4', 'h5', 'h6'))

_DEPTH_SCORE_DECAY = [(1 - d / 12.0) ** 5 for d in range(MAX_SCORE_DEPTH + 1)]


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
  if re.search(r'^http://(www\.)?reddit\.com/.*/comments/', url, re.I):
    strainer = BeautifulSoup.SoupStrainer(
        attrs={'class': re.compile(r'thing.*link')})
    soup = BeautifulSoup.BeautifulSoup(html, parseOnlyThese=strainer)
    return unicode(soup.find(attrs={'class': 'usertext-body'}))
  else:
    return _ExtractFromHtmlGeneric(url, html)


def StripJunk(soup):
  """Strip out junk nodes, for a variety of reasons."""
  soup_len = float(len(unicode(soup)))

  def _Strip(tag):
    tag_len = len(unicode(tag))
    if tag_len / soup_len > MAX_CLASS_ID_STRIP_PERCENTAGE:
      return
    tag.extract()


  # Remove forms, scripts, and styles.
  for tag in soup.findAll(('form', 'script', 'style')):
    _Strip(tag)
  # Script non-displayed nodes.
  for tag in soup.findAll(attrs={'style': RE_DISPLAY_NONE}):
    _Strip(tag)

  # Remove links to "social media" junk.
  for tag in soup.findAll(name='a', href=re.compile(
      r'addtoany\.com|api\.tweetmeme\.com|delicious\.com|^javascript:')):
    _Strip(tag)
  for tag in soup.findAll(src=re.compile(
      r'reddit\.com|stumbleupon\.com')):
    _Strip(tag)

  # Remove all tags with a class/id that matches my pattern.
  for tag in soup.findAll(
      lambda tag: util.IdOrClassMatches(tag, RE_CLASS_ID_STRIP)):
    if util.IdOrClassMatches(tag, RE_CLASS_ID_POSITIVE):
      continue
    if util.IS_DEV_APPSERVER:
      logging.info(
          'Strip for class/id: %s', util.SoupTagOnly(tag))
    _Strip(tag)


def _ApplyScore(tag, score, depth=0, name=None):
  """Recursively apply a decaying score to each parent up the tree."""
  if not tag:
    return
  if depth > MAX_SCORE_DEPTH:
    return
  decayed_score = score * _DEPTH_SCORE_DECAY[depth]

  if not tag.has_key('score'):
    tag['score'] = 0
  tag['score'] = float(tag['score']) + decayed_score

  if util.IS_DEV_APPSERVER and name:
    name_key = 'score_%s' % name
    if not tag.has_key(name_key):
      tag[name_key] = 0
    tag[name_key] = float(tag[name_key]) + decayed_score

  _ApplyScore(tag.parent, score, depth + 1, name=name)


def _ExtractFromHtmlGeneric(url, html):
  # Turn double-linebreaks into faked-up paragraphs before parsing.
  html = re.sub(RE_DOUBLE_BR, '</p><p>', html)

  try:
    soup = BeautifulSoup.BeautifulSoup(util.PreCleanHtml(html))
  except HTMLParser.HTMLParseError, e:
    logging.exception(e)
    return u''

  title = soup.find('title')
  title = title and title.text.lower() or ''

  # Strip tags that probably contain junk, before scoring.
  StripJunk(soup)

  _ScoreBlocks(soup)
  _ScoreClassId(soup)
  _ScoreImages(soup)
  _ScoreEmbeds(soup)

  # Get the highest scored nodes.
  scored_nodes = sorted(soup.findAll(attrs={'score': True}),
                        key=lambda x: x['score'])[-15:]
  if not scored_nodes:
    return u'<p>Scoring error.</p>'
  best_node = scored_nodes[-1]

  _TransformDivsToPs(soup)

  # If a header repeats the title, strip it and all preceding nodes.
  title_header = _FindTitleHeader(best_node, title)
  if title_header:
    _StripBefore(title_header)

  # For debugging ...
  if util.IS_DEV_APPSERVER:
    # Log scored nodes.
    for node in scored_nodes:
      logging.info('%10.2f %s', node['score'], util.SoupTagOnly(node)[0:69])

  return best_node


def _FindLeafBlocks(soup):
  for tag in soup.findAll(name=True, recursive=False):
    if tag.name in TAG_NAMES_BLOCK and not tag.find(name=TAG_NAMES_BLOCK):
      yield tag
    else:
      for child in _FindLeafBlocks(tag):
        yield child


def _FindTitleHeader(soup, title_text):
  headers = soup.findAll(TAG_NAMES_HEADER)
  for header in headers:
    header_text = header.text.lower()
    if len(header_text) < 10:
      continue  # avoid false positives thanks to short/empty headers
    if (title_text in header_text) or (header_text in title_text):
      return header


def _ScoreBlocks(soup):
  """Score up all leaf block nodes, based on the length of their text."""
  for leaf_block in _FindLeafBlocks(soup):
    # Length of stripped text, with all whitespace collapsed.
    block_text = leaf_block.text.strip()
    block_text = re.sub(r'\s\s+', ' ', block_text)
    block_text = re.sub(r'&[^;]{2,6};', '', block_text)
    text_len = len(block_text)

    if text_len == 0:
      continue
    if text_len < 20:
      _ApplyScore(leaf_block, -1.5, name='short_text')
    if text_len > 75:
      _ApplyScore(leaf_block, 6, name='some_text')
    if text_len > 250:
      _ApplyScore(leaf_block, 8, name='more_text')


def _ScoreClassId(soup):
  """Score up and down, based on class and id."""
  for tag in soup.findAll(True):
    if util.IdOrClassMatches(tag, RE_CLASS_ID_NEGATIVE):
      _ApplyScore(tag, -20, name='bad_class_id')
    elif util.IdOrClassMatches(tag, RE_CLASS_ID_POSITIVE):
      _ApplyScore(tag, 20, name='good_class_id')


def _ScoreEmbeds(soup):
  """Score up objects/embeds."""
  for tag in soup.findAll(EMBED_NAMES):
    if tag.findParent(EMBED_NAMES):
      continue
    _ApplyScore(tag, 15, name='has_embed')


def _ScoreImages(soup):
  """Score up images."""
  for tag in soup.findAll('img'):
    _ApplyScore(tag, 1, name='any_img')
    if not tag.has_key('width') or not tag.has_key('height'):
      continue
    try:
      size = int(tag['width']) * int(tag['height'])
    except ValueError:
      continue
    if size == 1:
      _ApplyScore(tag, -3, name='tiny_img')
    if size >= 125000:
      _ApplyScore(tag, 5, name='has_img')
    if size >= 500000:
      _ApplyScore(tag, 10, name='big_img')


def _StripBefore(strip_tag):
  ancestors = strip_tag.findParents(True)
  for tag in strip_tag.findAllPrevious():
    if tag in ancestors:
      # Don't strip the tags that contain the strip_tag.
      continue
    tag.extract()
  strip_tag.extract()


def _TransformDivsToPs(soup):
  for tag in soup.findAll('div'):
    if not tag.find(TAG_NAMES_BLOCK):
      tag.name = 'p'


if __name__ == '__main__':
  # For debugging, assume file on command line.
  print ExtractFromHtml('http://www.example.com', open(sys.argv[1]).read())
