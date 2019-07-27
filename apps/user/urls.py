from django.conf.urls import url
from . import views
urlpatterns = [
    url(r'^register', views.Register.as_view(),name='register'),
    url(r'^active/(.*)', views.Active.as_view(),name='active'),
    url(r'^login/', views.Login.as_view(),name='login'),
    url(r'^logout/', views.Logout.as_view(),name='logout'),

    url(r'^info/', views.Info.as_view(),name='user'),

    url(r'^order/(?P<page>\d+)$', views.Order.as_view(),name='order'),
    url(r'^address/', views.AddressView.as_view(),name='address'),
]
