from django.contrib import admin
from django.urls import path

import main

urlpatterns = [
    path(r'', main.Main),
    path(r'page', main.CleanPage),
    path(r'feed', main.CleanFeed),
    ]
