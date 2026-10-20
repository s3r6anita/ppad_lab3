# ППАД — лабораторная работа 3

## Тема

Аналитика активности публичных GitHub-репозиториев
из экосистемы Kotlin Multiplatform.

## Архитектура

GitHub REST API → PostgreSQL STG → DDS (SCD2) → CDM → Metabase.

Apache Airflow управляет загрузками и зависимостями задач.
Окружение разворачивается через Docker Compose.

## Ответственность участников

1. Инфраструктура, оркестрация, GitHub API → STG.
2. STG → DDS, проверки качества, SCD2.
3. DDS → CDM, аналитические витрины и Metabase.

## Статус

Работают PostgreSQL DWH и Apache Airflow 2.11.0.
Созданы схемы stg, dds, cdm.
Проверены база метаданных Airflow, scheduler и веб-интерфейс.

Инструкция управления: [docs/infrastructure.md](docs/infrastructure.md).

## Безопасность

Реальные токены и пароли не хранятся в Git.
Шаблон переменных окружения: .env.example.

## Передача результатов

Код, конфигурация и документация передаются через этот репозиторий.
Экспорт данных STG передается отдельно.

Контракт STG описан в [docs/stg_contract.md](docs/stg_contract.md).

Контракт DDS описан в [docs/dds_contract.md](docs/dds_contract.md).

## Структура репозитория

- [/config](config) - перечень анализируемых публичных GitHub-репозиториев
- [/dags](dags) - python-скрипты наполнения STG-хранилища данными из Github API
- [/docs](docs) - документация по проекту: общая инфрастуктурная и отдельно для stg, dds
- [/scripts](scripts) - python-скрипты:
  - [check_github_api.py](scripts/check_github_api.py) проверка доступности Github API
  - [check_dds_connection.py](scripts/check_dds_connection.py) проверка подключения к таблицам DDS
  - [check_dds_transform.py](scripts/check_dds_transform.py) проверка статуса преобразования из STG в DDS 
  - [load_dds.py](scripts/load_dds.py) наполнение таблиц DDS из STG
  - [dds_transform.py](scripts/dds_transform.py) преобразования данных из форматов STG в форматы DDS
- [/sql](sql) - sql-скрипты для создания, настройки и проверок таблиц
- [/test](test) - python- и sql-тесты преобразования данных из STG в DDS
- [docker-compose.yml](docker-compose.yml) - docker-контейнер с postgres, airflow-postgres
- [docker-compose.override.yml](docker-compose.override.yml) - docker-контейнер с сервисами airflow (инициализация, web-сервер и scheduler)
