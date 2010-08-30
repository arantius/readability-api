#!/usr/bin/env python
"""App Engine request handler for Readability API project.."""

__author__ = 'Anthony Lieuallen'
__copyright__ = 'Copyright 2010, Anthony Lieuallen'
__credits__ = ''
__license__ = 'GPLv3'
__version__ = '0.1'
__maintainer__ = __author__
__email__ = 'arantius@gmail.com'
__status__ = 'Prototype'  # 'Development'  # 'Production'

# Use default membership test instead of 'has_key'
# pylint: disable-msg=C6401
# -- this doesn't work with BeautifulSoup objects.  Disable check.

import logging
import os
import re

from third_party import BeautifulSoup

import extract_content
import extract_feed
import util

RE_ALIGNED = re.compile(r'(?:_|\b)(?:align)?(left|right)(?:_|\b)', re.I)
RE_FEEDBURNER_LINK = re.compile(r'https?://[^/]+/~.+/', re.I)
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
  if re.search(r'^http://www.youtube.com/watch', url, re.I):
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
    note = '<!-- cleaned feed -->\n'
    content = extractor.content
  except extract_feed.RssError, e:
    note = '<!-- cleaned content, %s, %s -->\n' % (e.__class__.__name__, e)
    content = extract_content.ExtractFromHtml(url, html)

  return note + Munge(content)

if not 'Development' in os.environ.get('SERVER_SOFTWARE', ''):
  Clean = util.Memoize('Clean_%s', 3600*24)(Clean)  # pylint: disable-msg=C6409


def Munge(html):
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
    else:
      if img.parent and (img.parent.name == 'p') and img.parent.text:
        if not img.findPreviousSiblings(name=True, limit=1):
          img['align'] = 'left'

  # Remove unwanted attributes from all tags (e.g. events, styles).
  for tag in soup.findAll(True):
    for attr in STRIP_ATTRS:
      del tag[attr]

  # Remove empty cells/divs/paragraphs.
  for tag in soup.findAll(('div', 'p', 'td')):
    if not tag.find(('embed', 'img', 'object')) and not tag.text.strip():
      tag.extract()

  # Remove feedburner noise links.
  for tag in soup.findAll(name='a', attrs={'href': RE_FEEDBURNER_LINK}):
    tag.extract()
  for tag in soup.findAll(name='img', attrs={'src': RE_FEEDBURNER_LINK}):
    tag.extract()

  content = soup.renderContents()

  return content
