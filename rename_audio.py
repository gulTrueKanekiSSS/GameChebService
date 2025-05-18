import os
import django
from django.conf import settings
import sys

# Добавляем путь к проекту в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quest_bot.settings')
django.setup()

from core.models import Point

def rename_audio_files():
    # Получаем все точки
    points = Point.objects.all()
    
    # Путь к директории с аудио файлами
    audio_dir = os.path.join(settings.MEDIA_ROOT, 'points', 'audio')
    
    # Для каждой точки
    for point in points:
        if point.audio_file:
            # Получаем текущее имя файла
            current_path = point.audio_file.path
            if os.path.exists(current_path):
                # Формируем новое имя файла
                new_filename = f"{point.name}.mp3"
                new_path = os.path.join(audio_dir, new_filename)
                
                try:
                    # Переименовываем файл
                    os.rename(current_path, new_path)
                    print(f"Переименован файл для точки '{point.name}': {os.path.basename(current_path)} -> {new_filename}")
                    
                    # Обновляем путь в базе данных
                    point.audio_file.name = os.path.join('points', 'audio', new_filename)
                    point.save()
                except Exception as e:
                    print(f"Ошибка при переименовании файла для точки '{point.name}': {e}")

if __name__ == "__main__":
    print("Начинаем переименование аудио файлов...")
    rename_audio_files()
    print("Готово!") 