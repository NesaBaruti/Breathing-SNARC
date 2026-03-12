# Baruti Analysis — Breathing and the SNARC Effect
**Author:** Nesa Baruti Zajmi  
**Language:** Python 3.8+
---

## Overview

This project investigates whether **breathing phase** (inhale vs. exhale) modulates spatial-numerical processing (the SNARC effect) in a reaction time task. Participants categorized numbers (1–4) by pressing a left or right key while their breathing phase was tracked. Breathing phase is detected in real time using a Vernier GDX-RB respiration belt. Participants respond by pressing F (odd) or J (even). Reaction times and accuracy are saved automatically to a CSV file.
If no belt is detected at startup, the script falls back to a 4-second timer so the experiment can still run.

---

## Hardware Required

| Device | Purpose |
|--------|---------|
| **Vernier GDX-RB** Respiration Belt | Measures breathing via Force sensor (Sensor 1) |
| Bluetooth-enabled computer | Connects to belt via BLE |

The belt reads a **force signal in Newtons**:
- Exhale trough ≈ **5.7 N**
- Inhale peak ≈ **21.3 N**

Personal min/max values are calibrated at the start of every session.

---

## Installation

### 1. Install Python

Download from [https://www.python.org/downloads/](https://www.python.org/downloads/)  
Requires **Python 3.8 or later**.

### 2. Install the required package

```bash
pip install godirect
```

That is the only external dependency. All other modules used (`tkinter`, `threading`, `time`, `random`, `csv`, `datetime`) are part of Python's standard library and require no installation.

---

## Running the Experiment

```bash
python breathing_snarc_experiment.py
```

1. Enter the **Participant ID** and click **Start Experiment**
2. The script will attempt to connect to the GDX-RB belt via Bluetooth
3. Complete the **2-step calibration**:
   - Exhale completely and hold for 4 seconds
   - Inhale completely and hold for 4 seconds
4. Read the on-screen instructions and press **Space** to begin
5. Complete **4 blocks × 20 trials = 80 trials total**
6. A CSV file is saved automatically when the experiment ends:
   ```
   BreathingSnarc_<ParticipantID>_<timestamp>.csv
   ```

> Press **Escape** at any time to exit and save progress.

---

## Experiment Design

- **Conditions:** Inhale vs. Exhale (alternating trial by trial)
- **Stimuli:** Numbers 1–4 (10 of each per condition, randomised)
- **Task:** Odd/Even categorisation — **F = Odd**, **J = Even**
- **Trigger logic:** Number appears when belt signal reaches ≥ 80% of range (inhale peak) or ≤ 20% (exhale trough)
- **Safety timeout:** If the belt target is not reached within 10 seconds, the number appears anyway

---

## Output CSV Columns

| Column | Description |
|--------|-------------|
| `ParticipantID` | Participant identifier |
| `TrialGlobal` | Global trial number (1–80) |
| `Block` | Block number (1–4) |
| `TrialInBlock` | Trial number within block (1–20) |
| `Condition` | `Inhale` or `Exhale` |
| `Number` | Stimulus number (1–4) |
| `CorrectKey` | Correct key: `F` (odd) or `J` (even) |
| `PressedKey` | Key the participant pressed |
| `Correct` | 1 = correct, 0 = incorrect |
| `ReactionTimeMs` | Reaction time in milliseconds |
| `BeltConnected` | 1 if belt was connected, 0 if timer fallback |
| `BeltCalibrated` | 1 if belt was calibrated, 0 otherwise |
| `ForceAtTrigger_N` | Raw force reading (N) at the moment the number appeared |
| `NormalisedAtTrigger` | Normalised belt value (0.0–1.0) at trigger |
| `TriggerLatencyMs` | Time (ms) from breathing cue to number onset |

---

## License

This project is for academic/research purposes. Please cite appropriately if you use or adapt this code.
