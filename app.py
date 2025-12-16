"""
Entry point for HuggingFace Spaces
Redirects to the actual app in src/ui/app.py
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the actual app
from src.ui.app import app

if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
