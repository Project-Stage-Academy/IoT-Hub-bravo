"""Defines URL patterns for rules"""

from django.urls import path

from . import views

app_name = 'rules'
urlpatterns = [
    path('', views.rules_index, name='rules_index'),  # Home page
]
