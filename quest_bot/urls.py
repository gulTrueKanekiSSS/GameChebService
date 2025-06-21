from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import TemplateView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="GameCheb API",
        default_version='v1',
        description="Документация для вашего API",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # — ваши существующие API-маршруты —
    path('api/', include('api.urls')),  # пример

    # Swagger JSON/YAML
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0),
            name='schema-json'),
    # Swagger UI
    path('swagger/',
         schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
    # Redoc UI (опционально)
    path('redoc/',
         schema_view.with_ui('redoc', cache_timeout=0),
         name='schema-redoc'),
    path("webapp/", TemplateView.as_view(template_name="index.html")),
    path("", TemplateView.as_view(template_name="webapp/index.html")),
]




# (при DEBUG=True manage.py runserver сам отдаёт статику)
