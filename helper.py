#!/usr/bin/env python3

# File: helper.py
# Author: Hadi Cahyadi <cumulus13@gmail.com>
# Date: 2026-10-03
# Description: 
# License: MIT


import os
import re
import sys
import json
import argparse
import zipfile

# Try importing PyQt5, fallback to Tkinter if unavailable
PYQT_AVAILABLE = False
try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QKeySequence, QFont
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout,
        QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QShortcut
    )
    PYQT_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk


def parse_shortcuts(file_path=None, raw_content=None):
    """Parses Sublime Text keymap JSON file with support for comments, trailing commas, and control chars."""
    if not file_path and not raw_content:
        return []

    shortcuts = []
    try:
        if raw_content:
            content = raw_content
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

        # 1. Remove block comments /* ... */
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # 2. Remove line comments // ... (make sure not to remove file:// or res:// by accident, though rare in keymaps)
        content = re.sub(r'(?<!:)//.*', '', content)
        # 3. Remove trailing commas from objects/arrays (invalid in strict JSON, allowed in ST)
        content = re.sub(r',\s*([\]}])', r'\1', content)

        # Parse the cleaned string as JSON. strict=False allows literal tabs/newlines in strings
        data = json.loads(content, strict=False)
        
        for item in data:
            if 'keys' in item and 'command' in item:
                # ST chords are in arrays (e.g. ["ctrl+o", "ctrl+k"]). Join them with a comma.
                hk = ", ".join(item['keys'])
                
                # Use the command name as the base description
                desc = item['command']
                
                # Append arguments if they exist to provide full context
                if 'args' in item:
                    args_str = json.dumps(item['args'])
                    desc = f"{desc}  |  args: {args_str}"
                    
                shortcuts.append({"key": hk, "desc": desc})
                
        return shortcuts
    except Exception as e:
        print(f"Error parsing keymap: {e}")
        return []


# ==========================================
# PyQt5 GUI Implementation
# ==========================================
if PYQT_AVAILABLE:
    class SearchLineEdit(QLineEdit):
        def __init__(self, table_widget, parent=None):
            super().__init__(parent)
            self.table_widget = table_widget

        def keyPressEvent(self, event):
            if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
                self.table_widget.keyPressEvent(event)
            else:
                super().keyPressEvent(event)

    class SublimeKeymapViewerPyQt(QMainWindow):
        def __init__(self, shortcuts, source_name):
            super().__init__()
            self.shortcuts = shortcuts
            self.filtered_shortcuts = shortcuts
            self.dark_mode = True
            self.source_name = source_name
            
            self.init_ui()
            self.apply_theme()

        def init_ui(self):
            self.setWindowTitle(f"Sublime Text Keymap Explorer ({self.source_name}) - Qt5")
            self.resize(900, 650)

            central_widget = QWidget(self)
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)

            self.search_bar = SearchLineEdit(None, self)
            self.search_bar.setPlaceholderText("Search commands or keys... Press 'f' to focus.")
            self.search_bar.textChanged.connect(self.filter_shortcuts)
            layout.addWidget(self.search_bar)

            self.table = QTableWidget()
            self.search_bar.table_widget = self.table
            self.table.setColumnCount(2)
            self.table.setHorizontalHeaderLabels(["HOTKEY", "COMMAND & ARGS"])
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.table.setSelectionBehavior(QTableWidget.SelectRows)
            self.table.setEditTriggers(QTableWidget.NoEditTriggers)
            layout.addWidget(self.table)

            self.populate_table(self.shortcuts)

            self.shortcut_quit_q = QShortcut(QKeySequence("q"), self)
            self.shortcut_quit_q.activated.connect(self.handle_q_quit)
            self.shortcut_quit_esc = QShortcut(QKeySequence("Esc"), self)
            self.shortcut_quit_esc.activated.connect(self.handle_escape)
            self.shortcut_focus_f = QShortcut(QKeySequence("f"), self)
            self.shortcut_focus_f.activated.connect(self.handle_focus_f)
            self.shortcut_theme = QShortcut(QKeySequence("Ctrl+d"), self)
            self.shortcut_theme.activated.connect(self.toggle_theme)

        def populate_table(self, data):
            self.table.setRowCount(len(data))
            for row, item in enumerate(data):
                key_item = QTableWidgetItem(item["key"])
                desc_item = QTableWidgetItem(item["desc"])
                
                key_item.setFont(QFont("Consolas", 10, QFont.Bold))
                desc_item.setFont(QFont("Consolas", 10))
                
                self.table.setItem(row, 0, key_item)
                self.table.setItem(row, 1, desc_item)

        def filter_shortcuts(self, text):
            query_parts = text.lower().split()
            if not query_parts:
                self.filtered_shortcuts = self.shortcuts
            else:
                self.filtered_shortcuts = []
                for s in self.shortcuts:
                    combined = f"{s['key']} {s['desc']}".lower()
                    if all(part in combined for part in query_parts):
                        self.filtered_shortcuts.append(s)
            self.populate_table(self.filtered_shortcuts)

        def handle_q_quit(self):
            if not self.search_bar.hasFocus(): self.close()

        def handle_escape(self):
            if self.search_bar.hasFocus() and self.search_bar.text(): self.search_bar.clear()
            else: self.close()

        def handle_focus_f(self):
            if not self.search_bar.hasFocus():
                self.search_bar.setFocus()
                self.search_bar.selectAll()

        def toggle_theme(self):
            self.dark_mode = not self.dark_mode
            self.apply_theme()

        def apply_theme(self):
            if self.dark_mode:
                self.setStyleSheet("""
                    QMainWindow { background-color: #1e1e1e; color: #d4d4d4; }
                    QLineEdit { background-color: #252526; color: #ffffff; border: 1px solid #3f3f46; padding: 6px; font-size: 13px; border-radius: 4px; }
                    QTableWidget { background-color: #1e1e1e; color: #d4d4d4; gridline-color: #2d2d30; border: none; }
                    QHeaderView::section { background-color: #2d2d30; color: #ffffff; padding: 6px; border: none; font-weight: bold; }
                    QTableWidget::item:selected { background-color: #094771; color: #ffffff; }
                """)
            else:
                self.setStyleSheet("""
                    QMainWindow { background-color: #f3f3f3; color: #000000; }
                    QLineEdit { background-color: #ffffff; color: #000000; border: 1px solid #cccccc; padding: 6px; font-size: 13px; border-radius: 4px; }
                    QTableWidget { background-color: #ffffff; color: #000000; gridline-color: #e0e0e0; border: none; }
                    QHeaderView::section { background-color: #e5e5e5; color: #000000; padding: 6px; border: none; font-weight: bold; }
                    QTableWidget::item:selected { background-color: #0078d7; color: #ffffff; }
                """)


# ==========================================
# Tkinter Fallback GUI Implementation
# ==========================================
else:
    class SublimeKeymapViewerTk:
        def __init__(self, root, shortcuts, source_name):
            self.root = root
            self.shortcuts = shortcuts
            self.filtered_shortcuts = shortcuts
            self.dark_mode = True
            self.source_name = source_name

            self.root.title(f"Sublime Text Keymap Explorer ({self.source_name}) - Tkinter Fallback")
            self.root.geometry("900x650")

            self.create_widgets()
            self.apply_theme()
            self.bind_events()

        def create_widgets(self):
            main_frame = ttk.Frame(self.root, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)

            self.search_var = tk.StringVar()
            self.search_var.trace("w", self.filter_shortcuts)
            self.search_entry = ttk.Entry(main_frame, textvariable=self.search_var, font=("Consolas", 11))
            self.search_entry.pack(fill=tk.X, pady=(0, 10))
            self.search_entry.focus_set()

            columns = ("key", "desc")
            self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="browse")
            self.tree.heading("key", anchor=tk.W, text="HOTKEY")
            self.tree.heading("desc", anchor=tk.W, text="COMMAND & ARGS")
            self.tree.column("key", width=200, minwidth=150)
            self.tree.column("desc", width=650, minwidth=300)

            scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
            self.tree.configure(yscrollcommand=scrollbar.set)

            self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.populate_tree(self.shortcuts)

        def populate_tree(self, data):
            for item in self.tree.get_children(): self.tree.delete(item)
            for item in data: self.tree.insert("", tk.END, values=(item["key"], item["desc"]))

        def filter_shortcuts(self, *args):
            query = self.search_var.get().lower().strip()
            query_parts = query.split()
            if not query_parts: self.filtered_shortcuts = self.shortcuts
            else:
                self.filtered_shortcuts = []
                for s in self.shortcuts:
                    combined = f"{s['key']} {s['desc']}".lower()
                    if all(part in combined for part in query_parts):
                        self.filtered_shortcuts.append(s)
            self.populate_tree(self.filtered_shortcuts)

        def bind_events(self):
            self.root.bind("<q>", self.handle_q_quit)
            self.root.bind("<Escape>", self.handle_escape)
            self.root.bind("<f>", self.handle_focus_f)
            self.root.bind("<Control-d>", self.toggle_theme)
            for key in ("<Up>", "<Down>", "<Prior>", "<Next>"):
                self.search_entry.bind(key, lambda e, k=key: self.redirect_navigation(k))

        def redirect_navigation(self, key_event):
            selected = self.tree.selection()
            children = self.tree.get_children()
            if not children: return "break"
            
            if not selected: target = children[0]
            else:
                current = selected[0]
                idx = children.index(current)
                if key_event == "<Up>": target = children[max(0, idx - 1)]
                elif key_event == "<Down>": target = children[min(len(children) - 1, idx + 1)]
                elif key_event == "<Prior>": target = children[max(0, idx - 10)]
                elif key_event == "<Next>": target = children[min(len(children) - 1, idx + 10)]
                else: target = current

            self.tree.selection_set(target)
            self.tree.see(target)
            return "break"

        def handle_q_quit(self, event):
            if self.root.focus_get() != self.search_entry: self.root.destroy()

        def handle_escape(self, event):
            if self.root.focus_get() == self.search_entry and self.search_var.get(): self.search_var.set("")
            else: self.root.destroy()

        def handle_focus_f(self, event):
            if self.root.focus_get() != self.search_entry:
                self.search_entry.focus_set()
                self.search_entry.icursor(tk.END)
                return "break"

        def toggle_theme(self, event=None):
            self.dark_mode = not self.dark_mode
            self.apply_theme()

        def apply_theme(self):
            if self.dark_mode: self.root.configure(bg="#1e1e1e")
            else: self.root.configure(bg="#f3f3f3")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sublime Text Keymap Explorer GUI")
    parser.add_argument("-d", "--default", action="store_true", help="Load the Default keymap instead of the User keymap")
    parser.add_argument("file", nargs="?", help="Optional custom .sublime-keymap file path")
    args = parser.parse_args()

    target_path = None
    raw_content = None

    if args.file:
        target_path = args.file
        source_name = "Custom File"
        
    elif args.default:
        # Sublime Text stores defaults in a .sublime-package zip file in Program Files
        package_paths = [
            r"C:\Program Files\Sublime Text\Packages\Default.sublime-package",     # ST4
            r"C:\Program Files\Sublime Text 3\Packages\Default.sublime-package",   # ST3
            r"C:\Program Files (x86)\Sublime Text 3\Packages\Default.sublime-package"
        ]
        
        for path in package_paths:
            if os.path.isfile(path):
                try:
                    with zipfile.ZipFile(path, 'r') as z:
                        # Extract the keymap directly from the zip archive into memory
                        with z.open("Default (Windows).sublime-keymap") as f:
                            raw_content = f.read().decode('utf-8')
                            source_name = "Default Map"
                            break
                except Exception as e:
                    pass
        
        if not raw_content:
            print("Error: Could not locate Default.sublime-package in standard installation directories.")
            sys.exit(1)
            
    else:
        # target_path = r"C:\Users\Admin\AppData\Roaming\Sublime Text\Packages\User\Default (Windows).sublime-keymap"
        # if not os.path.isfile(target_path):
        target_path = os.path.expandvars(r"%APPDATA%\Sublime Text\Packages\User\Default (Windows).sublime-keymap")
        
        if not os.path.isfile(target_path):
            print(f"File not found: {target_path}")
            sys.exit(1)
            
        source_name = "User Map"

    # Pass either the file_path OR the raw_content extracted from the zip
    parsed_data = parse_shortcuts(file_path=target_path, raw_content=raw_content)

    if not parsed_data:
        print("No valid shortcuts found.")
        sys.exit(1)

    if PYQT_AVAILABLE:
        app = QApplication([sys.argv[0]])
        viewer = SublimeKeymapViewerPyQt(parsed_data, source_name)
        viewer.show()
        sys.exit(app.exec_())
    else:
        root = tk.Tk()
        viewer = SublimeKeymapViewerTk(root, parsed_data, source_name)
        root.mainloop()