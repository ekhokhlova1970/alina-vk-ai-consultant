# Настройка и запуск

Пошаговая инструкция: от пустого окружения до работающего бота в сообществе ВКонтакте.

## 1. Требования

- Python **3.10+** (проект проверен на 3.10–3.12).
- Сообщество ВКонтакте, где вы администратор.
- Аккаунт [ProxyAPI](https://proxyapi.ru/) с положительным балансом.

## 2. Установка

```bash
git clone https://github.com/ekhokhlova1970/alina-vk-ai-consultant.git
cd alina-vk-ai-consultant
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

`pip install -e .` нужен, чтобы команда `alina-bot` и импорт `alina_bot` работали
без ручной настройки `PYTHONPATH`. Файлы `prompts/` и `data/` читаются из корня репозитория.

## 3. Ключ ProxyAPI

1. Войдите в личный кабинет ProxyAPI.
2. Создайте API-ключ.
3. Пополните баланс: без него запросы вернут `402 Insufficient balance`.
4. Убедитесь, что выбранная модель (`OPENAI_MODEL`) доступна в вашем тарифе.

Эндпоинт проекта — `https://api.proxyapi.ru/openai/v1`, авторизация — `Authorization: Bearer <ключ>`.

## 4. Сообщество ВКонтакте

1. Откройте сообщество → **Управление** → **Работа с API**.
2. Включите **Long Poll API** и выберите версию API.
3. Создайте **ключ доступа сообщества** с правами:
   - управление сообществом (для `groups.getById`);
   - сообщения сообщества (чтение и отправка).
4. В разделе **Сообщения** включите сообщения сообщества и разрешите ответы.
5. Скопируйте числовой ID сообщества (без минуса) — он нужен для `VK_GROUP_ID`.

Токен сообщества — секрет. Не публикуйте его и не пересоздавайте без необходимости:
после перевыпуска старый ключ перестаёт работать.

> Бот не принимает токены от пользователей и не хранит их вне `.env`.

## 5. Конфигурация

```bash
cp .env.example .env        # Windows: Copy-Item .env.example .env
```

Минимально заполните:

```dotenv
PROXY_API_KEY=<ваш ключ ProxyAPI>
VK_TOKEN=<токен сообщества ВКонтакте>
VK_GROUP_ID=<числовой ID сообщества>
```

Остальные переменные описаны в [README](../README.md#переменные-окружения).
Проверка конфигурации происходит при старте: при ошибке бот завершится
с понятным сообщением и кодом `1`.

## 6. Локальный запуск

```bash
alina-bot
```

Ожидаемый лог:

```text
2026-11-01 12:00:00,000 - INFO - Запуск Алины. Модель: gpt-4o-mini
2026-11-01 12:00:00,001 - INFO - База знаний загружена: 11 фрагментов
2026-11-01 12:00:00,500 - INFO - Подключение к ВКонтакте установлено: <название>
2026-11-01 12:00:00,501 - INFO - Ожидание сообщений ВКонтакте
```

Напишите сообществу — бот ответит. `Ctrl+C` останавливает процесс.

## 7. Docker

```bash
docker build -t alina-bot .
docker run --rm --env-file .env alina-bot
```

Секреты не попадают в образ: `.env` исключён через `.dockerignore` и передаётся
только в рантайме.

## 8. Постоянный запуск (Linux, systemd)

Создайте `/etc/systemd/system/alina-bot.service`:

```ini
[Unit]
Description=Alina VK AI consultant
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=alina
WorkingDirectory=/opt/alina-vk-ai-consultant
EnvironmentFile=/opt/alina-vk-ai-consultant/.env
ExecStart=/opt/alina-vk-ai-consultant/.venv/bin/alina-bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now alina-bot
journalctl -u alina-bot -f
```

## 9. Обновление

```bash
git pull
source .venv/bin/activate
pip install -e ".[dev]"
sudo systemctl restart alina-bot
```

После правок `data/knowledge_base.md` или `prompts/alina_system_prompt.md`
перезапуск обязателен: файлы читаются один раз при старте.

## Частые проблемы

| Симптом | Причина | Решение |
| --- | --- | --- |
| `Не задана переменная окружения PROXY_API_KEY` | Нет `.env` или переменная пуста | Создать `.env` из `.env.example`, заполнить |
| `VK_GROUP_ID должен содержать числовой ID` | Вставлен короткий адрес (`@club123`) | Указать числовой ID сообщества |
| `402 Insufficient balance` в ответе | Нулевой баланс ProxyAPI | Пополнить баланс |
| Бот молчит | Long Poll выключен или нет прав у токена | Проверить настройки API и права ключа |
| `401 Unauthorized` от VK | Токен отозван или скопирован с пробелом | Перевыпустить ключ, очистить значение |
| `403` от ProxyAPI | Ключ неактивен или модель недоступна | Проверить ключ и `OPENAI_MODEL` |
| Ответ не по теме | В базе знаний нет подходящего раздела | Дополнить `data/knowledge_base.md` |
| `ModuleNotFoundError: alina_bot` | Не выполнена установка пакета | `pip install -e .` из корня проекта |
