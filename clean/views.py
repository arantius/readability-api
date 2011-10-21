import math

from django import db
from django import shortcuts
import lxml.html

import util

THRESHOLD_SPAM = 0.95
THRESHOLD_HAM = 0.8

def page(request):
  url = request.GET['url']
  content, _, _ = util.getUrl(url)
  doc = lxml.html.fromstring(content)
  util.preCleanDoc(doc, url)

  # Calculate overall ham/spam probability.
  cursor = db.connection.cursor()  # @UndefinedVariable
  cursor.execute('SELECT SUM(ham_count), SUM(spam_count) FROM train_facet')
  ham_count, spam_count = cursor.fetchone()
  spam_prob = float(spam_count) / float(ham_count + spam_count)

  bayes_str = 2
  # Gather aggregated facet statistics in memory, with bayesian probabilities.
  facets = {}
  cursor = db.connection.cursor()  # @UndefinedVariable
  cursor.execute(
      """SELECT kind, data_char, data_int,
          SUM(ham_count) AS sh, SUM(spam_count) AS ss
      FROM train_facet
      GROUP BY kind, data_char, data_int
      HAVING sh >= %d AND ss >= %d""" % (bayes_str, bayes_str))
  for kind, data_char, data_int, ham_count, spam_count in cursor.fetchall():
    f = {'ham_count': float(ham_count),
         'spam_count': float(spam_count),
         'total': float(ham_count + spam_count)}
    # For these indexes to make sense: http://goo.gl/giZHx
    f['pws'] = f['spam_count'] / f['total']
    f['pwh'] = f['ham_count'] / f['total']
    f['psw'] = f['pws'] / (f['pws'] + f['pwh'])
    f['cpsw'] = (bayes_str * spam_prob + f['total'] * f['psw']
        ) / (bayes_str * f['total'])

    facets.setdefault(kind, {})
    facets[kind][data_char or data_int] = f

  for el in doc.iter():
    bayesian_probs = []
    for attr, word in util.attrWords(el):
      try:
        facet = facets[attr + '_word'][word]
        bayesian_probs.append(facet['psw'])
      except KeyError:
        pass

    text = ' '.join(el.xpath('./text()'))
    words = util.words(text)
    for word in words:
      try:
        facet = facets['text_word'][word]
        bayesian_probs.append(facet['psw'])
      except KeyError:
        pass

    if 'class' not in el.attrib:
      # Can't setdefault, it's not a dict.
      el.attrib['class'] = ''

    if bayesian_probs:
      print bayesian_probs
      n = sum(map(
          lambda pi: math.log(1 - pi) - math.log(pi),
          bayesian_probs))
      el_prob = 1 / (1 + math.pow(math.e, n))
      el.attrib['spam_prob'] = str(el_prob)

      if el_prob >= THRESHOLD_SPAM:
        el.attrib['class'] += ' cleaned_spam'
      elif el_prob <= THRESHOLD_HAM:
        el.attrib['class'] += ' cleaned_ham'
      else:
        el.attrib['class'] += ' cleaned_unknown'
    else:
      el.attrib['class'] += ' cleaned_unknown'

  full_content = ''.join([
      lxml.html.tostring(child)
      for child in doc.body.iterchildren()])
  for el in doc.iter():
    if 'cleaned_ham' not in el.attrib['class']:
      if el.getparent() is not None:
        el.drop_tag()
  doc = util.postCleanDoc(doc)
  cleaned_content = lxml.html.tostring(doc)

  return shortcuts.render_to_response('cleaned-page.html', {
      'cleaned_content': cleaned_content,
      'full_content': full_content,
      })
