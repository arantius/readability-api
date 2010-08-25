#!/usr/bin/env python
"""App Engine request handler for Readability API project.."""

__author__ = 'Anthony Lieuallen'
__copyright__ = 'Copyright 2010, Anthony Lieuallen'
__credits__ = ''
__license__ = 'Apache'
__version__ = '0.1'
__maintainer__ = __author__
__email__ = 'arantius@gmail.com'
__status__ = 'Prototype'  # 'Development'  # 'Production'

import os
import re

from google.appengine.ext.webapp import template

import clean_content
import clean_feed


def Clean(url):
  """Clean the contents of a given URL to only the "readable part".

  Handle special cases like YouTube, PDF, images directly.  Delegate out to
  either extract content from the site's feed, or parse and clean the HTML.

  Args:
    url: String, the URL to the interesting content.

  Returns:
    String: HTML representing the "readable part".
  """
  template_base = os.path.join(os.path.dirname(__file__), 'templates')
  if re.search(r'^http://www.youtube.com/watch', url, re.I):
    video_id = url.split('v=')[1]
    return template.render(os.path.join(template_base, '/youtube-embed.html'),
                           {'video_id': video_id})
  elif re.search(r'\.pdf(\?|$)', url, re.I):
    return template.render(os.path.join(template_base, '/pdf.html'),
                           {'url': url})
  elif re.search(r'\.(gif|jpe?g|png)(\?|$)', url, re.I):
    return template.render(os.path.join(template_base, '/image.html'),
                           {'url': url})

  try:
    feed_cleaner = clean_feed.FeedCleaner(url=url)
    return '<!-- cleaned from feed -->\n' + feed_cleaner.content
  except clean_feed.RssError:
    #return 'fail'
    return '<!-- cleaned from content -->\n' + clean_content.CleanUrl(url)
