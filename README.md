# Система уведомлений для учебного заведения

Система предназначена для автоматизации процесса создания и управления уведомлениями об академических задолженностях учащихся.

## Функциональные возможности

- Создание уведомлений о задолженностях по предметам
- Управление шаблонами документов
- Импорт данных об учениках и их задолженностях
- Автоматическая генерация документов
- Учет консультаций и дедлайнов
- Административный интерфейс для управления системой
- Анализ данных о задолженностях

## Структура проекта

```
notification_system/
├── admin/                # Административная часть системы
├── analysis/             # Модуль анализа данных
├── auth/                 # Авторизация и аутентификация
├── database/             # Модели и операции с базой данных
├── flask_session/        # Данные сессий Flask
├── static/               # Статические файлы (CSS, JS, изображения)
├── templates/            # HTML шаблоны
├── utils/                # Вспомогательные утилиты
├── app.py                # Основной файл приложения
├── requirements.txt      # Зависимости проекта
├── .env.example          # Пример файла с переменными окружения
└── __init__.py           # Инициализация пакета
```

## Установка и настройка

### Требования

- Python 3.8+
- SQLite или другая СУБД

### Установка

1. Клонировать репозиторий:
```bash
git clone https://github.com/chas36/notification_system.git
cd notification_system
```

2. Создать и активировать виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/MacOS
venv\Scripts\activate     # для Windows
```

3. Установить зависимости:
```bash
pip install -r requirements.txt
```

4. Настроить переменные окружения:
```bash
# Скопировать пример файла .env.example и переименовать его в .env
cp .env.example .env  # для Linux/MacOS
copy .env.example .env  # для Windows

# Затем отредактировать .env и указать свои значения
```

5. Инициализировать базу данных:
```bash
python -c "from database.db import init_db; init_db()"
```

### Запуск

```bash
flask run
# или
python app.py
```

Приложение будет доступно по адресу: http://127.0.0.1:5001

## API

### Получение списка учеников

```
GET /api/get_students
```

### Получение списка классов

```
GET /api/get_unique_classes
```

### Получение учеников по классу

```
GET /api/get_students_by_class/{class_name}
```

### Получение расписания звонков

```
GET /api/get_schedule_times
```

### Получение предметов по классу

```
GET /api/get_subjects_by_grade/{grade}
```

## Разработка

### Структура базы данных

- `students` - информация об учениках
- `subjects` - учебные предметы
- `template_types` - типы шаблонов уведомлений
- `notifications` - созданные уведомления
- `notification_subjects` - предметы в уведомлениях
- `deadline_dates` - даты дедлайнов для сдачи задолженностей
- `notification_meta` - метаданные уведомлений
- `notification_consultations` - консультации по предметам
- `class_profiles` - профили классов (связь классов и предметов)

## Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для вашей функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте ваши изменения (`git commit -m 'Add some amazing feature'`)
4. Отправьте ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## Лицензия

© 2025 
