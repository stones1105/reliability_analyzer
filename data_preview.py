import tkinter as tk
from tkinter import ttk

class DataPreviewWindow:
    def __init__(self, master, data):
        self.master = master
        self.data = data
        self.points_dict = {}
        self.window = tk.Toplevel(master)
        self.window.title("数据预览与拟合点数设置")
        self.window.geometry("1000x600")
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for stress_name, stress_dict in data.items():
            self._create_stress_tab(stress_name, stress_dict)
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="保存并关闭", command=self.save_and_close).pack(side=tk.RIGHT, padx=5)

    def _create_stress_tab(self, stress_name, stress_dict):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=stress_name)
        time_vals = stress_dict['time']
        data_df = stress_dict['data']
        device_cols = data_df.columns.tolist()
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tree_frame = ttk.LabelFrame(main_frame, text="数据", padding=5)
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        columns = ['Time'] + device_cols
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        tree.heading('Time', text='时间 (s)')
        for col in device_cols:
            tree.heading(col, text=col)
            tree.column(col, width=80, anchor='center')
        for i, t in enumerate(time_vals):
            row = [f"{t:.3e}"] + [f"{data_df[col].iloc[i]:.4e}" for col in device_cols]
            tree.insert('', 'end', values=row)
        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        setting_frame = ttk.LabelFrame(main_frame, text="拟合最后点数 (每个器件独立)", padding=10)
        setting_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        for col in device_cols:
            row_frame = ttk.Frame(setting_frame)
            row_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
            ttk.Label(row_frame, text=col, width=12).pack(side=tk.LEFT)
            var = tk.StringVar(value="5")
            entry = ttk.Entry(row_frame, textvariable=var, width=6)
            entry.pack(side=tk.RIGHT, padx=5)
            key = f"{stress_name}|{col}"
            self.points_dict[key] = var

    def save_and_close(self):
        self.window.destroy()

    def get_points(self):
        result = {}
        for key, var in self.points_dict.items():
            try:
                val = int(var.get())
                if val < 1:
                    val = 5
            except ValueError:
                val = 5
            result[key] = val
        return result