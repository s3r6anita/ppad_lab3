# Инфраструктура лабораторной

## Сервисы

| Сервис | Назначение | Доступ с компьютера |
|---|---|---|
| postgres | Аналитическая база ppad_dwh: stg, dds, cdm | localhost:15432 |
| airflow-postgres | Служебная база Airflow | Не опубликован |
| airflow-init | Одноразовая инициализация Airflow | Не требуется |
| airflow-webserver | Интерфейс Airflow | http://localhost:8080 |
| airflow-scheduler | Планирование и выполнение задач | Не опубликован |

Airflow: 2.11.0, Python 3.12, LocalExecutor.
PostgreSQL: образ postgres:16-bookworm.

## Конфигурация

- docker-compose.yml: PostgreSQL DWH и база метаданных Airflow.
- docker-compose.override.yml: компоненты Airflow.
- .env.example: шаблон настроек без реальных секретов.

  -f docker-compose.yml \
- .env: локальные значения, не передается через Git.

В командах явно указываются оба Compose-файла.

## Запуск уже инициализированного окружения

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  up -d --wait \
  postgres airflow-postgres airflow-webserver airflow-scheduler
```

## Проверка

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  ps -a
curl -fsS http://localhost:8080/health
```

Ожидается:
- Четыре постоянно работающих сервиса healthy.
- airflow-init завершен с кодом 0.
- В /health metadatabase и scheduler имеют status healthy.

## Остановка без удаления данных

```bash
docker compose \
  -f docker-compose.override.yml \
  stop
```

## Логи

```bash
docker compose \
  -f docker-compose.yml \
Не выполнять docker compose down -v:
  -f docker-compose.override.yml \
  logs --tail=60 airflow-webserver airflow-scheduler
```

Перед публикацией логов необходимо проверить отсутствие секретов.

## Данные и volumes

- postgres_data: аналитическая база.
- airflow_postgres_data: служебная база Airflow.
- logs/: локальные логи задач, не передаются через Git.

эта команда удаляет volumes вместе с данными.

SQL в /docker-entrypoint-initdb.d выполняется только при первом
создании базы с пустым каталогом данных. Последующие изменения
SQL необходимо применять отдельно.

## Статус передачи команде

Инфраструктура проверена на macOS / ARM64.
Созданы четыре таблицы STG и учетная запись ppad_loader.
Подключение github_stg проверено из контейнера airflow-scheduler.

Реализован DAG github_to_stg: полная загрузка трех репозиториев
из config/repositories.json с сохранением исходных объектов в STG.

Запуск ручной, schedule=None.
Одна задача load_github последовательно обрабатывает репозитории.
Повторные попытки: 2, интервал — 2 минуты.

Проверено:
- Первый запуск создает успешный батч и загружает все страницы.
- Повтор задачи успешного батча не изменяет данные.
- Новый запуск создает отдельный снимок и сохраняет предыдущий.

Восстановление после частичной ошибки пока отдельно не проверялось.
SCD2 и учет обработанных батчей реализуются участником DDS.

Инструкция первоначального развертывания с генерацией секретов
и инструкция восстановления данных будут добавлены перед передачей.
Простого копирования .env.example недостаточно:
значения-заглушки должны быть заменены.

## Подключение Airflow к STG

Connection ID: github_stg.

Соединение задается переменной AIRFLOW_CONN_GITHUB_STG
в общем блоке environment дополнительного Compose-файла.

- Тип: postgres.
- Host: postgres.
- Port: 5432.
- Database: значение POSTGRES_DB.
- Login: ppad_loader.
- Password: значение STG_LOADER_PASSWORD из локального .env.

Это отдельное подключение к DWH, не к метабазе Airflow.
Соединение из environment не отображается в списке Connections UI.

После изменения переменных окружения сервисы нужно
пересоздать через docker compose up -d, а не только restart.

## Подготовка STG в существующей базе

После создания схем необходимо применить SQL в следующем порядке:

1. sql/02_create_stg_tables.sql — таблицы, ограничения и индекс.
2. sql/04_setup_stg_loader.sql — учетная запись и права загрузчика.

sql/03_check_stg.sql — диагностические SELECT-запросы, а не миграция.

Применение таблиц:

```bash
docker compose exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  < sql/02_create_stg_tables.sql
```

Настройка загрузчика из доверенного локального .env:

```bash
(
  set -a
  . ./.env
  set +a

  docker compose exec -T -e STG_LOADER_PASSWORD postgres sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
    < sql/04_setup_stg_loader.sql
)
```

Проверка STG:

```bash
docker compose exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  < sql/03_check_stg.sql
```

Не запускать все файлы sql/ автоматически по маске:
часть файлов содержит проверки или требует переменных окружения.

## GitHub API

GITHUB_TOKEN хранится только в локальном .env.
В .env.example находится заглушка.

Токен передается в airflow-scheduler через environment.
При изменении токена scheduler необходимо пересоздать:

```bash
docker compose up -d --wait --wait-timeout 180 airflow-scheduler
```

Проверка доступа ко всем настроенным источникам:

```bash
docker compose exec -T airflow-scheduler python - < scripts/check_github_api.py
```

## Ручной запуск загрузки

Включить DAG:

```bash
docker compose exec -T airflow-scheduler airflow dags unpause github_to_stg
```

Создать новый запуск с уникальным run_id:

```bash
docker compose exec -T airflow-scheduler airflow dags trigger -r "snapshot_$(date -u +%Y%m%dT%H%M%SZ)" github_to_stg
```

Проверить запуски:

```bash
docker compose exec -T airflow-scheduler airflow dags list-runs -d github_to_stg
```

Логи задачи доступны в веб-интерфейсе Airflow.

## Проверки данных

- sql/05_check_first_load.sql — проверка запуска first_stg_load.
- sql/06_check_snapshots.sql — проверка первых двух снимков.

Это диагностические запросы, а не миграции.
Код в Git не содержит сами данные PostgreSQL.