import os
from .excel_loader import load_excel
from .current_loader import load_three_end_currents

class DataManager:
    def __init__(self):
        self._idsat_data = None
        self._current_data = None
        self._idsat_file_path = None
        self._current_file_path = None

    def load_idsat(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        self._idsat_data = load_excel(file_path)
        self._idsat_file_path = file_path
        return self._idsat_data

    def load_current(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        self._current_data = load_three_end_currents(file_path)
        self._current_file_path = file_path
        return self._current_data

    def get_idsat_data(self):
        return self._idsat_data

    def get_current_data(self):
        return self._current_data

    def get_idsat_file_path(self):
        return self._idsat_file_path

    def get_current_file_path(self):
        return self._current_file_path

    def clear(self):
        self._idsat_data = None
        self._current_data = None
        self._idsat_file_path = None
        self._current_file_path = None