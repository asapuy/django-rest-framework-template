from django.conf.urls import include, url
from django.contrib import admin
from django.http import HttpResponse

from administration import urls as administration_urls
from clients import urls as clients_urls

urlpatterns = []

urlpatterns.append(url(r'^api/', include(clients_urls.urlpatterns)))

admin.autodiscover()
urlpatterns.append(url(r'^', include(
    administration_urls.urlpatterns)))
# Make sure to always have a root url so aws doesn't complain with its internal tests to '/'

# Add robots.txt url
robots_res = "User-agent: *\r\nDisallow: /"


def robotstxt(request):
    return HttpResponse(robots_res)


urlpatterns.append(url(r'^robots\.txt$', robotstxt))
