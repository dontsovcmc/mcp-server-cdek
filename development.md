# Правила разработки MCP-серверов

## Безопасность

- **Валидация путей** — через `_safe_output_path()`. Никогда не принимать произвольные пути от LLM без проверки. Кроссплатформенная (Windows/Linux/macOS):
  - Разрешены только домашняя директория и системный temp (`tempfile.gettempdir()`, `/tmp`).
  - Запись в dotfiles/dotdirs под home запрещена (`~/.ssh`, `~/.bashrc`, `~/.config/...`) — проверка через `os.sep + "." in relative_path`.
  - Пути разворачиваются через `os.path.realpath()` (защита от `..` и симлинков).

```python
# Правильно
def _safe_output_path(path: str) -> str:
    resolved = os.path.realpath(path)
    home = os.path.realpath(os.path.expanduser("~"))
    tmp_dirs = {os.path.realpath(tempfile.gettempdir())}
    if os.path.isdir("/tmp"):
        tmp_dirs.add(os.path.realpath("/tmp"))
    is_under_home = resolved.startswith(home + os.sep)
    is_under_tmp = any(resolved.startswith(d + os.sep) for d in tmp_dirs)
    if not (is_under_home or is_under_tmp):
        raise ValueError(f"Output path must be under home or temp directory: {path}")
    if is_under_home and os.sep + "." in resolved[len(home):]:
        raise ValueError(f"Writing to hidden files/directories is not allowed: {path}")
    return resolved

# Неправильно
with open(path, "wb") as f:  # путь не проверен
    ...
```

- **Парсинг JSON от пользователя** — всегда через `_parse_json(text, label)`, не через голый `json.loads()`. Пользователь должен получить понятное сообщение об ошибке, а не стектрейс `JSONDecodeError`.

```python
# Правильно
_parse_json(items_json, "items_json")

# Неправильно
json.loads(items_json)
```

- **Секреты** — только через переменные окружения (`os.getenv`). Не хардкодить токены в коде или тестах. В тестах использовать вымышленные данные (`test-fake-client`, `test-fake-secret`).
- **Загрузка переменных окружения** — CLI и MCP-сервер поддерживают аргумент `--env <path>`. Если передан — загрузить переменные из указанного файла (формат `KEY=VALUE`, по одной на строку, `#`-комментарии). Если не передан — использовать стандартные переменные окружения. Реализация: `python-dotenv` (`load_dotenv(path)`), вызывается из `__init__.py` (MCP-режим) и `cli.py` (CLI-режим).
- **stdout зарезервирован** для JSON-RPC. Весь логгинг — только через `logging` в stderr.
- **HTTP-ответы в исключениях** — НИКОГДА не включать `resp.text` в `RuntimeError`. Тело ответа API может содержать персональные данные (ФИО, адреса, телефоны), которые утекут в логи Claude, MCP-ответ или скриншоты. В исключение — только метод, путь и статус-код. Полный ответ логировать только на уровне `log.debug()`.

```python
# Правильно
log.debug("GET %s error body: %s", path, resp.text)
raise RuntimeError(f"GET {path} -> {resp.status_code}")

# Неправильно
raise RuntimeError(f"GET {path} -> {resp.status_code}: {resp.text}")
```

- **Проверка персональных данных перед коммитом** — grep на токены, имена, адреса, телефоны, email в коде, тестах и документации. Заменять на вымышленные.

## Обработка ошибок

- **Никогда не глотать исключения молча.** `except Exception:` без логирования запрещён. Всегда логировать через `log.warning()` или `log.error()` с контекстом (что делали, для какого объекта).
- **HTTP-ошибки** — `CdekAPI` бросает `RuntimeError` с методом, путём и статус-кодом (без тела ответа). Не перехватывать эти ошибки в tool-функциях — FastMCP сам вернёт ошибку клиенту.
- **Ошибки валидации** — бросать `ValueError` / `RuntimeError` с понятным сообщением. Пример: `raise ValueError(f"Invalid JSON in {label}: {e}")`.

## Стиль кода

- **Именование** — функции-хелперы с префиксом `_`. Имена должны быть читаемыми: `_to_json`, `_parse_json`, `_safe_output_path`, а не `_j`, `_p`, `_s`.
- **Дублирование** — каждая tool-функция самодостаточна (вызывает `_get_api()`). Это допустимое повторение, а не дублирование. Не выносить в декораторы/контекстные менеджеры.
- **Типы** — аннотировать параметры и возвращаемые значения. `dict`, `list`, `str` — не `Dict`, `List`, `Str` (используем встроенные типы Python 3.10+).
- **Импорты** — стандартная библиотека → сторонние пакеты → локальные модули, разделённые пустой строкой. Не импортировать неиспользуемые имена.
- **Линтер** — `ruff check src/ tests/` должен проходить без ошибок перед коммитом. Правила: E (стиль), F (ошибки), W (предупреждения), I (импорты). Максимальная длина строки — 120 символов.

## Архитектура

- **Singleton API-клиент.** Кэшировать экземпляр HTTP-клиента в `_api_instance` в `server.py` (один экземпляр на процесс). Доступ только через `_get_api()`. Не создавать новый API-клиент на каждый вызов.
- **HTTP через хелперы** — `_get()`, `_post()`, `_patch()`, `_delete()` в `CdekAPI`. Не писать ручные запросы через `session.get()` / `session.post()` в бизнес-методах (исключение: скачивание файлов по временным URL после polling).
- **Таймауты** — 30 секунд на обычные запросы, 60 секунд на файловые операции. Настраиваемы через env-переменные (`CDEK_TIMEOUT`, `CDEK_FILE_TIMEOUT`). В коде использовать `self.timeout` и `self.file_timeout`, не хардкодить числа.
- **Polling с backoff** — при ожидании готовности PDF (barcode/label/waybill) использовать экспоненциальный backoff (2→4→8→16 сек), не фиксированный интервал.
- **Tool-функции самодостаточны** — каждая вызывает `_get_api()` сама. Это допустимое повторение, а не дублирование. Не выносить в декораторы/контекстные менеджеры.
- **Индивидуальные инструменты** (не search+execute). Сервер предоставляет ~15 конкретных MCP-инструментов с точными схемами параметров. Не вводить search+execute — у СДЭК небольшой набор хорошо определённых операций.
- **Server instructions.** Передавать `instructions=` в FastMCP, чтобы LLM знал порядок вызова инструментов (сначала `cdek_cities`, потом `cdek_delivery_points`, потом `cdek_create_order`).
- **Конфиг отправителя** — хранится в `~/.config/mcp-server-cdek/config.json` через `config.py`. Параметры отправителя берутся из конфига, а не только из env-переменных.
- **Справочник товаров** — хранится в `~/.config/mcp-server-cdek/goods.json` через `goods.py`. При создании заказа без явных параметров товара берётся первый товар из справочника.

## Pydantic-модели

- **Модели в `models.py`** — используются и для тестов, и в runtime.
- **`extra="allow"`** для forward compatibility с API.
- **Строить по swagger-спецификациям**, не по догадкам. Использовать документацию https://apidoc.cdek.ru/ для точных схем запросов.
- **`Field(description=...)`** для каждого поля — LLM видит полную JSON Schema.
- **Никаких PassThroughParams.** Если действие принимает параметры — для него должна быть конкретная Pydantic-модель. `params_json: str` без схемы вынуждает LLM угадывать поля.
- Не дублировать модели с одинаковыми полями.

## Логирование

- **`logging.basicConfig()`** вызывается **только один раз** — в `server.py`.
- В других модулях — только `log = logging.getLogger(__name__)` без `basicConfig`.
- Никогда не логировать токены, заголовки авторизации, персональные данные (ФИО, адреса, телефоны).

## Тесты

- **Мокаем API-клиент** на уровне класса: `@patch("mcp_server_cdek.server.CdekAPI")`. Кэш API сбрасывается автоматически через фикстуру `_reset_api_singleton` в `conftest.py` (`srv._api_instance = None`).
- **CLI-тесты проверяют поведение, не реализацию.** Проверять, какие команды существуют и какой API-метод они вызывают. Не тестировать внутреннюю структуру диспетча.
- **Пути в тестах** — использовать `os.path.realpath()` для сравнения путей (на macOS `/tmp` → `/private/tmp`). Temp-файлы создавать в `/tmp` явно: `NamedTemporaryFile(dir="/tmp")`.
- **Тестовые данные** — вымышленные имена, адреса, телефоны, токены. Никаких реальных персональных данных.
- **Обязательное покрытие** для каждого нового инструмента:
  1. **Happy path** — штатный вызов с корректными данными.
  2. **Невалидный JSON** — если инструмент принимает `*_json` параметр.
  3. **Ошибка API** — мок бросает `RuntimeError`, инструмент возвращает `isError=True`.
  4. **Path traversal** — если инструмент принимает `output_path` или `file_path`.

## Именование

- **CLI — kebab-case** (`track`, `create-order`, `calculate-tariff`). Стандартная конвенция CLI-инструментов.
- **MCP tools — snake_case с префиксом `cdek_`** (`cdek_track`, `cdek_create_order`, `cdek_calculate_tariff`). Префикс нужен для уникальности — у клиента может быть много MCP-серверов, имена не должны конфликтовать.
- **Паритет CLI и MCP.** Каждый MCP-инструмент должен иметь CLI-аналог. При добавлении нового tool — добавлять CLI-команду одновременно.

## Документация

- Целевая аудитория — русскоязычные пользователи. README, документация и комментарии к коммитам — на русском языке.
- **README для не-программистов.** Пошаговая установка с разделением macOS/Linux/Windows, примеры команд. Разные способы подключения (pip, uvx, --mcp-config).
- **Ссылка на официальную документацию API** — https://apidoc.cdek.ru/
- **Бейджик версии в README.** В начале README.md обязательно указывать бейджик с текущей версией: `[![Version](https://img.shields.io/badge/version-X.Y.Z-blue)](ссылка_на_репозиторий)`. Обновлять при каждом релизе.
- **README обновлять в том же PR.** При добавлении нового инструмента или изменении API обновлять README одновременно с кодом.

## Как Claude запускает MCP-сервер

Claude Code запускает MCP-сервер как **дочерний процесс** (subprocess) и общается с ним по **stdin/stdout** через JSON-RPC 2.0:

```
Claude Code                          MCP-сервер
    │                                    │
    │── spawn subprocess ──────────────►│  (command + args из конфига)
    │                                    │
    │── stdin: {"method":"initialize"} ─►│  handshake (таймаут 10 сек)
    │◄─ stdout: {"capabilities":...} ───│
    │                                    │
    │── stdin: {"method":"tools/list"} ─►│  получить список инструментов
    │◄─ stdout: [tools...] ─────────────│
    │                                    │
    │        ✓ Connected                 │
```

**Важно:**
- Сервер **не запускается в login shell** — `~/.bashrc`, `~/.zshrc` не выполняются
- **PATH может быть урезан** — команда может не находиться, хотя в обычном терминале работает
- **stdout зарезервирован** для протокола — любой `print()` в stdout ломает соединение (используйте stderr)

## `✗ Failed to connect` — что делать

**1. Запустить сервер вручную** — самый быстрый способ увидеть ошибку:

```bash
# Если ставили через uvx:
uvx mcp-server-cdek

# Если ставили через pip:
mcp-server-cdek
```

**2. Проверить что команда доступна:**

```bash
which mcp-server-cdek   # или: which uvx
```

Если `not found` — пакет не установлен или не в PATH.

**3. Использовать абсолютный путь** (если PATH урезан):

```bash
# Узнать полный путь:
which mcp-server-cdek
# Например: /Users/me/.local/bin/mcp-server-cdek

# Использовать его в конфиге:
claude mcp remove cdek
claude mcp add cdek \
  -e CDEK_CLIENT=ваш_client_id \
  -e CDEK_SECRET=ваш_client_secret \
  -- /полный/путь/к/mcp-server-cdek
```

**4. Посмотреть логи Claude Code:**

```bash
# macOS:
ls ~/Library/Logs/Claude/
tail -f ~/Library/Logs/Claude/mcp*.log

# Windows:
dir %APPDATA%\Claude\logs\

# Linux:
ls ~/.config/Claude/logs/
```

**5. Включить debug-режим:**

```bash
claude --mcp-debug          # отладка протокола MCP
claude --verbose             # подробный вывод
CLAUDE_DEBUG=1 claude        # максимум логов
```

## Частые проблемы

| Симптом | Причина | Решение |
|---------|---------|---------|
| `command not found` | Пакет не установлен или не в PATH | `pip install mcp-server-cdek` или используйте абсолютный путь |
| `Failed to connect` без ошибки | Claude не может найти команду из-за урезанного PATH | Используйте абсолютный путь к команде |
| Сервер запускается вручную, но не в Claude | PATH в Claude отличается от PATH в терминале | Используйте абсолютный путь |
| `No module named mcp_server_cdek` | pip установил в другой Python | Используйте entry point `mcp-server-cdek` вместо `python -m` |
| `CDEK auth error 401` | Неверные Client ID или Secret | Проверьте ключи в личном кабинете СДЭК |
| Таймаут при подключении | Сервер не ответил за 10 секунд | Проверьте сеть и ключи API |

## Публикация версии

Валидация, сборка, загрузка в PyPI и публикация в MCP Registry — одной командой:

```bash
mcp-publisher validate && python3 -m build && twine upload dist/* && rm -rf ./dist && mcp-publisher login github && mcp-publisher publish
```
