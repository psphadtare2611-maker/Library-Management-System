# ============================================================================
# main.py
# ----------------------------------------------------------------------------
# APPLICATION ENTRY POINT for the Library Management System.
#
# Run the whole app with:
#     python main.py
#
# Responsibilities:
#   - Build the main window (which hosts every screen and talks to the
#     service layer).
#   - Start the Tkinter event loop.
#   - Log startup/shutdown and catch any fatal error so it is recorded in
#     logs/app.log instead of vanishing.
#
# It stays thin on purpose: no business logic, no SQL, no widgets here.
# ============================================================================

from tkinter import messagebox

from ui.main_window import MainWindow
from utils.logger import logger


def main():
    """Launch the Library Management System desktop application."""
    try:
        app = MainWindow()
        app.mainloop()
    except Exception as error:
        # Anything that escapes to here is fatal; record it and tell the user.
        logger.error(f"Fatal error: {error}")
        try:
            messagebox.showerror(
                "Fatal error",
                "The application hit an unexpected error and must close.\n"
                "See logs/app.log for details.",
            )
        except Exception:
            # If even the dialog fails (e.g. no display), just re-raise.
            raise


if __name__ == "__main__":
    main()
