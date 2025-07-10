import os
from dotenv import load_dotenv
import telebot
from flask import Flask, request
import json
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
# Инициализация бота и Flask-приложения
TOKEN = os.getenv('TOKEN') or "7892124873:AAF7AnvpEPg5OdDv4MxC1i8G0vCVGbFSjIo"
print("Токен:", TOKEN)
if not TOKEN:
    raise ValueError("Токен не найден! Проверьте .env файл")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
products = {
    "яблоко": 52,
    "курица": 165,
    "шоколад": 546
}
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
# ======== ОСНОВНЫЕ КОМАНДЫ БОТА ========

@bot.message_handler(commands=['start', 'help'])
def send_commands(message):
    if message.text == '/start':
        bot.reply_to(message, "Привет! Я работаю через вебхук! 🚀")
    else:
        bot.send_message(message.chat.id, 
"""Доступные команды:
/start - Приветствие
/help - Справка
/calc - Калькулятор калорий""")
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    if message.text in products:
        msg = bot.send_message(message.chat.id, f"Введите вес {message.text} в граммах:")
        bot.register_next_step_handler(msg, lambda m: calculate(m, message.text))
    else:
        bot.reply_to(message, "Используйте команды из /help")

# ======== ФУНКЦИОНАЛ КАЛЬКУЛЯТОРА КАЛОРИЙ ========


@bot.message_handler(commands=['calc'])
def calculate_calories(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2)
    for product in products:
        markup.add(product)
    msg = bot.send_message(message.chat.id, "Выберите продукт:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_product_choice)

def process_product_choice(message):
    product = message.text.lower()
    if product not in products:
        bot.send_message(message.chat.id, "Продукт не найден!")
        return
    
    msg = bot.send_message(message.chat.id, f"Введите вес {product} в граммах:")
    bot.register_next_step_handler(msg, lambda m: calculate(m, product))

def calculate(message, product):
    try:
        grams = int(message.text)
        calories = (products[product] * grams) // 100
        bot.send_message(
            message.chat.id,
            f"🍏 {grams}г {product} = {calories} ккал",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите число!")

# ======== ОБЯЗАТЕЛЬНАЯ ЧАСТЬ ДЛЯ RENDER ========

@app.route('/')
def home():
    return "Бот работает! Для проверки отправьте /start в Telegram"

if __name__ == '__main__':
    print("Устанавливаем вебхук...")
    bot.remove_webhook()
    try:
        bot.set_webhook(
            url='https://telegram-bot-render-h7b5.onrender.com/webhook'
        )
        print("Вебхук установлен!")
    except Exception as e:
        print(f"Ошибка вебхука: {e}")
    # Запускаем Flask-сервер
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))