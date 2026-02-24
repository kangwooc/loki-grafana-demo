from django.urls import path

from api import views

urlpatterns = [
    path("api/hello", views.hello),
    path("api/error", views.trigger_error),
]
