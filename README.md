<!-- mcp-name: io.github.dontsovcmc/cdek -->

# mcp-server-cdek

[![Version](https://img.shields.io/badge/version-0.6.0-blue)](https://github.com/dontsovcmc/mcp-server-cdek)

MCP-сервер, CLI-утилита и библиотека Pydantic-моделей для [API СДЭК v2](https://apidoc.cdek.ru/).

- **MCP-сервер** — интеграция с Claude Code, Claude Desktop и другими MCP-клиентами
- **CLI-утилита** — работа с API из терминала, скрипты и автоматизация
- **Pydantic-модели** — типизированные модели API для использования в своих Python-программах

Все данные остаются на вашем компьютере — ключи никуда не передаются.

## Оглавление

- [Возможности](#возможности)
- [MCP-сервер](#mcp-сервер)
  - [Установка](#установка)
  - [Подключение к Claude Code](#подключение-к-claude-code)
  - [Подключение к Claude Desktop](#подключение-к-claude-desktop)
  - [Подключение через --mcp-config](#подключение-через---mcp-config)
  - [Примеры](#примеры-mcp)
- [CLI-утилита](#cli-утилита)
  - [Установка](#установка-cli)
  - [Использование](#использование-cli)
  - [Примеры команд](#примеры-команд)
- [Pydantic-модели](#pydantic-модели)
  - [Установка](#установка-библиотеки)
  - [Использование в своих программах](#использование-в-своих-программах)
- [Переменные окружения](#переменные-окружения)
- [Разработка](#разработка)
- [Лицензия](#лицензия)

## Возможности

### Доставка
| Инструмент | CLI | Описание |
|------------|-----|----------|
| `cdek_create_order` | `create-order` | Создать заказ на доставку (от меня / ко мне, на ПВЗ / до двери) |
| `cdek_track` | `track` | Отследить заказ по номеру СДЭК |
| `cdek_barcode` | `barcode` | Скачать PDF штрихкода для заказа |
| `cdek_label` | `label` | Скачать этикетку (A4/A5/A6/A7, по умолчанию A6 ~70x120мм) |
| `cdek_waybill` | `waybill` | Скачать PDF накладной для заказа |
| `cdek_delivery_points` | `delivery-points` | Поиск ПВЗ в городе |
| `cdek_cities` | `cities` | Поиск городов СДЭК по названию |

### Локальный справочник товаров
| Инструмент | CLI | Описание |
|------------|-----|----------|
| `goods_list` | `goods list` | Список всех товаров |
| `goods_add` | `goods add` | Добавить товар (название, вес, габариты, цена) |
| `goods_remove` | `goods remove` | Удалить товар по названию |

Товары хранятся локально в `~/.config/mcp-server-cdek/goods.json`. При создании заказа параметры берутся из справочника (если не указаны явно).

### Настройки
| Инструмент | CLI | Описание |
|------------|-----|----------|
| `config_show` | — | Показать текущую конфигурацию (отправитель, ПВЗ, дефолты товара) |
| `config_set` | — | Установить значение конфигурации |

Настройки хранятся в `~/.config/mcp-server-cdek/config.json`. Можно настроить через Claude: *«установи компанию-отправителя ООО Рога»*.

---

## MCP-сервер

### Установка

#### Шаг 1. Получить ключи API СДЭК

1. Зарегистрируйтесь в [личном кабинете СДЭК](https://lk.cdek.ru)
2. Перейдите в **Настройки** → **Интеграция**
3. Скопируйте **Client ID** и **Client Secret**

#### Шаг 2. Подключить MCP-сервер

### Подключение к Claude Code

**Способ 1: через uvx** (не требует установки пакета)

> Требуется [uv](https://docs.astral.sh/uv/) — если не установлен:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

```bash
claude mcp add cdek \
  -e CDEK_CLIENT=ваш_client_id \
  -e CDEK_SECRET=ваш_client_secret \
  -- uvx mcp-server-cdek
```

**Способ 2: через pip**

```bash
pip install mcp-server-cdek

claude mcp add cdek \
  -e CDEK_CLIENT=ваш_client_id \
  -e CDEK_SECRET=ваш_client_secret \
  -- python -m mcp_server_cdek
```

Данные отправителя настраиваются через Claude: *«установи отправителя: ООО Компания, Иванов И.И., ...»* → `config_set`. Также можно передать через env vars (см. ниже).

Для удаления:
```bash
claude mcp remove cdek
```

### Подключение к Claude Desktop

Добавьте в конфигурационный файл:

| Клиент | ОС | Путь к файлу |
|--------|----|-------------|
| Claude Code | все | `~/.claude/settings.json` (секция `mcpServers`) |
| Claude Desktop | macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop | Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Claude Desktop | Linux | `~/.config/Claude/claude_desktop_config.json` |

**Через uvx:**
```json
{
  "mcpServers": {
    "cdek": {
      "command": "uvx",
      "args": ["mcp-server-cdek"],
      "env": {
        "CDEK_CLIENT": "ваш_client_id",
        "CDEK_SECRET": "ваш_client_secret"
      }
    }
  }
}
```

**Через pip** (после `pip install mcp-server-cdek`):
```json
{
  "mcpServers": {
    "cdek": {
      "command": "python",
      "args": ["-m", "mcp_server_cdek"],
      "env": {
        "CDEK_CLIENT": "ваш_client_id",
        "CDEK_SECRET": "ваш_client_secret"
      }
    }
  }
}
```

Остальные настройки (отправитель, ПВЗ, дефолты товара) задаются через `config_set` или env vars (см. таблицу ниже).

### Подключение через --mcp-config

Подключает сервер только на время одной сессии Claude, не сохраняя в настройки. Токен хранится в отдельном `.env.mcp` файле, а не в конфиге Claude.

Из JSON-строки:
```bash
claude --mcp-config '{"cdek":{"command":"bash","args":["-c","source ~/.env.mcp && exec uvx mcp-server-cdek"]}}'
```

Из файла:
```bash
claude --mcp-config ~/mcp-servers.json
```

Пример `~/mcp-servers.json`:
```json
{
  "cdek": {
    "command": "bash",
    "args": ["-c", "source ~/.env.mcp && exec uvx mcp-server-cdek"]
  }
}
```

Пример `~/.env.mcp`:
```
CDEK_CLIENT=ваш_client_id
CDEK_SECRET=ваш_client_secret
```

#### Шаг 3. Проверить

Попросите Claude: *«найди ПВЗ СДЭК в Москве на Тверской»* — он вызовет `cdek_delivery_points`.

### Примеры (MCP)

- «отправь посылку Иванову на ПВЗ MSK005, телефон +79001234567» → `cdek_create_order`
- «отправь посылку до двери: Москва, Тверская 1, Петрову +79007654321» → `cdek_create_order`
- «создай возвратный заказ от Сидорова, адрес: Самара, Ленина 10» → `cdek_create_order` (to_me)
- «отследи посылку СДЭК 1234567890» → `cdek_track`
- «скачай штрихкод для заказа 1234567890» → `cdek_barcode`
- «скачай этикетку для заказа 1234567890» → `cdek_label`
- «скачай этикетку A4 для заказа 1234567890» → `cdek_label` (format=A4)
- «скачай накладную для заказа 1234567890» → `cdek_waybill`
- «найди ПВЗ в Новосибирске» → `cdek_delivery_points`
- «какие города СДЭК есть на "Новосиб"?» → `cdek_cities`
- «добавь товар: Wi-Fi модем, 0.17 кг, 8x7x10 см» → `goods_add`
- «список товаров» → `goods_list`

---

## CLI-утилита

### Установка (CLI)

```bash
pip install mcp-server-cdek
```

Переменные окружения `CDEK_CLIENT` и `CDEK_SECRET` обязательны:

```bash
export CDEK_CLIENT=ваш_client_id
export CDEK_SECRET=ваш_client_secret
```

Или через файл:

```bash
mcp-server-cdek --env /path/to/.env <command>
```

Формат файла — `KEY=VALUE`, по одной переменной на строку, `#`-комментарии.

Данные отправителя берутся из `~/.config/mcp-server-cdek/config.json` или переменных окружения.

### Использование (CLI)

Без аргументов запускается MCP-сервер, с командой — CLI. Все команды выводят JSON.

```bash
# Версия
mcp-server-cdek --version

# Справка
mcp-server-cdek --help
mcp-server-cdek <command> --help
```

### Примеры команд

```bash
# Создать заказ (от меня на ПВЗ)
mcp-server-cdek create-order --direction from_me --name "Петров Пётр" --phone "+79007654321" --pvz MSK005

# Создать заказ (от меня до двери)
mcp-server-cdek create-order --direction from_me --name "Петров Пётр" --phone "+79007654321" --address "Москва, Тверская 1"

# Создать возвратный заказ (ко мне)
mcp-server-cdek create-order --direction to_me --name "Сидоров" --phone "+79009876543" --address "Самара, Ленина 10"

# Отследить заказ
mcp-server-cdek track 1234567890

# Скачать штрихкод
mcp-server-cdek barcode 1234567890 --output /tmp/barcode.pdf

# Скачать этикетку (по умолчанию A6 ~70x120мм)
mcp-server-cdek label 1234567890 --output /tmp/label.pdf
mcp-server-cdek label 1234567890 --output /tmp/label_a4.pdf --format A4

# Скачать накладную
mcp-server-cdek waybill 1234567890 --output /tmp/waybill.pdf

# Поиск ПВЗ
mcp-server-cdek delivery-points Москва --search Тверская

# Поиск городов
mcp-server-cdek cities Новосиб

# Справочник товаров
mcp-server-cdek goods list
mcp-server-cdek goods add --name "Wi-Fi модем" --weight 0.17 --height 8 --width 7 --length 10
mcp-server-cdek goods remove --name "Wi-Fi модем"
```

---

## Pydantic-модели

Пакет содержит типизированные Pydantic-модели всех объектов API СДЭК v2. Модели можно использовать в своих Python-программах для валидации данных и автодополнения в IDE.

### Установка (библиотеки)

```bash
pip install mcp-server-cdek
```

### Использование в своих программах

```python
from mcp_server_cdek.models import OrderRequest, TariffRequest, Location, Package, Item

# Валидация данных из API
data = {"tariff_code": 136, "from_location": {"code": 44}, "to_location": {"code": 137}}
req = TariffRequest.model_validate(data)
print(req.tariff_code)  # type-safe доступ к полям

# Создание объекта
item = Item(name="Товар", ware_key="ART001", weight=170, cost=1000, amount=1, payment={"value": 0})
print(item.model_dump_json())
```

Все модели используют `extra="allow"` для forward compatibility — неизвестные поля API не вызывают ошибок.

Полный список моделей: [`models.py`](src/mcp_server_cdek/models.py)

---

## Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|------------|:------------:|:------------:|----------|
| `CDEK_CLIENT` | да | — | Client ID из личного кабинета СДЭК |
| `CDEK_SECRET` | да | — | Client Secret из личного кабинета СДЭК |
| `CDEK_SENDER_COMPANY` | нет | — | Название компании отправителя |
| `CDEK_SENDER_NAME` | нет | — | Краткое имя отправителя |
| `CDEK_SENDER_FULL_NAME` | нет | — | Полное ФИО отправителя |
| `CDEK_SENDER_EMAIL` | нет | — | Email отправителя |
| `CDEK_SENDER_PHONE` | нет | — | Телефон отправителя |
| `CDEK_MY_PVZ` | нет | — | Код вашего ПВЗ (для приёма посылок "ко мне") |
| `CDEK_DEFAULT_PRODUCT_NAME` | нет | `Товар` | Название товара по умолчанию |
| `CDEK_DEFAULT_WEIGHT` | нет | `0.17` | Вес по умолчанию в кг |
| `CDEK_DEFAULT_HEIGHT` | нет | `8` | Высота по умолчанию в см |
| `CDEK_DEFAULT_WIDTH` | нет | `7` | Ширина по умолчанию в см |
| `CDEK_DEFAULT_LENGTH` | нет | `10` | Длина по умолчанию в см |
| `CDEK_TIMEOUT` | нет | `30` | Таймаут HTTP-запросов к API (секунды) |
| `CDEK_FILE_TIMEOUT` | нет | `60` | Таймаут скачивания файлов (секунды) |

Настройки отправителя можно также задать через `config_set` — env vars имеют приоритет над конфиг-файлом.

## Разработка

```bash
pip install -e ".[test]"
ruff check src/ tests/
pytest tests/ -v
```

## Лицензия

MIT
