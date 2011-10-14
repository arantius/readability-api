import Cookie
import logging
import re
import urllib2
import urlparse

from django.core.cache import cache

import settings

EVENT_ATTRS = (
    'onblur', 'onchange ', 'onclick', 'ondblclick', 'onfocus', 'onkeydown',
    'onkeypress', 'onkeyup', 'onload', 'onmousedown', 'onmousemove',
    'onmouseout', 'onmouseover', 'onmouseup', 'onreset', 'onselect', 'onsubmit',
    'onunload',
    )


def applyCssToDoc(css, doc):
  pass


def cleanUrl(url):
  url = re.sub(r'utm_[a-z]+=[^&]+(&?)', r'\1', url)
  url = re.sub(r'[?&]+$', '', url)
  return url


def getUrl(orig_url):
  cache_key = 'url:' + orig_url
  result = cache.get(cache_key)
  if result:
    return result

  cookie = Cookie.SimpleCookie()
  redirect_limit = 10
  redirects = 0
  url = orig_url
  while url and redirects < redirect_limit:
    redirects += 1
    url = cleanUrl(url)
    if settings.DEBUG:
      logging.info('Fetching: %s', url)
    final_url = url

    response = urllib2.urlopen(url, timeout=5)
    content = response.read()

    mime_type = response.headers.get('Content-type')
    cookie.load(response.headers.get('Set-Cookie', ''))
    previous_url = url
    url = response.headers.get('Location')
    if url:
      url = urlparse.urljoin(previous_url, url)
  final_url = urlparse.urljoin(orig_url, final_url)

  result = (content, mime_type, final_url)
  cache.set(cache_key, result)
  return result


def preCleanDoc(doc):
  for el in doc.xpath('//head | //script | //style'):
    el.drop_tree()
  for el in doc.xpath('//*'):
    for attr in EVENT_ATTRS:
      try:
        del el.attrib[attr]
      except KeyError:
        # Attribute doesn't exist.
        pass


def words(s):
  """Turn camel case and underscore/hyphen separated strings to lists of words.

  e.g.
  fooBarBaz -> ['foo', 'bar', 'baz]
  foo_bar_baz -> ['foo', 'bar', 'baz]
  foo-bar-baz -> ['foo', 'bar', 'baz]

  Args:
    s: Any string.

  Returns:
    List of Strings, as described.
  """
  s = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', s)
  s = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s)
  s = re.sub('[-_\s]+', ' ', s)
  if not s: return []
  return s.lower().strip().split(' ')
