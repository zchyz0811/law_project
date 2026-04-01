from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QScrollArea, QFrame,
                             QComboBox, QMessageBox, QDateEdit, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from typing import List, Dict
from core.template_engine import Variable

class VariablePanel(QWidget):
    """变量填写面板"""
    generate_clicked = pyqtSignal(dict)  # 填写完成，发送变量值字典

    def __init__(self):
        super().__init__()
        self.variables: List[Variable] = []
        self.inputs: Dict[str, QWidget] = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 顶部：变量组选择
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("变量组:"))
        self.combo_groups = QComboBox()
        self.combo_groups.currentTextChanged.connect(self.load_variable_group)
        top_layout.addWidget(self.combo_groups)

        self.btn_save_group = QPushButton("保存为变量组")
        self.btn_save_group.setObjectName("secondary")
        self.btn_save_group.clicked.connect(self.save_as_group)
        top_layout.addWidget(self.btn_save_group)
        top_layout.addStretch()

        layout.addLayout(top_layout)

        # 中间：滚动区域显示变量输入框
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.form_widget = QWidget()
        self.form_layout = QFormLayout()
        self.form_widget.setLayout(self.form_layout)
        scroll.setWidget(self.form_widget)

        layout.addWidget(scroll)

        # 底部：生成按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.btn_generate = QPushButton("📋 一键生成")
        self.btn_generate.setObjectName("primary")
        self.btn_generate.clicked.connect(self.on_generate)
        bottom_layout.addWidget(self.btn_generate)

        layout.addLayout(bottom_layout)
        self.setLayout(layout)

    def load_variables(self, variables: List[Variable], groups: List[str]):
        """加载变量列表"""
        self.variables = variables
        self.inputs.clear()

        # 清空表单
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 更新变量组下拉框
        self.combo_groups.clear()
        self.combo_groups.addItem("-- 选择变量组 --")
        self.combo_groups.addItems(groups)

        # 创建输入框
        for var in variables:
            label = QLabel(f"{var.name}:")

            # 根据修饰符选择输入控件
            if var.modifier == "date":
                input_widget = QDateEdit()
                input_widget.setCalendarPopup(True)
                input_widget.setDate(QDate.currentDate())
                input_widget.setDisplayFormat("yyyy-MM-dd")
            else:
                input_widget = QLineEdit()
                input_widget.setPlaceholderText(f"请输入{var.name}")

            self.form_layout.addRow(label, input_widget)
            self.inputs[var.name] = input_widget

    def get_values(self) -> Dict[str, str]:
        """获取所有变量的值"""
        values = {}
        for name, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                values[name] = widget.text().strip()
            elif isinstance(widget, QDateEdit):
                values[name] = widget.date().toString("yyyy-MM-dd")
        return values

    def set_values(self, values: Dict[str, str]):
        """设置变量值"""
        for name, value in values.items():
            if name in self.inputs:
                widget = self.inputs[name]
                if isinstance(widget, QLineEdit):
                    widget.setText(value)
                elif isinstance(widget, QDateEdit):
                    date = QDate.fromString(value, "yyyy-MM-dd")
                    if date.isValid():
                        widget.setDate(date)

    def load_variable_group(self, group_name: str):
        """加载变量组"""
        if group_name == "-- 选择变量组 --":
            return
        # 由主窗口处理
        from db.database import Database
        db = Database()
        group = db.get_variable_group(group_name)
        if group:
            self.set_values(group['variables'])

    def save_as_group(self):
        """保存为变量组"""
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "保存变量组", "请输入变量组名称:")
        if ok and name:
            values = self.get_values()
            from db.database import Database
            db = Database()
            db.save_variable_group(name, values)
            QMessageBox.information(self, "成功", f"变量组 '{name}' 已保存")

            # 更新下拉框
            if self.combo_groups.findText(name) == -1:
                self.combo_groups.addItem(name)

    def on_generate(self):
        """点击生成按钮"""
        values = self.get_values()

        # 检查必填项
        empty_fields = [name for name, val in values.items() if not val]
        if empty_fields:
            QMessageBox.warning(
                self, "提示",
                f"以下字段不能为空：\n" + "\n".join(empty_fields)
            )
            return

        self.generate_clicked.emit(values)
