import json
import os
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

CONFIG_FILE = 'config.json'

def validate_config(config):
    """Проверяет и исправляет конфигурацию"""
    required_fields = {
        "verification_channel": None,
        "member_role": None,
        "welcome_channel": None,
        "info_channel": None,
        "ticket_channel": None,
        "ticket_category": None,
        "ticket_mod_role": None,
        "guild_id": None,
        "private_vc_category": None,
        "private_vc_lobby": None,
        "nsfw_channel": None,
        "moderation_application_channel": None,
        "moderation_recruiter_role": None,
        "banner_url_default": "https://media.discordapp.net/ephemeral-attachments/1374748463337836697/1375810057996079245/standard_2.gif?ex=68330a77&is=6831b8f7&hm=fa0adbc905994051bbae2c9b65ef89058edd4a5fb0d264922cc8e34fdbddae53&=",
        "gentle_pink_color_hex": "#FFB6C1",
        "welcome_banner_filename_default": "welcome.gif",
        "links_banner_filename_default": "links.gif",
        "mods_banner_filename_default": "mods.gif",
        "invite_banner_filename_default": "invite.gif"
    }
    
    # Проверяем наличие всех необходимых полей
    for field in required_fields:
        if field not in config:
            config[field] = required_fields[field]
            logging.warning(f"Отсутствует поле {field} в конфигурации, установлено значение по умолчанию")
    
    return config

def load_config():
    """Загружает конфигурацию из файла config.json"""
    if not os.path.exists(CONFIG_FILE):
        logging.info("Файл конфигурации не найден, создаем новый")
        default_config = {
            "verification_channel": None,
            "member_role": None,
            "welcome_channel": None,
            "info_channel": None,
            "ticket_channel": None,
            "ticket_category": None,
            "ticket_mod_role": None,
            "guild_id": None,
            "private_vc_category": None,
            "private_vc_lobby": None,
            "nsfw_channel": None,
            "moderation_application_channel": None,
            "moderation_recruiter_role": None,
            "banner_url_default": "https://media.discordapp.net/ephemeral-attachments/1374748463337836697/1375810057996079245/standard_2.gif?ex=68330a77&is=6831b8f7&hm=fa0adbc905994051bbae2c9b65ef89058edd4a5fb0d264922cc8e34fdbddae53&=",
            "gentle_pink_color_hex": "#FFB6C1",
            "welcome_banner_filename_default": "welcome.gif",
            "links_banner_filename_default": "links.gif",
            "mods_banner_filename_default": "mods.gif",
            "invite_banner_filename_default": "invite.gif"
        }
        save_config(default_config)
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return validate_config(config)
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка при чтении конфигурации: {e}")
        return {}
    except Exception as e:
        logging.error(f"Неожиданная ошибка при загрузке конфигурации: {e}")
        return {}

def save_config(config):
    """Сохраняет конфигурацию в файл config.json"""
    try:
        config = validate_config(config)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logging.info("Конфигурация успешно сохранена")
    except Exception as e:
        logging.error(f"Ошибка при сохранении конфигурации: {e}")

def update_config(key, value):
    """Обновляет одно значение в конфигурации"""
    config = load_config()
    config[key] = value
    save_config(config)
    logging.info(f"Обновлено значение {key} в конфигурации") 