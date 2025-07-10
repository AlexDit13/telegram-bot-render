import os
import telebot
from flask import Flask, request
from threading import Thread

# Инициализация бота и Flask-приложения
TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
    return 'OK', 200
# ======== ОСНОВНЫЕ КОМАНДЫ БОТА ========

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я работаю через вебхук! 🚀")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
    Доступные команды:
    /start - Приветствие
    /help - Это сообщение
    /calc - Калькулятор калорий
    """
    bot.send_message(message.chat.id, help_text)

# ======== ФУНКЦИОНАЛ КАЛЬКУЛЯТОРА КАЛОРИЙ ========

products = {
    "яблоко": 52,
    "курица": 165,
    "шоколад": 546
}

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
    bot.remove_webhook()
    bot.set_webhook(url='https://telegram-bot-render-h7b5.onrender.com/webhook')
    # Запускаем Flask-сервер
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))