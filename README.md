# 律师文档填充助手

一个完全离线的Windows桌面应用，帮助律师快速处理合同文档中的重复填写内容。

## 功能特点

- ✅ **智能识别变量**：自动识别Word/Excel文档中的日期、金额、公司名、身份证号等常见变量
- ✅ **可视化审核**：高亮显示识别结果，支持手动框选和调整
- ✅ **模板管理**：将原始文档转换为可复用的模板
- ✅ **变量组**：保存常用客户信息，一键调用
- ✅ **批量生成**：基于模板快速生成多份文档
- ✅ **完全离线**：无需网络，不依赖大模型，保护客户隐私

## 技术栈

- **UI框架**: PyQt6
- **文档处理**: python-docx, openpyxl
- **中文分词**: jieba
- **数据库**: SQLite
- **打包工具**: PyInstaller

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python main.py
```

## 使用流程

### 阶段一：创建模板（首次）

1. 点击"导入原始文档"，选择Word或Excel文件
2. 程序自动识别文档中的变量（日期、金额、公司名等）
3. 审核识别结果：
   - 蓝色高亮 = 高置信度，双击接受
   - 黄色高亮 = 待确认，双击后可修改变量名
   - 手动框选 = 选中文本后点击"手动框选"添加变量
4. 点击"保存为模板"，输入模板名称

### 阶段二：填充生成（日常使用）

1. 从左侧模板库选择模板
2. 填写变量值（可选择已保存的变量组）
3. 点击"一键生成"，选择保存位置
4. 完成！可选择立即打开文档

## 项目结构

```
law_pyqt/
├── main.py                  # 程序入口
├── requirements.txt         # 依赖列表
├── assets/
│   ├── legal_dict.txt      # 法律领域词典
│   └── styles/
│       └── theme.qss       # UI样式
├── core/
│   ├── template_engine.py   # 模板引擎
│   ├── recognition_engine.py # 三层识别引擎
│   ├── word_processor.py    # Word处理
│   └── excel_processor.py   # Excel处理
├── ui/
│   ├── main_window.py       # 主窗口
│   ├── template_editor.py   # 模板编辑器
│   └── variable_panel.py    # 变量填写面板
├── db/
│   └── database.py          # 数据库操作
└── utils/
    └── cn_number.py         # 人民币大写转换
```

## 打包为exe

```bash
pyinstaller --onefile --windowed \
  --add-data "assets;assets" \
  --name "律师文档填充助手" main.py
```

生成的exe文件在`dist`目录下，约40-60MB，可直接分发使用。

## 占位符语法

模板中使用双花括号语法：

```
{{甲方名称}}
{{合同金额|upper}}     # 自动转大写人民币
{{签订日期|date}}      # 格式化为中文日期
```

## 许可证

MIT License
