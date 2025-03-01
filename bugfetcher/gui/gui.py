import tkinter as tk
from tkinter import messagebox
from ..core import BugFetcherCore

class BugFetcherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bug Fetcher")
        self.fetcher = BugFetcherCore()
        self.is_fetching = False
        self.fetch_job = None
        self.create_widgets()
        self.load_config()

    def create_widgets(self):
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.grid(row=0, column=0, sticky=tk.NSEW)

        tk.Label(frame, text="ZenTao URL:").grid(row=0, column=0, sticky=tk.W)
        self.zentao_url = tk.Entry(frame)
        self.zentao_url.grid(row=0, column=1, sticky=tk.EW)

        tk.Label(frame, text="Username:").grid(row=1, column=0, sticky=tk.W)
        self.zentao_username = tk.Entry(frame)
        self.zentao_username.grid(row=1, column=1, sticky=tk.EW)

        tk.Label(frame, text="Password:").grid(row=2, column=0, sticky=tk.W)
        self.zentao_password = tk.Entry(frame, show="*")
        self.zentao_password.grid(row=2, column=1, sticky=tk.EW)

        tk.Label(frame, text="Feishu Webhook:").grid(row=3, column=0, sticky=tk.W)
        self.feishu_webhook = tk.Entry(frame)
        self.feishu_webhook.grid(row=3, column=1, sticky=tk.EW)

        tk.Label(frame, text="Interval (min):").grid(row=4, column=0, sticky=tk.W)
        self.fetch_interval = tk.Entry(frame)
        self.fetch_interval.grid(row=4, column=1, sticky=tk.EW)

        self.login_btn = tk.Button(frame, text="Login", command=self.login)
        self.login_btn.grid(row=5, column=0, columnspan=2)

        self.fetch_btn = tk.Button(frame, text="Start Fetching", command=self.toggle_fetching)
        self.fetch_btn.grid(row=6, column=0, columnspan=2)

        self.log_text = tk.Text(frame, height=10, state='disabled')
        self.log_text.grid(row=7, column=0, columnspan=2)

    def log(self, message):
        self.fetcher.log_message(message)
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.config(state='disabled')

    def load_config(self):
        config = self.fetcher._config
        self.zentao_url.insert(0, config.get("zentao_url", ""))
        self.zentao_username.insert(0, config.get("zentao_username", ""))
        self.zentao_password.insert(0, config.get("zentao_password", ""))
        self.feishu_webhook.insert(0, config.get("feishu_webhook_url", ""))
        self.fetch_interval.insert(0, str(config.get("fetch_interval", 60)))

    def login(self):
        self.fetcher._config["zentao_url"] = self.zentao_url.get()
        self.fetcher._config["zentao_username"] = self.zentao_username.get()
        self.fetcher._config["zentao_password"] = self.zentao_password.get()
        self.fetcher._config["feishu_webhook_url"] = self.feishu_webhook.get()
        self.fetcher._config["fetch_interval"] = int(self.fetch_interval.get())
        self.fetcher.save_config()
        token = self.fetcher.get_zentao_token_sync()
        if token:
            self.fetcher.zentao_token = token
            self.fetcher.save_config()
            self.log("Login successful")
            user_info = self.fetcher.fetch_user_info_sync()
            self.log("User info: " + str(user_info))
            self.select_product()
        else:
            self.log("Login failed")
            messagebox.showerror("Error", "Login failed")

    def select_product(self):
        products = self.fetcher.fetch_products_sync()
        if products:
            win = tk.Toplevel(self.root)
            win.title("Select Product")
            lb = tk.Listbox(win)
            for p in products:
                lb.insert(tk.END, p['name'])
            lb.pack()
            tk.Button(win, text="Confirm", command=lambda: self.confirm_product(win, lb, products)).pack()

    def confirm_product(self, win, lb, products):
        sel = lb.curselection()
        if sel:
            idx = sel[0]
            config_update = {
                "selected_product": products[idx]['name'],
                "selected_product_id": products[idx]['id']
            }
            self.log("Selected product: " + str(config_update))
            self.fetcher.save_config()
            win.destroy()

    def toggle_fetching(self):
        if not self.is_fetching:
            config_update = {
                "feishu_webhook_url": self.feishu_webhook.get(),
                "fetch_interval": int(self.fetch_interval.get())
            }
            self.log("Saving configuration: " + str(config_update))
            self.fetcher.save_config()
            self.start_fetching()
        else:
            self.log("Stopping fetching")
            self.stop_fetching()

    def start_fetching(self):
        self.is_fetching = True
        self.fetch_btn.config(text="Stop Fetching")
        self.log("Starting fetching")
        self.fetcher.fetch_new_bugs_sync()
        self.schedule_fetch()

    def stop_fetching(self):
        self.is_fetching = False
        self.fetch_btn.config(text="Start Fetching")
        self.log("Stopping fetching")
        if self.fetch_job:
            self.root.after_cancel(self.fetch_job)

    def schedule_fetch(self):
        if self.is_fetching:
            self.log("Fetching new bugs")
            self.fetcher.fetch_new_bugs_sync()
            self.fetch_job = self.root.after(self.fetcher.fetch_interval * 60000, self.schedule_fetch)
