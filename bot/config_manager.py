"""
Gestor de Configuración Centralizada (config.yaml)
Permite leer y modificar dinámicamente los parámetros del bot sin reiniciar.
"""

from pathlib import Path
import yaml

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.yaml"
EXAMPLE_CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.example.yaml"

DEFAULT_CONFIG = {
    "player_mode": "youtube",  # "youtube", "spotify" o "local"
    "tiktok": {
        "unique_id": "",
        "euler_api_key": ""
    },
    "spotify": {
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "http://127.0.0.1:8888/callback",
        "device_name": ""
    },
    "permissions": {
        "streamer_id": "",
        "moderators": []
    },
    "audio": {
        "music_folder": "./music",
        "allowed_extensions": [".mp3", ".wav", ".ogg", ".flac"],
        "default_volume": 0.8
    }
}


def load_config() -> dict:
    """Carga config.yaml. Si no existe, intenta copiarlo desde config.example.yaml o crear uno por defecto."""
    if not CONFIG_FILE.exists():
        if EXAMPLE_CONFIG_FILE.exists():
            try:
                with open(EXAMPLE_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or DEFAULT_CONFIG
                save_config(data)
                return data
            except Exception:
                save_config(DEFAULT_CONFIG)
                return DEFAULT_CONFIG.copy()
        else:
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                return DEFAULT_CONFIG.copy()
            # Asegurar claves mínimas
            if "player_mode" not in data:
                data["player_mode"] = "spotify"
            for section, values in DEFAULT_CONFIG.items():
                if section == "player_mode":
                    continue
                if section not in data:
                    data[section] = values
                elif isinstance(values, dict):
                    for k, v in values.items():
                        if k not in data[section]:
                            data[section][k] = v
            return data
    except Exception as e:
        print(f"[CONFIG] Error al leer config.yaml: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config_data: dict) -> bool:
    """Guarda la configuración en config.yaml."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"[CONFIG] Error al guardar config.yaml: {e}")
        return False
