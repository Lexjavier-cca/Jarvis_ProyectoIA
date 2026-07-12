import pyautogui
import subprocess
import os
import webbrowser

class WindowsController:
    @staticmethod
    def open_app(app_name):
        """
        Abre una aplicación. Si es 'navegador', abre el predeterminado.
        Usa 'start' para lanzar programas.
        """
        app_name = app_name.lower().strip()
        
        # Si es navegador, abrir el predeterminado
        if app_name in ["navegador", "browser", "internet"]:
            webbrowser.open("about:blank")
            return True

        # Mapeo de nombres a comandos
        apps = {
            "chrome": "start chrome",
            "google chrome": "start chrome",
            "firefox": "start firefox",
            "edge": "start msedge",
            "microsoft edge": "start msedge",
            "vscode": "code",
            "visual studio code": "code",
            "spotify": "start spotify",
            "word": "start winword",
            "excel": "start excel",
            "notepad": "start notepad",
            "calculadora": "start calc",
            "explorador": "start explorer",
            "cmd": "start cmd",
            "terminal": "start cmd",
            "consola": "start cmd",
            "discord": "start discord",
            "telegram": "start telegram",
            "whatsapp": "start whatsapp",
            "teams": "start teams",
            "zoom": "start zoom",
            "opera": "start opera",
            "brave": "start brave",
            "vlc": "start vlc",
            "photoshop": "start photoshop",
            "illustrator": "start illustrator",
            "premiere pro": "start premiere",
            "after effects": "start aftereffects",
            "blender": "start blender",
            "obs": "start obs-studio",
            "powerpoint": "start powerpnt"
        }
        cmd = apps.get(app_name)
        if cmd:
            try:
                os.system(cmd)
                return True
            except Exception as e:
                print(f"Error al abrir {app_name}: {e}")
                return False
        
        # Si no está en el diccionario, intentar abrir directamente con 'start'
        try:
            os.system(f"start {app_name}")
            return True
        except:
            return False

    @staticmethod
    def close_app(app_name):
        try:
            if not app_name.endswith('.exe'):
                process_name = f"{app_name}.exe"
            else:
                process_name = app_name
            subprocess.run(f"taskkill /f /im {process_name}", shell=True, capture_output=True)
            return True
        except:
            return False

    @staticmethod
    def volume_up(steps=5):
        for _ in range(steps):
            pyautogui.press('volumeup')

    @staticmethod
    def volume_down(steps=5):
        for _ in range(steps):
            pyautogui.press('volumedown')

    @staticmethod
    def shutdown():
        os.system("shutdown /s /t 5")

    @staticmethod
    def restart():
        os.system("shutdown /r /t 5")