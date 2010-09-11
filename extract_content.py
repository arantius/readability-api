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
import urlparse

from third_party import BeautifulSoup

import util

TAG_NAMES_BLOCK = set(('blockquote', 'div', 'li', 'p', 'pre', 'td', 'th'))
MAX_SCORE_DEPTH = 5
RE_CLASS_ID_STRIP_ANY = (
    '^addthis', 'functions', 'popular', '^related', 'tools', '^topic',
    'sharethis', 'social',
    )
RE_CLASS_ID_STRIP_WHOLE = (
    'pagination', 'prevnext', 'recent-posts',
    'notes-container',  # tumblr comments
    )
RE_CLASS_ID_STRIP_WORDS = (
    'comments?', 'head(er)?', 'hid(den|e)', 'foot(er)?', 'inset', 'nav',
    'print', 'share', 'sidebar', 'sprite', 'tags',
    'cnn_stry(btmcntnt|btntoolsbottom|cbftrtxt|lctcqrelt)',  # CNN Junk
    )
RE_CLASS_ID_STRIP = re.compile(
    r'(' + '|'.join(RE_CLASS_ID_STRIP_ANY) + r')'
    r'|(_|\b)(' + '|'.join(RE_CLASS_ID_STRIP_WORDS) + r')(_|\b)'
    r'|^(' + '|'.join(RE_CLASS_ID_STRIP_WHOLE) + r')$',
    re.I)
RE_CLASS_ID_POSITIVE_ANY = ('^article',)
RE_CLASS_ID_POSITIVE_WHOLE = ('content', 'entry', 'postcontent')
RE_CLASS_ID_POSITIVE_WORDS = ('post', 'text')
RE_CLASS_ID_POSITIVE = re.compile(
    r'(' + '|'.join(RE_CLASS_ID_POSITIVE_ANY) + r')'
    r'|(_|\b)(' + '|'.join(RE_CLASS_ID_POSITIVE_WORDS) + r')(_|\b)'
    r'|^(' + '|'.join(RE_CLASS_ID_POSITIVE_WHOLE) + r')$',
    re.I)
RE_DISPLAY_NONE = re.compile(r'display\s*:\s*none', re.I)
RE_DOCTYPE = re.compile(r'<!DOCTYPE.*?>', re.S)
RE_DOUBLE_BR = re.compile(r'<br[ /]*>\s*<br[ /]*>', re.I)
RE_HTML_COMMENTS = re.compile(r'<!--.*?-->', re.S)


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
  # Remove all HTML comments, doctypes.
  html = re.sub(RE_HTML_COMMENTS, '', html)
  html = re.sub(RE_DOCTYPE, '', html)
  # Turn double-linebreaks into faked-up paragraphs before parsing.
  html = re.sub(RE_DOUBLE_BR, '</p><p>', html)

  if re.search(r'^http://(www\.)?reddit\.com/.*/comments/', url, re.I):
    strainer = BeautifulSoup.SoupStrainer(
        attrs={'class': re.compile(r'thing.*link')})
    soup = BeautifulSoup.BeautifulSoup(html, parseOnlyThese=strainer)
    return unicode(soup.find(attrs={'class': 'usertext-body'}))
  else:
    return _ExtractFromHtmlGeneric(url, html)


_DEPTH_SCORE_DECAY = [(1 - depth / 12.0) ** 5
                      for depth in range(MAX_SCORE_DEPTH + 1)]
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
  try:
    soup = BeautifulSoup.BeautifulSoup(html)
  except HTMLParser.HTMLParseError, e:
    logging.exception(e)
    return u''

  # Strip tags that will throw off our "text" calculations.
  for tag in soup.findAll(name=set(('script', 'style'))):
    tag.extract()
  for tag in soup.findAll(attrs={'style': RE_DISPLAY_NONE}):
    tag.extract()
  # Strip tags that probably contain junk.
  for tag in soup.findAll(attrs={'class': RE_CLASS_ID_STRIP}):
    tag.extract()
  for tag in soup.findAll(attrs={'id': RE_CLASS_ID_STRIP}):
    tag.extract()

  # Score up all 'leaf block' nodes (blocks not containing other blocks),
  # based on the length of their text.
  for block_leaf in _FindLeafBlocks(soup):
    # Length of stripped text, with all whitespace collapsed.
    block_text = block_leaf.text.strip()
    block_text = re.sub(r'\s\s+', ' ', block_text)
    text_len = len(block_text)

    if text_len == 0:
      continue
    if text_len < 20:
      _ApplyScore(block_leaf, -2, name='short_text')
    if text_len > 75:
      _ApplyScore(block_leaf, 6, name='some_text')
    if text_len > 250:
      _ApplyScore(block_leaf, 8, name='more_text')

  # Score up images.
  for tag in soup.findAll('img'):
    if not tag.has_key('width') or not tag.has_key('height'):
      continue
    try:
      size = int(tag['width']) * int(tag['height'])
    except ValueError:
      continue
    if size >= 125000:
      _ApplyScore(tag, 5, name='has_img')
    if size >= 500000:
      _ApplyScore(tag, 10, name='big_img')

  # Score up objects/embeds.
  EMBED_NAMES = set(('embed', 'object'))
  for tag in soup.findAll(EMBED_NAMES):
    if tag.findParent(EMBED_NAMES):
      continue
    _ApplyScore(tag, 15, name='has_embed')

  # Score up based on id / class.
  for tag in soup.findAll(attrs={'class': RE_CLASS_ID_POSITIVE}):
    _ApplyScore(tag, 20, name='good_class')
  for tag in soup.findAll(attrs={'id': RE_CLASS_ID_POSITIVE}):
    _ApplyScore(tag, 20, name='good_id')

  # Get the highest scored nodes.
  scored_nodes = sorted(soup.findAll(attrs={'score': True}),
                        key=lambda x: x['score'])[-15:]
  if not scored_nodes:
    return '<-- no scored content! -->'
  best_node = scored_nodes[-1]

  # For debugging ...
  if 0 and util.IS_DEV_APPSERVER:
    # Log scored nodes.
    for node in scored_nodes:
      logging.info('%10.2f %s', node['score'], util.SoupTagOnly(node)[0:69])
    # Highlight the highest-scored node.
    best_node['style'] = 'border: 2px dotted red !important;'
    # Highlight positively-scored sibling nodes.
    for tag in best_node.findPreviousSiblings(True):
      if not tag.has_key('score'):
        continue
      if float(tag['score']) <= 0:
        continue
      tag['style'] = 'border: 2px dotted green !important;'
    for tag in best_node.findNextSiblings(True):
      if not tag.has_key('score'):
        continue
      if float(tag['score']) <= 0:
        continue
      tag['style'] = 'border: 2px dotted green !important;'
    # Return this whole marked-up soup.
    return unicode(soup)

  # Transform "text-only" (doesn't contain blocks) <div>s to <p>s.
  for tag in soup.findAll('div'):
    if not tag.find(TAG_NAMES_BLOCK):
      tag.name = 'p'
  # Fix relative URLs.
  _FixUrls(soup, url)

  return unicode(best_node)


def _FindLeafBlocks(soup):
  for tag in soup.findAll(name=True, recursive=False):
    if tag.name in TAG_NAMES_BLOCK and not tag.find(name=TAG_NAMES_BLOCK):
      yield tag
    else:
      for child in _FindLeafBlocks(tag):
        yield child


def _FixUrls(parent, base_url):
  for tag in parent.findAll():
    if tag.has_key('href'):
      tag['href'] = urlparse.urljoin(base_url, tag['href'])
    if tag.has_key('src'):
      tag['src'] = urlparse.urljoin(base_url, tag['src'])


if __name__ == '__main__':
  # For debugging, assume file on command line.
  print ExtractFromHtml('http://www.example.com', open(sys.argv[1]).read())
