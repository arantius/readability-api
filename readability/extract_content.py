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

import html.parser
import logging
import re
import sys

from bs4 import BeautifulSoup

from readability import patterns
from readability import util


def ExtractFromHtml(url, html):
  """Given a string of HTML, remove nasty bits, score and pick bit to keep."""
  if re.search(r'^http://(www\.)?reddit\.com/.*/comments/', url, re.I):
    strainer = BeautifulSoup.SoupStrainer(
        attrs={'class': re.compile(r'thing.*link|usertext border')})
    soup = BeautifulSoup.BeautifulSoup(html, parseOnlyThese=strainer)
    body = soup.find(attrs={'class': re.compile(r'\busertext-body\b')})
    if not body:
      body = soup.find('a', attrs={'class': re.compile(r'\btitle\b')})
      body = body and body.text or soup
    return soup, body
  elif re.search(r'^https://gfycat.com/[a-zA-Z]+$', url, re.I):
    soup = BeautifulSoup.BeautifulSoup(html)
    vid = soup.find('video')
    del vid['autoplay']
    vid['controls'] = 'controls'
    return soup, vid
  elif re.search(r'^http://(www\.)?xkcd\.com/\d+', url, re.I):
    soup = BeautifulSoup.BeautifulSoup(html)
    img = soup.find(alt=True, title=True)
    cont = img.parent.parent
    for tag in cont.findAll(('br', 'div')):
      util.Strip(tag)
    return soup, cont
  elif re.search(r'^http://groups\.google\.com/', url, re.I):
    strainer = BeautifulSoup.SoupStrainer(attrs={'class': 'maincontbox'})
    soup = BeautifulSoup.BeautifulSoup(html, parseOnlyThese=strainer)
    return _ExtractFromHtmlGeneric(url, str(soup))
  elif re.search(r'\.txt(\?|$)', url, re.I):
    soup = BeautifulSoup.BeautifulSoup()
    pre = BeautifulSoup.Tag(soup, 'pre')
    pre.insert(0, BeautifulSoup.NavigableString(html))
    soup.insert(0, pre)
    return soup, soup
  else:
    return _ExtractFromHtmlGeneric(url, html)


def _ExtractFromHtmlGeneric(url, html):
  html = util.PreCleanHtml(html)
  try:
    soup = BeautifulSoup.BeautifulSoup(html)
  except html.parser.HTMLParseError as e:
    logging.exception(e)
    return soup, ''

  util.PreCleanSoup(soup)

  title = soup.find('title')
  title = title and title.text.lower() or ''

  _TransformBrsToParagraphs(soup)
  patterns.Process(soup, url)
  _SiteSpecific(url, soup)

  # If a header repeats the title, strip it and all preceding nodes.
  title_header = _FindTitleHeader(soup, title)
  if title_header:
    util.ApplyScore(title_header, 11, name='title_header')
    if 'flickr.com' not in url:
      _StripBefore(title_header)

  # Get the highest scored nodes.
  scored_nodes = sorted(soup.findAll(attrs={'score': True}),
                        key=lambda x: x['score'])[-15:]
  if not scored_nodes:
    return soup, '<p>Scoring error.</p>'
  best_node = scored_nodes[-1]

  _TransformDivsToPs(best_node)

  # For debugging ...
  if util.IS_DEV_APPSERVER:
    # Log scored nodes.
    for node in scored_nodes:
      logging.info('%10.2f %s', node['score'], util.SoupTagOnly(node)[0:69])

  return soup, best_node


def _FindTitleHeader(root_tag, title_text):
  headers = root_tag.findAll(util.TAG_NAMES_HEADER)
  for header in headers:
    header_text = header.text.lower()
    if len(header_text) < 20:
      continue  # avoid false positives thanks to short/empty headers
    if (title_text in header_text) or (header_text in title_text):
      return header


def _SiteSpecific(url, root_tag):
  if 'www.cracked.com' in url:
    tag = root_tag.find(attrs={'class': 'Column2'})
    if tag: util.Strip(tag)
    tag = root_tag.find(attrs={'class': 'userStyled'})
    if tag: util.ApplyScore(tag, 20, name='special')


def _StripBefore(strip_tag):
  if util.IS_DEV_APPSERVER:
    logging.info('Strip before: %s', util.SoupTagOnly(strip_tag))
  ancestors = strip_tag.findParents(True)
  for tag in strip_tag.findAllPrevious():
    if tag in ancestors:
      # Don't strip the tags that contain the strip_tag.
      continue
    logging.info('Strip for being before title el: %s', util.SoupTagOnly(tag))
    util.Strip(tag)
  logging.info('Strip for being title el: %s', util.SoupTagOnly(tag))
  util.Strip(strip_tag)


def _TransformBrsToParagraphs(soup):
  for tag in soup.findAll('br'):
    _TransformBrsToParagraphsInner(soup, tag)


def _TransformBrsToParagraphsInner(soup, tag):
  next_tag = tag
  while True:
    next_tag = next_tag.next_tagSibling
    if not next_tag:
      return
    if isinstance(next_tag, BeautifulSoup.Tag):
      if next_tag.name == 'br':
        break
      else:
        return
    elif isinstance(next_tag, BeautifulSoup.NavigableString):
      if not str(next_tag).strip():
        continue
      else:
        return

  contents = []
  prev = tag
  while True:
    prev = prev.previousSibling
    if not prev: break
    if hasattr(prev, 'name') and prev.name in util.BR_TO_P_STOP_TAGS: break
    contents.insert(0, prev)

  newp = BeautifulSoup.Tag(soup, 'p')
  for i, newtag in enumerate(contents):
    newp.insert(i, newtag)
  util.Strip(next_tag)
  tag.replaceWith(newp)


def _TransformDivsToPs(root_tag):
  for tag in root_tag.findAll('div'):
    if not tag.find(util.TAG_NAMES_BLOCK):
      tag.name = 'p'


if __name__ == '__main__':
  # For debugging, assume file on command line.
  print(ExtractFromHtml('http://www.example.com', open(sys.argv[1]).read()))
