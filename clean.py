#!/usr/bin/env python
"""Cleaning wrapper.

Given a URL, first apply special cases.  Then try to fetch a feed of the
content, then try to directly handle the HTML.  Clean up all HTML where
appropriate.

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

import re

from third_party import BeautifulSoup

import extract_content
import extract_feed
import util

RE_ALIGNED = re.compile(r'(?:_|\b)(?:align)?(left|right)(?:_|\b)', re.I)
RE_FEEDBURNER_LINK = re.compile(r'^https?://[^/]+/~.{1,3}/', re.I)
STRIP_ATTRS = set((
    'class',
    'id'
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


def Clean(url):
  """Clean the contents of a given URL to only the "readable part".

  Handle special cases like YouTube, PDF, images directly.  Delegate out to
  either extract content from the site's feed, or parse and clean the HTML.

  Args:
    url: String, the URL to the interesting content.

  Returns:
    String: HTML representing the "readable part".
  """
  if re.search(r'^http://www\.youtube\.com/watch', url, re.I):
    video_id = url.split('v=')[1]
    return util.RenderTemplate('youtube.html', {'video_id': video_id})
  elif re.search(r'\.pdf(\?|$)', url, re.I):
    return util.RenderTemplate('pdf.html', {'url': url})
  elif re.search(r'\.(gif|jpe?g|png)(\?|$)', url, re.I):
    return util.RenderTemplate('image.html', {'url': url})

  match = re.search(r'^https?://docs.google.com.*docid=(.*?)(&|$)', url, re.I)
  if match:
    return util.RenderTemplate('google-docs.html', {'docid': match.group(1),
                                                    'url': url})

  html, final_url = util.Fetch(url)
  note = ''
  content = ''
  try:
    extractor = extract_feed.FeedExtractor(
        url=url, final_url=final_url, html=html)
    note = u'<!-- cleaned feed -->\n'
    content = extractor.content
  except extract_feed.RssError, e:
    note = u'<!-- cleaned content, %s, %s -->\n' % (e.__class__.__name__, e)
    content = extract_content.ExtractFromHtml(url, html)

  return note + _Munge(content)
if not util.IS_DEV_APPSERVER:
  Clean = util.Memoize('Clean_%s', 3600*24)(Clean)  # pylint: disable-msg=C6409


def _Munge(html):
  """Given a string of HTML content, munge it to be more pleasing."""
  html = html.replace('&nbsp;', ' ')
  soup = BeautifulSoup.BeautifulSoup(html)

  # For all images:
  #  * If they have a class that implies floating, apply alignment.
  #  * If they are at the beginning of a paragraph, with text, apply alignment.
  for img in soup.findAll('img'):
    if img.has_key('align'):
      continue

    if img.has_key('class'):
      match = RE_ALIGNED.search(img['class'])
      if match:
        img['align'] = match.group(1)
        continue

    parent_p = img.findParent('p', limit=1)
    if parent_p and not img.findPreviousSibling(name=True):
      if parent_p.text or not parent_p.findPreviousSibling('p'):
        img['align'] = 'left'

  # Remove unwanted attributes from all tags (e.g. events, styles).
  for tag in soup.findAll(True):
    for attr in STRIP_ATTRS:
      del tag[attr]

  # Remove links to "social media" junk.
  for tag in soup.findAll(name='a', href=re.compile(r'api.tweetmeme.com')):
    tag.extract()

  # Remove empty cells/divs/paragraphs.
  for tag in soup.findAll(('div', 'p', 'td')):
    if not tag.find(('embed', 'img', 'object')) and not tag.text.strip():
      tag.extract()

  # Remove feedburner noise links.
  for tag in soup.findAll(name='a', attrs={'href': RE_FEEDBURNER_LINK}):
    tag.extract()
  for tag in soup.findAll(name='img', attrs={'src': RE_FEEDBURNER_LINK}):
    tag.extract()

  return unicode(soup)
