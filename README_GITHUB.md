# Mariya Help Bot (@MariyaFedoseevaHelp_bot)

Telegram-бот для студии визажиста Марии Федосеевой (Сызрань).

## Что умеет

- Запись на макияж и услуги
- Каталог услуг и цен (с фото прайса)
- Запись на обучение (мастер-классы, курс «Сам себе визажист»)
- Продажа онлайн-уроков (6 закрытых каналов)
- Реферальная программа UDS
- Проверка бонусного баланса UDS
- Отзывы, контакты, адрес студии

## Запуск

```bash
pip install -r requirements.txt
export BOT_TOKEN=...   # от @BotFather
export ADMIN_CHAT_ID=... # твой Telegram ID
python bot.py
```

## Deploy на Render.com

1. Подключи репо через `Public Git Repository`
2. Runtime: `Python 3`
3. Build: `pip install -r requirements.txt`
4. Start: `python bot.py`
5. Env vars: `BOT_TOKEN`, `ADMIN_CHAT_ID`

## Стек

- aiogram 3.13 (async Telegram Bot API)
- aiohttp (async HTTP для UDS API и Т-Банк)
- gspread (Google Sheets)
- python-dotenv
