import sys
import asyncio
from bugfetcher.cli import run_cli
from bugfetcher.gui import BugFetcherGUI
from bugfetcher.api import app
import tkinter as tk
import uvicorn

def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "cli":
            asyncio.run(run_cli(sys.argv[2:]))
        elif mode == "gui":
            root = tk.Tk()
            app = BugFetcherGUI(root)
            root.mainloop()
        elif mode == "api":
            uvicorn.run("bugfetcher.api:app", host="0.0.0.0", port=55000)
        else:
            print("Usage: python main.py [cli|gui|api]")
    else:
        print("Please specify mode: cli, gui, or api")

if __name__ == "__main__":
    main()
