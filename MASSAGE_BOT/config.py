BOT_TOKEN = '8196753125:AAHpN-v-ul-C_XnaOOaXb04opQj6CdkimNs'
FULL_ADMIN_IDS = [950089691]  # Полный доступ
EDITOR_IDS = [987654321]     # Только редактирование видов массажа
from pathlib import Path

# Файл базы данных располагается в корне проекта. Путь рассчитывается
# относительно текущего файла, поэтому бот и утилиты будут работать с
# одной и той же базой независимо от рабочей директории.
BASE_DIR = Path(__file__).resolve().parent.parent

# Основная база данных лежит в корне проекта. Ранее файл мог
# находиться в папке MASSAGE_BOT, поэтому при первом запуске
# перенесём его при необходимости.
DEFAULT_DB = BASE_DIR / 'massage_bot.db'
LEGACY_DB = Path(__file__).resolve().parent / 'massage_bot.db'
if not DEFAULT_DB.exists() and LEGACY_DB.exists():
    DEFAULT_DB.write_bytes(LEGACY_DB.read_bytes())
DB_PATH = str(DEFAULT_DB)
ADMIN_IDS = FULL_ADMIN_IDS 