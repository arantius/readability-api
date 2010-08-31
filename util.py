#!/usr/bin/env python
"""General utility helper functions."""

"""
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

import os
import urllib2

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template

IS_DEV_APPSERVER = 'Development' in os.environ.get('SERVER_SOFTWARE', '')


def Memoize(formatted_key, time=3600):
  """Decorator to store a function call result in App Engine memcache."""

  def Decorator(func):
    def InnerDecorator(*args, **kwargs):
      key = formatted_key % args[0:formatted_key.count('%')]
      result = memcache.get_multi([key])
      if key in result:
        return result[key]
      result = func(*args, **kwargs)
      memcache.set(key, result, time)
      return result
    return InnerDecorator
  return Decorator


def EntryContent(entry):
  """Figure out the best content for this (feedparser) entry."""
  # Prefer "content".
  if 'content' in entry:
    # If there's only one, use it.
    if len(entry.content) == 1:
      return unicode(entry.content[0]['value'])
    # Or, use the text/html type if there's more than one.
    for content in entry.content:
      if 'text/html' == content.type:
        return unicode(content['value'])
  # Otherwise try "summary_detail" and "summary".
  if 'summary_detail' in entry:
    return unicode(entry.summary_detail['value'])
  if 'summary' in entry:
    return unicode(entry.summary)


@Memoize('Fetch_%s')
def Fetch(url):
  """Fetch a URL, return its contents and any final-after-redirects URL."""
  try:
    response = urllib2.urlopen(url)
  except (urlfetch.DownloadError, urllib2.HTTPError), e:
    return (repr(e), url)
  else:
    return (response.read(), response.geturl())


def IdOrClassMatches(tag, re):
  if not tag:
    return False
  if tag.has_key('class') and re.search(tag['class']):
    return True
  if tag.has_key('id') and re.search(tag['id']):
    return True
  return False


def RenderTemplate(template_name, template_values):
  template_base = os.path.join(os.path.dirname(__file__), 'templates')
  return template.render(os.path.join(template_base, template_name),
                         template_values)


def SoupTagOnly(tag):
  return str(tag).split('>')[0] + '>'
