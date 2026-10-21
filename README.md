# ППАД — лабораторная работа 3

## Тема

Аналитика активности публичных GitHub-репозиториев из экосистемы Kotlin Multiplatform (`arkivanov/Decompose`, `arkivanov/MVIKotlin`, `arkivanov/Essenty`).

## Архитектура

```
GitHub REST API
      ↓ (Airflow DAG: github_to_stg)
PostgreSQL STG (Raw JSON payloads, load_batches, repository_loads)
      ↓ (Airflow DAG: dds_to_cdm / scripts/load_dds.py)
PostgreSQL DDS (SCD2 historical versions, btree_gist exclusion constraints)
      ↓ (Airflow DAG: dds_to_cdm / scripts/load_cdm.py)
PostgreSQL CDM (Analytical Data Marts: summary, history, monthly, contributors, labels, lifecycle)
      ↓ (ppad_bi_reader)
Metabase BI / Standalone HTML Dashboard Preview (docs/bi_dashboard_preview.html)
```

Apache Airflow управляет загрузками и зависимостями задач.  
Окружение разворачивается через Docker Compose.

## Ответственность участников

1. **Участник 1 (Рахманов Сергей):** Инфраструктура, оркестрация, GitHub REST API → STG (`dags/github_to_stg.py`, `sql/01`–`06`, `docs/infrastructure.md`, `docs/stg_contract.md`).
2. **Участник 2 (Рахманова Софья):** STG → DDS, историчность SCD2, проверки качества (`scripts/load_dds.py`, `sql/07`–`10`, `docs/dds_contract.md`, `docs/dds_runbook.md`).
3. **Участник 3 (Звездаков Александр):** DDS → CDM, аналитические витрины, роли загрузчика/аналитика, дашборд Metabase / HTML Preview, Airflow интеграция (`scripts/load_cdm.py`, `sql/11`–`18`, `dags/dds_to_cdm.py`, `docs/cdm_contract.md`, `docs/cdm_runbook.md`, `docs/bi_dashboard_preview.html`).

## Статус

- **Инфраструктура:** Развернуты PostgreSQL DWH (схемы `stg`, `dds`, `cdm`) и Apache Airflow 2.11.0 (LocalExecutor, scheduler, webserver, healthchecks), а также Metabase v0.50.26.
- **Слой STG:** Реализован и проверен DAG `github_to_stg` со сбором срезов репозиториев и issues в сырые JSONB таблицы.
- **Слой DDS:** Реализована версионность SCD2 (`valid_from`, `valid_to`, `is_current`, `btree_gist`), сервисная роль `ppad_dds_loader`, тесты идемпотентности и устойчивости к сбоям.
- **Слой CDM & BI:** Созданы 6 аналитических витрин с жесткими ограничениями целостности, сервисные роли `ppad_cdm_loader` и `ppad_bi_reader`, транзакционный загрузчик `load_cdm.py`, DAG `dds_to_cdm`, 8 аналитических запросов Metabase (`sql/18_metabase_bi_queries.sql`), генератор автономного HTML-дашборда и сквозные тесты качества.

Инструкция управления инфраструктурой: [docs/infrastructure.md](docs/infrastructure.md).

## Безопасность и разграничение доступа

Реальные токены и пароли не хранятся в Git. Шаблон переменных окружения: `.env.example`.  
Доступ к слоям хранилища строго изолирован по принципу наименьших привилегий:
- `ppad_loader` — запись в `stg`, чтение не выходит за рамки STG.
- `ppad_dds_loader` — чтение из `stg`, запись в `dds`, нет доступа к `cdm`.
- `ppad_cdm_loader` — чтение из `dds`, запись в `cdm`, нет доступа к `stg`.
- `ppad_bi_reader` — строго чтение `SELECT` в схеме `cdm`, нет доступа к `dds` и `stg`.

## Контракты между участниками и регламенты

Код, конфигурация и документация передаются через этот репозиторий.  
Экспорт данных STG передается отдельно.

- Контракт STG: [docs/stg_contract.md](docs/stg_contract.md).
- Контракт DDS (SCD2): [docs/dds_contract.md](docs/dds_contract.md).
- Регламент и эксплуатация DDS: [docs/dds_runbook.md](docs/dds_runbook.md).
- Контракт витрин данных CDM: [docs/cdm_contract.md](docs/cdm_contract.md).
- Регламент запуска и верификации CDM: [docs/cdm_runbook.md](docs/cdm_runbook.md).
- Интерактивный дашборд (HTML Preview): [docs/bi_dashboard_preview.html](docs/bi_dashboard_preview.html).

## Структура репозитория

- [/config](config) — перечень анализируемых публичных GitHub-репозиториев (`repositories.json`)
- [/dags](dags) — DAG-пайплайны Apache Airflow:
  - [github_to_stg.py](dags/github_to_stg.py) — выгрузка срезов из GitHub REST API в STG
  - [dds_to_cdm.py](dags/dds_to_cdm.py) — сквозная цепочка загрузки STG → DDS → CDM и верификация качества витрин
- [/docs](docs) — документация проекта и регламенты:
  - [infrastructure.md](docs/infrastructure.md) — управление контейнерами, Airflow и базой данных
  - [stg_contract.md](docs/stg_contract.md) — спецификация сырого слоя STG
  - [dds_contract.md](docs/dds_contract.md) — контракт исторического слоя DDS (SCD2)
  - [dds_runbook.md](docs/dds_runbook.md) — регламент запуска и проверок DDS
  - [cdm_contract.md](docs/cdm_contract.md) — контракт аналитических витрин CDM
  - [cdm_runbook.md](docs/cdm_runbook.md) — инструкция развертывания витрин CDM, ролей и Metabase
  - [bi_dashboard_preview.html](docs/bi_dashboard_preview.html) — автономный интерактивный BI-отчет
- [/scripts](scripts) — исполняемые скрипты:
  - [check_github_api.py](scripts/check_github_api.py) — проверка доступности GitHub REST API
  - [check_dds_connection.py](scripts/check_dds_connection.py) — проверка подключения к таблицам DDS
  - [check_dds_transform.py](scripts/check_dds_transform.py) — проверка статуса преобразования из STG в DDS
  - [dds_transform.py](scripts/dds_transform.py) — чистые функции нормализации и расчета хешей для DDS
  - [load_dds.py](scripts/load_dds.py) — транзакционный загрузчик срезов STG в SCD2 DDS
  - [check_cdm_connection.py](scripts/check_cdm_connection.py) — проверка подключения и строк в витринах CDM
  - [check_cdm_transform.py](scripts/check_cdm_transform.py) — проверка чистых функций преобразования DDS → CDM
  - [cdm_transform.py](scripts/cdm_transform.py) — чистые функции агрегации и расчета витрин CDM
  - [load_cdm.py](scripts/load_cdm.py) — транзакционный расчет и обновление витрин CDM
  - [bi_html_report.py](scripts/bi_html_report.py) — модуль генерации автономного HTML-отчета дашборда витрин CDM
  - [setup_metabase_dashboard.py](scripts/setup_metabase_dashboard.py) — настройка дашборда и 8 карточек в Metabase / генерация HTML Preview
- [/sql](sql) — SQL-скрипты миграций, сервисных ролей и проверок качества:
  - `01`–`06` — DDL, индексы и проверки слоя STG
  - `07`–`10` — DDL, ограничения SCD2 слоя DDS и сервисная роль `ppad_dds_loader`
  - `11`–`14` — DDL витрин CDM, индексы и сервисная роль `ppad_cdm_loader`
  - `15`–`16` — настройка и аудит прав роли аналитика `ppad_bi_reader`
  - `17_check_cdm_quality.sql` — сквозной скрипт сверки контрольных инвариантов DDS ↔ CDM (Reconciliation)
  - `18_metabase_bi_queries.sql` — 8 аналитических SQL-запросов для дашборда Metabase
- [/tests](tests) — модульные и интеграционные тесты:
  - `sql/01_scd2_change.sql`..`05_service_role_batch.sql` — сценарии проверки версионности, откатов и прав DDS
  - `sql/06_cdm_reconciliation.sql` — переносимый тестовый фикстурный батч для сверки витрин CDM
  - [test_dds_transform.py](tests/test_dds_transform.py) — тесты детерминизма хешей и трансформаций DDS
  - [test_cdm_transform.py](tests/test_cdm_transform.py) — тесты бизнес-метрик и чистых функций CDM
  - [test_dds_to_cdm.py](tests/test_dds_to_cdm.py) — сквозные тесты задач Airflow DAG и запросов Metabase BI
- [docker-compose.yml](docker-compose.yml) — контейнеры PostgreSQL DWH и Airflow PostgreSQL
- [docker-compose.override.yml](docker-compose.override.yml) — сервисы Airflow (init, webserver, scheduler) и Metabase BI
