# DDS: запуск и проверки

## Статус

Реализованы и проверены:
- схема DDS и ограничения SCD2;
- преобразование JSON STG в типизированные бизнес-поля;
- SHA-256 по нормализованным бизнес-полям;
- загрузка успешных батчей по started_at, batch_id;
- учет обработанных батчей;
- транзакция на один батч;
- сессионная блокировка параллельного загрузчика;
- отдельная сервисная роль ppad_dds_loader;
- загрузка и закрытие версий под сервисной ролью;
- откат при ошибке и повторная обработка после ее устранения.

Пока не выполнены:
- подключение загрузчика к Airflow;
- интеграция с общей рабочей ppad_dwh;
- передача результата участнику CDM.

Первичные проверки выполнены под ppad_admin.
Дополнительно проверена загрузка под ppad_dds_loader:
чтение STG, вставка новых версий, закрытие старых
и регистрация обработанного батча.

Контракт модели и временной семантики:
docs/dds_contract.md.

## Базы

- ppad_dwh: база, создаваемая основной Compose-конфигурацией.
  У первого участника это рабочая база API → STG.
- ppad_dds_dev: локальная разработка на исходном архиве STG.
- ppad_dds_test: отдельная база с синтетическими тестовыми батчами.

Новые данные ppad_dwh автоматически в ppad_dds_dev не попадают.

Не переносить синтетические батчи из ppad_dds_test
в рабочую базу или демонстрационные данные.

Локальные данные PostgreSQL не передаются через Git.

## Требования

Проверенное окружение:
- macOS, Apple Silicon;
- PostgreSQL 16.15 в Docker;
- Python 3.12.15 через uv;
- psycopg[binary] 3.3.6.

Для ручного запуска используется только docker-compose.yml.
Airflow на этом этапе не нужен.

Все приведенные команды выполняются из корня репозитория.

Перейти в корень из любого подкаталога репозитория:

```bash
cd "$(git rev-parse --show-toplevel)"
```

Локальный .env и каталог .venv не должны попадать в Git.
Пароли и токены не передаются в чат или документацию.

## Первичная подготовка PostgreSQL и STG

Выполняется один раз в новом локальном окружении.

1. Подготовить локальный .env по .env.example.
2. Задать собственный POSTGRES_PASSWORD.
3. Открыть Docker Desktop и дождаться запуска движка.
4. Запустить PostgreSQL:

```bash
docker compose -f docker-compose.yml up -d --wait --wait-timeout 180 postgres
```

5. Проверить контейнер:

```bash
docker compose -f docker-compose.yml ps
```

Ожидается postgres со статусом healthy.

6. Проверить целостность архива STG и восстановить его
   в новую базу ppad_dds_dev по docs/stg_handoff.md.

При проверенной локальной раскладке архивы находятся
в соседнем каталоге:

```text
../imports/stg_snapshot.dump
../imports/stg_snapshot.dump.sha256
```

В исходном файле контрольной суммы записан путь exports/.
Для текущего расположения файлов проверка выполняется так:

```bash
awk '{print $1 "  ../imports/stg_snapshot.dump"}' ../imports/stg_snapshot.dump.sha256 | shasum -a 256 -c -
```

Ожидается OK. При несовпадении суммы восстановление не выполнять.

Создание новой базы:

```bash
docker compose -f docker-compose.yml exec -T postgres sh -c 'createdb -U "$POSTGRES_USER" --template=template0 ppad_dds_dev'
```

Восстановление:

```bash
docker compose -f docker-compose.yml exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d ppad_dds_dev --no-owner --no-acl --single-transaction' < ../imports/stg_snapshot.dump
```

Сразу проверить код завершения:

```bash
echo $?
```

Ожидается 0.

Если ppad_dds_dev уже существует, остановиться
и выяснить ее состояние. Не удалять базу автоматически.

До восстановления не применять 02_create_stg_tables.sql:
архив уже содержит структуру STG.

Не использовать --clean для обхода конфликтов восстановления.

Проверки восстановленного STG:

```bash
docker compose -f docker-compose.yml exec -T postgres sh -c 'psql -X -U "$POSTGRES_USER" -d ppad_dds_dev -v ON_ERROR_STOP=1 -P pager=off' < sql/03_check_stg.sql
```

```bash
docker compose -f docker-compose.yml exec -T postgres sh -c 'psql -X -U "$POSTGRES_USER" -d ppad_dds_dev -v ON_ERROR_STOP=1 -P pager=off' < sql/06_check_snapshots.sql
```

Для переданного архива ожидаются:
- load_batches: 2 успешных батча;
- repository_loads: 6 строк;
- github_repositories_raw: 6 строк;
- github_issues_raw: 2440 строк.

## Создание таблиц DDS

Применить миграцию один раз после восстановления STG:

```bash
docker compose -f docker-compose.yml exec -T postgres sh -c 'psql -X -U "$POSTGRES_USER" -d ppad_dds_dev -v ON_ERROR_STOP=1 -P pager=off' < sql/07_create_dds_tables.sql
```

Миграция создает:
- схему dds;
- расширение btree_gist;
- dds.repositories_scd2;
- dds.issues_scd2;
- dds.processed_batches;
- ограничения и индексы.

Для применения нужны административные права
или соответствующие права на создание объектов.

Не запускать миграцию повторно поверх существующих таблиц DDS.
Не запускать все SQL-файлы по маске.

## Создание Python-окружения

Установить uv, если он еще отсутствует:

```bash
brew install uv
```

Только если рабочей .venv еще нет:

```bash
uv venv --python 3.12.15 --managed-python --seed .venv
source .venv/bin/activate
python -m pip install -r requirements-dds.txt
```

Проверка:

```bash
python -c 'import sys, psycopg; print("Python:", sys.version.split()); print("Psycopg:", psycopg.__version__)'
```

На проверенном Mac Homebrew Python 3.14.4 не смог
импортировать pyexpat из-за несовместимости с системным Expat.
Для проекта использован независимый Python через uv.

Не пересоздавать исправную .venv при каждом запуске.
В новом терминале достаточно ее активировать.

## Сервисная роль DDS

Штатная учетная запись: ppad_dds_loader.

Пароли:
- POSTGRES_PASSWORD: пароль локального администратора ppad_admin;
- DDS_LOADER_PASSWORD: пароль сервисной роли ppad_dds_loader.

Значения хранятся только в локальном .env.
В .env.example должны находиться только заглушки.

Роль имеет:
- CONNECT к базе, в которой применен скрипт настройки;
- USAGE схем stg и dds;
- SELECT четырех таблиц STG;
- SELECT и INSERT трех таблиц DDS;
- UPDATE только valid_to и is_current исторических таблиц;
- USAGE identity-последовательностей DDS.

Не выдаются:
- административные привилегии;
- запись в STG;
- DELETE и TRUNCATE таблиц STG/DDS;
- CREATE в схемах stg и dds;
- UPDATE бизнес-полей исторических версий;
- UPDATE существующих отметок processed_batches.

Роль не является владельцем таблиц DDS.
Обычная работа загрузчика не требует административного пароля.

## Подготовка пароля сервисной роли

После создания Python-окружения выполнить:

```bash
python - <<'PY'
import secrets
from pathlib import Path

path = Path(".env")
content = path.read_text()

if any(
    line.startswith("DDS_LOADER_PASSWORD=")
    for line in content.splitlines()
):
    print("DDS_LOADER_PASSWORD already exists; file unchanged")
else:
    with path.open("a") as file:
        file.write(
            "\n# DDS loader database password\n"
            f"DDS_LOADER_PASSWORD={secrets.token_hex(24)}\n"
        )
    print("DDS loader password added to .env")

path.chmod(0o600)
PY
```

Если строка уже существует, проверить локально,
что она содержит реальный пароль, а не заглушку.

Не выводить пароль в общий лог и не добавлять .env в Git.

## Настройка прав сервисной роли

После создания таблиц администратор применяет:

```bash
(
  export DDS_LOADER_PASSWORD="$(sed -n 's/^DDS_LOADER_PASSWORD=//p' .env)"

  if [ -z "$DDS_LOADER_PASSWORD" ]; then
    echo "DDS_LOADER_PASSWORD не найден в .env"
    exit 1
  fi

  docker compose -f docker-compose.yml exec -T \
    -e DDS_LOADER_PASSWORD \
    postgres sh -c \
    'psql -X -U "$POSTGRES_USER" -d ppad_dds_dev -v ON_ERROR_STOP=1 -P pager=off' \
    < sql/09_setup_dds_loader.sql
)
```

Команда извлечения пароля рассчитана на созданное выше
hex-значение без кавычек и пробелов.

Проверка эффективных прав:

```bash
docker compose -f docker-compose.yml exec -T postgres sh -c 'psql -X -U "$POSTGRES_USER" -d ppad_dds_dev -v ON_ERROR_STOP=1 -P pager=off' < sql/10_check_dds_loader.sql
```

Проверка использует SET LOCAL ROLE внутри транзакции.
Она проверяет права, но сама по себе не проверяет пароль.

Для другой базы необходимо явно заменить имя базы
в командах настройки и проверки.

Роль и пароль общие для кластера PostgreSQL,
а права на объекты назначаются в каждой базе отдельно.

Скрипт повторно задает пароль из DDS_LOADER_PASSWORD.
Не менять его при применении к другой базе
без согласованного обновления клиентов.

Скрипт настройки прав не является автоматической миграцией:
он требует переменной окружения с паролем.

## Возобновление работы

Открыть Docker Desktop и дождаться запуска движка.
Перейти в корень репозитория.

```bash
docker compose -f docker-compose.yml up -d --wait --wait-timeout 180 postgres
source .venv/bin/activate
```

Активированная .venv не мешает выполнению Docker-команд.
Выходить из нее для работы с docker compose не нужно.

## Диагностическая проверка подключения

```bash
python scripts/check_dds_connection.py
```

Этот диагностический скрипт подключается к ppad_dds_dev
под ppad_admin и запрашивает POSTGRES_PASSWORD.

Он только читает базу и выводит текущие количества.
После загрузки DDS количества уже не будут нулевыми.

Проверка входа именно сервисной роли выполняется
штатной командой загрузчика с --user ppad_dds_loader.

## Преобразование без записи

```bash
python scripts/check_dds_transform.py
```

Этот диагностический скрипт также использует ppad_admin
и запрашивает POSTGRES_PASSWORD.

Проверяет преобразование успешных снимков и сравнивает
бизнес-хеши соседних снимков.

Это не полная проверка согласованности батча:
она выполняется загрузчиком перед записью.

## Штатная загрузка

```bash
python scripts/load_dds.py --database ppad_dds_dev --user ppad_dds_loader --apply
```

При запросе вводить DDS_LOADER_PASSWORD,
а не POSTGRES_PASSWORD.

Параметры подключения:
- --host: по умолчанию 127.0.0.1;
- --port: по умолчанию 15432;
- --database: обязателен;
- --user: для штатного запуска передавать ppad_dds_loader;
  значение по умолчанию в CLI пока остается ppad_admin;
- --apply: обязательное подтверждение записи.

Пароль запрашивается скрытым вводом.
Если PGPASSWORD уже задан в окружении процесса,
используется он без запроса.

Чтобы гарантированно получить запрос пароля:

```bash
(
  unset PGPASSWORD
  python scripts/load_dds.py \
    --database ppad_dds_dev \
    --user ppad_dds_loader \
    --apply
)
```

Загрузчик сам .env не читает.

Не передавать пароль аргументом командной строки
и не сохранять его в коде.

Успешный запуск без новых батчей завершается сообщениями:

```text
processed_batches=0
DDS_LOAD_OK
```

## Поведение при ошибке

Изменения текущего батча откатываются.
Ранее успешно завершенные батчи остаются обработанными.

После устранения причины повторить ту же команду.
Не удалять processed_batches для принудительного повтора.
Не очищать исторические таблицы.

При password authentication failed:
- проверить имя пользователя;
- использовать пароль соответствующей роли;
- проверить, не задан ли посторонний PGPASSWORD;
- не менять права роли для исправления ошибки пароля.

При DDS_LOADER_ALREADY_RUNNING проверить другой загрузчик
или тестовую сессию, удерживающую advisory lock (741203, 1).
Не обходить блокировку изменением ее ключа.

При LATE_BATCH_REQUIRES_REBUILD остановиться:
запоздавший батч требует отдельного решения
о перестроении истории.

При ошибках прав проверить:
- базу подключения;
- пользователя подключения;
- применение sql/09_setup_dds_loader.sql именно в этой базе.

Не выдавать суперпользователя для обхода ошибки прав.

## Автоматические тесты преобразований

Из корня репозитория:

```bash
python -m unittest discover -s tests -p 'test_dds_transform.py' -v
```

Проверено 11 тестов:
- независимость хеша от порядка labels/assignees;
- изменение хеша при изменении бизнес-полей;
- исключение технических и невыбранных полей;
- нормализация часовых поясов;
- проверка типов и идентификаторов;
- отклонение дубликатов элементов массивов;
- поддержка отсутствующего автора;
- отсутствие изменения входного JSON.

Эти тесты не подключаются к PostgreSQL.

## Проверенные интеграционные сценарии

### Исходные данные в ppad_dds_dev

На исходных двух батчах:
- 3 текущие версии репозиториев;
- 1220 текущих версий issues/PR;
- 2 обработанных батча;
- повтор не изменил подписи всех трех таблиц DDS.

### Изменение SCD2 и восстановление в ppad_dds_test

Последовательность проверки:

1. Создана отдельная копия ppad_dds_dev
   после обработки двух исходных батчей.
2. Применен tests/sql/01_scd2_change.sql:
   изменение одного репозитория и одного issue.
3. Загрузка третьего батча создала и закрыла
   по одной версии в каждой исторической таблице.
4. Применен tests/sql/02_rollback_setup.sql:
   четвертый батч и триггер принудительной ошибки.
5. Загрузка завершилась DDS_TEST_FORCED_FAILURE.
   Подписи строк DDS до и после ошибки совпали.
6. Применен tests/sql/03_rollback_cleanup.sql:
   удаление тестового триггера и функции.
7. Повтор успешно обработал четвертый батч.
8. tests/sql/04_check_recovery.sql подтвердил
   непрерывность границ версий и ожидаемые количества.
9. Следующий повтор обработал 0 батчей.

Состояние после обработки четвертого батча:
- repositories_scd2: 5 версий, 3 текущие, 2 закрытые;
- issues_scd2: 1222 версии, 1220 текущих, 2 закрытые;
- processed_batches: 4 строки;
- broken_version_boundaries: 0.

### Загрузка под сервисной ролью

1. sql/09_setup_dds_loader.sql применен в ppad_dds_dev
   и ppad_dds_test.
2. sql/10_check_dds_loader.sql подтвердил ограниченные права.
3. tests/sql/05_service_role_batch.sql создал пятый тестовый батч.
4. Загрузчик под ppad_dds_loader вставил и закрыл
   по одной версии репозитория и issue.
5. broken_version_boundaries остался равным 0.

После обработки пятого батча:
- repositories_scd2: 6 версий, 3 текущие, 3 закрытые;
- issues_scd2: 1223 версии, 1220 текущих, 3 закрытые;
- processed_batches: 5 строк;
- broken_version_boundaries: 0.

Подготовка синтетических батчей выполняется администратором,
поскольку требует записи в STG.
Сервисной роли запись в STG не выдается.

Файлы подготовки tests/sql/ проверяют имя ppad_dds_test.
Они запускаются один раз и требуют указанного исходного состояния.

tests/sql/04_check_recovery.sql только читает данные.

Не запускать тестовые сценарии автоматически по маске.
Не применять их к ppad_dds_dev или ppad_dwh.

Пропуски identity после отката допустимы.

## Проверка параллельного запуска

В Query Tool базы ppad_dds_test проверить базу:

```sql
SELECT current_database();
```

Один раз получить блокировку:

```sql
SELECT pg_try_advisory_lock(741203, 1);
```

Ожидается true.

Не закрывая сессию, запустить загрузчик из терминала:

```bash
python scripts/load_dds.py --database ppad_dds_test --user ppad_dds_loader --apply
```

Ожидается DDS_LOADER_ALREADY_RUNNING.

В той же сессии pgAdmin освободить блокировку:

```sql
SELECT pg_advisory_unlock(741203, 1);
```

Ожидается true.

Повторный запуск должен завершиться успешно.
Если все батчи обработаны, ожидается processed_batches=0.

Проверка отказа при занятой блокировке и успешного
запуска после освобождения выполнена под ppad_admin.
Получение блокировки сервисной ролью также подтверждено
ее успешной загрузкой пятого батча.

## Контроль содержимого DDS

```bash
docker compose -f docker-compose.yml exec -T postgres sh -c 'psql -X -U "$POSTGRES_USER" -d ppad_dds_dev -v ON_ERROR_STOP=1 -P pager=off' < sql/08_check_dds_fingerprints.sql
```

Для тестовой базы заменить имя на ppad_dds_test.

Подписи рассчитываются по всем полям строк,
включая технические поля и время обработки.

Они используются для сравнения состояния одной базы
до и после действия, а не как фиксированные ожидаемые
значения для разных установок.

Проверка подписей не сравнивает состояние
identity-последовательностей.

## Подключение pgAdmin 4

Локальные параметры:
- Host: 127.0.0.1;
- Port: 15432;
- Maintenance database: ppad_dds_dev;
- Username: ppad_admin;
- Password: локальный POSTGRES_PASSWORD.

Для проверки сервисного подключения:
- Username: ppad_dds_loader;
- Password: DDS_LOADER_PASSWORD.

Перед выполнением SQL проверить выбранную базу:

```sql
SELECT current_database(), current_user;
```

## Завершение работы

Дождаться завершения загрузчика, затем:

```bash
docker compose -f docker-compose.yml stop --timeout 60 postgres
deactivate
```

После остановки можно закрыть Docker Desktop.

Не выполнять docker compose down -v:
том содержит все локальные базы проекта.

## Дальнейшая интеграция

Для общей демонстрации требуется:
1. Применить миграцию DDS в рабочей ppad_dwh.
2. Настроить сервисную роль в этой базе
   с локальным паролем соответствующего окружения.
3. Обеспечить доступность модулей загрузчика
   и зависимости Psycopg в окружении Airflow.
4. Вызывать DDS только после успешной загрузки STG.
5. Проверить общий пайплайн и повторное выполнение.
6. Передать модель и правила чтения участнику CDM.

Внутри Docker-сети адрес PostgreSQL отличается
от локального подключения с Mac:
- host: postgres;
- port: 5432.

Параметры подключения должны соответствовать
окружению выполнения.

Архив с синтетическими тестовыми данными
для интеграции не используется.