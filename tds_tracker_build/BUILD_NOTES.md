## Build notes

The desktop app listens on `http://127.0.0.1:8765/webhook` by default. Screenshot recognition runs in a background worker so the webhook can acknowledge Ultimate Macro quickly.

OCR values with sufficient confidence replace the configured fallback values for that match. The original OCR text and confidence are stored with the database event for review.

Because result layouts can change, the interface also includes **Analizar una captura** for testing a real Triumph/Loss screenshot and adjusting the confidence threshold without losing the match history.
