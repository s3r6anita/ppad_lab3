# CDM и BI: Инструкция по развертыванию и эксплуатации

В данном документе описан регламент развертывания витрин данных CDM (Common Data Model), настройки сервисных ролей загрузчика и BI-аналитика, проведения сквозной загрузки из DDS, проверок качества данных, формирования дашборда Metabase и генерации автономного HTML-отчета.

---

## 1. Требования к окружению

- **ОС:** macOS (Apple Silicon / Intel) или Linux.
- **СУБД:** PostgreSQL 14+ (локальный Homebrew `postgresql@14` на `127.0.0.1:5432` или Docker-контейнер на `127.0.0.1:15432`).
- **Python:** Python 3.11+ с установленными зависимостями (`psycopg[binary]==3.3.6`).
- **Airflow:** Apache Airflow 2.11.0 (для автоматического запуска пайплайна).
- **Metabase:** Metabase v0.50+ (порт 3000) либо просмотр сгенерированного HTML-отчета `docs/bi_dashboard_preview.html`.

---

## 2. Порядок развертывания и инициализации

Все команды выполняются из корня репозитория `ppad_lab3`.

### Шаг 1. Создание схемы и таблиц CDM
Скрипт создает схему `cdm`, таблицы журнала `processed_batches` и 6 аналитических витрин с жесткими ограничениями целостности.

```bash
psql -h 127.0.0.1 -p 5432 -U ppad_admin -d ppad_dwh -f sql/11_create_cdm_tables.sql
```

### Шаг 2. Настройка роли загрузчика CDM (`ppad_cdm_loader`)
Роль наделяется минимальными правами по принципу наименьших привилегий:
- чтение из `dds.repositories_scd2`, `dds.issues_scd2`, `dds.processed_batches`;
- запись в `cdm.*`;
- **нет доступа** к сырым данным `stg`.

```bash
export CDM_LOADER_PASSWORD="secure_cdm_loader_password"
psql -h 127.0.0.1 -p 5432 -U ppad_admin -d ppad_dwh -f sql/13_setup_cdm_loader.sql
```

Проверка прав сервисной роли:
```bash
psql -h 127.0.0.1 -p 5432 -U ppad_admin -d ppad_dwh -f sql/14_check_cdm_loader.sql
```

### Шаг 3. Настройка роли аналитика BI (`ppad_bi_reader`)
Роль имеет права только на чтение (`SELECT`) в схеме `cdm` и не может обращаться к `dds` или `stg`.

```bash
export BI_READER_PASSWORD="secure_bi_reader_password"
psql -h 127.0.0.1 -p 5432 -U ppad_admin -d ppad_dwh -f sql/15_setup_bi_reader.sql
```

Проверка прав роли аналитика:
```bash
psql -h 127.0.0.1 -p 5432 -U ppad_admin -d ppad_dwh -f sql/16_check_bi_reader.sql
```

---

## 3. Загрузка данных из DDS в CDM

Загрузка выполняется скриптом `scripts/load_cdm.py`. Скрипт использует рекомендательную блокировку (PostgreSQL Advisory Lock) для исключения параллельного запуска и обрабатывает все новые батчи из `dds.processed_batches` в единой транзакции `REPEATABLE READ`.

```bash
export PGPASSWORD="$CDM_LOADER_PASSWORD"
.venv/bin/python scripts/load_cdm.py \
    --host 127.0.0.1 \
    --port 5432 \
    --database ppad_dwh \
    --user ppad_cdm_loader \
    --apply
```

Ожидаемый вывод:
```text
database=ppad_dwh
COMMITTED: new_batches=...; repository_summary=...
processed_batches=1
CDM_LOAD_OK
```

### Проверка идемпотентности:
Повторный запуск при отсутствии новых батчей в DDS не изменяет витрины и не обновляет временные метки:
```bash
.venv/bin/python scripts/load_cdm.py \
    --host 127.0.0.1 \
    --port 5432 \
    --database ppad_dwh \
    --user ppad_cdm_loader \
    --apply
```
Ожидаемый вывод:
```text
database=ppad_dwh
processed_batches=0
CDM_LOAD_OK
```

Фиксация и сверка контрольных сумм:
```bash
psql -h 127.0.0.1 -p 5432 -U ppad_admin -d ppad_dwh -f sql/12_check_cdm_fingerprints.sql
```

---

## 4. Контроль качества и реконсиляция данных (Reconciliation)

Скрипт `sql/17_check_cdm_quality.sql` выполняет детальную диагностику и сверку агрегатов между DDS и CDM:
- полнота покрытия текущих версий репозиториев;
- совпадение счетчиков всех сущностей (issues, PR, открытые/закрытые);
- соответствие числа версий в истории SCD2;
- сходимость помесячных и авторских сумм.

Запуск проверки:
```bash
psql -h 127.0.0.1 -p 5432 -U ppad_admin -d ppad_dwh -f sql/17_check_cdm_quality.sql
```

Все проверки в колонке `status` должны иметь статус **`OK`**.

---

## 5. Визуализация и BI-отчетность

### 5.1. Автономный интерактивный отчет (HTML Preview)
Скрипт `scripts/setup_metabase_dashboard.py` (и используемый им модуль `scripts/bi_html_report.py`) генерирует полноценный автономный дашборд с адаптивным дизайном, KPI карточками, диаграммами активности и таблицами детализации:

```bash
export PGPASSWORD="$BI_READER_PASSWORD"
.venv/bin/python scripts/setup_metabase_dashboard.py \
    --host 127.0.0.1 \
    --port 5432 \
    --database ppad_dwh \
    --user ppad_bi_reader \
    --render-html docs/bi_dashboard_preview.html
```

Файл `docs/bi_dashboard_preview.html` можно открыть в любом браузере для визуального анализа метрик. Также функцию генерации можно вызвать напрямую из Python:
```python
from bi_html_report import render_html_report
render_html_report(cursor, "docs/bi_dashboard_preview.html")
```

### 5.2. Автоматическая настройка дашборда и аналитических карточек в Metabase
При развернутом контейнере Metabase (порт 3000):
```bash
.venv/bin/python scripts/setup_metabase_dashboard.py \
    --host postgres \
    --port 5432 \
    --database ppad_dwh \
    --user ppad_bi_reader \
    --metabase-url http://127.0.0.1:3000 \
    --metabase-user admin@example.local \
    --metabase-password "$AIRFLOW_ADMIN_PASSWORD"
```

Команда через REST API Metabase выполняет:
1. Авторизацию и регистрацию подключения к базе `ppad_dwh` под ролью `ppad_bi_reader`;
2. Создание дашборда `"Аналитика репозиториев Kotlin Multiplatform (CDM)"`;
3. Создание 8 нативных SQL-карточек (`POST /api/card`) с визуализациями (таблицы, столбчатые диаграммы) и их компоновку на сетке дашборда (`POST /api/dashboard/{id}/cards`).

### 5.3. Аналитические SQL-запросы (`sql/18_metabase_bi_queries.sql`)
Все 8 аналитических запросов вынесены в файл `sql/18_metabase_bi_queries.sql` и могут выполняться напрямую через `psql` под учетной записью аналитика:

```bash
export PGPASSWORD="$BI_READER_PASSWORD"
psql -h 127.0.0.1 -p 5432 -U ppad_bi_reader -d ppad_dwh -v ON_ERROR_STOP=1 -f sql/18_metabase_bi_queries.sql
```

Перечень запросов:
- **Запрос 1:** `KPI Summary` — агрегаты по экосистеме, закрытым задачам, доле закрытия и SLA;
- **Запрос 2:** `Repository Overview` — таблица активности по каждому репозиторию со счетчиками и версиями SCD2;
- **Запрос 3:** `Monthly Activity Dynamics` — помесячная динамика создания и закрытия с накопленным итогом;
- **Запрос 4:** `Issues vs PRs Breakdown` — распределение сущностей по типам и доля PR;
- **Запрос 5:** `Resolution Time & Age Distribution` — перцентили SLA (p50, p90) и средний возраст открытых задач;
- **Запрос 6:** `Top Contributors` — рейтинг авторов по объему и скорости закрытия вклада;
- **Запрос 7:** `Label Analytics` — востребованность меток и результативность их закрытия;
- **Запрос 8:** `SCD2 Repository Version History` — аудит эволюции параметров репозиториев и дельт по срезам.


---

## 6. Оркестрация через Apache Airflow

DAG `dds_to_cdm` выполняет последовательную цепочку:
1. `load_stg_to_dds` — выгрузка накопленных срезов из STG в DDS (SCD2);
2. `load_dds_to_cdm` — расчет и обновление витрин CDM;
3. `verify_cdm_quality` — валидация контрольных инвариантов и реконсиляция через `sql/17_check_cdm_quality.sql`.

Запуск DAG через Airflow CLI:
```bash
airflow dags trigger dds_to_cdm
```
Либо через веб-интерфейс Airflow по адресу `http://localhost:8080`.

---

## 7. Модульное тестирование

Все бизнес-трансформации покрыты набором модульных тестов:
```bash
.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
```
Ожидается успешное прохождение всех тестов (`OK`).
