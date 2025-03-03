import json
import threading
import time
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import paho.mqtt.client as mqtt


MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
TELEMETRY_TOPIC = "lab/light"
COMMAND_TOPIC = "lab/light_command"
MODE_TOPIC = "lab/mode"

TELEGRAM_TOKEN = "8016023267:AAFH3D9s_wRYrS7Qex07J80zCkLFiz14vCc"

telemetry_data = {"light": False, "light_sensor_value": 0}
mode = "manual" 
light_on = False


mqtt_client = mqtt.Client(protocol=mqtt.MQTTv5)

def on_connect(client, userdata, flags, rc, properties=None):
    print("Подключено к MQTT с кодом:", rc)
    client.subscribe(TELEMETRY_TOPIC)
    client.subscribe(MODE_TOPIC)

def on_message(client, userdata, msg):
    global mode, light_on, telemetry_data
    payload = msg.payload.decode()
    print(f"Получено сообщение из {msg.topic}: {payload}")

    if msg.topic == MODE_TOPIC:
        if payload == "automatic":
            mode = "auto"
            print("Переключено в автоматический режим")
        elif payload == "manual":
            mode = "manual"
            print("Переключено в ручной режим")
    elif msg.topic == COMMAND_TOPIC and mode == "manual":
        if payload == "on":
            light_on = True
            print("Свет включен (ручной режим)")
        elif payload == "off":
            light_on = False
            print("Свет выключен (ручной режим)")


def start_mqtt():
    try:
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_forever()
        print("MQTT клиент успешно запущен.")
    except Exception as e:
        print(f"Ошибка при запуске MQTT клиента: {e}")

def simulate_light_sensor():
    global telemetry_data, light_on

    while True:
        try:
            light_sensor_value = random.randint(0, 100)
            telemetry_data["light_sensor_value"] = light_sensor_value
            telemetry_data["light"] = light_on

            
            if mode == "auto":
                if light_sensor_value < 50 and not light_on:
                    light_on = True
                    print("Свет включен (автоматический режим)")
                elif light_sensor_value >= 50 and light_on:
                    light_on = False
                    print("Свет выключен (автоматический режим)")


            mqtt_client.publish(TELEMETRY_TOPIC, json.dumps(telemetry_data))

            time.sleep(1)
        except Exception as e:
            print(f"Ошибка в симуляции датчика: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для управления светом. Используй команды:\n"
        "/status - Получить текущий статус\n"
        "/on - Включить свет (ручной режим)\n"
        "/off - Выключить свет (ручной режим)\n"
        "/auto - Переключить в автоматический режим\n"
        "/manual - Переключить в ручной режим"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global telemetry_data
    light_status = "Включен" if telemetry_data["light"] else "Выключен"
    light_sensor_value = telemetry_data["light_sensor_value"]
    await update.message.reply_text(
        f"Состояние света: {light_status}\nЗначение датчика света: {light_sensor_value}"
    )

async def turn_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if mode == "manual":
        mqtt_client.publish(COMMAND_TOPIC, "on")
        await update.message.reply_text("Свет включен (ручной режим).")
    else:
        await update.message.reply_text("Переключитесь в ручной режим, чтобы включить свет.")
async def turn_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if mode == "manual":
        mqtt_client.publish(COMMAND_TOPIC, "off")
        await update.message.reply_text("Свет выключен (ручной режим).")
    else:
        await update.message.reply_text("Переключитесь в ручной режим, чтобы выключить свет.")

async def switch_to_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mqtt_client.publish(MODE_TOPIC, "automatic")
    await update.message.reply_text("Переключено в автоматический режим.")

async def switch_to_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mqtt_client.publish(MODE_TOPIC, "manual")
    await update.message.reply_text("Переключено в ручной режим.")


def main():

    threading.Thread(target=start_mqtt, daemon=True).start()
    threading.Thread(target=simulate_light_sensor, daemon=True).start()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("on", turn_on))
    app.add_handler(CommandHandler("off", turn_off))
    app.add_handler(CommandHandler("auto", switch_to_auto))
    app.add_handler(CommandHandler("manual", switch_to_manual))

    print("Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    main()