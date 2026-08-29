import os
import sys
import ctypes
import threading
import string
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def get_drive_label(drive_letter):
    try:
        kernel32 = ctypes.windll.kernel32
        volumeNameBuffer = ctypes.create_unicode_buffer(1024)
        fileSystemNameBuffer = ctypes.create_unicode_buffer(1024)
        root = drive_letter.rstrip("\\") + "\\"
        rc = kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            volumeNameBuffer,
            ctypes.sizeof(volumeNameBuffer),
            None, None, None,
            fileSystemNameBuffer,
            ctypes.sizeof(fileSystemNameBuffer)
        )
        if rc and volumeNameBuffer.value.strip():
            return volumeNameBuffer.value.strip()
    except:
        pass
    return ""

STRINGS = {
    "EN": {
        "title": "🔍 Ghost Drive Cross-Disk Comparator & Duplicate Finder",
        "drives_to_compare": "Select Virtual Drives to Compare:",
        "scan_btn": "⚡ Scan & Compare Drives",
        "filter_dup_only": "Show Duplicates Only (≥ 2 Drives)",
        "search_lbl": "Search Filter:",
        "col_name": "Folder / File Name",
        "stat_ready": "Ready. Select drives and click Scan.",
        "stat_scanning": "Scanning drives in parallel...",
        "stat_done": "Scan complete! Found {dup_count} duplicate items across selected drives.",
        "open_in_exp": "📂 Open Location in Explorer",
        "expand_all": "➕ Expand All",
        "collapse_all": "➖ Collapse All"
    },
    "FA": {
        "title": "🔍 مقایسه‌گر درختی و تکراری‌یاب هاردهای مجازی",
        "drives_to_compare": "درایوهای مجازی مورد نظر برای مقایسه:",
        "scan_btn": "⚡ اسکن و مقایسه درایوها",
        "filter_dup_only": "فقط نمایش موارد تکراری (در ۲ یا چند هارد)",
        "search_lbl": "جستجو:",
        "col_name": "نام پوشه / فایل",
        "stat_ready": "آماده. درایوها را انتخاب و اسکن را بزنید.",
        "stat_scanning": "در حال اسکن و تطبیق ساختار فایل‌ها...",
        "stat_done": "اسکن کامل شد! تعداد {dup_count} مورد تکراری یافت شد.",
        "open_in_exp": "📂 باز کردن مسیر در اکسپلورر",
        "expand_all": "➕ باز کردن همه شاخه‌ها",
        "collapse_all": "➖ بستن همه شاخه‌ها"
    }
}

class GhostDriveComparatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.current_lang = "EN"
        self.title("Ghost Drive Cross-Disk Comparator")

        # Responsive resolution
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1000, int(screen_w * 0.92))
        win_h = min(880, int(screen_h * 0.90))
        pos_x = max(0, (screen_w - win_w) // 2)
        pos_y = max(0, (screen_h - win_h) // 2)

        self.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.minsize(750, 550)
        self.resizable(True, True)

        self.available_drives = self.get_available_drives()
        self.drive_vars = {}
        self.scanned_tree = {} # Path -> {name, is_dir, drives: {drive_letter: full_path}, children}

        # Top Bar
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.pack(fill="x", padx=15, pady=(8, 4))

        self.lbl_title = ctk.CTkLabel(self.frame_top, text=self.t("title"), font=("Segoe UI", 16, "bold"))
        self.lbl_title.pack(side="left", padx=5)

        self.cmb_lang = ctk.CTkComboBox(self.frame_top, values=["English", "فارسی"], width=95, command=self.change_language)
        self.cmb_lang.set("English")
        self.cmb_lang.pack(side="right", padx=5)

        # Drive Selector Checkboxes
        self.frame_drives = ctk.CTkFrame(self)
        self.frame_drives.pack(fill="x", padx=15, pady=4)

        self.lbl_select = ctk.CTkLabel(self.frame_drives, text=self.t("drives_to_compare"), font=("Segoe UI", 12, "bold"))
        self.lbl_select.pack(side="left", padx=10, pady=6)

        self.frame_chk_box = ctk.CTkFrame(self.frame_drives, fg_color="transparent")
        self.frame_chk_box.pack(side="left", fill="x", expand=True, padx=5)

        self.populate_drive_checkboxes()

        self.btn_scan = ctk.CTkButton(self.frame_drives, text=self.t("scan_btn"), font=("Segoe UI", 12, "bold"), fg_color="#00b894", hover_color="#00a383", command=self.start_scan_thread)
        self.btn_scan.pack(side="right", padx=10, pady=6)

        # Filters & Search Bar
        self.frame_filter = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_filter.pack(fill="x", padx=15, pady=2)

        self.chk_dup_only = ctk.CTkCheckBox(self.frame_filter, text=self.t("filter_dup_only"), command=self.apply_filters)
        self.chk_dup_only.select()
        self.chk_dup_only.pack(side="left", padx=5)

        self.btn_expand = ctk.CTkButton(self.frame_filter, text=self.t("expand_all"), width=100, height=24, fg_color="#34495e", hover_color="#2c3e50", command=self.expand_all_nodes)
        self.btn_expand.pack(side="left", padx=5)

        self.btn_collapse = ctk.CTkButton(self.frame_filter, text=self.t("collapse_all"), width=100, height=24, fg_color="#34495e", hover_color="#2c3e50", command=self.collapse_all_nodes)
        self.btn_collapse.pack(side="left", padx=5)

        self.txt_search = ctk.CTkEntry(self.frame_filter, placeholder_text="Search folder or file name...", width=200)
        self.txt_search.pack(side="right", padx=5)
        self.txt_search.bind("<KeyRelease>", lambda e: self.apply_filters())

        self.lbl_search = ctk.CTkLabel(self.frame_filter, text=self.t("search_lbl"), font=("Segoe UI", 11))
        self.lbl_search.pack(side="right", padx=5)

        # Treeview Container (Dark Mode Styled)
        self.frame_tree = ctk.CTkFrame(self, fg_color="#18191a", border_width=1, border_color="#3a3b3c")
        self.frame_tree.pack(fill="both", expand=True, padx=15, pady=6)

        self.setup_treeview_styles()

        # Treeview Widget with Scrollbars
        self.tree_scroll_y = ttk.Scrollbar(self.frame_tree, orient="vertical")
        self.tree_scroll_x = ttk.Scrollbar(self.frame_tree, orient="horizontal")

        self.tree = ttk.Treeview(
            self.frame_tree,
            selectmode="browse",
            yscrollcommand=self.tree_scroll_y.set,
            xscrollcommand=self.tree_scroll_x.set
        )
        self.tree_scroll_y.config(command=self.tree.yview)
        self.tree_scroll_x.config(command=self.tree.xview)

        self.tree_scroll_y.pack(side="right", fill="y")
        self.tree_scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        # Context Menu on Treeview
        self.tree_menu = tk.Menu(self, tearoff=0, bg="#2f3542", fg="white", activebackground="#1e90ff", activeforeground="white", font=("Segoe UI", 9))
        self.tree.bind("<Button-3>", self.show_tree_context_menu)

        # Bottom Status Bar
        self.lbl_status = ctk.CTkLabel(self, text=self.t("stat_ready"), font=("Segoe UI", 11), anchor="w")
        self.lbl_status.pack(fill="x", padx=20, pady=(2, 8))

    def t(self, key):
        return STRINGS[self.current_lang].get(key, key)

    def change_language(self, choice):
        self.current_lang = "FA" if choice == "فارسی" else "EN"
        self.lbl_title.configure(text=self.t("title"))
        self.lbl_select.configure(text=self.t("drives_to_compare"))
        self.btn_scan.configure(text=self.t("scan_btn"))
        self.chk_dup_only.configure(text=self.t("filter_dup_only"))
        self.btn_expand.configure(text=self.t("expand_all"))
        self.btn_collapse.configure(text=self.t("collapse_all"))
        self.lbl_search.configure(text=self.t("search_lbl"))
        self.lbl_status.configure(text=self.t("stat_ready"))

    def get_available_drives(self):
        drives = []
        for letter in string.ascii_uppercase:
            if os.path.exists(f"{letter}:\\") and letter != "C":
                label = get_drive_label(f"{letter}:")
                drives.append((f"{letter}:", label or "Drive"))
        return drives

    def populate_drive_checkboxes(self):
        for widget in self.frame_chk_box.winfo_children():
            widget.destroy()
        self.drive_vars.clear()

        for letter, label in self.available_drives:
            var = tk.BooleanVar(value=True)
            self.drive_vars[letter] = var
            chk = ctk.CTkCheckBox(self.frame_chk_box, text=f"{letter} ({label})", variable=var, font=("Segoe UI", 11))
            chk.pack(side="left", padx=6)

    def setup_treeview_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
            background="#242526",
            foreground="#f5f6fa",
            fieldbackground="#242526",
            rowheight=24,
            font=("Segoe UI", 10)
        )
        style.configure("Treeview.Heading",
            background="#1e1f20",
            foreground="#70a1ff",
            relief="flat",
            font=("Segoe UI", 10, "bold")
        )
        style.map("Treeview", background=[('selected', '#3742fa')])
        style.map("Treeview.Heading", background=[('active', '#2f3542')])

    def start_scan_thread(self):
        threading.Thread(target=self.scan_and_compare_task, daemon=True).start()

    def scan_and_compare_task(self):
        selected_drives = [letter for letter, var in self.drive_vars.items() if var.get()]
        if len(selected_drives) < 2:
            self.lbl_status.configure(text="Please select at least 2 drives to compare.")
            return

        self.lbl_status.configure(text=self.t("stat_scanning"))
        self.btn_scan.configure(state="disabled")

        # Set up Columns dynamically based on selected drives
        self.selected_active_drives = selected_drives
        columns = ["col_name"] + selected_drives
        self.tree["columns"] = columns
        self.tree.column("#0", width=0, stretch=tk.NO) # Hide default tree column

        self.tree.column("col_name", width=340, minwidth=200)
        self.tree.heading("col_name", text=self.t("col_name"))

        for d in selected_drives:
            label = get_drive_label(d)
            col_title = f"{d} ({label})" if label else d
            self.tree.column(d, width=180, minwidth=120)
            self.tree.heading(d, text=col_title)

        # Build Cross-Disk Directory Index Map
        # Key: Relative normalized path (e.g. "\Music\Rock\Pink Floyd")
        # Value: {"is_dir": bool, "name": str, "drives": {drive_letter: full_path}}
        index_map = {}

        for drive in selected_drives:
            root_path = f"{drive}\\"
            for root, dirs, files in os.walk(root_path):
                # Ignore system hidden folders
                dirs[:] = [d for d in dirs if d not in ["$RECYCLE.BIN", "System Volume Information"]]
                
                rel_root = os.path.relpath(root, root_path)
                rel_root_norm = "" if rel_root == "." else f"\\{rel_root}"

                # Index Folders
                for d in dirs:
                    folder_rel = f"{rel_root_norm}\\{d}".strip("\\")
                    if folder_rel not in index_map:
                        index_map[folder_rel] = {"is_dir": True, "name": d, "rel_path": folder_rel, "drives": {}}
                    index_map[folder_rel]["drives"][drive] = os.path.join(root, d)

                # Index Files
                for f in files:
                    if f in ["desktop.ini", "SpaceFiller.dat"]:
                        continue
                    file_rel = f"{rel_root_norm}\\{f}".strip("\\")
                    if file_rel not in index_map:
                        index_map[file_rel] = {"is_dir": False, "name": f, "rel_path": file_rel, "drives": {}}
                    index_map[file_rel]["drives"][drive] = os.path.join(root, f)

        self.index_map = index_map
        self.apply_filters()
        self.btn_scan.configure(state="normal")

    def apply_filters(self):
        if not hasattr(self, "index_map"):
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        dup_only = self.chk_dup_only.get()
        query = self.txt_search.get().strip().lower()

        dup_count = 0
        nodes_created = {} # rel_path -> item_id

        # Configure row colors for highlighting duplicates
        self.tree.tag_configure("duplicate_folder", foreground="#2ed573", font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("duplicate_file", foreground="#00d2d3")
        self.tree.tag_configure("single_item", foreground="#a4b0be")

        sorted_keys = sorted(self.index_map.keys(), key=lambda x: (x.count("\\"), x.lower()))

        for rel_path in sorted_keys:
            item = self.index_map[rel_path]
            is_dup = len(item["drives"]) >= 2

            if is_dup:
                dup_count += 1

            if dup_only and not is_dup:
                continue

            if query and query not in item["name"].lower():
                continue

            # Determine Tree Parent
            parent_rel = os.path.dirname(rel_path)
            parent_id = nodes_created.get(parent_rel, "")

            # Build row values for each drive column
            icon = "📁 " if item["is_dir"] else "📄 "
            row_values = [f"{icon}{item['name']}"]

            for d in self.selected_active_drives:
                if d in item["drives"]:
                    row_values.append("✔ Present")
                else:
                    row_values.append("—")

            tag = "duplicate_folder" if (item["is_dir"] and is_dup) else ("duplicate_file" if is_dup else "single_item")
            
            node_id = self.tree.insert(parent_id, "end", values=row_values, tags=(tag,), open=True)
            nodes_created[rel_path] = node_id

        status_text = self.t("stat_done").replace("{dup_count}", str(dup_count))
        self.lbl_status.configure(text=status_text)

    def expand_all_nodes(self):
        def _expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                _expand(child)
        for item in self.tree.get_children():
            _expand(item)

    def collapse_all_nodes(self):
        def _collapse(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                _collapse(child)
        for item in self.tree.get_children():
            _collapse(item)

    def show_tree_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        self.tree.selection_set(item_id)
        values = self.tree.item(item_id, "values")
        if not values:
            return

        raw_name = values[0].replace("📁 ", "").replace("📄 ", "")
        
        self.tree_menu.delete(0, "end")
        self.tree_menu.add_command(label=f"Item: {raw_name}", state="disabled")
        self.tree_menu.add_separator()

        # Find which drive has this item and add Open options
        for idx, drive in enumerate(self.selected_active_drives):
            if values[idx + 1] == "✔ Present":
                self.tree_menu.add_command(
                    label=f"📂 Open in {drive} ({get_drive_label(drive)})",
                    command=lambda d=drive: os.startfile(f"{d}\\")
                )

        try:
            self.tree_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.tree_menu.grab_release()

if __name__ == "__main__":
    app = GhostDriveComparatorApp()
    app.mainloop()
