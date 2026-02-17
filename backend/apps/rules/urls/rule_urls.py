from django.urls import path
from apps.rules.views.rule_views import rules_index

urlpatterns = [
    path("", rules_index, name="rules_index"),
]
