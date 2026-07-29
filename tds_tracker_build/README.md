# TDS Win Tracker v1.1.0 build source

This directory contains a split Base64 ZIP used only by the Windows GitHub Actions build.

The reconstructed project provides:

- a local Discord-compatible webhook receiver;
- SQLite session and match history;
- gold, gems, duration, win-rate, streak, and per-hour averages;
- background screenshot OCR using RapidOCR;
- manual screenshot analysis for calibration and corrections;
- an Ultimate Macro-inspired dark desktop interface;
- a standalone Windows folder containing `TDS Win Tracker.exe`.

The workflow reconstructs the ZIP, validates the parser and OCR engine, builds with PyInstaller on Windows, and uploads the packaged application as a workflow artifact.
