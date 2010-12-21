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

import patterns
import util

EMBED_NAMES = set(('embed', 'object'))
TAG_NAMES_BLOCK = set(('blockquote', 'div', 'li', 'p', 'pre', 'td', 'th'))
TAG_NAMES_HEADER = set(('h1', 'h2', 'h3', 'h4', 'h5', 'h6'))

BR_TO_P_STOP_TAGS = set(list(TAG_NAMES_BLOCK) + list(TAG_NAMES_HEADER) + ['br'])


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
    url = url.replace('reddit.com', 'reddit.com.nyud.net')
    html, _ = util.Fetch(url)
    strainer = BeautifulSoup.SoupStrainer(
        attrs={'class': re.compile(r'thing.*link|usertext border')})
    soup = BeautifulSoup.BeautifulSoup(html, parseOnlyThese=strainer)
    return soup.find(attrs={'class': 'usertext-body'}) or 'Reddit parse fail'
  elif re.search(r'^http://(www\.)?xkcd\.com/\d+', url, re.I):
    soup = BeautifulSoup.BeautifulSoup(html)
    img = soup.find(alt=True, title=True)
    cont = img.parent.parent
    for tag in cont.findAll(('br', 'div')):
      tag.extract()
    return cont
  elif re.search(r'^http://groups\.google\.com/', url, re.I):
    strainer = BeautifulSoup.SoupStrainer(attrs={'class': 'maincontbox'})
    soup = BeautifulSoup.BeautifulSoup(html, parseOnlyThese=strainer)
    return _ExtractFromHtmlGeneric(url, unicode(soup))
  elif re.search(r'^http://(www\.)?nytimes\.com/', url, re.I):
    soup = BeautifulSoup.BeautifulSoup(html)
    bodies = soup.findAll(attrs={'class': 'articleBody'})
    if bodies:
      # Put the first "article body" contents into the second -- for some
      # reason NYT splits the lead-in text into its own "body".
      while bodies[0].contents:
        bodies[1].insert(0, bodies[0].contents[-1])
    return _ExtractFromHtmlGeneric(url, unicode(soup))
  elif re.search(r'\.txt(\?|$)', url, re.I):
    soup = BeautifulSoup.BeautifulSoup()
    pre = BeautifulSoup.Tag(soup, 'pre')
    pre.insert(0, BeautifulSoup.NavigableString(html))
    soup.insert(0, pre)
    return soup
  else:
    return _ExtractFromHtmlGeneric(url, html)


def _ExtractFromHtmlGeneric(url, html):
  html = util.PreCleanHtml(html)
  try:
    soup = BeautifulSoup.BeautifulSoup(html)
  except HTMLParser.HTMLParseError, e:
    logging.exception(e)
    return u''

  title = soup.find('title')
  title = title and title.text.lower() or ''

  _TransformBrsToParagraphs(soup)
  patterns.Process(soup, url)
  _ScoreBlocks(soup)
  _ScoreImages(soup)
  _ScoreEmbeds(soup)
  _SiteSpecific(url, soup)

  # If a header repeats the title, strip it and all preceding nodes.
  title_header = _FindTitleHeader(soup, title)
  if title_header:
    util.ApplyScore(title_header, 11, name='title_header')
    _StripBefore(title_header)

  # Get the highest scored nodes.
  scored_nodes = sorted(soup.findAll(attrs={'score': True}),
                        key=lambda x: x['score'])[-15:]
  if not scored_nodes:
    return u'<p>Scoring error.</p>'
  best_node = scored_nodes[-1]

  _TransformDivsToPs(soup)

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
    if len(header_text) < 20:
      continue  # avoid false positives thanks to short/empty headers
    if (title_text in header_text) or (header_text in title_text):
      return header


def _ScoreBlocks(soup):
  """Score up all leaf block nodes, based on the length of their text."""
  for leaf_block in _FindLeafBlocks(soup):
    # Length of stripped text, with all whitespace collapsed.
    text_len = _TextLenNonAnchors(leaf_block)

    if text_len == 0:
      anchor = leaf_block.find('a')
      img = leaf_block.find('img')
      if anchor and not anchor.has_key('score_out_link') and not img:
        util.ApplyScore(leaf_block, -2, name='only_anchor')
      continue
    if text_len < 20:
      util.ApplyScore(leaf_block, -0.75, name='short_text')
    if text_len > 50:
      util.ApplyScore(leaf_block, 3, name='some_text')
    if text_len > 250:
      util.ApplyScore(leaf_block, 4, name='more_text')


def _ScoreEmbeds(soup):
  """Score up objects/embeds."""
  for tag in soup.findAll(EMBED_NAMES):
    if tag.findParent(EMBED_NAMES):
      continue
    size = _TagSize(tag)
    if size > 10000:
      util.ApplyScore(tag, 15, name='has_embed')


def _ScoreImages(soup):
  """Score up images."""
  for tag in soup.findAll('img'):
    util.ApplyScore(tag, 1.5, name='any_img')
    if tag.has_key('alt') and len(tag['alt']) > 50:
      util.ApplyScore(tag, 2, name='img_alt')

    size = _TagSize(tag)
    if size is None:
      continue
    if size <= 625:
      util.ApplyScore(tag, -1.5, name='tiny_img')
    if size >= 50000:
      util.ApplyScore(tag, 3, name='has_img')
    if size >= 250000:
      util.ApplyScore(tag, 4, name='big_img')


def _SiteSpecific(url, soup):
  if 'www.cracked.com' in url:
    tag = soup.find(attrs={'class': 'Column2'})
    if tag: tag.extract()
    tag = soup.find(attrs={'class': 'userStyled'})
    if tag: util.ApplyScore(tag, 20, name='special')


def _StripBefore(strip_tag):
  if util.IS_DEV_APPSERVER:
    logging.info('Strip before: %s', util.SoupTagOnly(strip_tag))
  ancestors = strip_tag.findParents(True)
  for tag in strip_tag.findAllPrevious():
    if tag in ancestors:
      # Don't strip the tags that contain the strip_tag.
      continue
    tag.extract()
  strip_tag.extract()


def _TagSize(tag):
  if tag.has_key('width') and tag.has_key('height'):
    w = tag['width']
    h = tag['height']
  elif tag.has_key('style'):
    try:
      w = re.search(r'width:\s*(\d+)px', tag['style']).group(1)
      h = re.search(r'height:\s*(\d+)px', tag['style']).group(1)
    except AttributeError:
      return None
  else:
    return None

  if w == '100%': w = 600
  if h == '100%': h = 400

  try:
    return int(w) * int(h)
  except ValueError:
    return None


def _TextLenNonAnchors(tag):
  """Length of this tag's text, without <a> nodes."""
  text_nodes = tag.findAll(text=True)
  text = [unicode(x).strip() for x in text_nodes if not x.findParent('a')]
  text = ''.join(text)
  text = re.sub(r'[ \t]+', ' ', text)
  text = re.sub(r'&[^;]{2,6};', '', text)
  return len(text)


def _TransformBrsToParagraphs(soup):
  for tag in soup.findAll('br'):
    _TransformBrsToParagraphsInner(soup, tag)


def _TransformBrsToParagraphsInner(soup, tag):
  next = tag
  while True:
    next = next.nextSibling
    if not next:
      return
    if isinstance(next, BeautifulSoup.Tag):
      if next.name == 'br':
        break
      else:
        return
    elif isinstance(next, BeautifulSoup.NavigableString):
      if not unicode(next).strip():
        continue
      else:
        return

  contents = []
  prev = tag
  while True:
    prev = prev.previousSibling
    if not prev: break
    if hasattr(prev, 'name') and prev.name in BR_TO_P_STOP_TAGS: break
    contents.insert(0, prev)

  newp = BeautifulSoup.Tag(soup, 'p')
  for i, newtag in enumerate(contents):
    newp.insert(i, newtag)
  next.extract()
  tag.replaceWith(newp)


def _TransformDivsToPs(soup):
  for tag in soup.findAll('div'):
    if not tag.find(TAG_NAMES_BLOCK):
      tag.name = 'p'


if __name__ == '__main__':
  # For debugging, assume file on command line.
  print ExtractFromHtml('http://www.example.com', open(sys.argv[1]).read())
