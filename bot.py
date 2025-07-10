import os
from dotenv import load_dotenv
import telebot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from flask import Flask, request
from collections import defaultdict
import json
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime, timedelta
import time
def back_to_menu_keyboard():
    """Клавиатура с единственной кнопкой возврата в меню"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🏠 Главное меню")
    return markup
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Инициализация бота и Flask-приложения
TOKEN = os.getenv('TOKEN') or "7892124873:AAF7AnvpEPg5OdDv4MxC1i8G0vCVGbFSjIo"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

PRODUCTS_FILE = "products.json"
USER_DATA_FILE = "user_data.json"
def load_data():
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
def save_data():
    with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(dict(user_data), f, ensure_ascii=False, indent=2)

products, user_data = load_data()
def generate_week_plot(user_id):
    user_stats = user_data.get(str(user_id), {})
    history = user_stats.get("history", [])
    daily_calories = {}
    
    for entry in history:
        date = entry["date"]
        daily_calories[date] = daily_calories.get(date, 0) + entry["calories"]
    
    if not daily_calories:
        return None
    
    dates = sorted(daily_calories.keys())
    calories = [daily_calories[date] for date in dates]
    
    plt.switch_backend('Agg')
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
def generate_pie_chart(user_id):
    user_stats = user_data.get(str(user_id), {})
    history = user_stats.get("history", [])
    
    if not history:
        return None
    
    product_calories = {}
    for entry in history:
        product = entry["product"]
        product_calories[product] = product_calories.get(product, 0) + entry["calories"]
    
    if not product_calories:
        return None
    
    plt.switch_backend('Agg')
    plt.figure(figsize=(8, 8))
    plt.pie(
        product_calories.values(),
        labels=product_calories.keys(),
        autopct='%1.1f%%',
        startangle=90
    )
    plt.title("Топ продуктов по калориям")
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=80)
    buffer.seek(0)
    plt.close()
    return buffer
def create_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = list(products.keys())
    markup.add(*buttons)
    markup.row("📊 Итог", "🔄 Сбросить")
    markup.row("➕ Добавить продукт", "❌ Удалить продукт")
    markup.row("📈 График за неделю", "🥧 Топ продуктов")
    markup.row("📜 История")
    markup.row("🏠 Главное меню", "❓ Помощь")
    return markup
@bot.message_handler(commands=['start', 'меню', 'главное меню'])
def start(message):
    user_data[str(message.chat.id)] = {"total": 0, "history": []}
    bot.send_message(
        message.chat.id,    
        "🍎 Бот-калькулятор калорий\nВыберите продукт или добавьте свой:",
        reply_markup=create_keyboard()
    )
@bot.message_handler(func=lambda m: m.text in products.keys())
def add_product(message):
    product = message.text
    if product in products:
        msg = bot.send_message(
            message.chat.id,
            f"Введите количество продукта '{product}' в граммах:",
            reply_markup=back_to_menu_keyboard()
        )
        bot.register_next_step_handler(msg, lambda m: process_product_amount(m, product))
def process_product_amount(message, product):
    try:
        amount = int(message.text)
        calories = int(products[product] * amount / 100)
        user_id = str(message.chat.id)
        
        # Обновляем данные пользователя
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
@bot.message_handler(func=lambda m: m.text == "📊 Итог")
def show_total(message):
    user_id = str(message.chat.id)
    total = user_data[user_id]["total"]
    bot.send_message(
        message.chat.id,
        f"📊 Всего потреблено калорий: {total} ккал",
        reply_markup=create_keyboard()
    )
@bot.message_handler(func=lambda m: m.text == "🔄 Сбросить")
def reset_counter(message):
    user_id = str(message.chat.id)
    user_data[user_id]["total"] = 0
    user_data[user_id]["history"] = []
    save_data()
    bot.send_message(
        message.chat.id,
        "🔄 Данные сброшены!",
        reply_markup=create_keyboard()
    )
@bot.message_handler(func=lambda m: m.text == "📈 График за неделю")
def send_week_plot(message):
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
@bot.message_handler(func=lambda m: m.text == "🥧 Топ продуктов")
def send_pie_chart(message):
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
def confirm_replace(message, name, kcal):
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

def process_add_product(message):
    """Обработка введённых данных"""
    if message.text.lower() in ["меню", "назад"]:
        return start(message)
    try:
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
    except Exception as e:
        error_markup = create_keyboard()
        error_markup.add("➕ Добавить продукт")
        bot.send_message(
            message.chat.id,
            f"❌ Ошибка: {str(e)}\nПопробуйте ещё раз или вернитесь в меню",
            reply_markup=error_markup
        )
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            json_data = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json.loads(json_data))
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            print(f"Webhook error: {e}")
            return 'Error', 400
    return 'Method not allowed', 405
@app.route('/')
def home():
    return "Бот работает! Для проверки отправьте /start в Telegram"

if __name__ == '__main__':
    print("Устанавливаем вебхук...")
    bot.remove_webhook()
    time.sleep(1)
    try:
        bot.set_webhook(
            url='https://telegram-bot-render-h7b5.onrender.com/webhook'
        )
        print("Вебхук установлен!")
    except Exception as e:
        print(f"Ошибка вебхука: {e}")
    
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))