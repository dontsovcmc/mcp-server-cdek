# CLAUDE.md

## Разработка

**CRITICAL: Все правила разработки описаны в [development.md](development.md). Всегда следовать им при любых изменениях кода, тестов и документации.**

### Запуск из исходников

```bash
pip install -e ".[test]"
```

### Запуск тестов

```bash
pytest tests/ -v
```

Тесты мокают API СДЭК — `CDEK_CLIENT` и `CDEK_SECRET` не нужны. Все тесты проходят локально без доступа к реальному API.

### CI

GitHub Actions: `.github/workflows/test.yml`, `runs-on: self-hosted`. Токен не требуется.

### Структура

```
src/mcp_server_cdek/
├── __init__.py          # main(), версия
├── __main__.py          # python -m entry point
├── server.py            # FastMCP, все tools
├── cdek_api.py          # HTTP-клиент API СДЭК v2
├── config.py            # конфиг пользователя (~/.config/mcp-server-cdek/config.json)
├── goods.py             # локальный справочник товаров
└── cli.py               # CLI-интерфейс
```

### API СДЭК

- Документация: https://apidoc.cdek.ru/
- Base URL: `https://api.cdek.ru/v2`
- Авторизация: OAuth 2.0 (client_credentials → Bearer token)

### Создание заказов

Два направления:

1. **from_me** (от меня): отправка со склада/ПВЗ на ПВЗ получателя (тариф 136) или до двери (тариф 137)
2. **to_me** (ко мне): приём от отправителя на свой ПВЗ (тариф 136). Требуется `CDEK_MY_PVZ`.

При создании заказа параметры товара берутся в приоритете:
1. Явно указанные параметры в вызове
2. Первый товар из справочника `goods_list`
3. Переменные окружения `CDEK_DEFAULT_*`
4. Захардкоженные дефолты (Товар, 0.17кг, 8x7x10см)

### Справочник товаров

Товары хранятся в `~/.config/mcp-server-cdek/goods.json`. Claude может добавлять/удалять товары. При создании заказа без явных параметров товара берётся первый товар из справочника.

### Обновление MCP-сервера

Когда пользователь просит "обнови mcp cdek":

1. Определить способ установки:
   ```bash
   which mcp-server-cdek && pip show mcp-server-cdek
   ```
2. Обновить пакет:
   - **pip:** `pip install --upgrade mcp-server-cdek`
   - **uvx:** `uvx --upgrade mcp-server-cdek`
3. Проверить версию:
   ```bash
   mcp-server-cdek --version 2>/dev/null || python -c "import mcp_server_cdek; print(mcp_server_cdek.__version__)"
   ```
4. Сообщить пользователю новую версию и попросить перезапустить Claude Code.

### Правила

- **CRITICAL: НИКОГДА не коммить в master!** Все коммиты — только в рабочую ветку.
- **Все изменения — через Pull Request в master.** Создать ветку, закоммитить, сделать rebase на свежий master, запушить, создать PR.
- **ПЕРЕД КОММИТОМ проверить, не слита ли текущая ветка в master.** Если ветка уже слита (merged) — создать новую ветку от свежего master и делать новый PR. Никогда не пушить в уже слитую ветку.
- **MANDATORY BEFORE EVERY `git push`: rebase onto fresh master:**
  ```bash
  git checkout master && git remote update && git pull && git checkout - && git rebase master
  ```
- **NEVER use `git stash`.**
- **NEVER use merge commits. ALWAYS rebase.**
- **CRITICAL: НИКОГДА не читать содержимое `.env` файлов** — запрещено использовать `cat`, `Read`, `grep`, `head`, `tail` и любые другие способы чтения `.env`. Для загрузки переменных использовать **только** `source <path>/.env`. Для проверки наличия файла — только `test -f`. Для проверки наличия переменной — `source .env && test -n "$VAR_NAME"` (без вывода значения).
- Не хардкодить токены и секреты в коде.
- stdout в MCP сервере занят JSON-RPC — для логов использовать только stderr.
- **ПЕРЕД КАЖДЫМ КОММИТОМ** проверять все исходные файлы, тесты и документацию на наличие реальных персональных данных (ИНН, номера счетов, имена, адреса, телефоны, email). Заменять на вымышленные.
- **В КАЖДОМ PR** обновлять версию в `pyproject.toml` и `src/mcp_server_cdek/__init__.py` (patch для фиксов, minor для новых фич).
