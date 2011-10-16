import Cookie
import hashlib
import logging
import re
import urllib2
import urlparse

import cssutils
from django.core.cache import cache
from lxml import cssselect

import settings

EVENT_ATTRS = (
    'onblur', 'onchange ', 'onclick', 'ondblclick', 'onfocus', 'onkeydown',
    'onkeypress', 'onkeyup', 'onload', 'onmousedown', 'onmousemove',
    'onmouseout', 'onmouseover', 'onmouseup', 'onreset', 'onselect', 'onsubmit',
    'onunload',
    )
NAMESPACE_RE = "http://exslt.org/regular-expressions"


def applyCss(css_url, doc, media=None):
  sheet = CSS_PARSER.parseUrl(css_url, media=media)
  cssutils.replaceUrls(sheet, lambda u: urlparse.urljoin(css_url, u))

  # For every rule in this sheet ...
  affected_els = applyCssRules(sheet.cssRules, doc, media=media)

  # Now that we (above) set a style dictionary, map it down into style attrib.
  def collapseStyle(t):
    """Turn one .items() from a .style dict into a CSS declaration."""
    p, v = t
    _, v = v
    return '%s:%s' % (p, v)
  for el in set(affected_els):
    if 'style' in el.attrib:
      try:
        attr_decl = cssutils.css.CSSStyleDeclaration(
            el.attrib.get('style', None))
      except:
        pass
      else:
        cssutils.replaceUrls(attr_decl, lambda u: urlparse.urljoin(css_url, u))
        for decl in attr_decl:
          el.style[decl.name] = 99999, decl.propertyValue.cssText
    el.attrib['style'] = ';'.join(map(collapseStyle, el.style.items()))


def applyCssRules(rules, doc, media):
  affected_els = []
  for rule in rules:
    if isinstance(rule, cssutils.css.CSSCharsetRule):
      pass
    elif isinstance(rule, cssutils.css.CSSComment):
      pass
    elif isinstance(rule, cssutils.css.CSSMediaRule):
      applyCssRules(
          rule.cssRules, doc,
          media=('print' in rule.media and 'print' or 'screen'))
    elif isinstance(rule, cssutils.css.CSSStyleRule):
      decl_dict = {}
      for decl in rule.style:
        decl_dict[decl.name] = decl.propertyValue.cssText

      # For every selector in this rule ...
      for selector in rule.selectorList:
        try:
          sel = cssselect.CSSSelector(selector.selectorText)
        except cssselect.ExpressionError:
          continue
        sel_specificity = sum(selector.specificity)
        if media == 'print':
          sel_specificity += 100

        # For every element that matches this selector ...
        for el in sel(doc):
          try:
            getattr(el, 'style')
          except AttributeError:
            el.style = {}

          # For every property in this declaration ...
          for prop, val in decl_dict.items():
            el_prop = el.style.get(prop)
            # If the property doesn't yet exist, or doeswith lower specificity..
            if not el_prop or el_prop[0] <= sel_specificity:
              # Use the new value.
              el.style[prop] = sel_specificity, val
              affected_els.append(el)
    else:
      print 'Unknown rule:', type(rule), rule
  return affected_els


def cacheKey(key):
  """The DB table has a 255 char limit, make sure that is not exceeded."""
  if len(key) < 255:
    return key
  else:
    return key[0:200] + hashlib.sha1(key[200:]).hexdigest()


def cleanUrl(url):
  # Handle de-facto standard "hash bang" URLs ( http://goo.gl/LNmg )
  url = url.replace('#!', '?_escaped_fragment_=')
  # Strip tracking noise.
  url = re.sub(r'utm_[a-z]+=[^&]+(&?)', r'\1', url)
  # Strip possibly left over query string delimiters.
  url = re.sub(r'[?&]+$', '', url)
  return url.strip()


def fetchCss(url):
  """Fetcher which uses getUrl() to provide cssutils' required format."""
  content, _, _ = getUrl(url)
  return None, content


def fixUrls(parent, base_url):
  def _fixUrl(el, attr):
    el.attrib[attr] = urlparse.urljoin(base_url, el.attrib[attr].strip())

  for attr in ('background', 'href', 'src'):
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
  # Strip elements by simple rules.
  for el in doc.xpath('//comment() | //script | //style | //head'):
    if el.getparent(): el.drop_tree()
  # Strip elements by style.
  for el in doc.xpath(
      "//*[re:test(@style, 'display\s*:\s*none|position\s*:\s*fixed|visibility\s*:\s*hidden', 'i')]",
      namespaces={'re': NAMESPACE_RE}):
    el.drop_tree()
  # Strip attributes from all elements.
  for el in doc.xpath('//*'):
    for attr in EVENT_ATTRS:
      try:
        del el.attrib[attr]
      except KeyError:
        # Attribute doesn't exist.
        pass


def postCleanDoc(doc):
  # Strip empty nodes.
  found_empty = False
  for el in doc.xpath('//*[not(node())]'):
    found_empty = True
    el.drop_tree()
  if found_empty:
    # Recurse in case removed nodes' parents are now empty.
    return postCleanDoc(doc)


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


# Constants depending on things defined above.
CSS_PARSER = cssutils.CSSParser(fetcher=fetchCss, loglevel=logging.CRITICAL)
