import logging

from django import http
import lxml.etree
import lxml.html

import util


def page(request):
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
