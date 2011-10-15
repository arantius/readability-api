import logging
import os
import urlparse

from django import http
from django import shortcuts
import lxml.etree
import lxml.html

import util

FAVICON_PATH = os.path.join(
    os.path.dirname(__file__), 'static', 'favicon.ico')
ROBOTS_PATH = os.path.join(
    os.path.dirname(__file__), 'static', 'robots.txt')

logger = logging.getLogger(__name__)


def cleanPage(request):
  url = request.GET['url']
  content, _, _ = util.getUrl(url)
  doc = lxml.html.fromstring(content)

  # Always unconditionally remove these elements.
  for el in doc.xpath('//head | //script | //style'):
    el.drop_tree()

  # Build "classid" values, counting occurrences as we go.
  word_freq = {}
  for el in doc.xpath('//*[@class or @id]'):
    words = set(
        util.words(el.attrib.get('class', '')) +
        util.words(el.attrib.get('id', ''))
        )
    for word in words:
      word_freq.setdefault(word, 0)
      word_freq[word] += 1
    el.attrib['classid'] = ' ' + ' '.join(words).strip() + ' '

  find_classid = lxml.etree.XPath('//*[contains(@classid, $search)]')
  for word, freq in word_freq.iteritems():
    if freq < 10: continue
    search = ' %s ' % word
    for el in find_classid(doc, search=search):
      print 'drop, too common classid', el, word
      el.drop_tree()

  # Add a base href.
  base = lxml.html.Element('base', href=url)
  doc.insert(0, base)

  # Turn it back into HTML!
  return http.HttpResponse(lxml.html.tostring(doc, encoding=unicode))


def favicon(request):
  return http.HttpResponse(
      open(FAVICON_PATH).read(), 'image/vnd.microsoft.icon')


def home(request):
  return shortcuts.render_to_response('main.html')


def robots(request):
  return http.HttpResponse(
      open(ROBOTS_PATH).read(), 'text/plain')


def train(request):
  url = request.GET['url']
  content, mime_type, final_url = util.getUrl(url)
  if 'text/html' not in mime_type:
    content = 'Unsupported mime type.'
  else:
    doc = lxml.html.fromstring(content)

    # Gather all CSS.
    for el in doc.xpath('//link[@rel="stylesheet"]'):
      css_url = urlparse.urljoin(final_url, el.attrib['href'])
      util.applyCss(css_url, doc)

    util.preCleanDoc(doc)
    util.fixUrls(doc, final_url)

    content = lxml.html.tostring(doc, encoding=unicode, pretty_print=True)

  return shortcuts.render_to_response('train.html', {
      'content': content,
      'final_url': final_url,
      'url': url,
      })
