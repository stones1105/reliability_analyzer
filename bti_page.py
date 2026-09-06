from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QTabWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTextEdit, QCheckBox, QGridLayout, QLineEdit,
                             QSizePolicy)
from PyQt5.QtCore import Qt
from qfluentwidgets import BodyLabel, PrimaryPushButton, ComboBox, LineEdit, PushButton, InfoBar, InfoBarPosition
from datetime import datetime
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from common import jedec_judgment, plot_degradation, plot_extrapolation, plot_cdf


class BTIPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("btiPage")
        self.data_loaded = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # ========== 工具栏（重构：弹性布局 + 分组） ==========
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            background-color: #f0f2f5; 
            border-radius: 6px; 
            padding: 6px 10px;
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(6)

        # ---- 第1组：文件操作 ----
        self.import_btn = PushButton("📂 导入 Excel")
        self.import_btn.clicked.connect(self.parent.load_bti_excel)
        toolbar_layout.addWidget(self.import_btn)

        self.preview_btn = PushButton("📊 预览数据")
        self.preview_btn.clicked.connect(self.open_preview)
        toolbar_layout.addWidget(self.preview_btn)

        toolbar_layout.addStretch(1)  # 弹性间隔

        # ---- 第2组：分析参数 ----
        param_widget = QWidget()
        param_layout = QHBoxLayout(param_widget)
        param_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.setSpacing(6)

        # 斜率模式
        param_layout.addWidget(BodyLabel("斜率:"))
        self.slope_combo = ComboBox()
        self.slope_combo.addItems(["平均斜率", "独立斜率", "总体平均"])
        self.slope_combo.setMinimumWidth(90)
        param_layout.addWidget(self.slope_combo)

        param_layout.addSpacing(10)

        # 判据类型 + 值
        param_layout.addWidget(BodyLabel("判据:"))
        self.crit_combo = ComboBox()
        self.crit_combo.addItems(["退化率(%)", "Vth shift (mV)"])
        self.crit_combo.setMinimumWidth(100)
        param_layout.addWidget(self.crit_combo)

        self.crit_edit = LineEdit()
        self.crit_edit.setText("10")
        self.crit_edit.setMinimumWidth(45)
        self.crit_edit.setAlignment(Qt.AlignCenter)
        param_layout.addWidget(self.crit_edit)

        param_layout.addSpacing(10)

        # 工作Vg
        param_layout.addWidget(BodyLabel("工作Vg:"))
        self.vg_edit = LineEdit()
        self.vg_edit.setText("1.1")
        self.vg_edit.setMinimumWidth(50)
        self.vg_edit.setAlignment(Qt.AlignCenter)
        param_layout.addWidget(self.vg_edit)

        param_layout.addSpacing(10)

        # 目标寿命
        param_layout.addWidget(BodyLabel("目标寿命:"))
        self.target_edit = LineEdit()
        self.target_edit.setText("0.2")
        self.target_edit.setMinimumWidth(50)
        self.target_edit.setAlignment(Qt.AlignCenter)
        param_layout.addWidget(self.target_edit)

        param_layout.addSpacing(10)

        # 外推模型
        param_layout.addWidget(BodyLabel("模型:"))
        self.model_combo = ComboBox()
        self.model_combo.addItems(["Vg", "1/Vg"])
        self.model_combo.setMinimumWidth(70)
        param_layout.addWidget(self.model_combo)

        param_layout.addSpacing(10)

        # TTF方法
        param_layout.addWidget(BodyLabel("TTF:"))
        self.ttf_combo = ComboBox()
        self.ttf_combo.addItems(["多点平均法", "简单法"])
        self.ttf_combo.setMinimumWidth(90)
        param_layout.addWidget(self.ttf_combo)

        # 分析按钮
        self.analyze_btn = PrimaryPushButton("▶ 开始分析")
        self.analyze_btn.setMinimumWidth(100)
        self.analyze_btn.clicked.connect(self.parent.run_bti_analysis)
        param_layout.addWidget(self.analyze_btn)

        param_layout.addStretch(0)

        toolbar_layout.addWidget(param_widget)

        main_layout.addWidget(toolbar)

        # ========== 标签页 ==========
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #d1d9e6; 
                border-radius: 4px; 
                background: white;
            }
            QTabBar::tab { 
                padding: 6px 16px; 
                margin-right: 2px;
            }
        """)

        # ---------- 页1：寿命外推 ----------
        tab1 = QWidget()
        tab1_layout = QHBoxLayout(tab1)
        tab1_layout.setContentsMargins(10, 10, 10, 10)
        tab1_layout.setSpacing(12)

        # 左侧：退化曲线
        left_frame = QFrame()
        left_frame.setStyleSheet("background-color: white; border: 1px solid #e0e5ed; border-radius: 4px;")
        left_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.addWidget(BodyLabel("退化曲线"))
        self.plot_frame1 = QFrame()
        self.plot_frame1.setStyleSheet("background-color: #fafafa; border: 1px solid #e8ecf2; border-radius: 3px;")
        self.plot_frame1.setMinimumHeight(280)
        self.plot_frame1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.plot_frame1)
        tab1_layout.addWidget(left_frame, 1)

        # 右侧：电压加速外推
        right_frame = QFrame()
        right_frame.setStyleSheet("background-color: white; border: 1px solid #e0e5ed; border-radius: 4px;")
        right_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.addWidget(BodyLabel("电压加速外推"))
        self.plot_frame2 = QFrame()
        self.plot_frame2.setStyleSheet("background-color: #fafafa; border: 1px solid #e8ecf2; border-radius: 3px;")
        self.plot_frame2.setMinimumHeight(280)
        self.plot_frame2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(self.plot_frame2)
        tab1_layout.addWidget(right_frame, 1)

        self.tab_widget.addTab(tab1, "📈 寿命外推")

        # ---------- 页2：CDF ----------
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        tab2_layout.setContentsMargins(10, 10, 10, 10)
        self.plot_frame3 = QFrame()
        self.plot_frame3.setStyleSheet("background-color: white; border: 1px solid #e0e5ed; border-radius: 4px;")
        self.plot_frame3.setMinimumHeight(380)
        self.plot_frame3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tab2_layout.addWidget(self.plot_frame3)

        check_layout = QHBoxLayout()
        check_layout.setContentsMargins(0, 8, 0, 4)
        check_layout.setSpacing(15)
        self.quantile_checks = {}
        for label in ['t63.2%', 't50%', 't0.1%', 't0.01%', 't0.001%']:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.quantile_checks[label] = cb
            check_layout.addWidget(cb)
        check_layout.addStretch()
        tab2_layout.addLayout(check_layout)
        self.tab_widget.addTab(tab2, "📊 CDF 分布")

        # ---------- 页3：结果摘要 ----------
        tab3 = QWidget()
        tab3_layout = QVBoxLayout(tab3)
        tab3_layout.setContentsMargins(10, 10, 10, 10)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("等待分析...")
        self.result_text.setStyleSheet("font-family: Consolas, monospace; font-size: 10pt;")
        tab3_layout.addWidget(self.result_text)
        self.tab_widget.addTab(tab3, "📋 结果摘要")

        # ---------- 页4：数据详情 ----------
        tab4 = QWidget()
        tab4_layout = QVBoxLayout(tab4)
        tab4_layout.setContentsMargins(10, 10, 10, 10)
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(7)
        self.detail_table.setHorizontalHeaderLabels(["应力", "器件", "平均斜率(n)", "独立斜率(n)", "TTF(s)", "工作寿命(年)", "初始值"])
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.detail_table.setAlternatingRowColors(True)
        tab4_layout.addWidget(self.detail_table)
        self.tab_widget.addTab(tab4, "📋 数据详情")

        # ---------- 页5：测试信息 ----------
        tab5 = QWidget()
        tab5_layout = QVBoxLayout(tab5)
        tab5_layout.setContentsMargins(10, 10, 10, 10)
        self._create_test_info_page(tab5)
        self.tab_widget.addTab(tab5, "📋 测试信息")

        main_layout.addWidget(self.tab_widget)

        # ========== 状态栏 ==========
        self.status_label = BodyLabel("就绪")
        self.status_label.setStyleSheet("color: #555; padding: 4px 0;")
        main_layout.addWidget(self.status_label)

    def _create_test_info_page(self, parent):
        parent.setLayout(QVBoxLayout())
        container = QWidget()
        parent.layout().addWidget(container)
        grid = QGridLayout(container)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        grid.addWidget(QLabel("测试日期:"), 0, 0)
        date_label = QLabel(now)
        date_label.setStyleSheet("color: #555;")
        grid.addWidget(date_label, 0, 1)

        entries = [
            ("制程节点", "process_node"),
            ("产品ID", "product_id"),
            ("批次ID", "batch_id"),
            ("晶圆ID", "wafer_id"),
            ("器件类型", "device_type"),
            ("器件名称", "device_name"),
            ("器件尺寸", "device_size"),
            ("测试温度 (°C)", "test_temp")
        ]
        self.test_vars = {}
        for i, (label, key) in enumerate(entries, start=1):
            grid.addWidget(QLabel(label + ":"), i, 0)
            var = QLineEdit()
            var.setMinimumWidth(180)
            self.test_vars[key] = var
            grid.addWidget(var, i, 1)

        vd_label = QLabel("应力电压 (Vd)")
        vd_label.setStyleSheet("font-weight: bold;")
        vg_label = QLabel("栅极电压 (Vg)")
        vg_label.setStyleSheet("font-weight: bold;")
        grid.addWidget(vd_label, len(entries)+1, 0)
        grid.addWidget(vg_label, len(entries)+1, 1)

        self.vg_vars = []
        self.vd_list = []
        self.update_vg_table([])

    def update_vg_table(self, vd_values, vg_values=None):
        parent = self.tab_widget.widget(4)
        if parent is None:
            return
        container = parent.findChild(QWidget)
        if container is None:
            return
        layout = container.layout()
        if layout is None:
            return
        items_to_remove = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QLineEdit):
                if i > 2:
                    items_to_remove.append(item.widget())
        for w in items_to_remove:
            w.deleteLater()
        if vd_values:
            pairs = sorted(zip(vd_values, vg_values if vg_values else ['']*len(vd_values)), key=lambda x: abs(x[0]))
            sorted_vd = [p[0] for p in pairs]
            sorted_vg = [p[1] for p in pairs]
        else:
            sorted_vd = []
            sorted_vg = []
        self.vd_list = sorted_vd
        self.vg_vars = []
        for idx, (vd, vg) in enumerate(zip(sorted_vd, sorted_vg)):
            row = len(self.test_vars) + 2 + idx
            label = QLabel(f"{vd:.3f} V")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(label, row, 0)
            var = QLineEdit()
            var.setMinimumWidth(180)
            var.setText(str(vg))
            self.vg_vars.append(var)
            layout.addWidget(var, row, 1)

    def get_vg_list(self):
        return [var.text().strip() for var in self.vg_vars]

    def get_selected_quantiles(self):
        return [label for label, cb in self.quantile_checks.items() if cb.isChecked()]

    def set_data_loaded(self, loaded):
        self.data_loaded = loaded

    def set_status(self, text):
        self.status_label.setText(text)

    def open_preview(self):
        if not self.data_loaded:
            InfoBar.warning(title="警告", content="请先导入 BTI 数据", parent=self)
            return
        from common.data_preview import DataPreviewWindow
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        preview = DataPreviewWindow(root, self.parent.bti_data)
        root.wait_window(preview.window)
        points = preview.get_points()
        self.parent.bti_points = points
        InfoBar.success(title="成功", content="拟合点数已更新", parent=self)

    def update_ui(self, res):
        self.result_text.clear()
        if res is None:
            self.result_text.setText("分析结果为空")
            return

        self.clear_plots()
        fig1 = plot_degradation(res['summary'], res['data'], vg_dict=res.get('vg_dict', {}), show_vd=False)
        canvas1 = FigureCanvas(fig1)
        canvas1.setParent(self.plot_frame1)
        canvas1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar1 = NavigationToolbar(canvas1, self.plot_frame1)
        layout1 = QVBoxLayout(self.plot_frame1)
        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.addWidget(toolbar1)
        layout1.addWidget(canvas1)

        fig2 = plot_extrapolation(res['devices_df'], res['result'], res['extrapolation_model'])
        canvas2 = FigureCanvas(fig2)
        canvas2.setParent(self.plot_frame2)
        canvas2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar2 = NavigationToolbar(canvas2, self.plot_frame2)
        layout2 = QVBoxLayout(self.plot_frame2)
        layout2.setContentsMargins(0, 0, 0, 0)
        layout2.addWidget(toolbar2)
        layout2.addWidget(canvas2)

        cdf_quantiles = self.get_selected_quantiles()
        target_years = float(self.target_edit.text()) if self.target_edit.text() else 0.2
        fig3, cdf_analyzer = plot_cdf(
            res['tf_work_list'],
            float(self.vg_edit.text()),
            target_years,
            cdf_quantiles,
            res.get('cdf_xlim', (0.1, 100))
        )
        canvas3 = FigureCanvas(fig3)
        canvas3.setParent(self.plot_frame3)
        canvas3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar3 = NavigationToolbar(canvas3, self.plot_frame3)
        layout3 = QVBoxLayout(self.plot_frame3)
        layout3.setContentsMargins(0, 0, 0, 0)
        layout3.addWidget(toolbar3)
        layout3.addWidget(canvas3)

        text = f"BTI 分析结果\n\n"
        text += f"外推工作寿命 (t50): {res['result']['tau_years']:.4e} 年\n"
        text += f"拟合 R²: {res['result']['r_sq']:.4f}\n"
        text += f"模型参数: a={res['result']['a']:.4f}, b={res['result']['b']:.4f}\n"
        if cdf_analyzer.results:
            ref = cdf_analyzer.results[0]
            text += f"对数标准差 σ: {ref['sigma']:.3f}\n"
        self.result_text.setText(text)

        details = res.get('device_details', [])
        self.detail_table.setRowCount(len(details))
        for i, d in enumerate(details):
            self.detail_table.setItem(i, 0, QTableWidgetItem(d.get('stress_name', '')))
            self.detail_table.setItem(i, 1, QTableWidgetItem(d.get('device_name', '')))
            self.detail_table.setItem(i, 2, QTableWidgetItem(f"{d.get('n_slope_avg', 0):.8f}" if d.get('n_slope_avg') else ''))
            self.detail_table.setItem(i, 3, QTableWidgetItem(f"{d.get('n_slope_ind', 0):.8f}" if d.get('n_slope_ind') else ''))
            self.detail_table.setItem(i, 4, QTableWidgetItem(f"{d.get('ttf', 0):.2e}" if d.get('ttf') else ''))
            self.detail_table.setItem(i, 5, QTableWidgetItem(f"{d.get('tf_work_years', 0):.2e}" if d.get('tf_work_years') else ''))
            self.detail_table.setItem(i, 6, QTableWidgetItem(f"{d.get('init_value', 0):.6e}" if d.get('init_value') else ''))

    def clear_plots(self):
        for frame in [self.plot_frame1, self.plot_frame2, self.plot_frame3]:
            layout = frame.layout()
            if layout:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()