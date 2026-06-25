# counter/urls.py
from django.urls import path
from . import views

app_name = "counter"

urlpatterns = [
    path("", views.home, name="home"),
    path("bobot/", views.hitung_bobot, name="hitung_bobot"),
    path("api/delete-bobot/<int:pk>/", views.delete_bobot_result, name="delete_bobot_result"),
    path("history/", views.history, name="history"),  
    path("detail/<int:pk>/", views.detail_orthophoto, name="detail_orthophoto"),
    path("api/delete/<int:pk>/", views.delete_result, name="delete_result"),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/signup/', views.signup_view, name='signup'),
    path('accounts/logout/', views.logout_view, name='logout'),
]
