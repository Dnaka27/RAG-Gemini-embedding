from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("documents/upload/", views.upload_document, name="upload_document"),
    path("documents/chunks/", views.list_chunks, name="list_chunks"),
    path("documents/clear/", views.clear_document, name="clear_document"),
    path("questions/ask/", views.ask_question, name="ask_question"),
]
