import os
import sys
import ctypes
import string
import threading
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk

# Auto-run as Administrator
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def get_drive_label(letter):
    try:
        kernel32 = ctypes.windll.kernel32
        vol_buf = ctypes.create_unicode_buffer(1024)
        fs_buf = ctypes.create_unicode_buffer(1024)
        rc = kernel32.GetVolumeInformationW(ctypes.c_wchar_p(letter.rstrip("\\") + "\\"), vol_buf, 1024, None, None, None, fs_buf, 1024)
        return vol_buf.value.strip() if rc else ""
    except:
        return ""

class DuplicateTreeFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("⚡ Ghost Drives Duplicate & Tree Matcher")
        
        # Responsive sizing
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ww = min(880, int(sw * 0.92))
        wh = min(860, int(sh * 0.90))
        self.geometry(f"{ww}x{wh}+{(sw-ww)//2}+{(sh-wh)//2}")
        self.minsize(680, 560)

        # Main Layout
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.pack(fill="x", padx=15, pady=8)

        self.lbl_title = ctk.CTkLabel(self.frame_top, text="🌲 Ghost Drives Duplicate & Tree Structure Matcher", font=("Segoe UI", 16, "bold"), text_color="#70a1ff")
        self.lbl_title.pack(side="left", padx=10, pady=6)

        # Drive Selector Checkboxes Container
        self.frame_drives = ctk.CTkFrame(self)
        self.frame_drives.pack(fill="x", padx=15, pady=4)
        
        self.lbl_select = ctk.CTkLabel(self.frame_drives, text="Select Drives to Compare:", font=("Segoe UI", 12, "bold"))
        self.lbl_select.pack(side="left", padx=10, pady=5)

        self.drive_vars = {}
        self.frame_chk_box = ctk.CTkFrame(self.frame_drives, fg_color="transparent")
        self.frame_chk_box.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_refresh_drives = ctk.CTkButton(self.frame_drives, text="🔄 Refresh", width=70, height=26, command=self.load_drive_checkboxes)
        self.btn_refresh_drives.pack(side="right", padx=10)

        self.load_drive_checkboxes()

        # Control Action Bar
        self.frame_actions = ctk.CTkFrame(self)
        self.frame_actions.pack(fill="x", padx=15, pady=4)

        self.cmb_filter = ctk.CTkComboBox(self.frame_actions, values=["All Duplicates", "Folders Only (Tree Match)", "Files Only"], width=190)
        self.cmb_filter.set("Folders Only (Tree Match)")
        self.cmb_filter.pack(side="left", padx=10, pady=6)

        self.txt_search = ctk.CTkEntry(self.frame_actions, placeholder_text="🔍 Filter by name...", width=200)
        self.txt_search.pack(side="left", padx=5)
        self.txt_search.bind("<KeyRelease>", self.on_search_filter)

        self.btn_scan = ctk.CTkButton(self.frame_actions, text="🚀 Start Comparison Scan", font=("Segoe UI", 12, "bold"), fg_color="#00b894", hover_color="#00a383", command=self.start_scan_thread)
        self.btn_scan.pack(side="right", padx=10)

        # Treeview Display Area
        self.frame_tree = ctk.CTkFrame(self, fg_color="#18191a", border_width=1, border_color="#3a3b3c")
        self.frame_tree.pack(fill="both", expand=True, padx=15, pady=6)

        # Style Treeview for Dark Theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#1e1f20",
                        foreground="#ffffff",
                        fieldbackground="#1e1f20",
                        rowheight=26,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background="#2f3542",
                        foreground="#70a1ff",
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#3742fa")])

        # Columns
        columns = ("type", "match_info", "full_path")
        self.tree = ttk.Treeview(self.frame_tree, columns=columns, show="tree headings", selectmode="browse")
        
        self.tree.heading("#0", text="📂 Item / Structure Name", anchor="w")
        self.tree.heading("type", text="Type", anchor="center")
        self.tree.heading("match_info", text="Match Details / Drive Info", anchor="w")
        self.tree.heading("full_path", text="Full Path (Double-click to Open)", anchor="w")

        self.tree.column("#0", width=260, minwidth=180)
        self.tree.column("type", width=80, minwidth=60, anchor="center")
        self.tree.column("match_info", width=220, minwidth=150)
        self.tree.column("full_path", width=380, minwidth=250)

        # Scrollbars
        sb_y = ttk.Scrollbar(self.frame_tree, orient="vertical", command=self.tree.yview)
        sb_x = ttk.Scrollbar(self.frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)

        # Bottom Bar: Stats & Export
        self.frame_bottom = ctk.CTkFrame(self)
        self.frame_bottom.pack(fill="x", padx=15, pady=(2, 8))

        self.lbl_stats = ctk.CTkLabel(self.frame_bottom, text="Ready. Select drives and click Start Comparison Scan.", font=("Segoe UI", 11))
        self.lbl_stats.pack(side="left", padx=10, pady=5)

        self.btn_export = ctk.CTkButton(self.frame_bottom, text="💾 Export Report (.TXT)", width=140, height=26, fg_color="#34495e", hover_color="#2c3e50", command=self.export_report)
        self.btn_export.pack(side="right", padx=10)

        # Right click Context Menu
        self.menu = tk.Menu(self, tearoff=0, bg="#2f3542", fg="white", activebackground="#70a1ff", activeforeground="black", font=("Segoe UI", 9))
        self.menu.add_command(label="📂 Open Folder in Explorer", command=self.open_selected)
        self.menu.add_command(label="📋 Copy Full Path", command=self.copy_selected_path)

        self.scan_results = []

    def load_drive_checkboxes(self):
        for w in self.frame_chk_box.winfo_children():
            w.destroy()
        self.drive_vars.clear()

        for letter in string.ascii_uppercase:
            root = f"{letter}:\\"
            if os.path.exists(root) and letter not in ["C"]:
                label = get_drive_label(f"{letter}:")
                txt = f"{letter}: ({label})" if label else f"{letter}:"
                var = ctk.BooleanVar(value=True)
                self.drive_vars[f"{letter}:"] = var
                chk = ctk.CTkCheckBox(self.frame_chk_box, text=txt, variable=var, font=("Segoe UI", 10))
                chk.pack(side="left", padx=6, pady=2)

    def start_scan_thread(self):
        selected_drives = [d for d, v in self.drive_vars.items() if v.get()]
        if len(selected_drives) < 2:
            messagebox.showwarning("Warning", "Please select at least 2 drives to compare duplicates!")
            return
        
        self.btn_scan.configure(state="disabled", text="⏳ Scanning...")
        self.lbl_stats.configure(text="Scanning drives, analyzing folder trees & files...")
        threading.Thread(target=self._scan_process, args=(selected_drives,), daemon=True).start()

    def _scan_process(self, drives):
        folders_by_name = defaultdict(list)
        files_by_name = defaultdict(list)
        ignore_dirs = {"$recycle.bin", "system volume information"}
        ignore_files = {"desktop.ini", "spacefiller.dat"}

        for drive in drives:
            for root, dirs, files in os.walk(drive):
                # Filter out system directories
                dirs[:] = [d for d in dirs if d.lower() not in ignore_dirs]
                
                # Record Folders
                for d in dirs:
                    folder_name = d.strip()
                    full_p = os.path.join(root, d)
                    
                    # Compute shallow sub-signature (names of sub-items)
                    try:
                        sub_items = sorted([item.lower() for item in os.listdir(full_p)])
                        sig = ",".join(sub_items[:15]) # hash fingerprint
                    except:
                        sig = ""
                    
                    folders_by_name[folder_name.lower()].append({
                        "name": folder_name,
                        "path": full_p,
                        "drive": drive[:2],
                        "signature": sig
                    })

                # Record Files
                for f in files:
                    if f.lower() not in ignore_files:
                        full_f = os.path.join(root, f)
                        files_by_name[f.lower()].append({
                            "name": f,
                            "path": full_f,
                            "drive": drive[:2]
                        })

        # Process Duplicate Folders across DIFFERENT drives
        dup_folders = []
        for name_key, entries in folders_by_name.items():
            drives_found = {e["drive"] for e in entries}
            if len(drives_found) > 1: # Found on 2 or more different drives
                # Check if sub-trees match
                sigs = {e["signature"] for e in entries if e["signature"]}
                is_exact_tree = (len(sigs) == 1 and len(entries) > 1 and list(sigs)[0] != "")
                dup_folders.append({
                    "name": entries[0]["name"],
                    "is_folder": True,
                    "is_exact_tree": is_exact_tree,
                    "entries": entries
                })

        # Process Duplicate Files across DIFFERENT drives
        dup_files = []
        for name_key, entries in files_by_name.items():
            drives_found = {e["drive"] for e in entries}
            if len(drives_found) > 1:
                dup_files.append({
                    "name": entries[0]["name"],
                    "is_folder": False,
                    "is_exact_tree": False,
                    "entries": entries
                })

        self.scan_results = dup_folders + dup_files
        self.after(0, self.render_tree_results)

    def render_tree_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        filter_mode = self.cmb_filter.get()
        search_query = self.txt_search.get().strip().lower()

        folder_count = 0
        file_count = 0

        for group in self.scan_results:
            is_folder = group["is_folder"]
            name = group["name"]

            # Filters
            if filter_mode == "Folders Only (Tree Match)" and not is_folder:
                continue
            if filter_mode == "Files Only" and is_folder:
                continue
            if search_query and search_query not in name.lower():
                continue

            if is_folder:
                folder_count += 1
                icon = "📁"
                type_str = "Folder"
                status_info = "⚡ 100% Identical Tree Match!" if group["is_exact_tree"] else f"Found on {len(group['entries'])} Drives"
            else:
                file_count += 1
                icon = "📄"
                type_str = "File"
                status_info = f"Found on {len(group['entries'])} Drives"

            # Parent Root Tree Node
            parent_id = self.tree.insert("", "end", text=f"{icon} {name}", values=(type_str, status_info, ""), open=True)

            # Child Branch Nodes (Showing occurrences across different drives face-to-face)
            for entry in group["entries"]:
                drive_badge = f"💽 Drive {entry['drive']}"
                self.tree.insert(parent_id, "end", text=f"   ↳ {drive_badge}", values=("Location", f"Drive {entry['drive']}", entry["path"]))

        self.btn_scan.configure(state="normal", text="🚀 Start Comparison Scan")
        self.lbl_stats.configure(text=f"Comparison Done! Found {folder_count} Duplicate Folder Groups & {file_count} Duplicate Files.")

    def on_search_filter(self, event=None):
        self.render_tree_results()

    def on_double_click(self, event):
        self.open_selected()

    def on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.tk_popup(event.x_root, event.y_root)

    def open_selected(self):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0], "values")[2]
        if path and os.path.exists(path):
            os.startfile(path if os.path.isdir(path) else os.path.dirname(path))

    def copy_selected_path(self):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0], "values")[2]
        if path:
            self.clipboard_clear()
            self.clipboard_append(path)
            messagebox.showinfo("Copied", f"Path copied to clipboard:\n{path}")

    def export_report(self):
        if not self.scan_results:
            messagebox.showwarning("Warning", "No scan results to export!")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text file", "*.txt")], title="Save Comparison Report")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("=== GHOST DRIVES DUPLICATE & TREE COMPARISON REPORT ===\n\n")
                for g in self.scan_results:
                    t = "FOLDER" if g["is_folder"] else "FILE"
                    f.write(f"[{t}] {g['name']}\n")
                    for e in g["entries"]:
                        f.write(f"   -> Drive {e['drive']}: {e['path']}\n")
                    f.write("\n")
            messagebox.showinfo("Success", f"Report saved successfully:\n{file_path}")

if __name__ == "__main__":
    app = DuplicateTreeFinderApp()
    app.mainloop()
