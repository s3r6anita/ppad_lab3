# Передача STG участнику DDS

## Что передается

Код и контракт — через Git:
- dags/github_to_stg.py
- config/repositories.json
- docs/stg_contract.md
- sql/02_create_stg_tables.sql
- sql/03_check_stg.sql
- sql/05_check_first_load.sql
- sql/06_check_snapshots.sql

Данные — отдельно:
- exports/stg_snapshot.dump
- exports/stg_snapshot.dump.sha256

Архив содержит структуру и данные только схемы stg.
Он не содержит роли PostgreSQL, пароли, токены, DDS, CDM
или метабазу Airflow. Права доступа не переносятся.

Для работы с готовыми данными GitHub-токен не нужен.

## Проверенное содержимое архива

- stg.load_batches: 2 строки, оба батча success.
- stg.repository_loads: 6 строк.
- stg.github_repositories_raw: 6 строк.
- stg.github_issues_raw: 2440 строк.

На каждый снимок:
- arkivanov/Decompose: 884 объекта.
- arkivanov/Essenty: 194 объекта.
- arkivanov/MVIKotlin: 142 объекта.

Объекты issues включают pull requests.
Отбор только issues: NOT (payload ? 'pull_request').

Архив проверен восстановлением в отдельную базу PostgreSQL 16.
Приведенные количества относятся к переданному архиву,
а не к любому будущему запуску загрузчика.

## Проверка целостности

Поместить оба файла в exports/ и выполнить из корня проекта:

```bash
shasum -a 256 -c exports/stg_snapshot.dump.sha256
```

Ожидается OK.

## Восстановление в отдельную базу

Команды рассчитаны на сервис postgres из нашего Compose.
Использовать PostgreSQL 16 и утилиты pg_restore версии 16.

Создать новую базу:

```bash
docker compose exec -T postgres sh -c 'createdb -U "$POSTGRES_USER" --template=template0 ppad_dds_dev'
```

Восстановить структуру и данные:

```bash
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d ppad_dds_dev --no-owner --no-acl --single-transaction' < exports/stg_snapshot.dump
```

Проверить:

```bash
docker compose exec -T postgres sh -c 'psql -X -U "$POSTGRES_USER" -d ppad_dds_dev -v ON_ERROR_STOP=1 -P pager=off' < sql/03_check_stg.sql
```

```bash
docker compose exec -T postgres sh -c 'psql -X -U "$POSTGRES_USER" -d ppad_dds_dev -v ON_ERROR_STOP=1 -P pager=off' < sql/06_check_snapshots.sql
```

Важно:
- Восстанавливать в новую базу без схемы stg.
- Не применять 02_create_stg_tables.sql до восстановления:
  структура уже включена в архив.
- Если ppad_dds_dev уже существует, остановиться
  и выяснить, какие данные в ней находятся.
- Не использовать --clean для обхода конфликта.
- Схемы dds и cdm этим архивом не создаются.
- Airflow Connection github_stg продолжает указывать на ppad_dwh;
  новая база автоматически к DAG не подключается.

## Правила STG → DDS

1. Читать только батчи со status='success'.
2. Обрабатывать все еще не обработанные успешные батчи
   в порядке started_at, batch_id.
3. Хранить учет обработанных batch_id на стороне DDS.
4. Записывать изменения DDS и отметку обработки
   одного батча в общей транзакции.
5. Повтор обработки не должен создавать новые версии
   при неизменных бизнес-полях.
6. STG не изменять и не очищать.

Натуральный ключ репозитория: payload.id.
Натуральный ключ issue/PR: github_issue_id.
repository_full_name — имя в конфигурации загрузчика,
а не устойчивый идентификатор сущности.
Поле number уникально только внутри репозитория.

Для hash_diff выбирать согласованные бизнес-поля.
Не включать batch_id, loaded_at, source_url.
Вложенные наборы labels и assignees перед хешированием
приводить к стабильному порядку.

SCD2 хранит состояния, наблюдавшиеся при наших загрузках.
Источник не дает атомарный снимок всех страниц.
Отсутствие объекта в следующем батче не доказывает удаление.

Временные метки технической загрузки — не время
фактического изменения объекта в GitHub.
Политику valid_from необходимо согласовать и документировать.

Если выбранные бизнес-поля двух снимков одинаковы,
вторая загрузка не должна создавать новую SCD2-версию.
Для демонстрации реального изменения потребуется
дополнительный снимок с изменившимися бизнес-полями
либо отдельно обозначенный тестовый сценарий.

## Интеграция

ppad_dds_dev — отдельная база для разработки на снимке.
Новые загрузки в ppad_dwh автоматически в нее не попадают.

Для общей демонстрации миграции и загрузчик DDS
необходимо интегрировать с рабочей ppad_dwh.

GitHub-токен и пароль администратора для передачи данных
не требуются. В общей базе участнику DDS нужны отдельные
права чтения STG и записи DDS, а не учетная запись ppad_loader.