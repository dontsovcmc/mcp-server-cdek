<!-- mcp-name: io.github.dontsovcmc/cdek -->

# mcp-server-cdek

MCP-сервер для работы с [API СДЭК v2](https://api-docs.cdek.ru/29923741.html) через Claude Code, Claude Desktop и другие MCP-совместимые клиенты.

Все данные остаются на вашем компьютере — ключи никуда не передаются.

## Возможности

### Доставка
| Инструмент | Описание |
|------------|----------|
| `cdek_create_order` | Создать заказ на доставку (от меня / ко мне, на ПВЗ / до двери) |
| `cdek_track` | Отследить заказ по номеру СДЭК |
| `cdek_barcode` | Скачать PDF штрихкода для заказа |
| `cdek_label` | Скачать этикетку (A4/A5/A6/A7, по умолчанию A6 ~70x120мм) |
| `cdek_waybill` | Скачать PDF накладной для заказа |
| `cdek_delivery_points` | Поиск ПВЗ в городе |
| `cdek_cities` | Поиск городов СДЭК по названию |

### Локальный справочник товаров
| Инструмент | Описание |
|------------|----------|
| `goods_list` | Список всех товаров |
| `goods_add` | Добавить товар (название, вес, габариты, цена) |
| `goods_remove` | Удалить товар по названию |

Товары хранятся локально в `~/.config/mcp-server-cdek/goods.json`. При создании заказа параметры берутся из справочника (если не указаны явно).

## Настройка

### Шаг 1. Получить ключи API СДЭК

1. Зарегистрируйтесь в [личном кабинете СДЭК](https://lk.cdek.ru)
2. Перейдите в **Настройки** → **Интеграция**
3. Скопируйте **Client ID** и **Client Secret**

### Шаг 2. Подключить MCP-сервер

#### Claude Code (CLI в терминале)

**Способ 1: через uvx** (не требует установки пакета)

> Требуется [uv](https://docs.astral.sh/uv/) — если не установлен:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

```bash
claude mcp add cdek \
  -e CDEK_CLIENT=ваш_client_id \
  -e CDEK_SECRET=ваш_client_secret \
  -e CDEK_SENDER_COMPANY="ООО Ваша Компания" \
  -e CDEK_SENDER_NAME="Иванов И.И." \
  -e CDEK_SENDER_FULL_NAME="Иванов Иван Иванович" \
  -e CDEK_SENDER_EMAIL="delivery@example.com" \
  -e CDEK_SENDER_PHONE="+79001234567" \
  -- uvx mcp-server-cdek
```

**Способ 2: через pip**

```bash
pip install mcp-server-cdek

claude mcp add cdek \
  -e CDEK_CLIENT=ваш_client_id \
  -e CDEK_SECRET=ваш_client_secret \
  -e CDEK_SENDER_COMPANY="ООО Ваша Компания" \
  -e CDEK_SENDER_NAME="Иванов И.И." \
  -e CDEK_SENDER_FULL_NAME="Иванов Иван Иванович" \
  -e CDEK_SENDER_EMAIL="delivery@example.com" \
  -e CDEK_SENDER_PHONE="+79001234567" \
  -- python -m mcp_server_cdek
```

Для удаления:
```bash
claude mcp remove cdek
```

#### Claude Desktop (десктопное приложение)

Добавьте в конфигурационный файл:

| Клиент | ОС | Путь к файлу |
|--------|----|-------------|
| Claude Code | все | `~/.claude/settings.json` (секция `mcpServers`) |
| Claude Desktop | macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop | Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Claude Desktop | Linux | `~/.config/Claude/claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "cdek": {
      "command": "uvx",
      "args": ["mcp-server-cdek"],
      "env": {
        "CDEK_CLIENT": "ваш_client_id",
        "CDEK_SECRET": "ваш_client_secret",
        "CDEK_SENDER_COMPANY": "ООО Ваша Компания",
        "CDEK_SENDER_NAME": "Иванов И.И.",
        "CDEK_SENDER_FULL_NAME": "Иванов Иван Иванович",
        "CDEK_SENDER_EMAIL": "delivery@example.com",
        "CDEK_SENDER_PHONE": "+79001234567",
        "CDEK_MY_PVZ": "MSK123"
      }
    }
  }
}
```

### Переменные окружения

| Переменная | Обязательная | Описание |
|-----------|:-----------:|----------|
| `CDEK_CLIENT` | да | Client ID из личного кабинета СДЭК |
| `CDEK_SECRET` | да | Client Secret из личного кабинета СДЭК |
| `CDEK_SENDER_COMPANY` | да | Название компании отправителя |
| `CDEK_SENDER_NAME` | да | Краткое имя отправителя |
| `CDEK_SENDER_FULL_NAME` | да | Полное ФИО отправителя |
| `CDEK_SENDER_EMAIL` | да | Email отправителя |
| `CDEK_SENDER_PHONE` | да | Телефон отправителя |
| `CDEK_MY_PVZ` | нет | Код вашего ПВЗ (для приёма посылок "ко мне") |
| `CDEK_DEFAULT_PRODUCT_NAME` | нет | Название товара по умолчанию (Товар) |
| `CDEK_DEFAULT_WEIGHT` | нет | Вес по умолчанию в кг (0.17) |
| `CDEK_DEFAULT_HEIGHT` | нет | Высота по умолчанию в см (8) |
| `CDEK_DEFAULT_WIDTH` | нет | Ширина по умолчанию в см (7) |
| `CDEK_DEFAULT_LENGTH` | нет | Длина по умолчанию в см (10) |

### Шаг 3. Проверить

Попросите Claude: *«найди ПВЗ СДЭК в Москве на Тверской»* — он вызовет `cdek_delivery_points`.

## Примеры (MCP)

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

## CLI-режим

Пакет можно использовать как CLI-инструмент в терминале. Без аргументов запускается MCP-сервер, с командой — CLI.

### Требования

Переменные окружения `CDEK_CLIENT`, `CDEK_SECRET` и данные отправителя должны быть установлены:

```bash
export CDEK_CLIENT=ваш_client_id
export CDEK_SECRET=ваш_client_secret
export CDEK_SENDER_COMPANY="ООО Ваша Компания"
export CDEK_SENDER_NAME="Иванов И.И."
export CDEK_SENDER_FULL_NAME="Иванов Иван Иванович"
export CDEK_SENDER_EMAIL="delivery@example.com"
export CDEK_SENDER_PHONE="+79001234567"
```

### Команды

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

Все команды выводят результат в JSON.

## Лицензия

MIT
