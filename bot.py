import logging
import os
import json
import time
from datetime import datetime
from collections import defaultdict
from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import telebot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from flask import Flask, request

# ==================== НАСТРОЙКА ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    logger.error("Токен бота не указан в переменных окружения!")
    exit(1)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==================== ДАННЫЕ ====================
PRODUCTS_FILE = "products.json"
USER_DATA_FILE = "user_data.json"

def load_data():
    """Загрузка данных из файлов"""
    try:
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
                products = json.load(f)
        else:
            products = {"яблоко": 52, "курица": 165, "шоколад": 546}

        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_data = defaultdict(
                    lambda: {"total": 0, "history": []},
                    {k: v if isinstance(v, dict) else {"total": v, "history": []} for k, v in data.items()}
                )
        else:
            user_data = defaultdict(lambda: {"total": 0, "history": []})
        
        return products, user_data
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return {"яблоко": 52, "курица": 165, "шоколад": 546}, defaultdict(lambda: {"total": 0, "history": []})

def save_data():
    """Сохранение данных в файлы"""
    try:
        with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(dict(user_data), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")

products, user_data = load_data()

# ==================== ГРАФИКИ ====================
def generate_week_plot(user_id):
    """Генерация графика за неделю"""
    try:
        user_stats = user_data.get(str(user_id), {})
        history = user_stats.get("history", [])
        daily_calories = defaultdict(int)
        
        for entry in history:
            date = entry["date"]
            daily_calories[date] += entry["calories"]
        
        if not daily_calories:
            return None
        
        dates = sorted(daily_calories.keys())[-7:]  # Последние 7 дней
        calories = [daily_calories[date] for date in dates]
        
        plt.figure(figsize=(10, 5))
        plt.plot(dates, calories, marker='o', linestyle='-', color='teal')
        plt.title("Калории за неделю")
        plt.xlabel("Дата")
        plt.ylabel("Ккал")
        plt.grid(True)
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=80)
        buffer.seek(0)
        plt.close()
        return buffer
    except Exception as e:
        logger.error(f"Ошибка генерации графика: {e}")
        return None

def generate_pie_chart(user_id):
    """Генерация круговой диаграммы"""
    try:
        user_stats = user_data.get(str(user_id), {})
        history = user_stats.get("history", [])
        
        if not history:
            return None
        
        product_calories = defaultdict(int)
        for entry in history:
            product_calories[entry["product"]] += entry["calories"]
        
        top_products = dict(sorted(product_calories.items(), key=lambda x: x[1], reverse=True)[:5])
        
        plt.figure(figsize=(8, 8))
        plt.pie(
            top_products.values(),
            labels=top_products.keys(),
            autopct='%1.1f%%',
            startangle=90
        )
        plt.title("Топ продуктов по калориям")
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=80)
        buffer.seek(0)
        plt.close()
        return buffer
    except Exception as e:
        logger.error(f"Ошибка генерации диаграммы: {e}")
        return None

# ==================== КЛАВИАТУРЫ ====================
def back_to_menu_keyboard():
    """Клавиатура для возврата в меню"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🏠 Главное меню")
    return markup

def create_keyboard():
    """Основная клавиатура"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = list(products.keys())
    markup.add(*buttons)
    markup.row("📊 Итог", "🔄 Сбросить")
    markup.row("➕ Добавить продукт", "❌ Удалить продукт")
    markup.row("📈 График за неделю", "🥧 Топ продуктов")
    markup.row("📜 История", "❓ Помощь")
    markup.row("🏠 Главное меню")
    return markup

# ==================== ОБРАБОТЧИКИ СООБЩЕНИЙ ====================
@bot.message_handler(commands=['start', 'help', 'меню', '🏠 Главное меню'])
def start(message):
    """Обработчик стартового сообщения"""
    try:
        user_id = str(message.chat.id)
        if user_id not in user_data:
            user_data[user_id] = {"total": 0, "history": []}
            save_data()
        
        bot.send_message(
            message.chat.id,
            "🍎 Бот-калькулятор калорий\nВыберите продукт или добавьте свой:",
            reply_markup=create_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка. Попробуйте позже.")

@bot.message_handler(func=lambda m: m.text in products.keys())
def add_product(message):
    """Добавление продукта из списка"""
    try:
        product = message.text
        msg = bot.send_message(
            message.chat.id,
            f"Введите количество продукта '{product}' в граммах:",
            reply_markup=back_to_menu_keyboard()
        )
        bot.register_next_step_handler(msg, lambda m: process_product_amount(m, product))
    except Exception as e:
        logger.error(f"Ошибка в add_product: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка обработки продукта", reply_markup=create_keyboard())

def process_product_amount(message, product):
    """Обработка количества продукта"""
    try:
        amount = int(message.text)
        calories = int(products[product] * amount / 100)
        user_id = str(message.chat.id)
        
        if user_id not in user_data:
            user_data[user_id] = {"total": 0, "history": []}
        
        user_data[user_id]["total"] += calories
        user_data[user_id]["history"].append({
            "product": product,
            "amount": amount,
            "calories": calories,
            "date": datetime.now().strftime("%Y-%m-%d")
        })
        save_data()
        
        bot.send_message(
            message.chat.id,
            f"✅ Добавлено: {product} - {amount}г ({calories} ккал)\n"
            f"Всего сегодня: {user_data[user_id]['total']} ккал",
            reply_markup=create_keyboard()
        )
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Пожалуйста, введите число!",
            reply_markup=create_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в process_product_amount: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка обработки количества", reply_markup=create_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 Итог")
def show_total(message):
    """Показать общее количество калорий"""
    try:
        user_id = str(message.chat.id)
        total = user_data.get(user_id, {}).get("total", 0)
        bot.send_message(
            message.chat.id,
            f"📊 Всего потреблено калорий: {total} ккал",
            reply_markup=create_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в show_total: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка получения данных", reply_markup=create_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔄 Сбросить")
def reset_counter(message):
    """Сброс данных пользователя"""
    try:
        user_id = str(message.chat.id)
        user_data[user_id] = {"total": 0, "history": []}
        save_data()
        bot.send_message(
            message.chat.id,
            "🔄 Данные сброшены!",
            reply_markup=create_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в reset_counter: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка сброса данных", reply_markup=create_keyboard())

@bot.message_handler(func=lambda m: m.text == "📈 График за неделю")
def send_week_plot(message):
    """Отправка графика за неделю"""
    try:
        plot = generate_week_plot(message.chat.id)
        if plot:
            bot.send_photo(
                message.chat.id,
                plot,
                caption="📈 Ваша статистика за неделю",
                reply_markup=create_keyboard()
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Нет данных для построения графика",
                reply_markup=create_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в send_week_plot: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка генерации графика", reply_markup=create_keyboard())

@bot.message_handler(func=lambda m: m.text == "🥧 Топ продуктов")
def send_pie_chart(message):
    """Отправка круговой диаграммы"""
    try:
        chart = generate_pie_chart(message.chat.id)
        if chart:
            bot.send_photo(
                message.chat.id,
                chart,
                caption="🥧 Топ потребляемых продуктов",
                reply_markup=create_keyboard()
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Нет данных для построения графика",
                reply_markup=create_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в send_pie_chart: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка генерации диаграммы", reply_markup=create_keyboard())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить продукт")
def add_new_product(message):
    """Добавление нового продукта"""
    try:
        msg = bot.send_message(
            message.chat.id,
            "Введите название продукта и калорийность в формате:\n"
            "Название:калорийность_на_100г\n"
            "Пример: Банан:95",
            reply_markup=back_to_menu_keyboard()
        )
        bot.register_next_step_handler(msg, process_add_product)
    except Exception as e:
        logger.error(f"Ошибка в add_new_product: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка добавления продукта", reply_markup=create_keyboard())
@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def main_menu(message):
    try:
        bot.send_message(
            message.chat.id,
            "Возвращаемся в главное меню:",
            reply_markup=create_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in main_menu: {e}")
def process_add_product(message):
    """Обработка добавления нового продукта"""
    try:
        if message.text.lower() in ["меню", "назад", "🏠 главное меню"]:
            return start(message)
            
        name, kcal = message.text.split(":")
        name = name.strip().lower()
        kcal = int(kcal.strip())
        
        if name in products:
            confirm_markup = ReplyKeyboardMarkup(resize_keyboard=True)
            confirm_markup.add("Да", "Нет", "🏠 Главное меню")
            msg = bot.send_message(
                message.chat.id,
                f"⚠️ Продукт '{name}' уже есть!\n"
                f"Текущая калорийность: {products[name]} ккал\n"
                "Заменить? (Да/Нет)",
                reply_markup=confirm_markup
            )
            bot.register_next_step_handler(msg, lambda m: confirm_replace(m, name, kcal))
        else:
            products[name] = kcal
            save_data()
            bot.send_message(
                message.chat.id,
                f"✅ '{name}' ({kcal} ккал/100г) добавлен!",
                reply_markup=create_keyboard()
            )
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Неверный формат. Используйте: Название:калорийность",
            reply_markup=create_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в process_add_product: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка обработки продукта", reply_markup=create_keyboard())

def confirm_replace(message, name, kcal):
    """Подтверждение замены продукта"""
    try:
        if message.text.lower() == "да":
            products[name] = kcal
            save_data()
            bot.send_message(
                message.chat.id,
                f"✅ '{name}' обновлён! Новая калорийность: {kcal} ккал/100г",
                reply_markup=create_keyboard()
            )
        else:
            bot.send_message(
                message.chat.id,
                "Отмена изменения",
                reply_markup=create_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в confirm_replace: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка подтверждения", reply_markup=create_keyboard())

@bot.message_handler(func=lambda m: m.text == "❌ Удалить продукт")
def remove_product_start(message):
    """Начало удаления продукта"""
    try:
        if not products:
            bot.send_message(message.chat.id, "Список продуктов пуст", reply_markup=create_keyboard())
            return
            
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        for product in products.keys():
            markup.add(product)
        markup.add("🏠 Главное меню")
        
        msg = bot.send_message(
            message.chat.id,
            "Выберите продукт для удаления:",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_remove_product)
    except Exception as e:
        logger.error(f"Ошибка в remove_product_start: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка удаления продукта", reply_markup=create_keyboard())

def process_remove_product(message):
    """Обработка удаления продукта"""
    try:
        product = message.text
        if product == "🏠 Главное меню":
            return start(message)
            
        if product in products:
            del products[product]
            save_data()
            bot.send_message(
                message.chat.id,
                f"✅ Продукт '{product}' удалён!",
                reply_markup=create_keyboard()
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Продукт не найден",
                reply_markup=create_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в process_remove_product: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка удаления", reply_markup=create_keyboard())

@bot.message_handler(func=lambda m: m.text == "📜 История")
def show_history(message):
    """Показать историю потребления"""
    try:
        user_id = str(message.chat.id)
        history = user_data.get(user_id, {}).get("history", [])
        
        if not history:
            bot.send_message(
                message.chat.id,
                "История пуста",
                reply_markup=create_keyboard()
            )
            return
            
        response = "📜 История потребления:\n\n"
        for entry in history[-10:]:  # Последние 10 записей
            response += (
                f"📅 {entry['date']}\n"
                f"🍏 {entry['product']}: {entry['amount']}г ({entry['calories']} ккал)\n\n"
            )
        
        bot.send_message(
            message.chat.id,
            response,
            reply_markup=create_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в show_history: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка получения истории", reply_markup=create_keyboard())

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def show_help(message):
    """Показать справку"""
    help_text = (
        "🍎 Помощь по боту-калькулятору калорий:\n\n"
        "1. Выберите продукт из списка и укажите количество в граммах\n"
        "2. Добавляйте свои продукты через меню\n"
        "3. Просматривайте статистику и графики\n\n"
        "Доступные команды:\n"
        "📊 Итог - общее количество калорий\n"
        "🔄 Сбросить - обнулить данные\n"
        "📈 График - статистика за неделю\n"
        "🥧 Топ - самые калорийные продукты\n"
        "📜 История - последние записи\n\n"
        "Для начала работы нажмите /start"
    )
    bot.send_message(
        message.chat.id,
        help_text,
        reply_markup=create_keyboard()
    )

# ==================== ВЕБХУК И ЗАПУСК ====================
@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхука от Telegram"""
    if request.method == "POST":
        try:
            json_data = request.get_json()
            logger.info(f"Received update: {json_data}")
            if not json_data:
                logger.error("Empty update received")
                return "empty update", 400
            update = telebot.types.Update.de_json(json_data)
            bot.process_new_updates([update])
            return "ok", 200
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return "error", 500

@app.route('/')
def home():
    """Стартовая страница"""
    return "Бот работает! Для проверки отправьте /start в Telegram"

def setup_webhook():
    """Настройка вебхука с повторами при ошибках"""
    webhook_url = 'https://telegram-bot-render-h7b5.onrender.com/webhook'
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            bot.remove_webhook()
            time.sleep(retry_delay)
            bot.set_webhook(url=webhook_url)
            webhook_info = bot.get_webhook_info()
            logger.info(f"Webhook установлен: {webhook_info}")
            return True
        except Exception as e:
            logger.warning(f"Попытка {attempt+1} не удалась: {e}")
            time.sleep(retry_delay)
    
    return False

if __name__ == '__main__':
    logger.info("Запуск бота...")
    bot.remove_webhook()
    time.sleep(1)
    webhook_url = 'https://telegram-bot-render-h7b5.onrender.com/webhook'
    try:
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
        logger.info(f"Current webhook info: {bot.get_webhook_info()}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
    if setup_webhook():
        port = int(os.getenv('PORT', 10000))
        logger.info(f"Сервер запущен на порту {port}")
        app.run(host='0.0.0.0', port=port)
    else:
        logger.error("Не удалось установить вебхук после нескольких попыток")