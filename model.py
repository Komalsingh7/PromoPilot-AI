"""Model adapter: Gemini is optional; heuristic mode works offline."""
import os

def model_status():
    if os.getenv('GEMINI_API_KEY'): return f"Gemini enabled ({os.getenv('GEMINI_MODEL','gemini-2.0-flash')})"
    return 'Offline heuristic mode (set GEMINI_API_KEY to enable Gemini)'
