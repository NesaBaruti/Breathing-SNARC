"""
Breathing SNARC Experiment — using Vernier godirect library.

Belt: GDX-RB, Sensor 1 = Force (N) = breathing signal
  Exhale trough: ~5.7 N
  Inhale peak:   ~21.3 N
  (calibration sets personal min/max each session)

Install dependency:  pip install godirect
"""

import tkinter as tk
import threading
import time
import random
import csv
from datetime import datetime
from godirect import GoDirect

# ── CONFIGURATION ──────────────────────────────────────────────────────────────

SENSOR_NUMBER    = 1        # Force (N) = breathing signal
SAMPLE_PERIOD_MS = 100      # 10 Hz

PEAK_FRACTION    = 0.80     # >= 80% of range = inhale peak
TROUGH_FRACTION  = 0.20     # <= 20% of range = exhale trough

BREATHING_CUE_MS = 2000     # show cue for 2s before watching belt
MAX_WAIT_MS      = 10000    # safety timeout — show number anyway after 10s

# ── BELT READER ────────────────────────────────────────────────────────────────

class BeltReader:
    def __init__(self):
        self.value      = 0.0
        self.normalised = 0.0
        self.cal_min    = None
        self.cal_max    = None
        self.calibrated = False
        self.connected  = False
        self._lock      = threading.Lock()
        self._stop      = threading.Event()
        self._gd        = None
        self._device    = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        import asyncio
        asyncio.set_event_loop(asyncio.new_event_loop())
        try:
            self._gd    = GoDirect(use_ble=True, use_usb=False)
            devices     = self._gd.list_devices()
            if not devices:
                print("[Belt] No GDX device found — timer fallback active")
                return

            self._device = devices[0]
            print(f"[Belt] Connecting to {self._device}...")
            self._device.open()
            self._device.enable_sensors([SENSOR_NUMBER])
            self._device.start(period=SAMPLE_PERIOD_MS)
            self.connected = True
            print("[Belt] ✓ Streaming")

            sensor = self._device.get_sensor(SENSOR_NUMBER)
            while not self._stop.is_set():
                if self._device.read():
                    if sensor.values:
                        raw = sensor.values[-1]
                        with self._lock:
                            self.value = raw
                            if self.calibrated and self.cal_max != self.cal_min:
                                span = self.cal_max - self.cal_min
                                self.normalised = max(0.0, min(1.0,
                                    (raw - self.cal_min) / span))
        except Exception as e:
            print(f"[Belt] Error: {e}")
        finally:
            self._shutdown()

    def _shutdown(self):
        try:
            if self._device:
                self._device.stop()
                self._device.close()
            if self._gd:
                self._gd.quit()
        except Exception:
            pass
        self.connected = False

    def stop(self):
        self._stop.set()

    def calibrate(self, cal_min, cal_max):
        with self._lock:
            self.cal_min    = cal_min
            self.cal_max    = cal_max
            self.calibrated = True
        print(f"[Belt] Calibrated: {cal_min:.2f} N – {cal_max:.2f} N")

    def get_value(self):
        with self._lock:
            return self.value

    def get_normalised(self):
        with self._lock:
            return self.normalised

    def is_inhale_peak(self):
        return self.calibrated and self.get_normalised() >= PEAK_FRACTION

    def is_exhale_trough(self):
        return self.calibrated and self.get_normalised() <= TROUGH_FRACTION


# ── GUI ────────────────────────────────────────────────────────────────────────

class BreathingSnarcGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Breathing SNARC Experiment")
        self.root.geometry("900x600")

        self.participant_id = ""
        self.trials         = []
        self.trial_index    = 0
        self.current_block  = 1
        self.state          = "intro"
        self.rt_start_time  = None
        self.csv_file       = None
        self.csv_writer     = None
        self.current_trial  = None
        self.trigger_time   = None
        self._belt_val_at_trigger  = 0.0
        self._belt_norm_at_trigger = 0.0
        self._trigger_latency_ms   = 0.0

        self.belt = BeltReader()

        # ── Layout ──────────────────────────────────────────────────────────
        self.frame = tk.Frame(self.root, bg="black")
        self.frame.pack(fill="both", expand=True)

        self.label_main = tk.Label(
            self.frame, text="", fg="white", bg="black",
            font=("Helvetica", 48), wraplength=800, justify="center"
        )
        self.label_main.pack(expand=True)

        self.label_sub = tk.Label(
            self.frame, text="", fg="white", bg="black",
            font=("Helvetica", 18), wraplength=800, justify="center"
        )
        self.label_sub.pack(pady=20)

        self.label_belt = tk.Label(
            self.frame, text="", fg="#555555", bg="black",
            font=("Courier", 12)
        )
        self.label_belt.pack(pady=5)

        self.entry_id     = tk.Entry(self.frame, font=("Helvetica", 18))
        self.button_start = tk.Button(
            self.frame, text="Start Experiment",
            font=("Helvetica", 16), command=self.on_start_clicked
        )

        self.root.bind("<Key>", self.on_key_press)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.belt.start()
        self._tick_status()
        self.show_intro_screen()

    # ── Status bar ───────────────────────────────────────────────────────────

    def _tick_status(self):
        if self.belt.connected:
            v      = self.belt.get_value()
            norm   = self.belt.get_normalised()
            filled = int(norm * 24) if self.belt.calibrated else 0
            bar    = "█" * filled + "░" * (24 - filled)
            cal    = (f"{self.belt.cal_min:.1f}–{self.belt.cal_max:.1f} N"
                      if self.belt.calibrated else "not calibrated")
            self.label_belt.config(text=f"Belt [{bar}]  {v:.2f} N  ({cal})")
        else:
            self.label_belt.config(text="Belt: connecting…")
        self.root.after(100, self._tick_status)

    # ── Intro ─────────────────────────────────────────────────────────────────

    def show_intro_screen(self):
        self.state = "intro"
        self.label_main.config(text="Breathing SNARC Experiment", font=("Helvetica", 40))
        self.label_sub.config(text="Enter Participant ID and click Start.\nLeave blank for P000.")
        self.entry_id.pack()
        self.button_start.pack(pady=10)

    def on_start_clicked(self):
        pid = self.entry_id.get().strip() or "P000"
        self.participant_id = pid
        self.entry_id.pack_forget()
        self.button_start.pack_forget()
        if self.belt.connected:
            self.show_calibration_exhale()
        else:
            self._wait_for_belt(timeout_s=8)

    def _wait_for_belt(self, timeout_s, elapsed=0):
        if self.belt.connected:
            self.show_calibration_exhale()
        elif elapsed >= timeout_s * 10:
            self.show_instructions_screen()
        else:
            self.label_main.config(
                text=f"Connecting to belt… ({timeout_s - elapsed//10}s)",
                font=("Helvetica", 30)
            )
            self.root.after(100, lambda: self._wait_for_belt(timeout_s, elapsed + 1))

    # ── Calibration ───────────────────────────────────────────────────────────

    def show_calibration_exhale(self):
        self.state = "cal_exhale"
        self.label_main.config(text="CALIBRATION  1 / 2", font=("Helvetica", 36))
        self.label_sub.config(
            text="EXHALE completely and keep your lungs empty.\n\n"
                 "Recording starts in 2 seconds — hold for 4 seconds."
        )
        self.root.after(2000, self._record_exhale)

    def _record_exhale(self):
        self.label_sub.config(text="EXHALE and HOLD  ●  recording…")
        samples, start = [], time.perf_counter()

        def collect():
            samples.append(self.belt.get_value())
            if time.perf_counter() - start < 4.0:
                self.root.after(100, collect)
            else:
                self._exhale_min = min(samples)
                self._exhale_max = max(samples)
                self.show_calibration_inhale()

        collect()

    def show_calibration_inhale(self):
        self.state = "cal_inhale"
        self.label_main.config(text="CALIBRATION  2 / 2", font=("Helvetica", 36))
        self.label_sub.config(
            text="INHALE completely and keep your lungs full.\n\n"
                 "Recording starts in 2 seconds — hold for 4 seconds."
        )
        self.root.after(2000, self._record_inhale)

    def _record_inhale(self):
        self.label_sub.config(text="INHALE and HOLD  ●  recording…")
        samples, start = [], time.perf_counter()

        def collect():
            samples.append(self.belt.get_value())
            if time.perf_counter() - start < 4.0:
                self.root.after(100, collect)
            else:
                self._inhale_min = min(samples)
                self._inhale_max = max(samples)
                global_min = min(self._exhale_min, self._inhale_min)
                global_max = max(self._exhale_max, self._inhale_max)
                self.belt.calibrate(global_min, global_max)
                self.show_instructions_screen()

        collect()

    # ── Instructions ──────────────────────────────────────────────────────────

    def show_instructions_screen(self):
        self.state = "instructions"
        if self.belt.connected and self.belt.calibrated:
            belt_note = "✓ Belt calibrated. Number appears at inhale peak / exhale trough."
        elif self.belt.connected:
            belt_note = "✓ Belt connected but not calibrated — using timer."
        else:
            belt_note = "⚠ No belt — using 4-second timer."

        self.label_main.config(text="Instructions", font=("Helvetica", 36))
        self.label_sub.config(text=(
            "You will complete 4 blocks of 20 trials.\n\n"
            "Each trial:\n"
            "  1) See INHALE or EXHALE — breathe and hold that position.\n"
            "  2) A number appears — decide ODD or EVEN:\n\n"
            "         F  =  ODD\n"
            "         J  =  EVEN\n\n"
            "Respond as quickly and accurately as possible.\n\n"
            f"{belt_note}\n\n"
            "Press SPACE to begin."
        ))

    # ── Trials ────────────────────────────────────────────────────────────────

    def build_trials(self):
        numbers     = [1, 2, 3, 4]
        inhale_pool = [n for n in numbers for _ in range(10)]
        exhale_pool = [n for n in numbers for _ in range(10)]
        random.shuffle(inhale_pool)
        random.shuffle(exhale_pool)
        trials, ii, ei = [], 0, 0
        for g in range(1, 81):
            cond = "Inhale" if g % 2 == 1 else "Exhale"
            if cond == "Inhale":
                number = inhale_pool[ii]; ii += 1
            else:
                number = exhale_pool[ei]; ei += 1
            trials.append({
                "trial_global":   g,
                "block":          (g - 1) // 20 + 1,
                "trial_in_block": (g - 1) % 20 + 1,
                "condition":      cond,
                "number":         number,
            })
        return trials

    def start_experiment(self):
        self.trials        = self.build_trials()
        self.trial_index   = 0
        self.current_block = 1
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"BreathingSnarc_{self.participant_id}_{ts}.csv"
        self.csv_file   = open(filename, mode="w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            "ParticipantID", "TrialGlobal", "Block", "TrialInBlock",
            "Condition", "Number", "CorrectKey", "PressedKey",
            "Correct", "ReactionTimeMs",
            "BeltConnected", "BeltCalibrated",
            "ForceAtTrigger_N", "NormalisedAtTrigger", "TriggerLatencyMs",
        ])
        self.show_block_start_screen(first_block=True)

    def show_block_start_screen(self, first_block=False):
        self.state = "block_start"
        self.label_main.config(text=f"Block {self.current_block} of 4", font=("Helvetica", 40))
        self.label_sub.config(text=(
            "Press SPACE to start." if first_block
            else "Take a short break.\n\nPress SPACE when ready to continue."
        ))

    def start_next_trial_or_block(self):
        if self.trial_index >= len(self.trials):
            self.finish_experiment()
            return
        trial = self.trials[self.trial_index]
        if trial["block"] != self.current_block:
            self.current_block = trial["block"]
            self.show_block_start_screen()
            return
        self.show_breathing_phase(trial)

    # ── Trial phases ──────────────────────────────────────────────────────────

    def show_breathing_phase(self, trial):
        self.state         = "breathing"
        self.current_trial = trial
        self.label_main.config(
            text="INHALE" if trial["condition"] == "Inhale" else "EXHALE",
            font=("Helvetica", 72)
        )
        self.label_sub.config(text="")
        self.root.after(BREATHING_CUE_MS, self._begin_waiting)

    def _begin_waiting(self):
        self.state        = "waiting"
        self.trigger_time = time.perf_counter()
        self._poll()

    def _poll(self):
        if self.state != "waiting":
            return
        elapsed_ms = (time.perf_counter() - self.trigger_time) * 1000
        cond       = self.current_trial["condition"]

        if not self.belt.connected or not self.belt.calibrated:
            reached = elapsed_ms >= (4000 - BREATHING_CUE_MS)
        elif cond == "Inhale":
            reached = self.belt.is_inhale_peak()
        else:
            reached = self.belt.is_exhale_trough()

        if elapsed_ms >= MAX_WAIT_MS:
            reached = True

        if reached:
            self._show_number()
        else:
            self.root.after(50, self._poll)

    def _show_number(self):
        self.state = "number"
        self._trigger_latency_ms   = (time.perf_counter() - self.trigger_time) * 1000
        self._belt_val_at_trigger  = self.belt.get_value()
        self._belt_norm_at_trigger = self.belt.get_normalised()
        self.label_main.config(text=str(self.current_trial["number"]), font=("Helvetica", 80))
        self.label_sub.config(text="")
        self.rt_start_time = time.perf_counter()

    # ── Response ──────────────────────────────────────────────────────────────

    def handle_response(self, key):
        if self.state != "number":
            return
        rt          = int(round((time.perf_counter() - self.rt_start_time) * 1000))
        trial       = self.current_trial
        correct_key = "F" if trial["number"] % 2 == 1 else "J"
        pressed_key = key.upper()
        correct     = 1 if pressed_key == correct_key else 0

        self.csv_writer.writerow([
            self.participant_id,
            trial["trial_global"], trial["block"], trial["trial_in_block"],
            trial["condition"], trial["number"],
            correct_key, pressed_key, correct, rt,
            int(self.belt.connected), int(self.belt.calibrated),
            f"{self._belt_val_at_trigger:.4f}",
            f"{self._belt_norm_at_trigger:.3f}",
            f"{self._trigger_latency_ms:.1f}",
        ])
        self.trial_index += 1
        self.root.after(500, self.start_next_trial_or_block)

    # ── Finish ────────────────────────────────────────────────────────────────

    def finish_experiment(self):
        self.state = "finished"
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
        self.label_main.config(text="Experiment complete!", font=("Helvetica", 40))
        self.label_sub.config(text="Thank you for participating!\n\nYou may close this window.")

    # ── Keys ──────────────────────────────────────────────────────────────────

    def on_key_press(self, event):
        key = event.keysym
        if self.state == "instructions" and key == "space":
            self.start_experiment()
        elif self.state == "block_start" and key == "space":
            self.start_next_trial_or_block()
        elif self.state == "number" and key.lower() in ("f", "j"):
            self.handle_response(key)
        if key == "Escape":
            self.on_close()

    def on_close(self):
        self.belt.stop()
        if self.csv_file:
            self.csv_file.close()
        self.root.destroy()


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    BreathingSnarcGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()