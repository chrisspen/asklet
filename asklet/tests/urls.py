from django.conf import settings
from django.conf.urls import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    
    url(settings.STATIC_URL[1:]+'(?P<path>.*)$',
        'django.views.static.serve',
        kwargs={'document_root':settings.STATIC_ROOT}),
                       
    (r'^admin/', include(admin.site.urls)),
)

#if settings.DEBUG or 1:
#    import debug_toolbar
#    urlpatterns += patterns('',
#        url(r'^__debug__/', include(debug_toolbar.urls)),
#    )
