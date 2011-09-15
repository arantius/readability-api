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
