from django.conf.urls import defaults

# Aliases just for familiar syntax.
patterns = defaults.patterns
url = defaults.url

urlpatterns = patterns('',
    url(r'^favicon.ico$', 'views.favicon', name='favicon'),
    url(r'^robots.txt$', 'views.robots', name='robots'),

    url(r'^page$', 'views.cleanPage', name='clean_page'),

    url(r'^$', 'views.home', name='home'),
    )
