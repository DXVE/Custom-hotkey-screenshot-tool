import sys
import os
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import keyboard
import pystray
from PIL import Image, ImageDraw


class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("自定义热键截图工具 v1.0")
        self.root.geometry("560x540")
        self.root.resizable(True, True)

        self.default_screenshot = "f4"
        self.default_exit = "ctrl+shift+q"

        self.screenshot_hotkey = self.default_screenshot
        self.exit_hotkey = self.default_exit

        self.hotkey_enabled = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="运行中")

        # 系统托盘相关
        self.tray_icon = None
        self.tray_thread = None
        self.exiting = False      # 退出标志，避免重复退出

        self.create_widgets()
        self.register_hotkeys()
        self.start_keyboard_listener()

        # 绑定窗口最小化事件（隐藏到托盘）
        self.root.bind("<Unmap>", self.on_window_hide)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_tray_icon(self):
        """创建系统托盘图标（不立即运行）"""
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill='black')
        draw.rectangle((24, 24, 40, 40), fill='white')
        draw.ellipse((28, 28, 36, 36), fill='black')

        menu = pystray.Menu(
            pystray.MenuItem("手动截图", self.tray_manual_screenshot),
            pystray.MenuItem("打开截图文件夹", self.tray_open_folder),
            pystray.MenuItem("显示窗口", self.show_window),
            pystray.MenuItem("退出程序", self.quit_app)
        )

        self.tray_icon = pystray.Icon("screenshot_tool", image, "自定义热键截图工具", menu)

    def tray_manual_screenshot(self, icon, item):
        self.root.after(0, self.manual_screenshot)

    def tray_open_folder(self, icon, item):
        self.root.after(0, self.open_screenshot_folder)

    def run_tray(self):
        if self.tray_icon:
            self.tray_icon.run()

    def show_window(self):
        self.root.after(0, self._restore_window)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        if self.tray_thread:
            self.tray_thread = None

    def quit_app(self, icon=None, item=None):
        """托盘菜单退出（先停止托盘，再安排主线程退出）"""
        if self.exiting:
            return
        self.exiting = True

        # 停止托盘图标（如果存在）
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        if self.tray_thread:
            self.tray_thread = None

        # 安排主线程执行真正的退出
        self.root.after(0, self._real_quit)

    def _real_quit(self):
        """实际退出逻辑（在主线程中执行）"""
        try:
            keyboard.unhook_all()
        except:
            pass
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def on_window_hide(self, event):
        if self.root.state() == 'iconic':
            self.root.withdraw()
            if self.tray_icon is None:
                self.create_tray_icon()
                self.tray_thread = threading.Thread(target=self.run_tray, daemon=True)
                self.tray_thread.start()

    def create_widgets(self):
        hotkey_frame = tk.LabelFrame(self.root, text="热键设置")
        hotkey_frame.pack(padx=10, pady=5, fill=tk.X)

        tk.Label(hotkey_frame, text="截图热键:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.entry_screenshot = tk.Entry(hotkey_frame, width=20)
        self.entry_screenshot.insert(0, self.screenshot_hotkey)
        self.entry_screenshot.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(hotkey_frame, text="退出热键:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.entry_exit = tk.Entry(hotkey_frame, width=20)
        self.entry_exit.insert(0, self.exit_hotkey)
        self.entry_exit.grid(row=1, column=1, padx=5, pady=5)

        btn_row = tk.Frame(hotkey_frame)
        btn_row.grid(row=2, column=0, columnspan=2, pady=5)

        self.btn_apply = tk.Button(btn_row, text="应用", width=10, command=self.apply_hotkeys)
        self.btn_apply.pack(side=tk.LEFT, padx=5)

        self.btn_reset = tk.Button(btn_row, text="恢复默认", width=10, command=self.reset_to_default)
        self.btn_reset.pack(side=tk.LEFT, padx=5)

        tip = tk.Label(hotkey_frame, text="示例：f4 / ctrl+shift+q / alt+f12", fg="gray", font=("微软雅黑", 8))
        tip.grid(row=3, column=0, columnspan=2, pady=2)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        self.btn_screenshot = tk.Button(btn_frame, text="手动截图", width=12, command=self.manual_screenshot)
        self.btn_screenshot.pack(side=tk.LEFT, padx=5)

        self.btn_open_folder = tk.Button(btn_frame, text="打开截图目录", width=12, command=self.open_screenshot_folder)
        self.btn_open_folder.pack(side=tk.LEFT, padx=5)

        self.btn_exit = tk.Button(btn_frame, text="退出", width=12, command=self.on_closing)
        self.btn_exit.pack(side=tk.LEFT, padx=5)

        switch_frame = tk.Frame(self.root)
        switch_frame.pack(pady=5)

        self.enable_cb = tk.Checkbutton(
            switch_frame,
            text="启用截图（热键）",
            variable=self.hotkey_enabled,
            command=self.toggle_hotkey
        )
        self.enable_cb.pack(side=tk.LEFT)

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(status_frame, text="状态：").pack(side=tk.LEFT)
        tk.Label(status_frame, textvariable=self.status_var, fg="blue").pack(side=tk.LEFT)

        log_frame = tk.LabelFrame(self.root, text="日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=15, state=tk.DISABLED, wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def register_hotkeys(self):
        try:
            keyboard.add_hotkey(self.screenshot_hotkey, self.hotkey_callback, suppress=True)
            self.log(f"截图热键已注册: {self.screenshot_hotkey} (独占)")
            keyboard.add_hotkey(self.exit_hotkey, self.on_closing, suppress=False)
            self.log(f"退出热键已注册: {self.exit_hotkey}")
        except Exception as e:
            self.log(f"热键注册失败: {e}")

    def apply_hotkeys(self):
        new_screenshot = self.entry_screenshot.get().strip().lower()
        new_exit = self.entry_exit.get().strip().lower()

        old_screenshot = self.screenshot_hotkey
        old_exit = self.exit_hotkey

        try:
            keyboard.unhook_all()
        except:
            pass

        success = True
        error_msg = ""

        try:
            keyboard.add_hotkey(new_screenshot, self.hotkey_callback, suppress=True)
            keyboard.add_hotkey(new_exit, self.on_closing, suppress=False)
        except Exception as e:
            success = False
            error_msg = str(e)
            try:
                keyboard.unhook_all()
                keyboard.add_hotkey(old_screenshot, self.hotkey_callback, suppress=True)
                keyboard.add_hotkey(old_exit, self.on_closing, suppress=False)
                self.log(f"热键应用失败，已恢复旧设置: {old_screenshot} / {old_exit}")
            except:
                self.log("严重错误：无法恢复热键，请重启程序")
        else:
            self.screenshot_hotkey = new_screenshot
            self.exit_hotkey = new_exit
            self.log(f"热键已更新: 截图={new_screenshot}, 退出={new_exit}")

        if not success:
            messagebox.showerror("热键错误", f"无法注册热键：{error_msg}\n请检查格式是否正确（如 f4, ctrl+shift+q）")

    def reset_to_default(self):
        self.entry_screenshot.delete(0, tk.END)
        self.entry_screenshot.insert(0, self.default_screenshot)
        self.entry_exit.delete(0, tk.END)
        self.entry_exit.insert(0, self.default_exit)
        self.apply_hotkeys()

    def toggle_hotkey(self):
        if self.hotkey_enabled.get():
            self.status_var.set("运行中")
            self.log("截图功能已启用")
        else:
            self.status_var.set("已禁用")
            self.log("截图功能已禁用")

    def hotkey_callback(self):
        if not self.hotkey_enabled.get():
            return
        self.root.after(0, self.take_screenshot)

    def take_screenshot(self):
        try:
            keyboard.press_and_release('win+print screen')
            self.log("截图已保存")
            self.status_var.set("就绪")
        except Exception as e:
            self.log(f"截图失败: {e}")
            self.status_var.set("错误")

    def manual_screenshot(self):
        self.take_screenshot()

    def open_screenshot_folder(self):
        screenshots_dir = os.path.expanduser(r"~\Pictures\Screenshots")
        if os.path.exists(screenshots_dir):
            os.startfile(screenshots_dir)
            self.log(f"已打开截图目录: {screenshots_dir}")
        else:
            self.log(f"截图目录不存在: {screenshots_dir}")
            try:
                os.makedirs(screenshots_dir, exist_ok=True)
                os.startfile(screenshots_dir)
                self.log(f"已创建并打开截图目录: {screenshots_dir}")
            except Exception as e:
                self.log(f"打开目录失败: {e}")

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_keyboard_listener(self):
        def listener():
            keyboard.wait()
        t = threading.Thread(target=listener, daemon=True)
        t.start()

    def on_closing(self):
        self.quit_app()


def main():
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
