from django.urls import path

from . import views

app_name = "dictionary"

urlpatterns = [
    path("", views.word_list, name="word_list"),
    path("word/<str:slug>/", views.word_detail, name="word_detail"),
    path("autocomplete/", views.autocomplete_words, name="autocomplete_words"),
]
