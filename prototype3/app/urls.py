from django.urls import path, reverse_lazy
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from . import views

# app_name = 'app'

urlpatterns = [
    # Document CRUD
    path('',               views.document_list,   name='document_list'),
    path('create/',        views.document_create, name='document_create'),
    path('<int:pk>/',      views.document_detail, name='document_detail'),
    path('<int:pk>/edit/', views.document_edit,   name='document_edit'),

    # Authentication
    path('register/',      views.register,         name='register'),
    path('login/',         LoginView.as_view(template_name='app/login.html'), name='login'),
    path('logout/',        LogoutView.as_view(),  name='logout'),

    # Find Username / Password Reset
    path('find-username/', views.find_username,   name='find_username'),
    path('find-password/', views.find_password,   name='find_password'),

    path('reset/',
         PasswordResetView.as_view(
             template_name='app/find_password.html',
             email_template_name='app/password_reset_email.html',
             success_url=reverse_lazy('login')
         ),
         name='password_reset'),
    path('reset/done/',
         PasswordResetDoneView.as_view(template_name='app/password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         PasswordResetConfirmView.as_view(
             template_name='app/password_reset_confirm.html',
             success_url=reverse_lazy('login')
         ),
         name='password_reset_confirm'),
    path('reset/complete/',
         PasswordResetCompleteView.as_view(template_name='app/password_reset_complete.html'),
         name='password_reset_complete'),
]
