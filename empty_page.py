from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from qfluentwidgets import TitleLabel, BodyLabel


class EmptyPage(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setObjectName(name.replace(" ", ""))
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        title = TitleLabel(f"{name} 页面")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        desc = BodyLabel("此页面正在开发中")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)