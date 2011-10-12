import os

from django.conf.urls import defaults

# Aliases just for familiar syntax.
patterns = defaults.patterns
url = defaults.url

urlpatterns = patterns('',
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(__file__, 'static')}),
    url(r'^favicon.ico$', 'views.favicon', name='favicon'),
    url(r'^robots.txt$', 'views.robots', name='robots'),

    url(r'^page$', 'views.cleanPage', name='clean_page'),
    url(r'^train$', 'views.train', name='train'),

    url(r'^$', 'views.home', name='home'),
    )
