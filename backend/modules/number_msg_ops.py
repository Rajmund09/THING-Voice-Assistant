import time
import urllib.parse
import subprocess
import os
import threading
import pyautogui

def send_number_msg(phone_number: str, message: str) -> str:
    """
    Sends a message to a specific phone number and uses Smart Focus to ensure it sends.
    """
    if not phone_number:
        return "No phone number specified."
    if not message:
        return "No message specified."

    # Clean the phone number
    clean_number = "".join(filter(str.isdigit, phone_number))
    if len(clean_number) == 10:
        clean_number = "91" + clean_number

    try:
        encoded_msg = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={clean_number}&text={encoded_msg}"

        # Open in a NEW tab in the current Chrome window
        if os.name == 'nt': # Windows
            subprocess.Popen(f'start chrome --new-tab "{url}"', shell=True)
        else:
            import webbrowser
            webbrowser.open_new_tab(url)

        # Start a background thread to focus and press Enter
        def auto_send():
            time.sleep(15) # Increased delay for WhatsApp Web load time
            
            if os.name == 'nt':
                try:
                    import win32gui
                    import win32con
                    
                    def window_enumeration_handler(hwnd, top_windows):
                        top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))

                    top_windows = []
                    win32gui.EnumWindows(window_enumeration_handler, top_windows)
                    
                    # Look for the WhatsApp/Chrome window
                    for i in top_windows:
                        if "whatsapp" in i[1].lower() or "google chrome" in i[1].lower():
                            win32gui.ShowWindow(i[0], win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(i[0])
                            time.sleep(0.5)
                            break
                except Exception as e:
                    print(f"[Focus] Failed to focus: {e}")

            # Send the message
            pyautogui.press("enter")
            
        threading.Thread(target=auto_send, daemon=True).start()
            
        return f"Sending WhatsApp message to {phone_number}. I'll focus the window and send it automatically in a few seconds."

    except Exception as e:
        return f"Error opening WhatsApp: {str(e)}"

if __name__ == "__main__":
    # Test
    # print(send_number_msg("919876543210", "Hello from THING!"))
    pass
