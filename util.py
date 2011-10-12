import re
import urllib2

from django.core.cache import cache

def getUrl(url):
  cache_key = 'url:' + url
  content = cache.get(cache_key)
  if content: return content

  response = urllib2.urlopen(url, timeout=5)
  content = response.read()

  cache.set(cache_key, content)
  return content

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
