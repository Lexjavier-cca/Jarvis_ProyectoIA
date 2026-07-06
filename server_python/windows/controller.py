import pyautogui
import subprocess
import os

class WindowsController:
    @staticmethod
    def open_app(app_name):
        apps = {
            "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "vscode": "code",
            "spotify": "spotify",
            "word": "winword",
            "notepad": "notepad"
        }
        path = apps.get(app_name.lower())
        if path:
            try:
                subprocess.Popen(path)
                return True
            except:
                return False
        return False
    
    @staticmethod
    def close_app(app_name):
        try:
            subprocess.run(f"taskkill /f /im {app_name}.exe", shell=True)
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
