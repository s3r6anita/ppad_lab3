# Контракт CDM (Common Data Model)

## 1. Назначение

Слой CDM (Common Data Model) предназначен для аналитических витрин данных, агрегации метрик репозиториев Kotlin Multiplatform, отслеживания динамики активности, распределения SLA/времени решения и предоставления данных для BI-систем (Metabase).

База данных: `ppad_dwh`.  
Схема: `cdm`.  
Сервисная роль загрузчика: `ppad_cdm_loader` (чтение из `dds`, запись в `cdm`, без доступа к `stg`).  
Роль BI-аналитика: `ppad_bi_reader` (строго `SELECT` в `cdm`, без доступа к `dds` и `stg`).

---

## 2. Структура витрин CDM

### 2.1. `cdm.processed_batches`
Журнал загрузок батчей в CDM. Каждая запись соответствует обработанному батчу из `dds.processed_batches`.

- `batch_id uuid PRIMARY KEY`: Идентификатор батча, внешний ключ на `dds.processed_batches (batch_id)`.
- `stg_started_at timestamptz NOT NULL`: Время старта сбора исходных данных в STG.
- `dds_processed_at timestamptz NOT NULL`: Время завершения обработки версий в DDS.
- `processed_at timestamptz NOT NULL`: Время фиксации витрин CDM.
- `repository_summary_count integer NOT NULL CHECK (>= 0)`: Число строк в витрине `repository_summary`.
- `repository_history_count integer NOT NULL CHECK (>= 0)`: Число строк в витрине `repository_version_history`.
- `activity_monthly_count integer NOT NULL CHECK (>= 0)`: Число строк в витрине `activity_monthly`.
- `contributor_activity_count integer NOT NULL CHECK (>= 0)`: Число строк в витрине `contributor_activity`.
- `label_analytics_count integer NOT NULL CHECK (>= 0)`: Число строк в витрине `label_analytics`.
- `issue_lifecycle_count integer NOT NULL CHECK (>= 0)`: Число строк в витрине `issue_lifecycle_current`.

---

### 2.2. `cdm.repository_summary`
Главная сводная витрина по текущим версиям репозиториев (`dds.repositories_scd2 WHERE is_current`). Ровно одна строка на каждый актуальный репозиторий.

- `github_repository_id bigint PRIMARY KEY CHECK (> 0)`: Натуральный идентификатор GitHub.
- `full_name text NOT NULL UNIQUE`: Полное имя репозитория (например, `arkivanov/Decompose`).
- `description text`, `language text`: Описание и основной язык.
- `archived boolean NOT NULL`: Признак архивации.
- `source_created_at timestamptz NOT NULL`: Дата создания репозитория на GitHub.
- `source_updated_at timestamptz`: Дата последнего обновления репозитория на GitHub.
- `stars_count bigint NOT NULL CHECK (>= 0)`: Количество звезд.
- `forks_count bigint NOT NULL CHECK (>= 0)`: Количество форков.
- `open_issues_api_count bigint NOT NULL CHECK (>= 0)`: Счетчик открытых issue по данным API.
- `total_items_count integer NOT NULL CHECK (>= 0)`: Общее число сущностей (issues + PR) в текущем состоянии.
- `issues_total_count integer NOT NULL CHECK (>= 0)`: Всего issues (без pull requests).
- `prs_total_count integer NOT NULL CHECK (>= 0)`: Всего pull requests.
- `open_issues_count integer NOT NULL CHECK (>= 0)`: Открытые issues.
- `closed_issues_count integer NOT NULL CHECK (>= 0)`: Закрытые issues.
- `issue_close_rate_pct numeric(5,2) NOT NULL CHECK (BETWEEN 0 AND 100)`: Процент закрытия issues: `closed_issues / total_issues * 100%`.
- `open_prs_count integer NOT NULL CHECK (>= 0)`: Открытые PR.
- `closed_prs_count integer NOT NULL CHECK (>= 0)`: Закрытые PR.
- `pr_close_rate_pct numeric(5,2) NOT NULL CHECK (BETWEEN 0 AND 100)`: Процент закрытия PR: `closed_prs / total_prs * 100%`.
- `avg_issue_resolution_hours numeric(12,2)`: Среднее время решения закрытых issues (часы).
- `median_issue_resolution_hours numeric(12,2)`: Медиана времени решения закрытых issues (часы).
- `avg_pr_resolution_hours numeric(12,2)`: Среднее время решения закрытых PR (часы).
- `median_pr_resolution_hours numeric(12,2)`: Медиана времени решения закрытых PR (часы).
- `unique_authors_count integer NOT NULL CHECK (>= 0)`: Число уникальных авторов issues/PR.
- `unassigned_open_items_count integer NOT NULL CHECK (>= 0)`: Число открытых сущностей без назначенных исполнителей.
- `unlabeled_open_items_count integer NOT NULL CHECK (>= 0)`: Число открытых сущностей без меток.
- `first_item_created_at timestamptz`: Дата создания самого раннего issue/PR.
- `last_item_created_at timestamptz`: Дата создания последнего issue/PR.
- `last_item_closed_at timestamptz`: Дата закрытия последнего закрытого issue/PR.
- `repository_versions_count integer NOT NULL CHECK (>= 1)`: Количество версий репозитория в истории SCD2.
- `issue_versions_changed_count integer NOT NULL CHECK (>= 0)`: Количество сущностей, менявших состояние (>1 версии в SCD2).
- `valid_from timestamptz NOT NULL`: Момент вступления в силу текущей версии в DDS.
- `source_batch_id uuid NOT NULL REFERENCES dds.processed_batches (batch_id)`.
- `cdm_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()`.

---

### 2.3. `cdm.repository_version_history`
Полная история версий репозиториев из SCD2 с расчетом дельт между последовательными срезами.

- `repository_version_id bigint PRIMARY KEY`: Суррогатный ключ версии из `dds.repositories_scd2`.
- `github_repository_id bigint NOT NULL CHECK (> 0)`: Идентификатор репозитория.
- `full_name text NOT NULL`: Имя репозитория.
- `version_number integer NOT NULL CHECK (>= 1)`: Номер версии по порядку (1, 2, ...).
- `stars_count bigint NOT NULL CHECK (>= 0)`: Число звезд на момент версии.
- `stars_delta bigint NOT NULL`: Прирост/убыль звезд относительно предыдущей версии (0 для v1).
- `forks_count bigint NOT NULL CHECK (>= 0)`: Число форков.
- `forks_delta bigint NOT NULL`: Изменение форков (0 для v1).
- `open_issues_count bigint NOT NULL CHECK (>= 0)`: Число открытых issues по API.
- `open_issues_delta bigint NOT NULL`: Изменение открытых issues (0 для v1).
- `archived boolean NOT NULL`: Статус архивации.
- `valid_from timestamptz NOT NULL`, `valid_to timestamptz`, `is_current boolean NOT NULL`.
- `source_batch_id uuid NOT NULL REFERENCES dds.processed_batches (batch_id)`.
- `cdm_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()`.

---

### 2.4. `cdm.activity_monthly`
Помесячная динамика создания и закрытия сущностей в разрезе репозитория и типа (`issue` или `pull_request`).

- `github_repository_id bigint NOT NULL CHECK (> 0)`.
- `period_month date NOT NULL`: Первый день календарного месяца (`YYYY-MM-01`).
- `item_type text NOT NULL CHECK (IN ('issue', 'pull_request'))`.
- `full_name text NOT NULL`: Имя репозитория.
- `created_count integer NOT NULL CHECK (>= 0)`: Создано сущностей в данном месяце.
- `closed_count integer NOT NULL CHECK (>= 0)`: Закрыто сущностей в данном месяце.
- `net_open_delta integer NOT NULL`: Чистый прирост бэклога: `created_count - closed_count`.
- `cumulative_created_count integer NOT NULL CHECK (>= 0)`: Накопленный итог созданных сущностей с начала истории.
- `cumulative_closed_count integer NOT NULL CHECK (>= 0)`: Накопленный итог закрытых сущностей.
- `avg_resolution_hours numeric(12,2)`: Среднее время решения сущностей, закрытых в этом месяце.
- `PRIMARY KEY (github_repository_id, period_month, item_type)`.

---

### 2.5. `cdm.contributor_activity`
Аналитика активности контрибьюторов репозиториев.

- `github_repository_id bigint NOT NULL CHECK (> 0)`.
- `author_key text NOT NULL`: Устойчивый ключ автора (`id:<github_id>` либо `login:<login>` / `unknown`).
- `full_name text NOT NULL`: Имя репозитория.
- `author_id bigint CHECK (author_id IS NULL OR author_id > 0)`.
- `author_login text NOT NULL`: Логин автора (или `ghost` при удалении аккаунта на GitHub).
- `total_items_count integer NOT NULL CHECK (> 0)`: Всего создано сущностей данным автором.
- `issues_created_count integer NOT NULL CHECK (>= 0)`: Создано issues.
- `open_issues_count integer NOT NULL CHECK (>= 0)`: Открытых issues.
- `closed_issues_count integer NOT NULL CHECK (>= 0)`: Закрытых issues.
- `prs_created_count integer NOT NULL CHECK (>= 0)`: Создано PR.
- `open_prs_count integer NOT NULL CHECK (>= 0)`: Открытых PR.
- `closed_prs_count integer NOT NULL CHECK (>= 0)`: Закрытых PR.
- `avg_resolution_hours numeric(12,2)`: Среднее время решения закрытых сущностей автора.
- `first_created_at timestamptz NOT NULL`: Дата первой активности.
- `last_created_at timestamptz NOT NULL`: Дата последней активности.
- `PRIMARY KEY (github_repository_id, author_key)`.

---

### 2.6. `cdm.label_analytics`
Статистика использования меток (labels) и метрики скорости их закрытия.

- `github_repository_id bigint NOT NULL CHECK (> 0)`.
- `label_id bigint NOT NULL CHECK (> 0)`: Идентификатор метки GitHub.
- `full_name text NOT NULL`: Имя репозитория.
- `label_name text NOT NULL`: Название метки (например, `bug`, `feature`).
- `total_items_count integer NOT NULL CHECK (> 0)`: Сущностей с данной меткой.
- `issues_count integer NOT NULL CHECK (>= 0)`: Issues с данной меткой.
- `prs_count integer NOT NULL CHECK (>= 0)`: PR с данной меткой.
- `open_items_count integer NOT NULL CHECK (>= 0)`: Открытых сущностей.
- `closed_items_count integer NOT NULL CHECK (>= 0)`: Закрытых сущностей.
- `close_rate_pct numeric(5,2) NOT NULL CHECK (BETWEEN 0 AND 100)`: Процент закрытия.
- `avg_resolution_hours numeric(12,2)`: Среднее время решения сущностей с этой меткой.
- `PRIMARY KEY (github_repository_id, label_id)`.

---

### 2.7. `cdm.issue_lifecycle_current`
Обогащенный детальный срез текущего состояния сущностей для детального drill-down анализа в BI и расчета SLA.

- `github_issue_id bigint PRIMARY KEY CHECK (> 0)`: Идентификатор GitHub issue/PR.
- `github_repository_id bigint NOT NULL CHECK (> 0)`.
- `repository_full_name text NOT NULL`.
- `issue_number bigint NOT NULL CHECK (> 0)`: Номер в репозитории (#123).
- `item_type text NOT NULL CHECK (IN ('issue', 'pull_request'))`.
- `is_pull_request boolean NOT NULL`.
- `title text NOT NULL`.
- `state text NOT NULL CHECK (IN ('open', 'closed'))`.
- `author_id bigint CHECK (author_id IS NULL OR author_id > 0)`.
- `author_login text`.
- `source_created_at timestamptz NOT NULL`, `source_updated_at timestamptz`, `source_closed_at timestamptz`.
- `resolution_hours numeric(12,2)`: Время решения в часах (для закрытых; NULL для открытых).
- `age_days numeric(10,2) NOT NULL CHECK (age_days >= 0)`: Возраст сущности (дней). Для закрытых — время жизни до закрытия; для открытых — текущий возраст от момента создания.
- `labels_count integer NOT NULL CHECK (>= 0)`, `labels_csv text NOT NULL`: Число меток и отсортированный список через запятую.
- `assignees_count integer NOT NULL CHECK (>= 0)`, `assignees_csv text NOT NULL`: Число назначенных лиц и список логинов.
- `scd2_versions_count integer NOT NULL CHECK (>= 1)`: Число зафиксированных версий в `dds.issues_scd2`.
- `valid_from timestamptz NOT NULL`.
- `source_batch_id uuid NOT NULL REFERENCES dds.processed_batches (batch_id)`.
- `cdm_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()`.

---

## 3. Правила расчетов и инварианты

1. **Округление и квантование:**  
   Все проценты (`*_rate_pct`), часы (`*_hours`) и дни (`age_days`) рассчитываются в типе `Decimal` и квантуются до сотых (`0.01`, `ROUND_HALF_UP`).
2. **Нулевой делитель:**  
   При расчете процентов при отсутствии сущностей (`whole == 0`) гарантирован возврат `0.00`.
3. **Согласованность данных (Reconciliation):**  
   - Каждому репозиторию в `dds.repositories_scd2 WHERE is_current` соответствует ровно одна запись в `cdm.repository_summary`.
   - Сумма `total_items_count` в `repository_summary` строго равна числу строк в `dds.issues_scd2 WHERE is_current` и в `cdm.issue_lifecycle_current`.
   - Сумма `created_count` в `cdm.activity_monthly` строго равна общему количеству сущностей.
   - Сумма `total_items_count` в `cdm.contributor_activity` строго равна общему количеству сущностей.
   - Число строк в `cdm.repository_version_history` строго равно общему числу строк в `dds.repositories_scd2`.
4. **Идемпотентность загрузки:**  
   Повторный запуск `scripts/load_cdm.py` без появления новых батчей в `dds.processed_batches` не вносит изменений в базу, возвращает `processed_batches=0`, оставляя хеши и контрольные суммы (`sql/12_check_cdm_fingerprints.sql`) неизменными.

---

## 4. Аналитические запросы для BI (Metabase)

Для визуализации витрин в BI-системе Metabase подготовлен файл [`sql/18_metabase_bi_queries.sql`](../sql/18_metabase_bi_queries.sql), содержащий 8 готовых аналитических запросов, выполняемых под ролью `ppad_bi_reader`:

1. **KPI Summary:** Сводные метрики экосистемы (репозитории, всего задач, доля закрытия, средний SLA, авторы).
2. **Repository Overview:** Сводная таблица по репозиториям (звезды, форки, задачи, PR, SLA и версии SCD2).
3. **Monthly Activity Dynamics:** Помесячная динамика создания и закрытия задач и PR с накопленным итогом.
4. **Issues vs PRs Breakdown:** Соотношение Issues и Pull Requests и доля PR в структуре каждого проекта.
5. **Resolution Time & Age Distribution:** Распределение SLA (p50, p90) и среднего возраста открытых задач.
6. **Top Contributors:** Рейтинг наиболее активных контрибьюторов экосистемы.
7. **Label Analytics:** Популярность тегов/меток и результативность их закрытия.
8. **SCD2 Repository Version History:** Хронология версий SCD2 с дельтами прироста звезд, форков и задач.

---

## 5. Модули отчетности и визуализации

Для автоматизированной выгрузки аналитики и публикации дашборда используются:
- [`scripts/setup_metabase_dashboard.py`](../scripts/setup_metabase_dashboard.py) — инициализация коллекций и карточек дашборда в Metabase API, а также экспорт автономного HTML-отчета.
- [`scripts/bi_html_report.py`](../scripts/bi_html_report.py) — модуль сборки автономного HTML-дашборда ([`docs/bi_dashboard_preview.html`](bi_dashboard_preview.html)) с адаптивной версткой, KPI-виджетами и таблицами на основе аналитических витрин `cdm`.
