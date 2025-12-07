import subprocess
import json
import os
import time
import datetime
import random

# Конфигурация
LOG_FILE = "codes.log"
TICKET_STATE_FILE = "ticket.json"  # Файл для хранения последнего номера билета
CHECK_INTERVAL = 10  # секунды

def send_sms(number, message):
    try:
        subprocess.run(["termux-sms-send", "-n", number, message], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка отправки SMS на {number}: {e}")
        return False

def get_latest_sms(last_sms_id=None):
    try:
        sms_data = subprocess.check_output(["termux-sms-list", "-l", "1", "-t", "inbox"]).decode()
        sms_list = json.loads(sms_data)
        if not sms_list:
            return None, last_sms_id
        sms = sms_list[0]
        sms_id = sms.get("_id")
        if last_sms_id and sms_id <= last_sms_id:
            return None, last_sms_id
        return sms, sms_id
    except Exception as e:
        print(f"Ошибка чтения SMS: {e}")
        return None, last_sms_id

# Загружаем или инициализируем последний номер билета
def load_last_ticket():
    if os.path.exists(TICKET_STATE_FILE):
        try:
            with open(TICKET_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_ticket", None)
        except:
            return None
    return None

def save_last_ticket(ticket_number):
    with open(TICKET_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_ticket": ticket_number}, f, ensure_ascii=False, indent=2)

# Основной цикл
last_sms_id = None
last_ticket_number = load_last_ticket()  # Загружаем последний использованный номер

print(f"Последний использованный билет: {last_ticket_number or 'не найден — будет сгенерирован новый'}")

while True:
    try:
        sms, last_sms_id = get_latest_sms(last_sms_id)

        if sms:
            body = sms["body"].strip()
            user_number = sms["number"]

            # Команда выхода
            if body.lower() == "exit":
                print("Бот остановлен через SMS.")
                break

            # Проверяем, что прислан только цифры (код борта)
            if body.isdigit():
                code = int(body)
                now = datetime.datetime.now()

                # === Генерация следующего номера билета ===
                if last_ticket_number is None:
                    # Первый запуск — используем код + 5681 как базу
                    ticket_number = int(str(code) + "5681")
                    print(f"Первый билет, база: {ticket_number}")
                else:
                    # Берём последний выданный и добавляем 4–7
                    add = random.randint(4, 7)
                    ticket_number = last_ticket_number + add
                    print(f"Следующий билет: {last_ticket_number} + {add} = {ticket_number}")

                # Сохраняем новый номер как последний
                last_ticket_number = ticket_number
                save_last_ticket(ticket_number)

                valid_until = now + datetime.timedelta(hours=1)
                date_str = now.strftime("%d.%m.%Y")
                time_from = now.strftime("%H:%M")
                time_to = valid_until.strftime("%H:%M")

                # Текст билета
                response = (
                    "Bilet electronic nr.\n"
                    f"{ticket_number}\n"
                    f"{date_str}\n"
                    f"Valabil 1 ora (de la {time_from} pina la {time_to})\n"
                    "Pret 6 MDL\n"
                    f"Numar de bord {code}"
                )

                # Отправляем
                if send_sms(user_number, response):
                    print(f"Билет {ticket_number} отправлен на {user_number}")

                    # Логируем
                    log_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(f"[{log_time}] Код: {code}, Номер: {user_number}, Билет: {ticket_number}\n")
                else:
                    print("Ошибка отправки SMS")

            else:
                print(f"Некорректное сообщение от {user_number}: '{body}'")

        time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\nБот остановлен вручную.")
        break
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        time.sleep(CHECK_INTERVAL)
