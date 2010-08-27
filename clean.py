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

import logging
import os
import re

import extract_content
import extract_feed
import util

logging.basicConfig(level=logging.DEBUG)


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
  except extract_feed.RssError:
    note = '<!-- cleaned content -->\n'
    content = extract_content.ExtractFromHtml(url, html)

  return note + content

if not 'Development' in os.environ.get('SERVER_SOFTWARE', ''):
  Clean = util.Memoize('Clean_%s', 3600*24)(Clean)  # pylint: disable-msg=C6409
