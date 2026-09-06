"""
main_gui.py - 主入口（PyQt Fluent 风格）
完整实现所有功能，包括数据加载、分析、绘图、历史记录等。
修复：使用信号/槽将 UI 更新移到主线程，避免卡死。
修复：移除 HCI 调用中多余的 vg_list 参数。
新增：BTI 分析信号机制与详细调试日志。
新增：BTI 预览功能支持。
新增：BTI 目标寿命输入并存储。
"""

import sys
import os
import threading
import time
import traceback
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtWidgets import (QApplication, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QMetaObject, Q_ARG
from PyQt5.QtGui import QFont
from qfluentwidgets import FluentWindow, NavigationItemPosition, setTheme, Theme, FluentIcon as FIF
from qfluentwidgets import InfoBar, InfoBarPosition

# 导入页面
from ui.pages import HomePage, HCIPage, BTIPage, EmptyPage

# 导入业务逻辑
from common.excel_loader import load_excel
from common.current_loader import load_three_end_currents
from common.history_manager import get_history_list, save_history
from hci_analysis import run_hci_analysis
from bti_analysis import run_bti_analysis
from common import jedec_judgment, plot_degradation, plot_extrapolation, plot_cdf


class MainWindow(FluentWindow):
    # 定义信号，用于从工作线程传递分析结果到主线程
    analysis_done = pyqtSignal(object)          # HCI 结果
    bti_analysis_done = pyqtSignal(object)      # BTI 结果
    error_occurred = pyqtSignal(str, str)       # 标题, 内容

    def __init__(self):
        super().__init__()
        self.setWindowTitle("可靠性分析工具 v5.1")
        self.setMinimumSize(1200, 800)

        setTheme(Theme.LIGHT)

        # 数据存储
        self.hci_data = None
        self.hci_current_data = None
        self.hci_result = None
        self.hci_points = None
        self.hci_file_path = None

        self.bti_data = None
        self.bti_result = None
        self.bti_points = None           # BTI 预览选中的拟合点数
        self.bti_target_years = 0.2      # BTI 目标寿命（默认0.2年）
        self.bti_file_path = None

        # 创建页面
        self.home_page = HomePage(self)
        self.hci_page = HCIPage(self)
        self.bti_page = BTIPage(self)
        self.goi_vramp_page = EmptyPage("GOI Vramp", self)
        self.goi_tddb_page = EmptyPage("GOI TDDB", self)
        self.imd_vramp_page = EmptyPage("IMD Vramp", self)
        self.imd_tddb_page = EmptyPage("IMD TDDB", self)
        self.em_page = EmptyPage("EM", self)
        self.sm_page = EmptyPage("SM", self)

        # 添加导航项
        self.addSubInterface(self.home_page, FIF.HOME, "主页")
        self.addSubInterface(self.hci_page, FIF.DOCUMENT, "HCI")
        self.addSubInterface(self.bti_page, FIF.DOCUMENT, "BTI")
        self.addSubInterface(self.goi_vramp_page, FIF.DOCUMENT, "GOI Vramp")
        self.addSubInterface(self.goi_tddb_page, FIF.DOCUMENT, "GOI TDDB")
        self.addSubInterface(self.imd_vramp_page, FIF.DOCUMENT, "IMD Vramp")
        self.addSubInterface(self.imd_tddb_page, FIF.DOCUMENT, "IMD TDDB")
        self.addSubInterface(self.em_page, FIF.DOCUMENT, "EM")
        self.addSubInterface(self.sm_page, FIF.DOCUMENT, "SM")

        self.switchTo(self.home_page)
        self.navigationInterface.setMenuButtonVisible(False)

        # 连接信号到槽
        self.analysis_done.connect(self.hci_page.update_ui)
        self.bti_analysis_done.connect(self._on_bti_analysis_done)
        self.error_occurred.connect(self._show_error)

        # 加载历史
        self.home_page.load_history()

    def switchTo(self, page):
        self.stackedWidget.setCurrentWidget(page)
        self.navigationInterface.setCurrentItem(page.objectName())

    # ---------- 辅助：显示错误信息（线程安全） ----------
    def _show_error(self, title, content):
        InfoBar.error(title=title, content=content, parent=self)

    # ---------- BTI 结果处理（主线程） ----------
    def _on_bti_analysis_done(self, result):
        """主线程处理 BTI 分析结果"""
        self.bti_result = result
        # update_ui 内部会自行读取 bti_page.target_edit 中的目标寿命用于 CDF 比较
        self.bti_page.update_ui(result)
        self.bti_page.set_status("分析完成")
        # 可以在此添加历史保存等
        print(">> BTI UI 更新完成（主线程）")

    # ---------- HCI 方法 ----------
    def load_hci_excel(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "选择 HCI Excel 文件", "", "Excel files (*.xlsx *.xls)")
        if not filepath:
            return
        try:
            self.hci_data = load_excel(filepath)
            self.hci_file_path = filepath
            # 提取 Vd/Vg
            vd_values = []
            vg_values = []
            for stress in self.hci_data.values():
                vd_values.append(stress.get('Vd_stress', 0))
                vg = stress.get('Vg_stress')
                vg_values.append(str(vg) if vg is not None else "")
            self.hci_page.update_vg_table(vd_values, vg_values)
            # 更新状态
            self.hci_page.set_data_loaded(True)
            InfoBar.success(title="成功", content=f"已加载 HCI 数据，{len(self.hci_data)} 个应力", parent=self)
        except Exception as e:
            InfoBar.error(title="错误", content=str(e), parent=self)

    def load_hci_current(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "选择三端电流文件", "", "Excel files (*.xlsx *.xls)")
        if not filepath:
            return
        try:
            self.hci_current_data = load_three_end_currents(filepath)
            self.hci_page.set_current_file_label(f"已加载: {os.path.basename(filepath)}")
            InfoBar.success(title="成功", content="三端电流加载成功", parent=self)
        except Exception as e:
            InfoBar.error(title="错误", content=str(e), parent=self)

    def run_hci_analysis(self):
        if self.hci_data is None:
            InfoBar.warning(title="警告", content="请先导入 HCI 数据", parent=self)
            return

        # 获取参数
        try:
            vd_work = float(self.hci_page.vd_edit.text())
            target_years = float(self.hci_page.target_edit.text())
            failure_percent = float(self.hci_page.fail_edit.text())
        except ValueError:
            InfoBar.warning(title="参数错误", content="请检查输入是否为有效数字", parent=self)
            return

        model_type = 'isub' if self.hci_page.model_combo.currentText() == "Isub/Id" else '1overV'
        slope_mode = self.hci_page.slope_combo.currentText()
        slope_map = {"平均斜率": "average", "独立斜率": "individual"}
        slope_mode = slope_map.get(slope_mode, "average")
        failure_criteria = failure_percent / 100.0
        cdf_quantiles = self.hci_page.get_selected_quantiles()
        device_points = self.hci_points
        # vg_list 不再需要，因为底层函数从数据中提取 Vg

        self.hci_page.set_status("分析中...")
        print("=== 开始 HCI 分析 ===")

        def analyze():
            try:
                print("  - 执行 run_hci_analysis...")
                result = run_hci_analysis(
                    data=self.hci_data,
                    vd_work=vd_work,
                    target_years=target_years,
                    model_type=model_type,
                    device_points=device_points,
                    n_last_default=5,
                    slope_mode=slope_mode,
                    cdf_quantiles=cdf_quantiles,
                    cdf_xlim=(0.1, 100),
                    current_data=self.hci_current_data,
                    isub_work_method="算术平均",
                    failure_criteria=failure_criteria
                )
                print("  - run_hci_analysis 完成")
                self.hci_result = result
                # 发射信号，将结果传递到主线程
                self.analysis_done.emit(result)
                # 保存历史
                save_history("HCI", self.hci_file_path, vd_work, target_years, model_type, device_points)
                self.home_page.load_history()
                self.hci_page.set_status("分析完成")
                print("=== HCI 分析成功 ===")
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.hci_page.set_status("错误")
                # 使用信号显示错误（线程安全）
                self.error_occurred.emit("分析错误", str(e))

        # 启动线程
        threading.Thread(target=analyze).start()

    # ---------- BTI 方法（带调试日志） ----------
    def load_bti_excel(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "选择 BTI Excel 文件", "", "Excel files (*.xlsx *.xls)")
        if not filepath:
            return
        try:
            self.bti_data = load_excel(filepath)
            self.bti_file_path = filepath
            vd_values = []
            vg_values = []
            for stress in self.bti_data.values():
                vd_values.append(stress.get('Vd_stress', 0))
                vg = stress.get('Vg_stress')
                vg_values.append(str(vg) if vg is not None else "")
            self.bti_page.update_vg_table(vd_values, vg_values)
            self.bti_page.set_data_loaded(True)
            InfoBar.success(title="成功", content=f"已加载 BTI 数据，{len(self.bti_data)} 个应力", parent=self)
        except Exception as e:
            InfoBar.error(title="错误", content=str(e), parent=self)

    def run_bti_analysis(self):
        """BTI 分析（带详细调试信息）"""
        # ---------- 调试：记录开始时间 ----------
        t0 = time.time()
        print("\n" + "="*60)
        print(">>> BTI 分析开始 <<<")
        print(f"时间戳: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # ---------- 1. 数据检查 ----------
        if self.bti_data is None:
            InfoBar.warning(title="警告", content="请先导入 BTI 数据", parent=self)
            print(">> 错误：bti_data 为 None")
            return

        print(f">> 数据加载成功：{len(self.bti_data)} 个应力条件")
        # 打印每个应力的名称和 Vd/Vg
        for name, info in self.bti_data.items():
            vd = info.get('Vd_stress', 'N/A')
            vg = info.get('Vg_stress', 'N/A')
            rows = info['data'].shape[0] if hasattr(info['data'], 'shape') else len(info['data'])
            cols = info['data'].shape[1] if hasattr(info['data'], 'shape') else len(info['data'].columns)
            print(f"   - {name}: Vd={vd}, Vg={vg}, 数据行={rows}, 器件数={cols}")

        # ---------- 2. 获取 UI 参数并检查类型 ----------
        try:
            criteria_type = self.bti_page.crit_combo.currentText()
            criteria_type = "percent" if criteria_type == "退化率(%)" else "shift"
            criteria_value_str = self.bti_page.crit_edit.text()
            vg_work_str = self.bti_page.vg_edit.text()
            target_years_str = self.bti_page.target_edit.text()
            print(f"\n>> 界面参数获取：")
            print(f"   - 判据类型: {criteria_type}")
            print(f"   - 判据数值(字符串): '{criteria_value_str}'")
            print(f"   - 工作Vg(字符串): '{vg_work_str}'")
            print(f"   - 目标寿命(字符串): '{target_years_str}'")

            if criteria_type == "percent":
                criteria_value = float(criteria_value_str) / 100.0
            else:
                criteria_value = float(criteria_value_str) / 1000.0
            vg_work = float(vg_work_str)
            self.bti_target_years = float(target_years_str)  # 存储目标寿命
            print(f"   - 转换后判据值: {criteria_value:.6f}")
            print(f"   - 转换后工作Vg: {vg_work:.6f}")
            print(f"   - 目标寿命: {self.bti_target_years:.6f} 年")
        except ValueError as e:
            InfoBar.warning(title="参数错误", content="请检查输入是否为有效数字", parent=self)
            print(f">> 参数转换错误: {e}")
            return

        # 其他参数
        slope_mode = self.bti_page.slope_combo.currentText()
        slope_map = {"平均斜率": "average", "独立斜率": "individual", "总体平均": "global_average"}
        slope_mode = slope_map.get(slope_mode, "average")
        extrapolation_model = self.bti_page.model_combo.currentText()
        extrapolation_model = "Vg" if extrapolation_model == "Vg" else "1/Vg"
        ttf_method = self.bti_page.ttf_combo.currentText()
        cdf_quantiles = self.bti_page.get_selected_quantiles()
        print(f"   - 斜率模式: {slope_mode}")
        print(f"   - 外推模型: {extrapolation_model}")
        print(f"   - TTF方法: {ttf_method}")
        print(f"   - CDF分位数: {cdf_quantiles}")

        # ---------- 3. 调用前计时 ----------
        t1 = time.time()
        print(f"\n>> 开始调用 run_bti_analysis (参数准备耗时 {t1-t0:.3f}s)")

        # ---------- 4. 调用分析函数（带异常捕获和计时） ----------
        self.bti_page.set_status("分析中...")

        def analyze():
            t_analyze_start = time.time()
            try:
                # 打印传入参数（方便核对）
                print("\n>> 调用 run_bti_analysis 的实参：")
                call_args = {
                    'data': self.bti_data,
                    'vg_work': vg_work,
                    'failure_criteria_type': criteria_type,
                    'failure_criteria_value': criteria_value,
                    'slope_mode': slope_mode,
                    'n_last_points': 5,
                    'extrapolation_model': extrapolation_model,
                    'cdf_quantiles': cdf_quantiles,
                    'cdf_xlim': (0.1, 100),
                    'ttf_method': ttf_method,
                    'device_points': self.bti_points   # 使用预览设置的点数，若无则为 None
                }
                for k, v in call_args.items():
                    if k == 'data':
                        print(f"   - {k}: <数据对象，含 {len(v)} 个应力>")
                    else:
                        print(f"   - {k}: {v}")

                # 执行分析
                result = run_bti_analysis(**call_args)

                t_analyze_end = time.time()
                print(f"\n>> run_bti_analysis 执行完成，耗时 {t_analyze_end - t_analyze_start:.3f}s")

                # ---------- 5. 检查返回结果的结构 ----------
                print("\n>> 返回结果的结构：")
                print(f"   - result 类型: {type(result)}")
                if isinstance(result, dict):
                    print(f"   - result 的键: {list(result.keys())}")
                    # 打印关键字段的长度/形状
                    for key in ['summary', 'devices_df', 'tf_work_list', 'result']:
                        if key in result:
                            val = result[key]
                            if isinstance(val, list):
                                print(f"   - {key} 长度: {len(val)}")
                            elif isinstance(val, pd.DataFrame):
                                print(f"   - {key} 形状: {val.shape}")
                            elif isinstance(val, dict):
                                print(f"   - {key} 的键: {list(val.keys())}")
                            else:
                                print(f"   - {key}: {val}")
                    # 打印第一个 summary 示例（如果有）
                    if result.get('summary'):
                        first = result['summary'][0]
                        print(f"   - 第一个应力结果示例: {first.get('stress_name')} t50={first.get('t50', 'N/A')}")
                    # 打印 tf_work_list 示例
                    if result.get('tf_work_list'):
                        print(f"   - tf_work_list 前5个: {result['tf_work_list'][:5]}")
                else:
                    print(f"   - result 内容: {result}")

                # 发射信号，将结果传递到主线程
                self.bti_analysis_done.emit(result)

            except Exception as e:
                t_analyze_end = time.time()
                print(f"\n>> ❌ 分析过程中抛出异常 (耗时 {t_analyze_end - t_analyze_start:.3f}s)")
                print(">> 完整堆栈：")
                traceback.print_exc()
                # 错误信息通过信号显示（线程安全）
                self.error_occurred.emit("BTI分析错误", str(e))
                # 状态更新需在主线程
                QMetaObject.invokeMethod(self.bti_page, "set_status", Qt.QueuedConnection, Q_ARG(str, "错误"))

        threading.Thread(target=analyze).start()

    # ---------- 历史加载 ----------
    def load_history_analysis(self, history_data):
        """由主页的 Load 按钮调用"""
        file_path = history_data.get('file_path')
        if not file_path or not os.path.exists(file_path):
            InfoBar.error(title="错误", content="数据文件不存在", parent=self)
            return
        test_type = history_data.get('test_type', 'HCI')
        if test_type == "HCI":
            self.hci_data = load_excel(file_path)
            self.hci_file_path = file_path
            self.hci_page.set_data_loaded(True)
            vd_work = history_data.get('vd_work', 1.1)
            target_years = history_data.get('target_years', 0.2)
            model_type = history_data.get('model_type', 'isub')
            self.hci_page.vd_edit.setText(str(vd_work))
            self.hci_page.target_edit.setText(str(target_years))
            self.hci_page.model_combo.setCurrentText("Isub/Id" if model_type == "isub" else "1/Vd")
            self.switchTo(self.hci_page)
            InfoBar.success(title="成功", content="历史记录已加载，请点击「开始分析」", parent=self)
        elif test_type == "BTI":
            self.bti_data = load_excel(file_path)
            self.bti_file_path = file_path
            self.bti_page.set_data_loaded(True)
            self.switchTo(self.bti_page)
            InfoBar.success(title="成功", content="历史记录已加载，请点击「开始分析」", parent=self)
        else:
            InfoBar.warning(title="提示", content="暂不支持此测试类型", parent=self)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())