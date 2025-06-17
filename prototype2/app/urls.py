from django.urls import path
from . import views

app_name='app'
urlpatterns=[
    path('',views.form_view,name='form'),
    path('document/<int:pk>/',views.detail_view,name='detail'),
    path('document/<int:pk>/edit/',views.edit_view,name='edit'),
    path('document/<int:pk>/delete/',views.delete_view,name='delete'),
]