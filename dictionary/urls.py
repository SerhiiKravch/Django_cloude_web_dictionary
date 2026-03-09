from django.urls import path

from . import views

app_name = "dictionary"

urlpatterns = [
    path("", views.word_list, name="word_list"),
    path("word/<slug:slug>/", views.word_detail, name="word_detail"),
]
