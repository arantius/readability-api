import math

from django import db
from django import http
import lxml.html

import util


def page(request):
  url = request.GET['url']
  content, _, _ = util.getUrl(url)
  doc = lxml.html.fromstring(content)

#  # Calculate overall ham/spam probability.
#  cursor = db.connection.cursor()  # @UndefinedVariable
#  cursor.execute('SELECT SUM(ham_count), SUM(spam_count) FROM train_facet')
#  ham_count, spam_count = cursor.fetchone()
#  spam_prob = float(spam_count) / float(ham_count + spam_count)

  # Gather aggregated facet statistics in memory, with bayesian probabilities.
  facets = {}
  cursor = db.connection.cursor()  # @UndefinedVariable
  cursor.execute(
      """SELECT kind, data_char, data_int, SUM(ham_count), SUM(spam_count)
      FROM train_facet
      WHERE (ham_count + spam_count) > 4
          AND ham_count > 0 AND spam_count > 0
      GROUP BY kind, data_char, data_int""")
  for kind, data_char, data_int, ham_count, spam_count in cursor.fetchall():
    f = {'ham_count': float(ham_count),
         'spam_count': float(spam_count),
         'total': float(ham_count + spam_count)}
    # For these indexes to make sense: http://goo.gl/giZHx
    f['pws'] = f['spam_count'] / f['total']
    f['pwh'] = f['ham_count'] / f['total']
    f['psw'] = f['pws'] / (f['pws'] + f['pwh'])

    facets.setdefault(kind, {})
    facets[kind][data_char or data_int] = f

  out = []
  for el in doc.iter():
    bayesian_probs = []
    for attr, word in util.attrWords(el):
      try:
        facet = facets[attr + '_word'][word]
        bayesian_probs.append(facet['psw'])
      except KeyError:
        pass

    if bayesian_probs:
      print bayesian_probs
      n = sum(map(
          lambda pi: math.log(1 - pi) - math.log(pi),
          bayesian_probs))
      el_prob = 1 / (1 + math.pow(math.e, n))

      out.append({
          'el': str(el),
          'el_prob': el_prob,
          'bayesian_probs': bayesian_probs})

  # Turn it back into HTML!
  import json
  return http.HttpResponse(
      '<body><pre>%s</pre></body>' % json.dumps(out, indent=2))
