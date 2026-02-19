"""Defines URL patterns for rules"""

from django.urls import path

from apps.rules.views import RuleView, RuleEvaluateView

app_name = 'rules'
urlpatterns = [
    path('', RuleView.as_view(), name='rule-list'),
    path('<int:rule_id>/', RuleView.as_view(), name="rule-detail"),
    path('evaluate/', RuleEvaluateView.as_view(), name="rule-evaluate"),
    
]
