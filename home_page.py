import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGridLayout, QListWidget, QListWidgetItem,
                             QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from qfluentwidgets import TitleLabel, BodyLabel, SubtitleLabel, PrimaryPushButton, ListWidget, InfoBar, InfoBarPosition
from common.history_manager import get_history_list


class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("homePage")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 左侧面板
        left_panel = QFrame()
        left_panel.setFixedWidth(400)
        left_panel.setStyleSheet("background-color: #f5f5f5; border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)

        title = TitleLabel("可靠性分析工具")
        left_layout.addWidget(title)

        self.image_label = QLabel()
        self.image_label.setFixedSize(360, 240)
        self.image_label.setStyleSheet("background-color: #ffffff; border: 1px solid #d1d9e6; border-radius: 4px;")
        self.image_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.image_label)

        self.desc_label = BodyLabel("请选择测试项目")
        self.desc_label.setWordWrap(True)
        left_layout.addWidget(self.desc_label)

        history_label = SubtitleLabel("History")
        left_layout.addWidget(history_label)

        self.history_list = ListWidget()
        self.history_list.setMaximumHeight(120)
        self.history_list.itemClicked.connect(self.on_history_selected)
        left_layout.addWidget(self.history_list)

        self.load_btn = PrimaryPushButton("Load")
        self.load_btn.setFixedWidth(100)
        self.load_btn.setEnabled(False)
        self.load_btn.clicked.connect(self.on_load_history)
        left_layout.addWidget(self.load_btn, alignment=Qt.AlignRight)

        left_layout.addStretch()

        # 右侧面板
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: white; border-radius: 8px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)

        grid = QGridLayout()
        grid.setSpacing(15)

        tests = [
            ("GOI Vramp", "goi_vramp"),
            ("GOI TDDB", "goi_tddb"),
            ("IMD Vramp", "imd_vramp"),
            ("IMD TDDB", "imd_tddb"),
            ("HCI", "hci"),
            ("BTI", "bti"),
            ("EM", "em"),
            ("SM", "sm")
        ]

        for idx, (label, page_name) in enumerate(tests):
            row = idx // 2
            col = idx % 2
            btn = PrimaryPushButton(label)
            btn.setFixedHeight(60)
            btn.clicked.connect(lambda checked, p=page_name: self.on_button_click(p))
            grid.addWidget(btn, row, col)

        for i in range(4):
            grid.setRowStretch(i, 1)
        for j in range(2):
            grid.setColumnStretch(j, 1)

        right_layout.addLayout(grid)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

        self._selected_record = None
        self._history_records = []

        self.update_preview("HCI")

    def on_button_click(self, page_name):
        self.update_preview(page_name.upper())
        if page_name == "hci":
            self.parent.switchTo(self.parent.hci_page)
        elif page_name == "bti":
            self.parent.switchTo(self.parent.bti_page)
        else:
            InfoBar.info(
                title="提示",
                content=f"{page_name} 功能开发中",
                parent=self.parent,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000
            )

    def update_preview(self, test_name):
        image_dir = "images"
        image_file = test_name.lower().replace(' ', '_') + '.png'
        image_path = os.path.join(image_dir, image_file)
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(360, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText("[图片加载失败]")
        else:
            self.image_label.setText("[图片占位]")

        descriptions = {
            "HCI": "热载流子注入（HCI）是 MOS 器件在沟道电场作用下，载流子获得足够能量注入栅氧化层，引起参数退化的可靠性问题。",
            "BTI": "偏置温度不稳定性（BTI）是指 MOS 器件在高温和电场应力下，界面陷阱和氧化层电荷增加导致的阈值电压漂移。",
            "GOI Vramp": "栅氧化层完整性（GOI）电压斜坡测试，用于评估栅氧化层的本征击穿特性。",
            "GOI TDDB": "栅氧化层经时击穿（TDDB）测试，评估氧化层在长期恒定电压应力下的寿命。",
            "IMD Vramp": "金属层间介质（IMD）电压斜坡测试，用于评估层间介质的击穿强度。",
            "IMD TDDB": "金属层间介质经时击穿（TDDB）测试，评估层间介质在长期电压应力下的可靠性。",
            "EM": "电迁移（EM）是金属互连线在电流作用下原子定向迁移导致的失效现象，是互连可靠性的重要指标。",
            "SM": "应力迁移（SM）是金属线在机械应力作用下原子扩散导致的失效，与封装和温度应力相关。"
        }
        self.desc_label.setText(descriptions.get(test_name, ""))

    def load_history(self):
        self._history_records = get_history_list()
        self.history_list.clear()
        if self._history_records:
            for rec in self._history_records:
                item = QListWidgetItem(rec['display'])
                item.setData(Qt.UserRole, rec['record'])
                self.history_list.addItem(item)
            self.history_list.setCurrentRow(0)
            self._selected_record = self._history_records[0]['record']
            self.load_btn.setEnabled(True)
        else:
            self.history_list.addItem("暂无历史记录")
            self.load_btn.setEnabled(False)

    def on_history_selected(self, item):
        record = item.data(Qt.UserRole)
        if record:
            self._selected_record = record
            self.load_btn.setEnabled(True)
        else:
            self._selected_record = None
            self.load_btn.setEnabled(False)

    def on_load_history(self):
        if self._selected_record:
            # 调用主窗口的历史加载方法
            self.parent.load_history_analysis(self._selected_record)