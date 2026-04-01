import re
import uuid
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
                             QInputDialog, QMessageBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor, QAction
from core.template_engine import VariableOccurrence, PLACEHOLDER_PATTERN
from typing import List, Dict, Optional


class TemplateEditor(QWidget):
    """模板编辑器：手动选择变量并生成模板"""
    # 发射 (当前occurrences, 初始occurrences, 原始文本, 编辑模式)
    template_saved = pyqtSignal(list, list, str, bool)

    def __init__(self):
        super().__init__()
        self.occurrences: List[VariableOccurrence] = []
        self.initial_occurrences: List[VariableOccurrence] = []  # 加载时的快照
        self.edit_mode = False
        self.original_text = ""
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        # 左侧：文档显示区
        left_panel = QVBoxLayout()
        self.label_left = QLabel('文档内容（选中文本后点击"替换为变量"或在光标处"插入变量"）')
        left_panel.addWidget(self.label_left)

        self.text_edit = QTextEdit()
        self.text_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        left_panel.addWidget(self.text_edit)

        # 右侧：变量管理
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("变量列表"))

        self.var_tree = QTreeWidget()
        self.var_tree.setHeaderLabels(["变量/出处", "原文"])
        self.var_tree.setColumnCount(2)
        self.var_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.var_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.var_tree.itemClicked.connect(self._on_tree_item_clicked)
        right_panel.addWidget(self.var_tree)

        # 操作按钮 - 第一行
        btn_layout1 = QHBoxLayout()
        self.btn_add = QPushButton("+ 替换为变量")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self.add_variable_from_selection)
        btn_layout1.addWidget(self.btn_add)

        self.btn_insert = QPushButton("+ 插入变量")
        self.btn_insert.setObjectName("primary")
        self.btn_insert.clicked.connect(self.insert_variable_at_cursor)
        btn_layout1.addWidget(self.btn_insert)

        right_panel.addLayout(btn_layout1)

        # 操作按钮 - 第二行
        btn_layout2 = QHBoxLayout()
        self.btn_rename = QPushButton("重命名")
        self.btn_rename.setObjectName("secondary")
        self.btn_rename.clicked.connect(self._on_rename)
        btn_layout2.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("删除")
        self.btn_delete.setObjectName("secondary")
        self.btn_delete.clicked.connect(self._on_delete)
        btn_layout2.addWidget(self.btn_delete)

        right_panel.addLayout(btn_layout2)

        # 保存按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.btn_save = QPushButton("保存模板")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save_template)
        bottom_layout.addWidget(self.btn_save)
        right_panel.addLayout(bottom_layout)

        layout.addLayout(left_panel, 3)
        layout.addLayout(right_panel, 2)
        self.setLayout(layout)

    # ── 加载 ────────────────────────────────────────────

    def load_document_for_creation(self, text: str):
        """新建模式：加载原始文档文本"""
        self.edit_mode = False
        self.original_text = text
        self.occurrences.clear()
        self.initial_occurrences.clear()
        self.text_edit.setPlainText(text)
        self.text_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.label_left.setText('选中文本后点击"替换为变量"，或将光标置于目标位置后点击"插入变量"')
        self._refresh_variable_list()

    def load_template_for_edit(self, text: str):
        """编辑模式：加载已有模板，解析其中的 {{变量}} 占位符"""
        self.edit_mode = True
        self.original_text = text
        self.occurrences.clear()
        self.initial_occurrences.clear()
        self.text_edit.setPlainText(text)
        self.text_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.label_left.setText('选中文本后点击"替换为变量"，或将光标置于目标位置后点击"插入变量"')

        # 扫描所有 {{...}} 占位符
        for match in PLACEHOLDER_PATTERN.finditer(text):
            var_name = match.group(1).strip()
            modifier = match.group(2) or ""
            occ = VariableOccurrence(
                id=uuid.uuid4().hex,
                var_name=var_name,
                original_text=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
                modifier=modifier,
            )
            self.occurrences.append(occ)

        # 保存初始快照（用于保存时比对删除了哪些）
        import copy
        self.initial_occurrences = copy.deepcopy(self.occurrences)

        self._refresh_variable_list()
        self._refresh_highlights()

    # ── 替换为变量（需要选中文本） ──────────────────────

    def add_variable_from_selection(self):
        """将选中的文本替换为变量"""
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            QMessageBox.information(self, "提示", "请先在左侧文档中选中要替换的文本")
            return

        selected_text = cursor.selectedText().strip()
        if not selected_text:
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        # 检查是否与已有变量重叠
        for occ in self.occurrences:
            if not (end <= occ.start_pos or start >= occ.end_pos):
                QMessageBox.warning(self, "冲突",
                    f"选中区域与已有变量「{occ.var_name}」重叠，请重新选择")
                return

        name, ok = QInputDialog.getText(
            self, "命名变量",
            f"选中内容：「{selected_text[:50]}」\n请输入变量名：",
            text=self._suggest_name(selected_text)
        )
        if not ok or not name:
            return

        occ = VariableOccurrence(
            id=uuid.uuid4().hex,
            var_name=name,
            original_text=selected_text,
            start_pos=start,
            end_pos=end,
        )
        self.occurrences.append(occ)
        self._refresh_variable_list()
        self._refresh_highlights()

    # ── 插入变量（光标位置，不需要选中） ────────────────

    def insert_variable_at_cursor(self):
        """在光标位置插入一个新变量占位符"""
        cursor = self.text_edit.textCursor()
        pos = cursor.position()

        # 如果有选中文本，提示用"替换为变量"
        if cursor.hasSelection():
            QMessageBox.information(self, "提示",
                '已选中文本，请使用"替换为变量"功能')
            return

        # 检查光标是否在某个已有变量内部
        for occ in self.occurrences:
            if occ.start_pos <= pos < occ.end_pos:
                QMessageBox.warning(self, "冲突",
                    f"光标位于已有变量「{occ.var_name}」内部，请移到其他位置")
                return

        name, ok = QInputDialog.getText(
            self, "插入变量",
            "请输入变量名：",
            text="变量"
        )
        if not ok or not name:
            return

        # 插入类型：start_pos == end_pos，original_text 为空
        occ = VariableOccurrence(
            id=uuid.uuid4().hex,
            var_name=name,
            original_text="",  # 空表示纯插入
            start_pos=pos,
            end_pos=pos,
        )
        self.occurrences.append(occ)
        self._refresh_variable_list()
        self._refresh_highlights()

    # ── 重命名/删除 ─────────────────────────────────────

    def _on_rename(self):
        item = self.var_tree.currentItem()
        if not item:
            return
        if item.parent() is None:
            self._rename_group(item)
        else:
            self._rename_occurrence(item)

    def _on_delete(self):
        item = self.var_tree.currentItem()
        if not item:
            return
        if item.parent() is None:
            self._delete_group(item)
        else:
            self._delete_occurrence(item)

    def _rename_group(self, group_item: QTreeWidgetItem):
        old_name = group_item.data(0, Qt.ItemDataRole.UserRole)
        new_name, ok = QInputDialog.getText(
            self, "重命名变量组", f"将「{old_name}」重命名为：", text=old_name
        )
        if ok and new_name and new_name != old_name:
            for occ in self.occurrences:
                if occ.var_name == old_name:
                    occ.var_name = new_name
            self._refresh_variable_list()

    def _rename_occurrence(self, item: QTreeWidgetItem):
        occ_id = item.data(0, Qt.ItemDataRole.UserRole)
        occ = self._find_occurrence(occ_id)
        if not occ:
            return

        new_name, ok = QInputDialog.getText(
            self, "重命名变量", f"原文：「{occ.original_text[:50]}」\n新变量名：",
            text=occ.var_name
        )
        if ok and new_name and new_name != occ.var_name:
            occ.var_name = new_name
            self._refresh_variable_list()

    def _delete_group(self, group_item: QTreeWidgetItem):
        group_name = group_item.data(0, Qt.ItemDataRole.UserRole)
        count = sum(1 for o in self.occurrences if o.var_name == group_name)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除变量「{group_name}」的全部 {count} 处定义？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.occurrences = [o for o in self.occurrences if o.var_name != group_name]
            self._refresh_variable_list()
            self._refresh_highlights()

    def _delete_occurrence(self, item: QTreeWidgetItem):
        occ_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.occurrences = [o for o in self.occurrences if o.id != occ_id]
        self._refresh_variable_list()
        self._refresh_highlights()

    # ── 右键菜单 ────────────────────────────────────────

    def _show_context_menu(self, pos):
        item = self.var_tree.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        if item.parent() is None:
            action_rename = QAction("重命名整组", self)
            action_rename.triggered.connect(lambda: self._rename_group(item))
            menu.addAction(action_rename)

            action_delete = QAction("删除整组", self)
            action_delete.triggered.connect(lambda: self._delete_group(item))
            menu.addAction(action_delete)
        else:
            action_rename = QAction("重命名", self)
            action_rename.triggered.connect(lambda: self._rename_occurrence(item))
            menu.addAction(action_rename)

            action_delete = QAction("删除", self)
            action_delete.triggered.connect(lambda: self._delete_occurrence(item))
            menu.addAction(action_delete)

        menu.exec(self.var_tree.viewport().mapToGlobal(pos))

    # ── 树形列表刷新 ────────────────────────────────────

    def _refresh_variable_list(self):
        self.var_tree.clear()

        groups: Dict[str, List[VariableOccurrence]] = {}
        for occ in self.occurrences:
            groups.setdefault(occ.var_name, []).append(occ)

        for var_name, occs in groups.items():
            group_item = QTreeWidgetItem([f"{var_name}（{len(occs)}处）", ""])
            group_item.setData(0, Qt.ItemDataRole.UserRole, var_name)
            group_item.setExpanded(True)

            for i, occ in enumerate(occs, 1):
                if occ.original_text:
                    display = occ.original_text[:30]
                    if len(occ.original_text) > 30:
                        display += "..."
                else:
                    display = "[插入]"
                child = QTreeWidgetItem([f"  #{i}", display])
                child.setData(0, Qt.ItemDataRole.UserRole, occ.id)
                group_item.addChild(child)

            self.var_tree.addTopLevelItem(group_item)

        self.var_tree.resizeColumnToContents(0)

    # ── 高亮 ────────────────────────────────────────────

    def _refresh_highlights(self):
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(255, 255, 255))
        cursor.setCharFormat(fmt)

        for occ in self.occurrences:
            if occ.start_pos < occ.end_pos:
                self._highlight_range(occ.start_pos, occ.end_pos, QColor(144, 238, 144))

    def _highlight_range(self, start: int, end: int, color: QColor):
        cursor = self.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        cursor.setCharFormat(fmt)

    # ── 点击定位 ────────────────────────────────────────

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        if item.parent() is None:
            return

        occ_id = item.data(0, Qt.ItemDataRole.UserRole)
        occ = self._find_occurrence(occ_id)
        if occ:
            cursor = self.text_edit.textCursor()
            cursor.setPosition(occ.start_pos)
            if occ.end_pos > occ.start_pos:
                cursor.setPosition(occ.end_pos, QTextCursor.MoveMode.KeepAnchor)
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()

    # ── 保存 ────────────────────────────────────────────

    def save_template(self):
        if not self.occurrences:
            QMessageBox.warning(self, "提示", "请至少添加一个变量")
            return

        self.template_saved.emit(
            list(self.occurrences),
            list(self.initial_occurrences),
            self.original_text,
            self.edit_mode
        )

    # ── 辅助方法 ────────────────────────────────────────

    def _find_occurrence(self, occ_id: str) -> Optional[VariableOccurrence]:
        for occ in self.occurrences:
            if occ.id == occ_id:
                return occ
        return None

    def _suggest_name(self, text: str) -> str:
        if re.match(r'\d{4}年', text):
            return "日期"
        if '有限公司' in text or '股份' in text:
            return "公司名称"
        if len(text) <= 3:
            return "姓名"
        if '地址' in text or '区' in text:
            return "地址"
        return "变量"
