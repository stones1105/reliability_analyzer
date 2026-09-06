import os
from common.history_manager import get_history_list, save_history
from common.excel_loader import load_excel


class HistoryHandler:
    def __init__(self, app):
        self.app = app

    def load_and_display_history(self):
        # 由主页直接调用
        pass

    def load_history_analysis(self, history_data):
        # 已在 main_gui 中实现
        pass

    def save_current_history(self, vd_work, target_years, model_type, device_points, test_type="HCI"):
        # 由 main_gui 调用
        pass