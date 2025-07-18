BOT_TOKEN = '8196753125:AAHpN-v-ul-C_XnaOOaXb04opQj6CdkimNs'
FULL_ADMIN_IDS = [950089691]  # Полный доступ
EDITOR_IDS = [987654321]     # Только редактирование видов массажа
from pathlib import Path

# Файл базы данных располагается в корне проекта. Путь рассчитывается
# относительно текущего файла, поэтому бот и утилиты будут работать с
# одной и той же базой независимо от рабочей директории.
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / 'massage_bot.db')
ADMIN_IDS = FULL_ADMIN_IDS 