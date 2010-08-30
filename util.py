#!/usr/bin/env python
"""General utility helper functions."""

__author__ = 'Anthony Lieuallen'
__copyright__ = 'Copyright 2010, Anthony Lieuallen'
__credits__ = ''
__license__ = 'GPLv3'
__version__ = '0.1'
__maintainer__ = __author__
__email__ = 'arantius@gmail.com'
__status__ = 'Prototype'  # 'Development'  # 'Production'

import os
import urllib2

from google.appengine.api import memcache
from google.appengine.ext.webapp import template


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


@Memoize('Fetch_%s')
def Fetch(url):
  """Fetch a URL, return its contents and any final-after-redirects URL."""
  response = urllib2.urlopen(url)
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
