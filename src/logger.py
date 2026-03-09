# Özel Loglama mekanizması
import logging
import os

# Log dosyası: Tek bir dosya kullanılır (her import'ta yeni dosya oluşturmaz)
# Günlük rotasyon gerekirse logging.handlers.TimedRotatingFileHandler kullanılabilir.
LOG_FILE = "app.log"

# Logların kaydedileceği klasör yolu: (proje_dizini/logs)
logs_path = os.path.join(os.getcwd(), "logs")

# Klasörü oluştur (varsa geç)
os.makedirs(logs_path, exist_ok=True)

LOG_FILE_PATH = os.path.join(logs_path, LOG_FILE)

logging.basicConfig(
    filename=LOG_FILE_PATH,
    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
