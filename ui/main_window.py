from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QListWidget, QFileDialog,
                             QMessageBox, QStackedWidget, QListWidgetItem,
                             QInputDialog, QSplitter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import os
import shutil
import tempfile
from pathlib import Path

from core.word_processor import WordProcessor
from core.excel_processor import ExcelProcessor
from db.database import Database
from ui.template_editor import TemplateEditor
from ui.variable_panel import VariablePanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.word_processor = WordProcessor()
        self.excel_processor = ExcelProcessor()

        self.current_template = None
        self.current_template_path = None
        self.editing_template_id = None  # 用于标记是否在编辑现有模板

        self.init_ui()
        self.load_templates()

    def init_ui(self):
        self.setWindowTitle("律师文档填充助手")
        self.setGeometry(100, 100, 1400, 800)

        # 加载样式
        self.load_stylesheet()

        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()

        # 左侧：模板库
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("📚 模板库"))

        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self.on_template_selected)
        left_panel.addWidget(self.template_list)

        btn_layout = QVBoxLayout()
        self.btn_import_doc = QPushButton("+ 导入原始文档")
        self.btn_import_doc.setObjectName("primary")
        self.btn_import_doc.clicked.connect(self.import_document)
        btn_layout.addWidget(self.btn_import_doc)

        self.btn_import_template = QPushButton("+ 导入已有模板")
        self.btn_import_template.setObjectName("secondary")
        self.btn_import_template.clicked.connect(self.import_template)
        btn_layout.addWidget(self.btn_import_template)

        self.btn_edit = QPushButton("✏️ 编辑模板")
        self.btn_edit.setObjectName("secondary")
        self.btn_edit.clicked.connect(self.edit_template)
        btn_layout.addWidget(self.btn_edit)

        self.btn_export = QPushButton("📤 导出模板")
        self.btn_export.setObjectName("secondary")
        self.btn_export.clicked.connect(self.export_template)
        btn_layout.addWidget(self.btn_export)

        self.btn_help = QPushButton("❓ 模板格式说明")
        self.btn_help.setObjectName("secondary")
        self.btn_help.clicked.connect(self.show_template_help)
        btn_layout.addWidget(self.btn_help)

        self.btn_delete = QPushButton("删除模板")
        self.btn_delete.setObjectName("secondary")
        self.btn_delete.clicked.connect(self.delete_template)
        btn_layout.addWidget(self.btn_delete)

        left_panel.addLayout(btn_layout)

        # 中间和右侧：堆叠窗口
        self.stacked_widget = QStackedWidget()

        # 页面1：模板编辑器
        self.template_editor = TemplateEditor()
        self.template_editor.template_saved.connect(self.on_template_saved)
        self.stacked_widget.addWidget(self.template_editor)

        # 页面2：变量填写面板
        self.variable_panel = VariablePanel()
        self.variable_panel.generate_clicked.connect(self.on_generate_document)
        self.stacked_widget.addWidget(self.variable_panel)

        # 页面3：欢迎页
        welcome = QWidget()
        welcome_layout = QVBoxLayout()
        welcome_layout.addStretch()
        welcome_label = QLabel("👈 请从左侧导入文档或选择模板")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 18px; color: #999;")
        welcome_layout.addWidget(welcome_label)
        welcome_layout.addStretch()
        welcome.setLayout(welcome_layout)
        self.stacked_widget.addWidget(welcome)

        # 默认显示欢迎页
        self.stacked_widget.setCurrentIndex(2)

        # 组合布局
        main_layout.addLayout(left_panel, 1)
        main_layout.addWidget(self.stacked_widget, 4)

        central.setLayout(main_layout)

    def load_stylesheet(self):
        """加载样式表"""
        style_path = Path(__file__).parent.parent / "assets" / "styles" / "theme.qss"
        if style_path.exists():
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

    def load_templates(self):
        """加载模板列表"""
        self.template_list.clear()
        templates = self.db.get_templates()

        for tpl in templates:
            item = QListWidgetItem(f"📄 {tpl['name']}")
            item.setData(Qt.ItemDataRole.UserRole, tpl)
            self.template_list.addItem(item)

    def import_document(self):
        """导入原始文档进行模板化"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择原始文档",
            "", "文档文件 (*.docx *.xlsx)"
        )

        if not file_path:
            return

        try:
            if file_path.endswith('.docx'):
                text = self.word_processor.extract_text(file_path)
                processor = self.word_processor
            else:
                text = self.excel_processor.extract_text(file_path)
                processor = self.excel_processor

            # 直接加载到编辑器，由用户手动选择变量
            self.template_editor.load_document_for_creation(text)
            self.stacked_widget.setCurrentWidget(self.template_editor)

            self.editing_template_id = None
            self.current_original_path = file_path
            self.current_processor = processor

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败：{str(e)}")

    def on_template_saved(self, occurrences: list, initial_occurrences: list,
                          original_text: str, is_edit: bool):
        """模板保存回调（新建和编辑共用）

        统一使用按位置替换，支持：替换文本、插入变量、删除变量、重命名变量
        """
        if self.editing_template_id:
            name = self.current_template['name']
        else:
            name, ok = QInputDialog.getText(self, "保存模板", "请输入模板名称:")
            if not ok or not name:
                return

        try:
            templates_dir = Path("templates")
            templates_dir.mkdir(exist_ok=True)

            file_ext = Path(self.current_original_path).suffix
            file_type = "word" if file_ext == ".docx" else "excel"

            # 构建按位置替换列表: [(start, end, new_text), ...]
            replacement_list = []

            if is_edit:
                # 编辑模式：比对初始和当前 occurrences
                initial_by_id = {o.id: o for o in initial_occurrences}
                current_ids = {o.id for o in occurrences}

                # 1) 被删除的变量 -> 替换为空字符串
                for init_occ in initial_occurrences:
                    if init_occ.id not in current_ids:
                        replacement_list.append(
                            (init_occ.start_pos, init_occ.end_pos, "")
                        )

                # 2) 保留的变量（可能被重命名）
                for occ in occurrences:
                    placeholder = f"{{{{{occ.var_name}}}}}"
                    if occ.modifier:
                        placeholder = f"{{{{{occ.var_name}|{occ.modifier}}}}}"

                    if occ.id in initial_by_id:
                        # 原有变量：检查是否重命名
                        if occ.original_text != placeholder:
                            replacement_list.append(
                                (occ.start_pos, occ.end_pos, placeholder)
                            )
                    else:
                        # 新增的变量
                        replacement_list.append(
                            (occ.start_pos, occ.end_pos, placeholder)
                        )
            else:
                # 新建模式：每个 occurrence 替换为占位符
                for occ in occurrences:
                    placeholder = f"{{{{{occ.var_name}}}}}"
                    if occ.modifier:
                        placeholder = f"{{{{{occ.var_name}|{occ.modifier}}}}}"
                    replacement_list.append(
                        (occ.start_pos, occ.end_pos, placeholder)
                    )

            if is_edit:
                # 编辑模式：在原模板文件上操作
                if replacement_list:
                    temp_fd, temp_path = tempfile.mkstemp(suffix=file_ext)
                    os.close(temp_fd)
                    try:
                        self.current_processor.apply_replacements_by_positions(
                            self.current_original_path, temp_path, replacement_list
                        )
                        shutil.move(temp_path, self.current_original_path)
                    except Exception:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        raise

                self.db.update_template(
                    self.editing_template_id, name,
                    self.current_original_path, file_type
                )
                QMessageBox.information(self, "成功", f"模板「{name}」已更新")
                self.editing_template_id = None
            else:
                # 新建模式
                template_path = templates_dir / f"{name}{file_ext}"
                self.current_processor.apply_replacements_by_positions(
                    self.current_original_path,
                    str(template_path),
                    replacement_list
                )
                self.db.add_template(name, str(template_path), file_type)
                QMessageBox.information(self, "成功", f"模板「{name}」已创建")

            self.load_templates()
            self.stacked_widget.setCurrentIndex(2)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存模板失败：{str(e)}")

    def import_template(self):
        """导入已有模板"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择模板文件",
            "", "模板文件 (*.docx *.xlsx)"
        )

        if not file_path:
            return

        name, ok = QInputDialog.getText(self, "导入模板", "请输入模板名称:")
        if not ok or not name:
            return

        try:
            # 复制到templates目录
            templates_dir = Path("templates")
            templates_dir.mkdir(exist_ok=True)

            file_ext = Path(file_path).suffix
            template_path = templates_dir / f"{name}{file_ext}"

            import shutil
            shutil.copy(file_path, template_path)

            # 保存到数据库
            file_type = "word" if file_ext == ".docx" else "excel"
            self.db.add_template(name, str(template_path), file_type)

            QMessageBox.information(self, "成功", f"模板 '{name}' 已导入")
            self.load_templates()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败：{str(e)}")

    def on_template_selected(self, item: QListWidgetItem):
        """选择模板"""
        template = item.data(Qt.ItemDataRole.UserRole)
        self.current_template = template
        self.current_template_path = template['file_path']

        try:
            # 提取变量
            if template['file_type'] == 'word':
                variables = self.word_processor.extract_variables(template['file_path'])
            else:
                variables = self.excel_processor.extract_variables(template['file_path'])

            # 获取变量组列表
            groups = [g['name'] for g in self.db.get_variable_groups()]

            # 显示变量填写面板
            self.variable_panel.load_variables(variables, groups)
            self.stacked_widget.setCurrentWidget(self.variable_panel)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模板失败：{str(e)}")

    def on_generate_document(self, values: dict):
        """生成最终文档"""
        if not self.current_template:
            return

        # 选择保存位置
        default_name = f"{self.current_template['name']}_生成.{self.current_template['file_type']}"
        if self.current_template['file_type'] == 'word':
            default_name = default_name.replace('.word', '.docx')
        else:
            default_name = default_name.replace('.excel', '.xlsx')

        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存文档",
            default_name,
            "文档文件 (*.docx *.xlsx)"
        )

        if not output_path:
            return

        try:
            # 生成文档
            if self.current_template['file_type'] == 'word':
                self.word_processor.fill_and_save(
                    self.current_template_path,
                    output_path,
                    values
                )
            else:
                self.excel_processor.fill_and_save(
                    self.current_template_path,
                    output_path,
                    values
                )

            # 保存历史记录
            self.db.add_history(self.current_template['id'], output_path, values)

            QMessageBox.information(self, "成功", f"文档已生成：\n{output_path}")

            # 询问是否打开
            reply = QMessageBox.question(
                self, "提示", "是否打开生成的文档？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(output_path)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成文档失败：{str(e)}")

    def delete_template(self):
        """删除模板"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要删除的模板")
            return

        template = current_item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板 '{template['name']}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 删除文件
                if os.path.exists(template['file_path']):
                    os.remove(template['file_path'])

                # 从数据库删除
                self.db.delete_template(template['id'])

                QMessageBox.information(self, "成功", "模板已删除")
                self.load_templates()
                self.stacked_widget.setCurrentIndex(2)

            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败：{str(e)}")

    def show_template_help(self):
        """显示模板格式说明"""
        help_text = """
<h3>📋 模板格式说明</h3>

<p><b>支持的文件格式：</b></p>
<ul>
<li>Word文档：.docx（不支持旧版.doc）</li>
<li>Excel表格：.xlsx（不支持旧版.xls）</li>
</ul>

<p><b>占位符语法：</b></p>
<p>使用双花括号包裹变量名：</p>
<pre>
{{甲方名称}}
{{乙方名称}}
{{合同金额}}
{{签订日期}}
</pre>

<p><b>支持的修饰符（可选）：</b></p>
<pre>
{{合同金额|upper}}  → 自动转换为大写人民币
{{签订日期|date}}   → 格式化为中文日期（如：2025年01月01日）
</pre>

<p><b>示例模板内容：</b></p>
<pre>
本合同由 {{甲方名称}} （以下简称"甲方"）与 {{乙方名称}}
（以下简称"乙方"）于 {{签订日期|date}} 签订。

合同金额为 {{合同金额|upper}}。
</pre>

<p><b>💡 提示：</b></p>
<ul>
<li>如果没有现成模板，建议使用"导入原始文档"功能</li>
<li>在原始文档中选中文本，点击"添加变量"即可创建变量</li>
<li>同一个变量名可以在文档中多次使用，填写时只需填一遍</li>
<li>已有模板可以随时通过"编辑模板"功能进行修改</li>
</ul>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("模板格式说明")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def edit_template(self):
        """编辑现有模板"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要编辑的模板")
            return

        template = current_item.data(Qt.ItemDataRole.UserRole)

        try:
            if template['file_type'] == 'word':
                text = self.word_processor.extract_text(template['file_path'])
                processor = self.word_processor
            else:
                text = self.excel_processor.extract_text(template['file_path'])
                processor = self.excel_processor

            # 编辑模式：解析已有 {{变量}} 占位符
            self.template_editor.load_template_for_edit(text)
            self.stacked_widget.setCurrentWidget(self.template_editor)

            self.editing_template_id = template['id']
            self.current_template = template
            self.current_original_path = template['file_path']
            self.current_processor = processor

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模板失败：{str(e)}")

    def export_template(self):
        """导出模板"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要导出的模板")
            return

        template = current_item.data(Qt.ItemDataRole.UserRole)

        # 选择保存位置
        file_ext = ".docx" if template['file_type'] == 'word' else ".xlsx"
        default_name = f"{template['name']}{file_ext}"

        output_path, _ = QFileDialog.getSaveFileName(
            self, "导出模板",
            default_name,
            f"{'Word文档' if file_ext == '.docx' else 'Excel表格'} (*{file_ext})"
        )

        if output_path:
            try:
                import shutil
                shutil.copy(template['file_path'], output_path)
                QMessageBox.information(self, "成功", f"模板已导出到：\n{output_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败：{str(e)}")

