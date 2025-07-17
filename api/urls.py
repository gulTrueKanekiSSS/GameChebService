from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    QuestViewSet,
    PromoCodeViewSet,
    UserQuestProgressViewSet,
    RouteViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'quests', QuestViewSet)
router.register(r'promocodes', PromoCodeViewSet)
router.register(r'progress', UserQuestProgressViewSet)
router.register(r'routes', RouteViewSet, basename='route')

urlpatterns = [
    path('', include(router.urls)),
] 