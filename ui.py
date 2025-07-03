import os
import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QFileDialog, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "noco_gui_config.json")
GENERAL_FILE = os.path.join(CONFIG_DIR, "noco_gui_general.json")

class NocoDBTool(QWidget):
    def __init__(self):
        super().__init__()
         # 新增：确保 config 文件夹存在
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.setWindowTitle("NocoDB 导出 json 可视化工具")
        self.resize(1000, 600)
        self.configs = []
        self.init_ui()
        self.load_general()
        self.load_configs()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 左侧配置列表
        self.config_list = QListWidget()
        self.config_list.itemClicked.connect(self.apply_config)

        # 配置删除按钮
        self.delete_btn = QPushButton("删除配置")
        self.delete_btn.clicked.connect(self.delete_config)
        self.delete_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")  # 红色

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.config_list)
        left_layout.addWidget(self.delete_btn)
        main_layout.addLayout(left_layout, 1)

        # 右侧表单
        form_layout = QVBoxLayout()

        # 通用设置区域
        general_group = QVBoxLayout()
        general_group.addWidget(QLabel("【通用设置】"))
        self.host_input = QLineEdit("localhost:8080")  # 默认值
        self.token_input = QLineEdit()
        general_group.addWidget(QLabel("Host:"))
        general_group.addWidget(self.host_input)
        general_group.addWidget(QLabel("Token:"))
        general_group.addWidget(self.token_input)
        form_layout.addLayout(general_group)

        # 分割线
        line = QLabel("--------------------------------------------------")
        line.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(line)

        # 任务参数区域
        self.table_id_input = QLineEdit()
        self.view_id_input = QLineEdit()
        output_file_layout = QHBoxLayout()
        self.output_file_input = QLineEdit("processed_data.json")
        self.output_file_btn = QPushButton("选择路径")
        self.output_file_btn.clicked.connect(self.choose_output_file)
        output_file_layout.addWidget(self.output_file_input)
        output_file_layout.addWidget(self.output_file_btn)

        form_layout.addWidget(QLabel("Table ID:"))
        form_layout.addWidget(self.table_id_input)
        form_layout.addWidget(QLabel("View ID:"))
        form_layout.addWidget(self.view_id_input)
        form_layout.addWidget(QLabel("输出文件名:"))
        form_layout.addLayout(output_file_layout)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("执行")
        self.run_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")  # 绿色
        self.save_btn = QPushButton("保存为配置")
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")  # 蓝色
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.save_btn)
        form_layout.addLayout(btn_layout)

        self.run_btn.clicked.connect(self.run_script)
        self.save_btn.clicked.connect(self.save_config)

        main_layout.addLayout(form_layout, 2)

    def choose_output_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "选择输出文件", self.output_file_input.text(), "JSON Files (*.json);;All Files (*)")
        if path:
            self.output_file_input.setText(path)

    def delete_config(self):
        idx = self.config_list.currentRow()
        if idx < 0 or idx >= len(self.configs):
            QMessageBox.warning(self, "提示", "请选择要删除的配置")
            return
        reply = QMessageBox.question(self, "确认删除", f"确定要删除配置“{self.configs[idx]['name']}”吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.configs[idx]
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.configs, f, ensure_ascii=False, indent=2)
            self.load_configs()
    def load_general(self):
        try:
            with open(GENERAL_FILE, "r", encoding="utf-8") as f:
                general = json.load(f)
            self.host_input.setText(general.get("host", ""))
            self.token_input.setText(general.get("token", ""))
        except Exception:
            self.host_input.setText("")
            self.token_input.setText("")

    def save_general(self):
        general = {
            "host": self.host_input.text().strip(),
            "token": self.token_input.text().strip()
        }
        with open(GENERAL_FILE, "w", encoding="utf-8") as f:
            json.dump(general, f, ensure_ascii=False, indent=2)

    def load_configs(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.configs = json.load(f)
            self.config_list.clear()
            for cfg in self.configs:
                self.config_list.addItem(cfg["name"])
        except Exception:
            self.configs = []

    def save_config(self):
        name, ok = QInputDialog.getText(self, "配置名称", "请输入配置名称：")
        if not ok or not name.strip():
            return
        config = {
            "name": name.strip(),
            "table_id": self.table_id_input.text().strip(),
            "view_id": self.view_id_input.text().strip(),
            "output_file": self.output_file_input.text().strip()
        }
        self.configs.append(config)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.configs, f, ensure_ascii=False, indent=2)
        self.load_configs()
        self.save_general()  # 保存通用设置

    def apply_config(self, item):
        idx = self.config_list.currentRow()
        cfg = self.configs[idx]
        self.table_id_input.setText(cfg["table_id"])
        self.view_id_input.setText(cfg["view_id"])
        self.output_file_input.setText(cfg["output_file"])

    def run_script(self):
        # 这里直接调用你已有的处理逻辑
        try:
            from JsonExporter import main as noco_main
        except ImportError:
            QMessageBox.critical(self, "错误", "请将主处理逻辑封装为 JsonExporter.py 的 main(host, token, table_id, view_id, output_file) 函数")
            return
        host = self.host_input.text().strip()
        token = self.token_input.text().strip()
        table_id = self.table_id_input.text().strip()
        view_id = self.view_id_input.text().strip()
        output_file = self.output_file_input.text().strip()
        try:
            noco_main(host, token, table_id, view_id, output_file)
            QMessageBox.information(self, "完成", f"数据已保存到 {output_file}")
        except Exception as e:
            QMessageBox.critical(self, "执行失败", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = NocoDBTool()
    win.show()
    sys.exit(app.exec_())