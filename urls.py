import os

from django.conf.urls import defaults

import views
from clean import views as clean_views
from train import views as train_views

# Aliases just for familiar syntax.
patterns = defaults.patterns
url = defaults.url

urlpatterns = patterns('',
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(__file__), 'static')}),
    url(r'^favicon.ico$', views.favicon, name='favicon'),
    url(r'^robots.txt$', views.robots, name='robots'),

    # TODO: Put these in urls modules in these packages.
    url(r'^clean/page$', clean_views.page, name='clean_page'),

    url(r'^train/data$', train_views.data, name='train_data'),
    url(r'^train/form$', train_views.form, name='train_form'),

    url(r'^$', views.home, name='home'),
    )
