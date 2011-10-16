from django import http
from django import shortcuts
import lxml.html

import util


def data(request):
  doc = lxml.html.fromstring(request.POST['html'])
  return http.HttpResponse('todo: actually train!')


def form(request):
  url = request.GET['url']
  content, mime_type, final_url = util.getUrl(url)
  if 'text/html' not in mime_type:
    content = 'Unsupported mime type.'
  else:
    doc = lxml.html.fromstring(content)

    util.preCleanDoc(doc, final_url)
    util.fixUrls(doc, final_url)
    util.postCleanDoc(doc)

    content = ''.join([
        lxml.html.tostring(child)
        for child in doc.body.iterchildren()])

  return shortcuts.render_to_response('train-form.html', {
      'content': content,
      'final_url': final_url,
      'url': url,
      })
