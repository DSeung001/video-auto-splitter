"""Tkinter-based settings/run UI for lecture_splitter.

Lets a user pick input/output paths, edit key config values, save them to a
YAML config file, and run the split pipeline without touching the CLI.
"""

from __future__ import annotations

import contextlib
import queue
import tempfile
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from types import SimpleNamespace

from lecture_splitter.cli import run_pipeline
from lecture_splitter.config import AppConfig, load_config, save_config
from lecture_splitter.optimizer import AudioOptimizationResult, optimize_audio_config

# (label, config section attr, field attr, cast)
FIELD_SPECS: list[tuple[str, str, str, type]] = [
    ("무음 임계값 (absolute_quiet_db)", "audio", "absolute_quiet_db", float),
    ("무음 상대 하락폭 (relative_drop_db)", "audio", "relative_drop_db", float),
    ("무음 점수 임계값 (quiet_score_threshold)", "audio", "quiet_score_threshold", float),
    ("화면 정지 임계값 (static_diff_threshold)", "video", "static_diff_threshold", float),
    ("화면 정지 점수 임계값 (static_score_threshold)", "video", "static_score_threshold", float),
    ("최소 쉬는시간 (min_break_duration_sec)", "break_detection", "min_break_duration_sec", float),
    ("최대 쉬는시간 (max_break_duration_sec)", "break_detection", "max_break_duration_sec", float),
    ("최소 강의시간 (min_lesson_duration_sec)", "break_detection", "min_lesson_duration_sec", float),
    ("break 점수 임계값 (break_score_threshold)", "scoring", "break_score_threshold", float),
]


class LectureSplitterGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Lecture Auto Splitter")
        self.root.geometry("640x640")

        self._config: AppConfig = load_config(None)
        self._field_vars: dict[str, tk.StringVar] = {}
        self._log_queue: "queue.Queue[str]" = queue.Queue()
        self._running = False
        self._optimizing = False

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.config_var = tk.StringVar()
        self.preset_var = tk.StringVar(value="balanced")
        self.mode_var = tk.StringVar(value="copy")
        self.dry_run_var = tk.BooleanVar(value=False)

        self._build_layout()
        self._poll_log_queue()

    # ---------- layout ----------
    def _build_layout(self) -> None:
        pad = {"padx": 8, "pady": 4}

        paths_frame = ttk.LabelFrame(self.root, text="입력 / 출력")
        paths_frame.pack(fill="x", **pad)
        self._add_path_row(paths_frame, "입력 파일", self.input_var, self._browse_input)
        self._add_path_row(paths_frame, "출력 디렉터리", self.output_var, self._browse_output)
        self._add_path_row(paths_frame, "Config 파일", self.config_var, self._browse_config)

        options_frame = ttk.LabelFrame(self.root, text="실행 옵션")
        options_frame.pack(fill="x", **pad)

        ttk.Label(options_frame, text="프리셋 (신규 config 생성 시 사용)").grid(row=0, column=0, sticky="w", **pad)
        preset_combo = ttk.Combobox(
            options_frame, textvariable=self.preset_var, values=["balanced", "sensitive", "strict"], state="readonly", width=15
        )
        preset_combo.grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(options_frame, text="모드").grid(row=1, column=0, sticky="w", **pad)
        mode_frame = ttk.Frame(options_frame)
        mode_frame.grid(row=1, column=1, sticky="w", **pad)
        ttk.Radiobutton(mode_frame, text="copy (빠름)", variable=self.mode_var, value="copy").pack(side="left")
        ttk.Radiobutton(mode_frame, text="accurate (재인코딩)", variable=self.mode_var, value="accurate").pack(side="left")

        ttk.Checkbutton(options_frame, text="Dry-run (분석만 수행)", variable=self.dry_run_var).grid(
            row=2, column=0, columnspan=2, sticky="w", **pad
        )

        settings_frame = ttk.LabelFrame(self.root, text="주요 설정값")
        settings_frame.pack(fill="both", expand=False, **pad)
        for row, (label, section, attr, _cast) in enumerate(FIELD_SPECS):
            ttk.Label(settings_frame, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=2)
            var = tk.StringVar(value=str(getattr(getattr(self._config, section), attr)))
            entry = ttk.Entry(settings_frame, textvariable=var, width=12)
            entry.grid(row=row, column=1, sticky="w", padx=8, pady=2)
            self._field_vars[f"{section}.{attr}"] = var

        settings_buttons = ttk.Frame(settings_frame)
        settings_buttons.grid(row=len(FIELD_SPECS), column=0, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Button(settings_buttons, text="선택한 Config 불러오기", command=self._load_config_into_fields).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(settings_buttons, text="설정 저장", command=self._save_settings).pack(side="left", padx=(0, 6))
        self.optimize_button = ttk.Button(
            settings_buttons, text="설정 최적화 (입력 오디오 분석)", command=self._on_optimize_clicked
        )
        self.optimize_button.pack(side="left")

        run_frame = ttk.Frame(self.root)
        run_frame.pack(fill="x", **pad)
        self.run_button = ttk.Button(run_frame, text="실행", command=self._on_run_clicked)
        self.run_button.pack(side="left")
        self.status_label = ttk.Label(run_frame, text="대기 중")
        self.status_label.pack(side="left", padx=12)

        log_frame = ttk.LabelFrame(self.root, text="로그")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=12, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _add_path_row(self, parent: ttk.LabelFrame, label: str, var: tk.StringVar, browse_cmd) -> None:
        row = parent.grid_size()[1]
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        entry = ttk.Entry(parent, textvariable=var, width=48)
        entry.grid(row=row, column=1, sticky="we", padx=8, pady=4)
        ttk.Button(parent, text="찾아보기", command=browse_cmd).grid(row=row, column=2, padx=8, pady=4)
        parent.columnconfigure(1, weight=1)

    # ---------- browse handlers ----------
    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="입력 파일 선택", filetypes=[("Video files", "*.mp4 *.webm"), ("All files", "*.*")]
        )
        if path:
            self.input_var.set(path)
            if not self.output_var.get():
                self.output_var.set(str(Path("output") / Path(path).stem))

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="출력 디렉터리 선택")
        if path:
            self.output_var.set(path)

    def _browse_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Config 파일 선택 (없으면 새 경로 입력)", filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        if path:
            self.config_var.set(path)
            self._load_config_into_fields()

    # ---------- settings ----------
    def _load_config_into_fields(self) -> None:
        config_path = self.config_var.get().strip() or None
        try:
            if config_path and not Path(config_path).exists():
                messagebox.showinfo("안내", "해당 config 파일이 없어 기본값을 표시합니다. '설정 저장'으로 새로 생성할 수 있습니다.")
                config = load_config(None)
            else:
                config = load_config(config_path)
        except Exception as exc:  # noqa: BLE001 - surface to user
            messagebox.showerror("Config 로드 실패", str(exc))
            return

        self._config = config
        for key, var in self._field_vars.items():
            section, attr = key.split(".")
            var.set(str(getattr(getattr(config, section), attr)))

    def _collect_config_from_fields(self) -> AppConfig:
        from dataclasses import replace

        config = self._config
        updates: dict[str, dict] = {}
        for _label, section, attr, cast in FIELD_SPECS:
            key = f"{section}.{attr}"
            updates.setdefault(section, {})[attr] = cast(self._field_vars[key].get())

        for section, values in updates.items():
            current_section = getattr(config, section)
            new_section = replace(current_section, **values)
            config = replace(config, **{section: new_section})
        return config

    def _save_settings(self) -> None:
        config_path = self.config_var.get().strip()
        if not config_path:
            messagebox.showwarning("경고", "저장할 Config 파일 경로를 입력하거나 선택하세요.")
            return
        try:
            config = self._collect_config_from_fields()
            save_config(config_path, config)
            self._config = config
        except Exception as exc:  # noqa: BLE001 - surface to user
            messagebox.showerror("저장 실패", str(exc))
            return
        messagebox.showinfo("완료", f"Config를 저장했습니다: {config_path}")

    # ---------- audio optimization ----------
    def _on_optimize_clicked(self) -> None:
        if self._optimizing or self._running:
            return
        input_path = self.input_var.get().strip()
        if not input_path:
            messagebox.showwarning("경고", "먼저 입력 파일을 선택하세요.")
            return

        try:
            config = self._collect_config_from_fields()
        except ValueError as exc:
            messagebox.showerror("입력 오류", f"설정값 입력이 올바르지 않습니다:\n{exc}")
            return

        self._set_optimizing(True)
        thread = threading.Thread(target=self._run_optimize_thread, args=(input_path, config), daemon=True)
        thread.start()

    def _run_optimize_thread(self, input_path: str, config: AppConfig) -> None:
        try:
            result = optimize_audio_config(input_path, config.audio)
        except Exception as exc:  # noqa: BLE001 - surface to user
            self.root.after(0, self._on_optimize_failed, exc)
            return
        self.root.after(0, self._on_optimize_done, result)

    def _on_optimize_done(self, result: AudioOptimizationResult) -> None:
        from dataclasses import replace

        self._set_optimizing(False)
        self._config = replace(self._config, audio=result.config)
        for key, var in self._field_vars.items():
            section, attr = key.split(".")
            if section != "audio":
                continue
            var.set(str(getattr(result.config, attr)))

        messagebox.showinfo(
            "설정 최적화 완료",
            (
                f"쉬는 시간(추정) 평균 음량: {result.quiet_mean_db:.1f} dB\n"
                f"강의 중(추정) 평균 음량: {result.active_mean_db:.1f} dB\n"
                f"구분 기준(임계값): {result.threshold_db:.1f} dB\n"
                f"조용한 구간 비율: {result.quiet_ratio * 100:.1f}%\n"
                f"분석 샘플 수: {result.sample_count}\n\n"
                f"적용된 값:\n"
                f"  무음 임계값 (absolute_quiet_db): {result.config.absolute_quiet_db}\n"
                f"  무음 상대 하락폭 (relative_drop_db): {result.config.relative_drop_db}\n"
                f"  무음 점수 임계값 (quiet_score_threshold): {result.config.quiet_score_threshold}\n\n"
                "'설정 저장'을 눌러야 config 파일에 반영됩니다."
            ),
        )

    def _on_optimize_failed(self, exc: Exception) -> None:
        self._set_optimizing(False)
        messagebox.showerror("설정 최적화 실패", str(exc))

    def _set_optimizing(self, optimizing: bool) -> None:
        self._optimizing = optimizing
        self.optimize_button.config(state="disabled" if optimizing else "normal")
        self.run_button.config(state="disabled" if optimizing else "normal")
        if optimizing:
            self.status_label.config(text="오디오 분석 중...")
        else:
            self.status_label.config(text="대기 중")

    # ---------- run ----------
    def _on_run_clicked(self) -> None:
        if self._running or self._optimizing:
            return
        input_path = self.input_var.get().strip()
        if not input_path:
            messagebox.showwarning("경고", "입력 파일을 선택하세요.")
            return

        try:
            config = self._collect_config_from_fields()
        except ValueError as exc:
            messagebox.showerror("입력 오류", f"설정값 입력이 올바르지 않습니다:\n{exc}")
            return

        # Persist whatever is currently in the fields before running, so the
        # pipeline always sees the values shown on screen even if the user
        # forgot to click "설정 저장" first.
        config_path = self.config_var.get().strip() or None
        if config_path:
            try:
                save_config(config_path, config)
                self._config = config
            except Exception as exc:  # noqa: BLE001 - surface to user
                messagebox.showerror("저장 실패", f"실행 전 설정을 저장하는 중 오류가 발생했습니다:\n{exc}")
                return
        else:
            try:
                temp_config_path = Path(tempfile.gettempdir()) / "lecture_splitter_temp_config.yaml"
                save_config(str(temp_config_path), config)
                config_path = str(temp_config_path)
                self._config = config
            except Exception as exc:  # noqa: BLE001 - surface to user
                messagebox.showerror("임시 설정 저장 실패", f"임시 설정을 저장하는 중 오류가 발생했습니다:\n{exc}")
                return

        output_path = self.output_var.get().strip() or None
        args = SimpleNamespace(
            input_path=input_path,
            config=config_path,
            dry_run=self.dry_run_var.get(),
            output=output_path,
            init_config=None,
            config_preset=self.preset_var.get(),
            force=False,
            copy=self.mode_var.get() == "copy",
            accurate=self.mode_var.get() == "accurate",
        )

        self._set_running(True)
        self._clear_log()
        thread = threading.Thread(target=self._run_pipeline_thread, args=(args,), daemon=True)
        thread.start()

    def _run_pipeline_thread(self, args: SimpleNamespace) -> None:
        class _QueueWriter:
            """File-like object that streams writes into the log queue.

            Using this instead of buffering into an io.StringIO lets the UI
            display log lines as they happen instead of all at once when the
            pipeline finishes.
            """

            def __init__(self, log_queue: "queue.Queue[str]") -> None:
                self._queue = log_queue

            def write(self, text: str) -> int:
                if text:
                    self._queue.put(text)
                return len(text)

            def flush(self) -> None:
                pass

        writer = _QueueWriter(self._log_queue)
        exit_code = 1
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                exit_code = run_pipeline(args)
        except Exception as exc:  # noqa: BLE001 - surface to user
            self._log_queue.put(f"ERROR: {exc}\n")
            self._log_queue.put(traceback.format_exc())
        finally:
            self._log_queue.put("__DONE__" if exit_code == 0 else "__FAILED__")

    def _poll_log_queue(self) -> None:
        try:
            while True:
                message = self._log_queue.get_nowait()
                if message == "__DONE__":
                    self._set_running(False)
                    self.status_label.config(text="완료")
                elif message == "__FAILED__":
                    self._set_running(False)
                    self.status_label.config(text="실패")
                else:
                    self._append_log(message)
        except queue.Empty:
            pass
        self.root.after(150, self._poll_log_queue)

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.run_button.config(state="disabled" if running else "normal")
        self.optimize_button.config(state="disabled" if running else "normal")
        if running:
            self.status_label.config(text="실행 중...")

    def _clear_log(self) -> None:
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def _append_log(self, message: str) -> None:
        if not message:
            return
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")


def launch() -> int:
    root = tk.Tk()
    LectureSplitterGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(launch())
