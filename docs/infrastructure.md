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
DAG, таблицы STG и доступ загрузчика к DWH пока не реализованы.

Инструкция первоначального развертывания с генерацией секретов
и инструкция восстановления данных будут добавлены перед передачей.
Простого копирования .env.example недостаточно:
значения-заглушки должны быть заменены.
