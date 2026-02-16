# Özel Loglama mekanizması
import logging
import os
from datetime import datetime

# Log dosyasının adı: "08_25_2023_14_30_05.log" formatında
LOG_FILE = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"

# Logların kaydedileceği ana klasör yolu: (proje_dizini/logs)
logs_path = os.path.join(os.getcwd(), "logs", LOG_FILE)

# Klasörü oluştur (varsa geç)
os.makedirs(logs_path, exist_ok=True)

LOG_FILE_PATH = os.path.join(logs_path, LOG_FILE)

logging.basicConfig(
    filename=LOG_FILE_PATH,
    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
