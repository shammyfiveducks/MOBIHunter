#!/usr/bin/env python3
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import PhotoImage, StringVar, Toplevel, messagebox, scrolledtext, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    raise SystemExit("You need to install tkinterdnd2: pip install tkinterdnd2")


class HoverTooltip:
    def __init__(self, widget, text, delay_ms=350):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip_window = None

        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _event=None):
        self._schedule_show()

    def _on_leave(self, _event=None):
        self._cancel_scheduled()
        self._hide()

    def _schedule_show(self):
        self._cancel_scheduled()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel_scheduled(self):
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self):
        if self._tip_window is not None:
            return
        self._after_id = None

        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self._tip_window = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        try:
            tw.wm_attributes("-topmost", True)
        except Exception:
            pass
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#fffbe6",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
            wraplength=330,
        )
        label.pack()

    def _hide(self):
        if self._tip_window is not None:
            self._tip_window.destroy()
            self._tip_window = None


class MobiToEpubApp(TkinterDnD.Tk):
    APP_NAME = "MOBI Hunter"
    APP_VERSION = "0.6.0"
    APP_AUTHOR = "shammyfiveducks"
    APP_GITHUB_URL = "https://github.com/shammyfiveducks/mobi_to_epub_gui"
    ICON_RELATIVE_PATH = os.path.join("assets", "mobi_hunter_icon.png")
    MAIN_ICON_SIZE = 128
    ABOUT_ICON_SIZE = 220

    DEFAULT_TIMEOUT_SECONDS = 600
    EVENT_POLL_MS = 100

    POLICY_SKIP = "Skip existing"
    POLICY_OVERWRITE = "Overwrite existing"
    POLICY_RENAME = "Rename new file"
    POLICIES = (POLICY_SKIP, POLICY_OVERWRITE, POLICY_RENAME)
    FAIL_POLICY_KEEP = "Keep failed queued"
    FAIL_POLICY_REMOVE = "Remove failed from queue"
    FAIL_POLICIES = (FAIL_POLICY_KEEP, FAIL_POLICY_REMOVE)
    SPLIT_RETRY_FLAGS = ("--flow-size", "0", "--dont-split-on-page-breaks")
    TIMEOUT_TOOLTIP_TEXT = (
        "Maximum time allowed per file conversion.\n"
        "If ebook-convert runs longer than this, it is stopped and marked as failed."
    )

    def __init__(self):
        super().__init__()
        self.title(self.APP_NAME)
        self.geometry("1220x1120")

        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(self.app_dir, self.ICON_RELATIVE_PATH)
        self.files_to_convert = []
        self.file_keys = set()
        self.is_converting = False
        self.event_queue = queue.Queue()
        self.last_errors = []
        self.converter_cmd = None
        self.current_process = None
        self.process_lock = threading.Lock()
        self.cancel_requested = False
        self.last_output_path = None
        self.last_browse_dir = os.path.expanduser("~")
        self.about_window = None
        self.app_icon_image = None
        self.about_icon_image = None
        self.existing_policy = StringVar(self, value=self.POLICY_SKIP)
        self.failure_policy = StringVar(self, value=self.FAIL_POLICY_KEEP)
        self.timeout_seconds_var = StringVar(self, value=str(self.DEFAULT_TIMEOUT_SECONDS))
        self.delete_source_var = StringVar(self, value="0")
        self.output_dir_var = StringVar(self, value="")
        self.output_dir_display_var = StringVar(self, value="Input folder (default)")
        self.timeout_tooltips = []

        self.drop_frame = ttk.Frame(self, width=1200, height=140)
        self.drop_frame.pack(padx=10, pady=10)
        self.drop_frame.pack_propagate(False)

        self.drop_label = ttk.Label(
            self.drop_frame, text="Drag .mobi files or folders here", relief="groove", anchor="center"
        )
        self.drop_label.pack(fill="both", expand=True)
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self.on_drop)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=5)

        self.add_button = ttk.Button(button_frame, text="Add MOBI...", command=self.add_mobi_from_dialog)
        self.add_button.pack(side="left", padx=5)

        self.clear_button = ttk.Button(button_frame, text="Clear List", command=self.clear_list)
        self.clear_button.pack(side="left", padx=5)

        self.convert_button = ttk.Button(button_frame, text="Convert All", command=self.start_conversion)
        self.convert_button.pack(side="left", padx=5)

        self.cancel_button = ttk.Button(
            button_frame, text="Cancel", command=self.cancel_conversion, state="disabled"
        )
        self.cancel_button.pack(side="left", padx=5)

        self.copy_errors_button = ttk.Button(
            button_frame, text="Copy Errors", command=self.copy_errors, state="disabled"
        )
        self.copy_errors_button.pack(side="left", padx=5)

        self.open_folder_button = ttk.Button(
            button_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            state="disabled",
        )
        self.open_folder_button.pack(side="left", padx=5)

        self.about_button = tk.Button(button_frame, text="About", width=7, command=self.show_about)
        self.about_button.pack(side="right", padx=5)
        self.about_button_default_bg = self.about_button.cget("bg")
        self.about_button_default_fg = self.about_button.cget("fg")
        self.about_button_default_active_bg = self.about_button.cget("activebackground")
        self.about_button_default_active_fg = self.about_button.cget("activeforeground")

        options_frame = ttk.Frame(self)
        options_frame.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Label(options_frame, text="If EPUB exists:").pack(side="left", padx=(0, 5))
        self.policy_combo = ttk.Combobox(
            options_frame,
            textvariable=self.existing_policy,
            values=self.POLICIES,
            state="readonly",
            width=18,
        )
        self.policy_combo.pack(side="left", padx=5)
        self.timeout_label = ttk.Label(options_frame, text="Timeout (s):")
        self.timeout_label.pack(side="left", padx=(12, 5))
        self.timeout_spinbox = ttk.Spinbox(
            options_frame,
            from_=30,
            to=7200,
            increment=30,
            textvariable=self.timeout_seconds_var,
            width=7,
        )
        self.timeout_spinbox.pack(side="left", padx=5)
        ttk.Label(options_frame, text="On failure:").pack(side="left", padx=(12, 5))
        self.failure_policy_combo = ttk.Combobox(
            options_frame,
            textvariable=self.failure_policy,
            values=self.FAIL_POLICIES,
            state="readonly",
            width=22,
        )
        self.failure_policy_combo.pack(side="left", padx=5)
        self.delete_source_check = ttk.Checkbutton(
            options_frame,
            text="Delete source MOBI on success",
            variable=self.delete_source_var,
            onvalue="1",
            offvalue="0",
        )
        self.delete_source_check.pack(side="left", padx=(12, 0))

        output_frame = ttk.Frame(self)
        output_frame.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Label(output_frame, text="Output folder:").pack(side="left", padx=(0, 6))
        self.output_dir_entry = ttk.Entry(output_frame, textvariable=self.output_dir_display_var, state="readonly")
        self.output_dir_entry.pack(side="left", fill="x", expand=True)
        self.output_browse_button = ttk.Button(output_frame, text="Choose...", command=self.choose_output_directory)
        self.output_browse_button.pack(side="left", padx=(6, 0))
        self.output_default_button = ttk.Button(
            output_frame, text="Use Input Folder", command=self.clear_output_directory
        )
        self.output_default_button.pack(side="left", padx=(6, 0))

        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.progress_text = StringVar(self, value="Progress: Idle")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_text)
        self.progress_label.pack(side="left", padx=(0, 8))
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", maximum=1, value=0)
        self.progress_bar.pack(side="left", fill="x", expand=True)

        self.log = scrolledtext.ScrolledText(
            self, wrap="word", height=10, state="disabled", font="TkDefaultFont"
        )
        self.log.pack(fill="both", expand=True, padx=10, pady=10)

        self.timeout_tooltips = [
            HoverTooltip(self.timeout_label, self.TIMEOUT_TOOLTIP_TEXT),
            HoverTooltip(self.timeout_spinbox, self.TIMEOUT_TOOLTIP_TEXT),
        ]
        self.load_icons()
        self.after(self.EVENT_POLL_MS, self.process_event_queue)
        if not self.check_converter_available(show_dialog=True):
            self.queue_log(self.get_calibre_install_hint())
        self.update_about_button_status()
        self.log_startup_dependency_hints()

    def on_drop(self, event):
        converting_now = self.is_converting
        added_count = 0
        for path in self.split_drop_payload(event.data):
            added_count += self.queue_path(path)
        if added_count == 0:
            self.queue_log("No new .mobi files were added from this drop.")
        elif converting_now:
            self.queue_log(f"Added {added_count} file(s) for the next batch after the current run.")

    def add_mobi_from_dialog(self):
        converting_now = self.is_converting
        selection = self.show_custom_path_picker(mode="both", title="Add MOBI files or folder")
        if not selection:
            return
        selection_type, selection_value = selection

        if selection_type == "files":
            selected_files = selection_value
            self.last_browse_dir = os.path.dirname(selected_files[0]) or self.last_browse_dir
            added_count = 0
            for path in selected_files:
                added_count += self.queue_path(path)
        else:
            selected_folder = selection_value
            self.last_browse_dir = selected_folder
            added_count = self.queue_path(selected_folder)
        self.log_manual_add_result(added_count, converting_now)

    def show_custom_path_picker(self, mode, start_dir=None, title=None):
        if start_dir and os.path.isdir(start_dir):
            initial_dir = start_dir
        else:
            initial_dir = self.last_browse_dir if os.path.isdir(self.last_browse_dir) else os.path.expanduser("~")
        result = {"value": None}
        current_dir = {"value": initial_dir}
        item_meta = {}
        counter = {"value": 0}

        dialog = Toplevel(self)
        dialog.title(title or ("Select MOBI files" if mode == "files" else "Select folder"))
        dialog.minsize(900, 600)
        dialog.resizable(True, True)
        dialog.transient(self)

        container = ttk.Frame(dialog, padding=10)
        container.pack(fill="both", expand=True)
        container.rowconfigure(2, weight=1)
        container.columnconfigure(0, weight=1)

        path_var = StringVar(dialog, value=initial_dir)
        info_var = StringVar(dialog, value="")

        nav_frame = ttk.Frame(container)
        nav_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        nav_frame.columnconfigure(1, weight=1)

        ttk.Label(nav_frame, text="Location:").grid(row=0, column=0, padx=(0, 6), sticky="w")
        path_entry = ttk.Entry(nav_frame, textvariable=path_var)
        path_entry.grid(row=0, column=1, sticky="ew")
        ttk.Button(nav_frame, text="Go", command=lambda: refresh_listing(path_var.get())).grid(
            row=0, column=2, padx=(6, 0)
        )
        ttk.Button(nav_frame, text="Up", command=lambda: navigate_up()).grid(row=0, column=3, padx=(6, 0))
        ttk.Button(
            nav_frame, text="Home", command=lambda: refresh_listing(os.path.expanduser("~"))
        ).grid(row=0, column=4, padx=(6, 0))
        ttk.Button(nav_frame, text="Refresh", command=lambda: refresh_listing(current_dir["value"])).grid(
            row=0, column=5, padx=(6, 0)
        )

        ttk.Label(container, textvariable=info_var).grid(row=1, column=0, sticky="w", pady=(0, 6))

        list_frame = ttk.Frame(container)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        tree = ttk.Treeview(
            list_frame,
            columns=("kind", "size"),
            show="tree headings",
            selectmode="browse" if mode == "folder" else "extended",
        )
        tree.heading("#0", text="Name", anchor="w")
        tree.heading("kind", text="Type", anchor="w")
        tree.heading("size", text="Size", anchor="e")
        tree.column("#0", width=560, anchor="w")
        tree.column("kind", width=140, anchor="w")
        tree.column("size", width=120, anchor="e")
        tree.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(list_frame, orient="horizontal", command=tree.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        action_frame = ttk.Frame(container)
        action_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        action_frame.columnconfigure(0, weight=1)
        hint_text = (
            "Double-click folders to open. Use Ctrl/Shift for multi-select."
            if mode == "files"
            else (
                "Double-click folders to open. Select files or select a folder."
                if mode == "both"
                else "Double-click folders to open. Select a folder or use current location."
            )
        )
        ttk.Label(action_frame, text=hint_text).grid(row=0, column=0, sticky="w")

        button_row = ttk.Frame(action_frame)
        button_row.grid(row=0, column=1, sticky="e")
        ttk.Button(button_row, text="Cancel", command=dialog.destroy).pack(side="right")
        if mode == "both":
            ttk.Button(button_row, text="Select Folder", command=lambda: finalize_selection("folder")).pack(
                side="right", padx=(0, 8)
            )
            ttk.Button(button_row, text="Select File(s)", command=lambda: finalize_selection("files")).pack(
                side="right", padx=(0, 8)
            )
        else:
            ttk.Button(button_row, text="Select", command=lambda: finalize_selection()).pack(
                side="right", padx=(0, 8)
            )

        def add_item(name, full_path, is_dir):
            counter["value"] += 1
            iid = f"i{counter['value']}"
            display_name = f"{name}{os.sep}" if is_dir else name
            size_text = ""
            if not is_dir:
                try:
                    size_text = self.format_size(os.path.getsize(full_path))
                except OSError:
                    size_text = "?"
            tree.insert("", "end", iid=iid, text=display_name, values=("Folder" if is_dir else "MOBI", size_text))
            item_meta[iid] = (full_path, is_dir)

        def refresh_listing(directory):
            directory = os.path.abspath(os.path.expanduser(directory))
            if not os.path.isdir(directory):
                info_var.set(f"Folder not found: {directory}")
                return

            current_dir["value"] = directory
            path_var.set(directory)
            item_meta.clear()
            counter["value"] = 0
            tree.delete(*tree.get_children())

            try:
                names = os.listdir(directory)
            except OSError as exc:
                info_var.set(f"Cannot open folder: {exc}")
                return

            dirs = []
            files = []
            for name in names:
                full_path = os.path.join(directory, name)
                if os.path.isdir(full_path):
                    dirs.append((name, full_path))
                elif mode in ("files", "both") and name.lower().endswith(".mobi"):
                    files.append((name, full_path))

            dirs.sort(key=lambda item: item[0].lower())
            files.sort(key=lambda item: item[0].lower())

            for name, full_path in dirs:
                add_item(name, full_path, is_dir=True)
            for name, full_path in files:
                add_item(name, full_path, is_dir=False)

            if mode in ("files", "both"):
                info_var.set(f"{len(dirs)} folder(s), {len(files)} .mobi file(s) in {directory}")
            else:
                info_var.set(f"{len(dirs)} folder(s) in {directory}")

        def navigate_up():
            parent = os.path.dirname(current_dir["value"])
            if parent and parent != current_dir["value"]:
                refresh_listing(parent)

        def finalize_selection(action=None):
            selections = [item_meta[iid] for iid in tree.selection() if iid in item_meta]
            selected_mode = action or mode

            if selected_mode == "files":
                chosen = [path for path, is_dir in selections if not is_dir]
                if not chosen:
                    messagebox.showwarning("No files selected", "Select one or more .mobi files.", parent=dialog)
                    return
                if mode == "both":
                    result["value"] = ("files", chosen)
                else:
                    result["value"] = chosen
                dialog.destroy()
                return

            for path, is_dir in selections:
                if is_dir:
                    if mode == "both":
                        result["value"] = ("folder", path)
                    else:
                        result["value"] = path
                    dialog.destroy()
                    return
            if mode == "both":
                result["value"] = ("folder", current_dir["value"])
            else:
                result["value"] = current_dir["value"]
            dialog.destroy()

        def open_selected_or_finalize(_event=None):
            focused = tree.focus()
            if not focused or focused not in item_meta:
                return
            path, is_dir = item_meta[focused]
            if is_dir:
                refresh_listing(path)
                return
            if mode in ("files", "both"):
                finalize_selection("files")

        path_entry.bind("<Return>", lambda _event: refresh_listing(path_var.get()))
        tree.bind("<Double-1>", open_selected_or_finalize)
        tree.bind("<Return>", open_selected_or_finalize)

        refresh_listing(initial_dir)
        self.center_child_window(dialog, 1020, 700)
        dialog.grab_set()
        dialog.focus_force()
        path_entry.focus_set()
        self.wait_window(dialog)
        return result["value"]

    def choose_output_directory(self):
        base_dir = self.output_dir_var.get().strip() or self.last_browse_dir
        if not os.path.isdir(base_dir):
            base_dir = os.path.expanduser("~")

        selected_folder = self.show_custom_path_picker(mode="folder", start_dir=base_dir, title="Select output folder")
        if not selected_folder:
            return
        self.output_dir_var.set(selected_folder)
        self.last_browse_dir = selected_folder
        self.update_output_dir_display()
        self.queue_log(f"Output folder set to: {selected_folder}")

    def clear_output_directory(self):
        self.output_dir_var.set("")
        self.update_output_dir_display()
        self.queue_log("Output folder reset to input folder (default).")

    def update_output_dir_display(self):
        selected = self.output_dir_var.get().strip()
        self.output_dir_display_var.set(selected if selected else "Input folder (default)")

    def log_manual_add_result(self, added_count, converting_now):
        if added_count == 0:
            self.queue_log("No new .mobi files were added from picker selection.")
        elif converting_now:
            self.queue_log(f"Added {added_count} file(s) for the next batch after the current run.")

    def format_size(self, size_bytes):
        units = ("B", "KB", "MB", "GB", "TB")
        size = float(size_bytes)
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024.0

    def split_drop_payload(self, raw_data):
        try:
            parts = list(self.tk.splitlist(raw_data))
        except Exception:
            parts = [raw_data]

        paths = []
        for part in parts:
            for candidate in str(part).splitlines():
                candidate = candidate.strip()
                if candidate:
                    paths.append(candidate)
        return paths

    def queue_path(self, path):
        path = os.path.abspath(path)
        if os.path.isfile(path):
            if path.lower().endswith(".mobi"):
                return 1 if self.queue_file(path) else 0
            self.queue_log(f"Skipped unsupported file: {path}")
            return 0

        if os.path.isdir(path):
            added = 0
            for root, _, files in os.walk(path):
                for file_name in files:
                    if file_name.lower().endswith(".mobi"):
                        full_path = os.path.join(root, file_name)
                        if self.queue_file(full_path):
                            added += 1
            if added == 0:
                self.queue_log(f"No .mobi files found in: {path}")
            return added

        self.queue_log(f"Skipped unsupported path: {path}")
        return 0

    def queue_file(self, path):
        canonical = self.canonical_path(path)
        if canonical in self.file_keys:
            self.queue_log(f"Skipped duplicate: {path}")
            return False
        self.file_keys.add(canonical)
        self.files_to_convert.append(path)
        self.queue_log(f"{len(self.files_to_convert)}. {path}")
        return True

    def clear_list(self):
        if self.is_converting:
            messagebox.showinfo("Busy", "Wait for the current conversion to finish before clearing the list.")
            return
        if not self.files_to_convert:
            self.queue_log("Queue is already empty.")
            return
        if not messagebox.askyesno(
            "Clear queue", f"Remove all {len(self.files_to_convert)} queued file(s)?"
        ):
            return

        removed = len(self.files_to_convert)
        self.files_to_convert.clear()
        self.file_keys.clear()
        self.last_errors.clear()
        self.copy_errors_button.configure(state="disabled")
        self.set_progress(0, 0)
        self.queue_log(f"Cleared {removed} queued file(s).")

    def start_conversion(self):
        if self.is_converting:
            self.queue_log("Conversion already running.")
            return
        if not self.files_to_convert:
            messagebox.showwarning("No files", "No .mobi files queued for conversion.")
            return
        converter_cmd = self.check_converter_available(show_dialog=True)
        if not converter_cmd:
            return
        try:
            timeout_seconds = self.get_timeout_seconds()
        except ValueError as exc:
            messagebox.showerror("Invalid timeout", str(exc))
            return
        output_dir = self.output_dir_var.get().strip() or None
        if output_dir and not os.path.isdir(output_dir):
            messagebox.showerror("Invalid output folder", f"Selected output folder does not exist:\n{output_dir}")
            return

        snapshot = list(self.files_to_convert)
        policy = self.existing_policy.get()
        self.cancel_requested = False
        self.set_conversion_controls(running=True)
        self.set_progress(0, len(snapshot))
        if output_dir:
            self.queue_log(f"Using output folder: {output_dir}")
        self.queue_log(f"Starting conversion of {len(snapshot)} file(s).")
        worker = threading.Thread(
            target=self.convert_all, args=(snapshot, policy, timeout_seconds, converter_cmd, output_dir), daemon=True
        )
        worker.start()

    def convert_all(self, files, policy, timeout_seconds, converter_cmd, output_dir):
        successes = []
        skipped = []
        failures = []
        cancelled = False
        processed_count = 0

        total = len(files)
        for index, mobi_path in enumerate(files, start=1):
            if self.cancel_requested:
                cancelled = True
                break

            status, detail, output_path = self.convert_file(
                mobi_path, policy, timeout_seconds, converter_cmd, output_dir
            )
            if status == "success":
                successes.append((mobi_path, output_path))
            elif status == "skipped":
                skipped.append(mobi_path)
            elif status == "cancelled":
                failures.append((mobi_path, detail))
                cancelled = True
                processed_count = index
                self.event_queue.put(("progress", processed_count, total))
                break
            else:
                failures.append((mobi_path, detail))
            processed_count = index
            self.event_queue.put(("progress", processed_count, total))

        self.event_queue.put(("finished", successes, skipped, failures, total, processed_count, cancelled))

    def convert_file(self, mobi_file, policy, timeout_seconds, converter_cmd, output_dir):
        output_path, should_skip = self.resolve_output_path(mobi_file, policy, output_dir)
        if should_skip:
            self.event_queue.put(("log", f"Skipped existing EPUB: {output_path}"))
            return "skipped", "Output already exists.", output_path

        self.event_queue.put(("log", f"Converting: {mobi_file} -> {output_path}"))
        command = [converter_cmd, mobi_file, output_path]
        return_code, stdout, stderr, fatal_error = self.run_conversion_command(command, timeout_seconds, mobi_file)
        if fatal_error:
            return "failed", fatal_error, output_path

        if return_code == 0:
            delete_ok, delete_error = self.delete_source_if_enabled(mobi_file)
            if not delete_ok:
                return "failed", delete_error, output_path
            self.event_queue.put(("log", f"✓ Success: {output_path}"))
            return "success", "", output_path

        if self.cancel_requested:
            msg = "Cancelled by user."
            self.event_queue.put(("log", f"⏹ Cancelled: {mobi_file}"))
            return "cancelled", msg, output_path

        raw_tool_output = (stderr or stdout or "").strip()
        if self.is_split_error(raw_tool_output):
            flags_text = " ".join(self.SPLIT_RETRY_FLAGS)
            self.event_queue.put(
                ("log", f"Split error detected. Retrying with safer split settings: {flags_text}")
            )
            retry_command = command + list(self.SPLIT_RETRY_FLAGS)
            retry_code, retry_stdout, retry_stderr, retry_fatal = self.run_conversion_command(
                retry_command, timeout_seconds, mobi_file
            )
            if retry_fatal:
                return "failed", retry_fatal, output_path
            if retry_code == 0:
                delete_ok, delete_error = self.delete_source_if_enabled(mobi_file)
                if not delete_ok:
                    return "failed", delete_error, output_path
                self.event_queue.put(("log", f"✓ Success after split-safe retry: {output_path}"))
                return "success", "", output_path
            if self.cancel_requested:
                msg = "Cancelled by user."
                self.event_queue.put(("log", f"⏹ Cancelled: {mobi_file}"))
                return "cancelled", msg, output_path

            retry_output = self.trim_tool_output((retry_stderr or retry_stdout or "").strip())
            if retry_output:
                self.event_queue.put(("log", f"✗ Retry also failed for {mobi_file}:\n{retry_output}"))
            else:
                self.event_queue.put(
                    ("log", f"✗ Retry failed for {mobi_file}: process exited with code {retry_code}")
                )
            return "failed", retry_output or f"Retry exited with code {retry_code}", output_path

        tool_output = self.trim_tool_output(raw_tool_output)
        if tool_output:
            self.event_queue.put(("log", f"✗ Error converting {mobi_file}:\n{tool_output}"))
        else:
            self.event_queue.put(
                ("log", f"✗ Error converting {mobi_file}: process exited with code {return_code}")
            )
        return "failed", tool_output or f"Process exited with code {return_code}", output_path

    def run_conversion_command(self, command, timeout_seconds, mobi_file):
        process = None
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            with self.process_lock:
                self.current_process = process
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except FileNotFoundError:
            msg = "ebook-convert was not found. Install Calibre and ensure it is on PATH."
            self.event_queue.put(("log", f"✗ {msg}"))
            return None, "", "", msg
        except subprocess.TimeoutExpired:
            if process is not None:
                process.kill()
                stdout, stderr = process.communicate()
            msg = f"Timed out after {timeout_seconds} seconds."
            self.event_queue.put(("log", f"✗ Timeout converting: {mobi_file}"))
            return None, stdout or "", stderr or "", msg
        except Exception as exc:
            msg = f"Unexpected exception: {exc}"
            self.event_queue.put(("log", f"✗ {msg}"))
            return None, "", "", msg
        finally:
            with self.process_lock:
                self.current_process = None

        return_code = process.returncode if process is not None else 1
        return return_code, stdout or "", stderr or "", None

    def resolve_output_path(self, mobi_file, policy, output_dir):
        if output_dir:
            file_stem = os.path.splitext(os.path.basename(mobi_file))[0]
            base = os.path.join(output_dir, file_stem)
        else:
            base, _ = os.path.splitext(mobi_file)
        target = base + ".epub"
        if not os.path.exists(target):
            return target, False

        if policy == self.POLICY_SKIP:
            return target, True
        if policy == self.POLICY_OVERWRITE:
            return target, False

        index = self.find_next_rename_index(base)
        candidate = f"{base} ({index}).epub"
        if not os.path.exists(candidate):
            return candidate, False
        while os.path.exists(candidate):
            index += 1
            candidate = f"{base} ({index}).epub"
        return candidate, False

    def find_next_rename_index(self, base):
        directory = os.path.dirname(base) or "."
        stem = os.path.basename(base)
        pattern = re.compile(rf"^{re.escape(stem)} \((\d+)\)\.epub$", re.IGNORECASE)
        max_index = 0
        try:
            for name in os.listdir(directory):
                matched = pattern.match(name)
                if matched:
                    max_index = max(max_index, int(matched.group(1)))
        except OSError:
            return 1
        return max_index + 1

    def process_event_queue(self):
        while True:
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                break

            event_type = event[0]
            if event_type == "log":
                self.log_message(event[1])
            elif event_type == "progress":
                _, current, total = event
                self.set_progress(current, total)
            elif event_type == "finished":
                _, successes, skipped, failures, total, processed_count, cancelled = event
                self.on_conversion_finished(successes, skipped, failures, total, processed_count, cancelled)

        self.after(self.EVENT_POLL_MS, self.process_event_queue)

    def on_conversion_finished(self, successes, skipped, failures, total, processed_count, cancelled):
        self.set_conversion_controls(running=False)
        self.set_progress(processed_count, total)

        if successes:
            self.last_output_path = successes[-1][1]
            self.open_folder_button.configure(state="normal")

        success_inputs = [path for path, _ in successes]
        processed = {self.canonical_path(path) for path in success_inputs + skipped}
        if self.failure_policy.get() == self.FAIL_POLICY_REMOVE:
            processed.update(self.canonical_path(path) for path, _ in failures)
        if processed:
            self.files_to_convert = [
                path for path in self.files_to_convert if self.canonical_path(path) not in processed
            ]
            self.file_keys = {self.canonical_path(path) for path in self.files_to_convert}

        self.last_errors = []
        for mobi_path, detail in failures:
            self.last_errors.append(f"{mobi_path}\n{detail}")
        self.copy_errors_button.configure(state="normal" if self.last_errors else "disabled")

        self.log_message(
            f"Finished: {len(successes)} converted, {len(skipped)} skipped, {len(failures)} failed "
            f"(processed this run: {processed_count}/{total})."
        )
        if failures:
            if self.failure_policy.get() == self.FAIL_POLICY_REMOVE:
                self.log_message("Removed failed files from queue per policy.")
            else:
                self.log_message("Failed files remain queued for retry.")
        if cancelled:
            self.log_message("Conversion cancelled by user.")
        self.log_message(f"Queue now has {len(self.files_to_convert)} file(s).")

        if cancelled:
            messagebox.showinfo(
                "Conversion cancelled",
                f"Stopped after {processed_count}/{total} file(s).\n"
                f"{len(successes)} converted, {len(skipped)} skipped, {len(failures)} failed.",
            )
        elif failures:
            messagebox.showwarning(
                "Conversion complete",
                f"{len(successes)} converted, {len(skipped)} skipped, {len(failures)} failed.\n"
                "Use 'Copy Errors' for details.",
            )
        else:
            messagebox.showinfo(
                "Conversion complete", f"{len(successes)} converted, {len(skipped)} skipped."
            )

    def copy_errors(self):
        if not self.last_errors:
            self.queue_log("No conversion errors to copy.")
            return

        text = "\n\n".join(self.last_errors)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()
        self.queue_log("Copied conversion errors to clipboard.")

    def open_output_folder(self):
        if not self.last_output_path:
            self.queue_log("No successful conversion yet. Nothing to open.")
            return

        folder = os.path.dirname(self.last_output_path) or "."
        if not os.path.isdir(folder):
            self.queue_log(f"Output folder does not exist: {folder}")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            self.queue_log(f"Opened output folder: {folder}")
        except Exception as exc:
            self.queue_log(f"Could not open output folder: {exc}")

    def cancel_conversion(self):
        if not self.is_converting:
            self.queue_log("No active conversion to cancel.")
            return
        self.cancel_requested = True
        with self.process_lock:
            process = self.current_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except Exception as exc:
                self.queue_log(f"Failed to terminate current conversion: {exc}")
                return
        self.queue_log("Cancellation requested. Stopping after current step.")

    def show_about(self):
        self.update_about_button_status()
        if self.about_window is not None and self.about_window.winfo_exists():
            self.about_window.deiconify()
            self.about_window.lift()
            self.about_window.focus_force()
            return

        about = Toplevel(self)
        self.about_window = about
        about.title(f"About {self.APP_NAME}")
        about.resizable(False, False)
        about.transient(self)
        about.grab_set()
        if self.app_icon_image is not None:
            about.iconphoto(True, self.app_icon_image)

        panel = ttk.Frame(about, padding=16)
        panel.pack(fill="both", expand=True)

        if self.about_icon_image is not None:
            ttk.Label(panel, image=self.about_icon_image).pack(pady=(0, 10))
        ttk.Label(panel, text=self.APP_NAME, font=("TkDefaultFont", 13, "bold")).pack()
        ttk.Label(panel, text=f"Version: {self.APP_VERSION}").pack(pady=(6, 0))
        ttk.Label(panel, text=f"Author: {self.APP_AUTHOR}").pack(pady=(4, 0))
        ttk.Label(panel, text=f"GitHub: {self.APP_GITHUB_URL}", justify="center").pack(pady=(8, 2))
        ttk.Button(panel, text="Open GitHub", command=self.open_github_link).pack(pady=(2, 10))

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=(4, 8))
        dep_frame = ttk.LabelFrame(panel, text="Dependency Status", padding=(10, 8))
        dep_frame.pack(fill="x", pady=(0, 12))
        for name, status, detail in self.get_dependency_status_rows():
            ttk.Label(dep_frame, text=f"{name}: {status}").pack(anchor="w")
            if detail:
                ttk.Label(dep_frame, text=detail, justify="left", wraplength=620).pack(anchor="w", pady=(0, 6))

        ttk.Button(panel, text="Close", command=self.close_about_window).pack()

        about.protocol("WM_DELETE_WINDOW", self.close_about_window)
        self.center_child_window(about, 700, 720)
        about.focus_force()

    def close_about_window(self):
        if self.about_window is not None and self.about_window.winfo_exists():
            self.about_window.destroy()
        self.about_window = None

    def open_github_link(self):
        try:
            webbrowser.open(self.APP_GITHUB_URL)
        except Exception as exc:
            self.queue_log(f"Could not open GitHub link: {exc}")

    def get_dependency_status_rows(self):
        rows = []
        for dependency in self.get_dependency_status_items():
            status = f"Installed ({dependency['location']})" if dependency["ok"] and dependency["location"] else (
                "Installed" if dependency["ok"] else "Missing"
            )
            rows.append((dependency["name"], status, dependency["detail"]))
        return rows

    def get_dependency_status_items(self):
        items = []

        converter_cmd = shutil.which("ebook-convert")
        items.append(
            {
                "name": "ebook-convert",
                "ok": bool(converter_cmd),
                "location": converter_cmd or "",
                "detail": "Required for MOBI -> EPUB conversion."
                if converter_cmd
                else self.get_calibre_install_hint(),
            }
        )

        dnd_available = "tkinterdnd2" in sys.modules
        items.append(
            {
                "name": "tkinterdnd2",
                "ok": dnd_available,
                "location": "",
                "detail": "Required for drag-and-drop support."
                if dnd_available
                else "Install in this Python environment: pip install tkinterdnd2",
            }
        )

        pillow_ok, pillow_version = self.get_pillow_status()
        items.append(
            {
                "name": "Pillow",
                "ok": pillow_ok,
                "location": pillow_version if pillow_ok else "",
                "detail": "Used for high-quality icon resizing."
                if pillow_ok
                else "Install in this Python environment: pip install Pillow",
            }
        )

        return items

    def get_missing_dependency_names(self):
        return [item["name"] for item in self.get_dependency_status_items() if not item["ok"]]

    def update_about_button_status(self):
        missing = self.get_missing_dependency_names()
        if missing:
            self.about_button.configure(
                bg="#c62828",
                fg="white",
                activebackground="#b71c1c",
                activeforeground="white",
            )
            return

        self.about_button.configure(
            bg=self.about_button_default_bg,
            fg=self.about_button_default_fg,
            activebackground=self.about_button_default_active_bg,
            activeforeground=self.about_button_default_active_fg,
        )

    def get_calibre_install_hint(self):
        base_url = "https://calibre-ebook.com/download"
        if sys.platform.startswith("win"):
            return f"Install Calibre from {base_url}, then restart the app."
        if sys.platform == "darwin":
            return f"Install Calibre from {base_url} (or run: brew install --cask calibre), then restart."
        return f"Install Calibre from {base_url} (or your distro package manager), then restart."

    def get_pillow_status(self):
        try:
            from PIL import __version__ as pillow_version

            return True, pillow_version
        except Exception:
            return False, ""

    def log_startup_dependency_hints(self):
        missing = self.get_missing_dependency_names()
        if not missing:
            return
        self.queue_log(
            f"Dependency check: missing {', '.join(missing)}. "
            "Open About for install guidance."
        )

    def set_conversion_controls(self, running):
        self.is_converting = running
        self.convert_button.configure(state="disabled" if running else "normal")
        self.cancel_button.configure(state="normal" if running else "disabled")
        self.clear_button.configure(state="disabled" if running else "normal")
        self.policy_combo.configure(state="disabled" if running else "readonly")
        self.timeout_spinbox.configure(state="disabled" if running else "normal")
        self.failure_policy_combo.configure(state="disabled" if running else "readonly")
        self.delete_source_check.configure(state="disabled" if running else "normal")
        self.output_browse_button.configure(state="disabled" if running else "normal")
        self.output_default_button.configure(state="disabled" if running else "normal")
        if running:
            self.drop_label.configure(text="Converting... please wait")
        else:
            self.drop_label.configure(text="Drag .mobi files or folders here")

    def get_timeout_seconds(self):
        raw_value = self.timeout_seconds_var.get().strip()
        try:
            timeout = int(raw_value)
        except ValueError as exc:
            raise ValueError("Timeout must be a whole number of seconds.") from exc
        if timeout < 30:
            raise ValueError("Timeout must be at least 30 seconds.")
        if timeout > 7200:
            raise ValueError("Timeout must be 7200 seconds or less.")
        return timeout

    def set_progress(self, current, total):
        safe_total = max(total, 1)
        self.progress_bar.configure(maximum=safe_total, value=min(current, safe_total))
        if total <= 0:
            self.progress_text.set("Progress: Idle")
        else:
            self.progress_text.set(f"Progress: {current}/{total}")

    def check_converter_available(self, show_dialog=False):
        self.converter_cmd = shutil.which("ebook-convert")
        if self.converter_cmd:
            return self.converter_cmd

        install_hint = "Calibre's 'ebook-convert' command was not found.\n\n" + self.get_calibre_install_hint()
        if show_dialog:
            messagebox.showerror("ebook-convert not found", install_hint)
        return None

    def load_icons(self):
        self.app_icon_image = self.load_icon_image(self.MAIN_ICON_SIZE)
        self.about_icon_image = self.load_icon_image(self.ABOUT_ICON_SIZE)

        if self.app_icon_image is not None:
            self.iconphoto(True, self.app_icon_image)
        else:
            self.queue_log(f"Icon not found or unreadable: {self.icon_path}")

    def load_icon_image(self, target_size):
        if not os.path.isfile(self.icon_path):
            return None

        try:
            from PIL import Image, ImageTk

            image = Image.open(self.icon_path).convert("RGBA")
            image.thumbnail((target_size, target_size))
            return ImageTk.PhotoImage(image)
        except Exception:
            pass

        try:
            image = PhotoImage(file=self.icon_path)
            width = image.width()
            height = image.height()
            if width > target_size or height > target_size:
                scale = max(1, (max(width, height) + target_size - 1) // target_size)
                image = image.subsample(scale, scale)
            return image
        except Exception:
            return None

    def center_child_window(self, window, width, height):
        self.update_idletasks()
        x = self.winfo_rootx() + max((self.winfo_width() - width) // 2, 0)
        y = self.winfo_rooty() + max((self.winfo_height() - height) // 2, 0)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def canonical_path(self, path):
        return os.path.normcase(os.path.normpath(os.path.abspath(path)))

    def trim_tool_output(self, text, limit=1600):
        if len(text) <= limit:
            return text
        return text[:limit] + "\n...[output truncated]..."

    def delete_source_if_enabled(self, source_path):
        if self.delete_source_var.get() != "1":
            return True, ""
        try:
            os.remove(source_path)
            self.event_queue.put(("log", f"Deleted source MOBI: {source_path}"))
            return True, ""
        except Exception as exc:
            msg = f"Converted but could not delete source file: {source_path} ({exc})"
            self.event_queue.put(("log", f"✗ {msg}"))
            return False, msg

    def is_split_error(self, text):
        lower_text = text.lower()
        split_markers = (
            "could not find reasonable point at which to split",
            "calibre.ebooks.oeb.transforms.split.spliterror",
            "oeb/transforms/split.py",
        )
        return any(marker in lower_text for marker in split_markers)

    def queue_log(self, message):
        self.log_message(message)

    def log_message(self, msg):
        if threading.current_thread() is not threading.main_thread():
            self.event_queue.put(("log", msg))
            return
        self._log_message_ui(msg)

    def _log_message_ui(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


if __name__ == "__main__":
    app = MobiToEpubApp()
    app.mainloop()
