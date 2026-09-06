import tkinter as tk
from tkinter import ttk
import os
from .pages import HomePage, HCIPage, EmptyPage, BTIPage

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ===== 全局字体设置 =====
FONT_FAMILY = "幼圆"
FONT_FALLBACK = ["微软雅黑", "Microsoft YaHei", "黑体", "SimHei", "Arial Unicode MS"]

class HCIUI:
    def __init__(self, master):
        self.master = master
        master.title("可靠性分析工具 v4.0")
        master.geometry("1300x850")
        master.minsize(1000, 700)

        # 移除默认图标
        try:
            transparent = tk.PhotoImage(width=1, height=1)
            master.iconphoto(True, transparent)
            self._icon = transparent
        except Exception:
            pass

        self.control_vars = {}
        self.widgets = {}
        self.data = None

        self._setup_style()
        self.main_container = ttk.Frame(master)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.pages = {}
        self._create_pages()
        self.show_page("home")
        self._create_statusbar()

    def _setup_style(self):
        import tkinter.font as tkfont
        font_list = [FONT_FAMILY] + FONT_FALLBACK
        available = set(tkfont.families())
        for f in font_list:
            if f in available:
                self.font_name = f
                break
        else:
            self.font_name = "TkDefaultFont"

        style = ttk.Style()
        style.theme_use('clam')

        bg_color = '#f0f2f5'
        card_bg = '#ffffff'
        fg_color = '#1e293b'
        accent_color = '#3b82f6'
        accent_hover = '#2563eb'
        border_color = '#d1d9e6'
        text_light = '#64748b'
        self.master.configure(bg=bg_color)

        default_font = (self.font_name, 10)
        bold_font = (self.font_name, 10, 'bold')
        title_font = (self.font_name, 16, 'bold')
        small_font = (self.font_name, 9)
        button_font = (self.font_name, 10, 'bold')

        style.configure('TFrame', background=bg_color)
        style.configure('Card.TFrame', background=card_bg, relief='flat', borderwidth=0)

        style.configure('TLabelframe', background=card_bg, foreground=fg_color,
                        borderwidth=1, relief='solid', bordercolor=border_color,
                        font=bold_font)
        style.configure('TLabelframe.Label', background=card_bg, foreground=fg_color,
                        font=bold_font)

        style.configure('TButton', background=card_bg, foreground=fg_color,
                        borderwidth=1, relief='solid', focuscolor='none',
                        padding=(14, 8), font=button_font, bordercolor=border_color)
        style.map('TButton',
                  background=[('active', '#e8ecf1'), ('pressed', '#d5dce4')],
                  foreground=[('active', fg_color), ('pressed', fg_color)],
                  bordercolor=[('active', accent_color), ('pressed', accent_color)])

        style.configure('Home.TButton', background=card_bg, foreground=fg_color,
                        borderwidth=1, relief='solid', focuscolor='none',
                        padding=(24, 32), font=(self.font_name, 12, 'bold'), bordercolor=border_color)
        style.map('Home.TButton',
                  background=[('active', '#e8ecf1'), ('pressed', '#d5dce4')],
                  foreground=[('active', accent_color), ('pressed', accent_color)],
                  bordercolor=[('active', accent_color), ('pressed', accent_color)])

        style.configure('TLabel', background=bg_color, foreground=fg_color, font=default_font)
        style.configure('Title.TLabel', background=bg_color, foreground=fg_color, font=title_font)
        style.configure('Desc.TLabel', background=bg_color, foreground=text_light,
                        font=(self.font_name, 11), wraplength=350)

        style.configure('TEntry', fieldbackground=card_bg, foreground=fg_color,
                        borderwidth=1, relief='solid', padding=6, font=default_font, bordercolor=border_color)
        style.map('TEntry', bordercolor=[('focus', accent_color), ('!focus', border_color)])

        style.configure('TCombobox', fieldbackground=card_bg, foreground=fg_color,
                        padding=6, font=default_font, bordercolor=border_color)
        style.map('TCombobox', bordercolor=[('focus', accent_color), ('!focus', border_color)])
        style.configure('White.TCombobox', fieldbackground='white', background='white',
                        font=default_font)

        style.configure('TNotebook', background=bg_color, borderwidth=0)
        style.configure('TNotebook.Tab', background=bg_color, foreground=fg_color,
                        padding=[20, 10], font=bold_font, borderwidth=0, relief='flat')
        style.map('TNotebook.Tab', background=[('selected', card_bg), ('active', '#e8ecf1')],
                  foreground=[('selected', accent_color), ('active', fg_color)])

        style.configure('Status.TLabel', background='#d1d9e6', foreground=text_light, font=small_font)

        style.configure('Primary.TButton', background=accent_color, foreground='white',
                        borderwidth=0, focuscolor='none', padding=(20, 10), font=button_font)
        style.map('Primary.TButton',
                  background=[('active', accent_hover), ('pressed', accent_hover)],
                  foreground=[('active', 'white'), ('pressed', 'white')])

        style.configure('Toolbar.TButton', background=bg_color, foreground=fg_color,
                        borderwidth=0, padding=8, font=default_font)
        style.map('Toolbar.TButton',
                  background=[('active', '#d5dce4'), ('pressed', '#c0c8d4')],
                  foreground=[('active', fg_color), ('pressed', fg_color)])

        style.configure('Back.TButton', background=bg_color, foreground=accent_color,
                        borderwidth=0, padding=6, font=bold_font)
        style.map('Back.TButton',
                  background=[('active', '#d5dce4'), ('pressed', '#c0c8d4')],
                  foreground=[('active', accent_hover), ('pressed', accent_hover)])

        style.configure('History.TButton', background=card_bg, foreground=accent_color,
                        borderwidth=1, relief='solid', padding=(12, 6), font=default_font, bordercolor=border_color)
        style.map('History.TButton',
                  background=[('active', '#e8ecf1'), ('pressed', '#d5dce4')],
                  foreground=[('active', accent_hover), ('pressed', accent_hover)],
                  bordercolor=[('active', accent_color), ('pressed', accent_color)])

    def _create_pages(self):
        self.pages['home'] = HomePage(self.main_container, self)
        self.pages['hci'] = HCIPage(self.main_container, self)
        self.pages['bti'] = BTIPage(self.main_container, self)
        self.pages['goi_vramp'] = EmptyPage(self.main_container, self, "GOI Vramp")
        self.pages['goi_tddb'] = EmptyPage(self.main_container, self, "GOI TDDB")
        self.pages['imd_vramp'] = EmptyPage(self.main_container, self, "IMD Vramp")
        self.pages['imd_tddb'] = EmptyPage(self.main_container, self, "IMD TDDB")
        self.pages['vramp'] = EmptyPage(self.main_container, self, "VRAMP")
        self.pages['tddb'] = EmptyPage(self.main_container, self, "TDDB")
        self.pages['em'] = EmptyPage(self.main_container, self, "EM")
        self.pages['sm'] = EmptyPage(self.main_container, self, "SM")
        for page in self.pages.values():
            page.hide()

    def show_page(self, page_name):
        if page_name == 'home':
            self.master.geometry("1180x850")   # 再缩60
            self.master.resizable(False, False)
        else:
            self.master.geometry("1300x850")
            self.master.resizable(True, True)

        for name, page in self.pages.items():
            if name == page_name:
                page.show()
            else:
                page.hide()

    def _create_statusbar(self):
        statusbar = ttk.Frame(self.master, relief=tk.SUNKEN, padding=(6, 2))
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.widgets['lbl_status2'] = ttk.Label(statusbar, text="就绪", style='Status.TLabel')
        self.widgets['lbl_status2'].pack(side=tk.LEFT)
        self.widgets['lbl_result'] = ttk.Label(statusbar, text="", style='Status.TLabel')
        self.widgets['lbl_result'].pack(side=tk.RIGHT)

    # ---------- 公共接口 ----------
    def get_widget(self, name):
        return self.widgets.get(name)

    def get_var(self, name):
        return self.control_vars.get(name)

    def set_status(self, text):
        if 'lbl_status2' in self.widgets:
            self.widgets['lbl_status2'].config(text=text)

    def set_result(self, text):
        if 'lbl_result' in self.widgets:
            self.widgets['lbl_result'].config(text=text)

    def set_result_text(self, text, page='hci'):
        if page == 'hci' and 'hci' in self.pages:
            self.pages['hci'].set_result_text(text)
        elif page == 'bti' and 'bti' in self.pages:
            self.pages['bti'].set_result_text(text)

    def clear_plots(self, page='hci'):
        if page == 'hci' and 'hci' in self.pages:
            self.pages['hci'].clear_plots()
        elif page == 'bti' and 'bti' in self.pages:
            self.pages['bti'].clear_plots()

    def get_selected_quantiles(self, page='hci'):
        if page == 'hci' and 'hci' in self.pages:
            return self.pages['hci'].get_selected_quantiles()
        elif page == 'bti' and 'bti' in self.pages:
            return self.pages['bti'].get_selected_quantiles()
        return []

    def set_device_details(self, details, page='hci'):
        if page == 'hci' and 'hci' in self.pages:
            self.pages['hci'].set_device_details(details)
        elif page == 'bti' and 'bti' in self.pages:
            self.pages['bti'].set_device_details(details)

    def open_data_preview(self):
        if self.data is None:
            return None
        from common import DataPreviewWindow
        preview = DataPreviewWindow(self.master, self.data)
        self.master.wait_window(preview.window)
        return preview.get_points()

    def set_history_load_callback(self, callback):
        if 'home' in self.pages:
            self.pages['home'].set_history_load_callback(callback)