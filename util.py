import Cookie
import hashlib
import logging
import re
import urllib2
import urlparse

import css.css
import css.parse
from django.core.cache import cache
from lxml import cssselect

import settings

EVENT_ATTRS = (
    'onblur', 'onchange ', 'onclick', 'ondblclick', 'onfocus', 'onkeydown',
    'onkeypress', 'onkeyup', 'onload', 'onmousedown', 'onmousemove',
    'onmouseout', 'onmouseover', 'onmouseup', 'onreset', 'onselect', 'onsubmit',
    'onunload',
    )


def applyCss(css_url, doc, specificity_boost=0):
  print 'Applying css:', css_url
  try:
    css_str, _, _ = getUrl(css_url)
  except urllib2.HTTPError, e:
    if e.code == 404:
      pass
    else:
      logging.debug('error fetching url: %s', css_url)
      logging.exception(e)
    return

  applyCssRules(css_url, css.parse.parse(css_str), doc)


def applyCssRules(css_url, rules, doc, specificity_boost=0):
  for obj in rules:
    if isinstance(obj, css.css.Ruleset):
      for selector in obj.selectors:
        try:
          sel = cssselect.CSSSelector(selector)
        except cssselect.ExpressionError:
          continue
        else:
          for el in sel(doc):
            # TODO: Specificity!
            el.style_dict = {}
            for decl in obj.declarations:
              el.style_dict[decl.property] = decl.value
            # TODO: Don't overwrite actual style attributes.
            el.attrib['style'] = ';'.join(
                ['%s:%s' % (p, v) for p, v in el.style_dict.items()])
    elif isinstance(obj, css.css.Charset):
      pass
    elif isinstance(obj, css.css.Import):
      applyCss(obj.source, doc)
    elif isinstance(obj, css.css.Media):
      boost = 0
      if 'print' in obj.media_types:
        boost = 100
        print 'applying a @media statement', obj.media_types
      applyCssRules(css_url, obj.rulesets, doc, boost)
    else:
      print 'Unsupported css object:', type(obj), obj


def cacheKey(key):
  """The DB table has a 255 char limit, make sure that is not exceeded."""
  if len(key) < 255:
    return key
  else:
    return key[0:200] + hashlib.sha1(key[200:]).hexdigest()


def cleanUrl(url):
  url = re.sub(r'utm_[a-z]+=[^&]+(&?)', r'\1', url)
  url = re.sub(r'[?&]+$', '', url)
  return url.strip()


def fixUrls(parent, base_url):
  def _fixUrl(el, attr):
    el.attrib[attr] = urlparse.urljoin(base_url, el.attrib[attr].strip())

  for attr in ('href', 'src'):
    for el in parent.xpath('//*[@%s]' % attr): _fixUrl(el, attr)
    if parent.attrib.has_key(attr): _fixUrl(parent, attr)

  for el in parent.xpath('//object[@data]'): _fixUrl(el, 'data')
  if parent.tag == 'object' and el.attrib.has_key('data'):
    _fixUrl(parent, 'data')

  for el in parent.xpath('//param[@name="movie" and @value]'):
    _fixUrl(el, 'value')


def getUrl(orig_url):
  cache_key = cacheKey('url:' + cleanUrl(orig_url))
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
