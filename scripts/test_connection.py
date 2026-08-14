"""
Script de Validación de Conexión (Fase 0)
=========================================
Prueba la conexión a un TikTok LIVE usando la librería TikTokLive y la API Key de Euler Stream.
Lee las credenciales desde config.yaml y escucha los comentarios del chat en tiempo real.
"""

import sys
import os
import asyncio
from pathlib import Path
import yaml
from colorama import init, Fore, Style

# Inicializar colorama para soporte de colores en la terminal de Windows
init(autoreset=True)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.example.yaml"


def load_config() -> dict:
    """Carga y valida el archivo config.yaml."""
    if not CONFIG_PATH.exists():
        print(f"\n{Fore.RED}[ERROR] No se encontró el archivo 'config.yaml'.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Por favor, copia '{EXAMPLE_CONFIG_PATH.name}' a 'config.yaml' y completa tus datos:")
        print(f"  copy config.example.yaml config.yaml{Style.RESET_ALL}\n")
        sys.exit(1)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"\n{Fore.RED}[ERROR] Error al leer 'config.yaml': {e}{Style.RESET_ALL}\n")
        sys.exit(1)

    tiktok_cfg = config.get("tiktok", {})
    unique_id = tiktok_cfg.get("unique_id", "").strip()
    euler_api_key = tiktok_cfg.get("euler_api_key", "").strip()

    if not unique_id or unique_id == "tu_usuario_de_tiktok":
        print(f"\n{Fore.RED}[ERROR] 'unique_id' en config.yaml no está configurado.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Escribe tu nombre de usuario de TikTok en config.yaml.{Style.RESET_ALL}\n")
        sys.exit(1)

    if not euler_api_key or euler_api_key == "TU_API_KEY_DE_EULER_STREAM":
        print(f"\n{Fore.YELLOW}[ADVERTENCIA] 'euler_api_key' no está configurada o contiene el texto por defecto.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}TikTokLive intentará conectar directamente, pero podría ser limitado por tasa.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Obtén una key gratuita en: https://www.eulerstream.com/{Style.RESET_ALL}\n")

    return config


async def main():
    print(f"\n{Fore.CYAN}====================================================={Style.RESET_ALL}")
    print(f"{Fore.CYAN} 🎵 TikTok Song Bot - Test de Conexión (Fase 0) 🎵{Style.RESET_ALL}")
    print(f"{Fore.CYAN}====================================================={Style.RESET_ALL}\n")

    config = load_config()
    unique_id = config["tiktok"]["unique_id"]
    euler_key = config["tiktok"].get("euler_api_key", "").strip()

    # Normalizar unique_id (eliminar @ si viene incluido)
    clean_id = unique_id.lstrip("@")

    print(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} Objetivo del LIVE: {Fore.GREEN}@{clean_id}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} Euler Stream API Key: {Fore.GREEN}{'Configurada (' + euler_key[:4] + '...)' if euler_key and euler_key != 'TU_API_KEY_DE_EULER_STREAM' else 'No configurada'}{Style.RESET_ALL}")

    try:
        from TikTokLive import TikTokLiveClient
        from TikTokLive.events import ConnectEvent, DisconnectEvent, CommentEvent
    except ImportError:
        print(f"\n{Fore.RED}[ERROR] La librería TikTokLive no está instalada.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Ejecuta: pip install -r requirements.txt{Style.RESET_ALL}\n")
        sys.exit(1)

    # Inicializar el cliente TikTokLive con la sign_api_key si está presente
    client_kwargs = {"unique_id": f"@{clean_id}"}
    if euler_key and euler_key != "TU_API_KEY_DE_EULER_STREAM":
        client_kwargs["sign_api_key"] = euler_key

    client = TikTokLiveClient(**client_kwargs)

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        print(f"\n{Fore.GREEN}✅ [CONECTADO EXITOSAMENTE]{Style.RESET_ALL} Escuchando el chat de @{clean_id}...")
        print(f"{Fore.WHITE}Escribe en el chat de TikTok o envía un comando para probar la recepción.{Style.RESET_ALL}")
        print(f"{Fore.BLACK}{Style.BRIGHT}(Presiona Ctrl + C en cualquier momento para salir){Style.RESET_ALL}\n")

    @client.on(DisconnectEvent)
    async def on_disconnect(event: DisconnectEvent):
        print(f"\n{Fore.YELLOW}⚠️ [DESCONECTADO]{Style.RESET_ALL} La conexión con el LIVE se ha cerrado.\n")

    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        user = event.user.unique_id
        nickname = event.user.nickname
        comment = event.comment
        print(f"{Fore.MAGENTA}[CHAT]{Style.RESET_ALL} {Fore.CYAN}{nickname}{Style.RESET_ALL} ({Fore.YELLOW}@{user}{Style.RESET_ALL}): {Fore.WHITE}{comment}{Style.RESET_ALL}")

    print(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} Conectando a TikTok LIVE...")
    try:
        await client.start()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"\n{Fore.RED}❌ [ERROR AL CONECTAR]{Style.RESET_ALL}: {e}")
        print(f"{Fore.YELLOW}Verifica que:{Style.RESET_ALL}")
        print(f" 1. La cuenta @{clean_id} esté actualmente EN VIVO (transmitiendo).")
        print(f" 2. Tu API Key de Euler Stream sea válida.")
        print(f" 3. Tengas conexión a Internet activa.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[TEST FINALIZADO]{Style.RESET_ALL} Conexión cerrada por el usuario. ¡Hasta luego!\n")
