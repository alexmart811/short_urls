Сервис для генерации коротких ссылок из длинных. Используется **FastAPI** для обработки запросов, **Redis** для хранения временных данных и **PostgreSQL** для постоянного хранения ссылок.  

## Функционал
- Генерация коротких ссылок из длинных URL.
- Хранение ссылок в базе данных PostgreSQL.
- Автоматическое удаление неиспользуемых ссылок с помощью Celery.
- Авторизация пользователей.
- Использование Redis для кэширования данных.

## Структура проекта
```
│── alembic/ # Миграции базы данных 
│── docker/ # Скрипты для запуска через Docker 
│ ├── app.sh
│ └── celery.sh
│── src/ # Исходный код проекта 
│ ├── auth/ # Модуль аутентификации
│ │ ├── db.py 
│ │ ├── schemas.py 
│ │ └── users.py 
│ ├── redis_folder/ # Работа с Redis
│ │ ├── redis_func.py # Функции для Redis
│ │ └── tasks.py # Фоновые задачи Celery
│ ├── urls/ # Основной функционал сервиса
│ │ ├── models.py # Таблица urls БД
│ │ ├── router.py # Роуты FastAPI
│ │ └── schemas.py # Pydantic-схемы
│ ├── config.py # Настройки проекта
│ ├── main.py # Основной запуск FastAPI
│ └── models.py # Таблица user БД
│── .gitignore 
│── alembic.ini
│── docker-compose.yml
│── Dockerfile
```

## Запуск через Docker
`docker compose up --build`
### Конфиг, с которым запускались контейнеры
```
DB_HOST=db_app
DB_PORT=5432
DB_USER=postgres
DB_PASS=1234
DB_NAME=postgres
REDIS_HOST=redis_app
REDIS_PORT=6379
PYTHONPATH=./src
```

## Описание БД
В сервисе используются база данных с двумя таблицами: User - для хранения зарегистрированных пользователей, Urls - для хранения ссылок
### Таблица `User`
```
**Описание полей:**
| Поле              | Тип         | Описание                          |
|-------------------|-------------|-----------------------------------|
| id                | UUID        | Первичный ключ                    |
| email             | String      | Уникальный email пользователя     |
| hashed_password   | String      | Хеш пароля                        |
| is_active         | Boolean     | Активен ли аккаунт                |
| is_superuser      | Boolean     | Права администратора              |
| is_verified       | Boolean     | Подтвержденный email              |
```
### Таблица `Urls`
```
**Описание полей:**
| Поле              | Тип         | Описание                          |
|-------------------|-------------|-----------------------------------|
| id                | Integer     | Первичный ключ                    |
| user_id           | UUID        | Внешний ключ к таблице users      |
| orig_url          | String      | Оригинальный URL                  |
| short_url         | String      | Сокращенный URL                   |
| expires_at        | TIMESTAMP   | Время истечения срока ссылки      |
| date_of_create    | TIMESTAMP   | Дата создания записи              |
| last_usage        | TIMESTAMP   | Последнее использование           |
| count_ref         | Integer     | Счетчик переходов                 |
```
