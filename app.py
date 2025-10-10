# UI moderne (ttkbootstrap si disponible, sinon ttk standard)
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

# try ttkbootstrap, fallback to ttk
try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import LEFT, RIGHT, TOP, BOTTOM, X, Y, BOTH
    UsingBootstrap = True
except Exception:
    import tkinter.ttk as tb
    LEFT, RIGHT, TOP, BOTTOM, X, Y, BOTH = tk.LEFT, tk.RIGHT, tk.TOP, tk.BOTTOM, tk.X, tk.Y, tk.BOTH
    UsingBootstrap = False

from sha256 import sha256_hex, sha256_trace
from utils import bytes_to_hex


class ModernApp(tb.Window if UsingBootstrap else tk.Tk):
    def __init__(self):
        if UsingBootstrap:
            super().__init__(themename="darkly")
        else:
            super().__init__()
        self.title("SHA-256 — Démo pas-à-pas (UI moderne)")
        self.geometry("1200x820")
        self.minsize(1024, 700)

        # Menu
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        m_app = tk.Menu(menubar, tearoff=False)
        m_view = tk.Menu(menubar, tearoff=False)
        m_help = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Application", menu=m_app)
        menubar.add_cascade(label="Affichage", menu=m_view)
        menubar.add_cascade(label="Aide", menu=m_help)
        m_app.add_command(label="Ouvrir…", command=self.open_file, accelerator="Ctrl+O")
        m_app.add_separator()
        m_app.add_command(label="Quitter", command=self.quit, accelerator="Ctrl+Q")
        if UsingBootstrap:
            m_view.add_command(label="Thème clair", command=lambda: self._switch_theme("flatly"))
            m_view.add_command(label="Thème sombre", command=lambda: self._switch_theme("darkly"))
        m_help.add_command(label="À propos", command=self._about)

        # Shortcuts
        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-q>", lambda e: self.quit())

        # Toolbar
        toolbar = tb.Frame(self)
        toolbar.pack(side=TOP, fill=X, padx=10, pady=8)
        btn_open = tb.Button(toolbar, text="Ouvrir…", command=self.open_file, width=12)
        btn_hash = tb.Button(toolbar, text="Hacher", command=self.do_hash, width=12)
        btn_trace = tb.Button(toolbar, text="Tracer étapes", command=self.do_trace, width=16)
        for w in (btn_open, btn_hash, btn_trace):
            w.pack(side=LEFT, padx=5)

        # Message input + digest
        top_frame = tb.Labelframe(self, text="Message")
        top_frame.pack(side=TOP, fill=BOTH, expand=True, padx=12, pady=(0, 10))
        self.txt = ScrolledText(top_frame, height=6, wrap=tk.WORD)
        self.txt.pack(side=TOP, fill=BOTH, expand=True, padx=10, pady=10)
        digest_row = tb.Frame(top_frame)
        digest_row.pack(side=TOP, fill=X, padx=10, pady=(0, 10))
        tb.Label(digest_row, text="Digest (hex)").pack(side=LEFT)
        self.var_hex = tk.StringVar(value="—")
        self.entry_hex = tb.Entry(digest_row, textvariable=self.var_hex, state="readonly")
        self.entry_hex.pack(side=LEFT, fill=X, expand=True, padx=10)

        # Notebook
        nb = tb.Notebook(self)
        nb.pack(side=TOP, fill=BOTH, expand=True, padx=12, pady=0)
        self.nb = nb
        self.tab_padding = self._build_tab_padding()
        self.tab_blocks = self._build_tab_blocks()
        self.tab_schedule = self._build_tab_schedule()
        self.tab_rounds = self._build_tab_rounds()
        self.tab_visual = self._build_tab_visual()
        self.tab_matrix = self._build_tab_matrix()   # <-- NOUVEL ONGLET

        # status
        self.status = tk.StringVar(value="Prêt")
        statusbar = tb.Frame(self)
        statusbar.pack(side=BOTTOM, fill=X)
        self.status_label = tb.Label(statusbar, textvariable=self.status, anchor="w")
        self.status_label.pack(side=LEFT, padx=10, pady=6)

        # state
        self._trace = None
        self._current_block = 0
        self._current_round = 0
        self._auto = False

        self._tweak_style()

    # --- Tabs builders ---
    def _build_tab_padding(self):
        f = tb.Frame(self.nb); self.nb.add(f, text="Padding")
        grid = tb.Frame(f); grid.pack(side=TOP, anchor="nw", padx=16, pady=16)
        self.pad_vars = {k: tk.StringVar(value="—") for k in
                         ['data_bits', 'one_bit', 'zero_pad_bits', 'len_field_bits', 'total_bits', 'blocks']}
        labels = [
            ("Bits de données", 'data_bits'),
            ("Bit '1'", 'one_bit'),
            ("Zéros de bourrage", 'zero_pad_bits'),
            ("Champ longueur (64 bits)", 'len_field_bits'),
            ("Total après padding (bits)", 'total_bits'),
            ("Nombre de blocs (512b)", 'blocks'),
        ]
        for i, (lab, key) in enumerate(labels):
            tb.Label(grid, text=lab).grid(row=i, column=0, sticky="w", pady=4, padx=(0, 12))
            tb.Label(grid, textvariable=self.pad_vars[key]).grid(row=i, column=1, sticky="w")
        return f

    def _build_tab_blocks(self):
        f = tb.Frame(self.nb); self.nb.add(f, text="Blocs & mots")
        ctrl = tb.Frame(f); ctrl.pack(side=TOP, fill=X, padx=12, pady=(12, 6))
        tb.Label(ctrl, text="Bloc #").pack(side=LEFT)
        self.spin_block = tk.Spinbox(ctrl, from_=0, to=0, width=6, command=self.on_block_changed)
        self.spin_block.pack(side=LEFT, padx=8)
        tb.Button(ctrl, text="◀", width=3, command=lambda: self._jump_block(-1)).pack(side=LEFT)
        tb.Button(ctrl, text="▶", width=3, command=lambda: self._jump_block(+1)).pack(side=LEFT, padx=(4, 0))
        cols = [f"W{i}" for i in range(16)]
        self.tbl_words = tb.Treeview(f, columns=cols, show="headings", height=6)
        for c in cols:
            self.tbl_words.heading(c, text=c); self.tbl_words.column(c, width=90, anchor="center")
        self.tbl_words.pack(side=TOP, fill=BOTH, expand=True, padx=12, pady=(0, 12))
        return f

    def _build_tab_schedule(self):
        f = tb.Frame(self.nb); self.nb.add(f, text="Schedule (W[0..63])")
        header = tb.Frame(f); header.pack(side=TOP, fill=X, padx=12, pady=(12, 0))
        self.lbl_sched_block = tb.Label(header, text="Bloc 0"); self.lbl_sched_block.pack(side=LEFT)
        self.tbl_sched = tb.Treeview(f, columns=("i", "W"), show="headings", height=18)
        self.tbl_sched.heading("i", text="i"); self.tbl_sched.column("i", width=70, anchor="center")
        self.tbl_sched.heading("W", text="W[i]"); self.tbl_sched.column("W", width=260, anchor="w")
        self.tbl_sched.pack(side=TOP, fill=BOTH, expand=True, padx=12, pady=12)
        return f

    def _build_tab_rounds(self):
        f = tb.Frame(self.nb); self.nb.add(f, text="Rounds (0..63)")
        ctrl = tb.Frame(f); ctrl.pack(side=TOP, fill=X, padx=12, pady=(12, 6))
        tb.Label(ctrl, text="Bloc:").pack(side=LEFT)
        self.spin_block_r = tk.Spinbox(ctrl, from_=0, to=0, width=6, command=self.on_block_round_changed)
        self.spin_block_r.pack(side=LEFT, padx=(6, 12))
        tb.Button(ctrl, text="◀", width=3, command=lambda: self._jump_block(-1, rounds=True)).pack(side=LEFT)
        tb.Button(ctrl, text="▶", width=3, command=lambda: self._jump_block(+1, rounds=True)).pack(side=LEFT)
        tb.Separator(ctrl, orient=tk.VERTICAL).pack(side=LEFT, fill=Y, padx=12)
        tb.Label(ctrl, text="Round:").pack(side=LEFT)
        self.spin_round = tk.Spinbox(ctrl, from_=0, to=63, width=6, command=self.on_round_changed)
        self.spin_round.pack(side=LEFT, padx=6)
        tb.Button(ctrl, text="◀", width=3, command=lambda: self._jump_round(-1)).pack(side=LEFT)
        tb.Button(ctrl, text="▶", width=3, command=lambda: self._jump_round(+1)).pack(side=LEFT, padx=(4, 8))
        tb.Button(ctrl, text="▶▶ Play", command=self.auto_play).pack(side=LEFT)
        tb.Button(ctrl, text="⏸ Pause", command=self.auto_stop).pack(side=LEFT, padx=(6, 0))
        body = tb.Frame(f); body.pack(side=TOP, fill=BOTH, expand=True, padx=12, pady=6)
        left = tb.Labelframe(body, text="Registres a..h"); left.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 8))
        right = tb.Labelframe(body, text="T1 / T2 / K / W"); right.pack(side=LEFT, fill=BOTH, expand=True, padx=(8, 0))
        self.round_vars = {k: tk.StringVar(value="—") for k in list("abcdefgh") + ["T1", "T2", "K", "W"]}
        for i, reg in enumerate("abcdefgh"):
            row = tb.Frame(left); row.pack(side=TOP, anchor="w", pady=4, padx=10)
            tb.Label(row, text=f"{reg}").pack(side=LEFT, padx=(0, 10))
            tb.Label(row, textvariable=self.round_vars[reg], font=("Consolas", 11)).pack(side=LEFT)
        for lab in ["T1", "T2", "K", "W"]:
            row = tb.Frame(right); row.pack(side=TOP, anchor="w", pady=4, padx=10)
            tb.Label(row, text=lab).pack(side=LEFT, padx=(0, 10))
            tb.Label(row, textvariable=self.round_vars[lab], font=("Consolas", 11)).pack(side=LEFT)
        return f

    def _build_tab_visual(self):
        f = tb.Frame(self.nb); self.nb.add(f, text="Vue graphique")
        top = tb.Frame(f); top.pack(fill=X, padx=8, pady=6)
        tb.Label(top, text="Bloc:").pack(side=LEFT)
        self.spin_block_v = tk.Spinbox(top, from_=0, to=0, width=6, command=lambda: self._on_visual_block_change())
        self.spin_block_v.pack(side=LEFT, padx=(4, 12))
        tb.Label(top, text="Round:").pack(side=LEFT)
        self.spin_round_v = tk.Spinbox(top, from_=0, to=63, width=6, command=lambda: self._on_visual_round_change())
        self.spin_round_v.pack(side=LEFT, padx=6)
        tb.Button(top, text="◀", width=3, command=lambda: self._jump_round_visual(-1)).pack(side=LEFT)
        tb.Button(top, text="▶", width=3, command=lambda: self._jump_round_visual(+1)).pack(side=LEFT)
        self.canvas = tk.Canvas(f, height=360, background="#f9f9fb")
        self.canvas.pack(fill=BOTH, expand=True, padx=8, pady=8)
        # draw registers a..h
        self.vis_regs = {}
        x0, y0, w, h, gap = 40, 80, 110, 48, 18
        for i, reg in enumerate("abcdefgh"):
            x = x0 + i*(w+gap)
            rect = self.canvas.create_rectangle(x, y0, x+w, y0+h, fill="#e8eefc", outline="#4776e6", width=2)
            self.canvas.create_text(x+w/2, y0-16, text=reg, font=("Segoe UI", 11, "bold"), fill="#334")
            txt = self.canvas.create_text(x+w/2, y0+h/2, text="—", font=("Consolas", 11))
            self.vis_regs[reg] = (rect, txt)
            if i > 0:
                self.canvas.create_line(x-gap, y0+h/2, x-6, y0+h/2, arrow=tk.LAST, width=2, fill="#888")
        # T1,T2,K,W
        self.vis_misc = {}
        mx0, my0 = 40, 220
        labels = ["T1", "T2", "K", "W"]
        for j, lab in enumerate(labels):
            xx = mx0 + j*(w+gap)
            rect = self.canvas.create_rectangle(xx, my0, xx+w, my0+h,
                                                fill="#eaf7ea" if lab in ("T1", "T2") else "#fff7e6",
                                                outline="#34a853" if lab in ("T1", "T2") else "#f6a400", width=2)
            self.canvas.create_text(xx+w/2, my0-16, text=lab, font=("Segoe UI", 11, "bold"), fill="#334")
            txt = self.canvas.create_text(xx+w/2, my0+h/2, text="—", font=("Consolas", 11))
            self.vis_misc[lab] = (rect, txt)
        self.vis_round_label = self.canvas.create_text(980, 24, text="Round: –", font=("Segoe UI", 12, "bold"), fill="#333")
        return f

    # ---------- NOUVEL ONGLET : Matrices de bits ----------
    def _build_tab_matrix(self):
        f = tb.Frame(self.nb)
        self.nb.add(f, text="Matrices (bits)")

        top = tb.Frame(f); top.pack(fill=X, padx=10, pady=6)
        tb.Label(top, text="Bloc:").pack(side=LEFT)
        self.spin_block_m = tk.Spinbox(top, from_=0, to=0, width=6, command=self._on_matrix_block_change)
        self.spin_block_m.pack(side=LEFT, padx=(4, 12))
        tb.Label(top, text="Round:").pack(side=LEFT)
        self.spin_round_m = tk.Spinbox(top, from_=0, to=63, width=6, command=self._on_matrix_round_change)
        self.spin_round_m.pack(side=LEFT, padx=6)
        tb.Button(top, text="◀", width=3, command=lambda: self._jump_round_matrix(-1)).pack(side=LEFT)
        tb.Button(top, text="▶", width=3, command=lambda: self._jump_round_matrix(+1)).pack(side=LEFT)

        # Canvas des matrices : 8 lignes (a..h) x 32 colonnes (bits)
        # chaque case ~ 18x18, espacements = 2px
        self.matrix_canvas = tk.Canvas(f, height=8*22 + 80, background="#ffffff")
        self.matrix_canvas.pack(fill=BOTH, expand=True, padx=10, pady=8)

        self._matrix_cells = {}  # {reg: [rect_id x32]}
        self._matrix_labels = {} # {reg: text_id for label on left}
        self._build_matrix_grid()

        return f

    def _build_matrix_grid(self):
        self.matrix_canvas.delete("all")
        regs = list("abcdefgh")
        cell_w = 18
        cell_h = 18
        gap = 2
        left_margin = 60
        top_margin = 30

        # entêtes de colonnes (0..31)
        for col in range(32):
            x = left_margin + col*(cell_w+gap) + cell_w/2
            self.matrix_canvas.create_text(x, top_margin-14, text=str(col), font=("Segoe UI", 8), fill="#777")

        self._matrix_cells.clear()
        self._matrix_labels.clear()

        for row, reg in enumerate(regs):
            y0 = top_margin + row*(cell_h+gap)
            # label de ligne (a..h)
            lab = self.matrix_canvas.create_text(24, y0 + cell_h/2, text=reg,
                                                 font=("Segoe UI", 11, "bold"), fill="#333")
            self._matrix_labels[reg] = lab

            cells = []
            for col in range(32):
                x0 = left_margin + col*(cell_w+gap)
                rect = self.matrix_canvas.create_rectangle(
                    x0, y0, x0+cell_w, y0+cell_h,
                    fill="#f1f5f9", outline="#cbd5e1"
                )
                cells.append(rect)
            self._matrix_cells[reg] = cells

        # légende
        self.matrix_canvas.create_text(
            left_margin, top_margin + 8*(cell_h+gap) + 18,
            text="Bit = 1 → bleu • Bit = 0 → gris", anchor="w",
            font=("Segoe UI", 10), fill="#555"
        )

    # -------------------- Actions --------------------
    def do_hash(self):
        s = self.txt.get("1.0", tk.END).rstrip("\n")
        try:
            self.var_hex.set(sha256_hex(s))
            self.status.set("Digest calculé")
        except Exception as e:
            messagebox.showerror("Erreur", f"{e}\n\n{traceback.format_exc()}")

    def do_trace(self):
        s = self.txt.get("1.0", tk.END).rstrip("\n")
        try:
            digest, trace = sha256_trace(s.encode("utf-8"))
            self._trace = trace
            self.var_hex.set(bytes_to_hex(digest))
            self.status.set("Trace générée — utilisez les contrôles de bloc/round")
            self._current_block = 0
            self._current_round = 0
            self._refresh_all()
            self.nb.select(self.tab_rounds)
        except Exception as e:
            messagebox.showerror("Erreur", f"{e}\n\n{traceback.format_exc()}")

    # -------------------- Rafraîchissements --------------------
    def _refresh_all(self):
        if not self._trace:
            return
        for k, v in self._trace.padding.items():
            if k in self.pad_vars:
                self.pad_vars[k].set(str(v))
        nb = len(self._trace.blocks)
        # spin max pour blocs
        self.spin_block.config(to=max(0, nb - 1))
        self.spin_block_r.config(to=max(0, nb - 1))
        # visuel tab
        if hasattr(self, "spin_block_v"):
            self.spin_block_v.config(to=max(0, nb - 1))
            self.spin_round_v.config(to=63)
            self.spin_block_v.delete(0, tk.END); self.spin_block_v.insert(0, str(self._current_block))
            self.spin_round_v.delete(0, tk.END); self.spin_round_v.insert(0, str(self._current_round))
        # matrix tab
        self.spin_block_m.config(to=max(0, nb - 1))
        self.spin_round_m.config(to=63)
        self.spin_block_m.delete(0, tk.END); self.spin_block_m.insert(0, str(self._current_block))
        self.spin_round_m.delete(0, tk.END); self.spin_round_m.insert(0, str(self._current_round))

        # data views
        self._fill_words(self._current_block)
        self._fill_schedule(self._current_block)
        self._show_round(self._current_block, self._current_round)
        self._update_visual(self._current_block, self._current_round)
        self._update_matrix(self._current_block, self._current_round)

    def _fill_words(self, bidx: int):
        for it in self.tbl_words.get_children():
            self.tbl_words.delete(it)
        row = [f"0x{w:08x}" for w in self._trace.blocks[bidx]]
        for r in range(4):
            vals = row[r*4:(r+1)*4]
            self.tbl_words.insert("", "end", values=vals)

    def _fill_schedule(self, bidx: int):
        self.lbl_sched_block.config(text=f"Bloc {bidx}")
        for it in self.tbl_sched.get_children():
            self.tbl_sched.delete(it)
        for i, w in enumerate(self._trace.schedules[bidx]):
            self.tbl_sched.insert("", "end", values=(i, f"0x{w:08x}"))

    def _show_round(self, bidx: int, ridx: int):
        ridx = max(0, min(63, ridx))
        self._current_round = ridx
        r = self._trace.rounds[bidx][ridx]
        for reg in "abcdefgh":
            self.round_vars[reg].set(f"0x{getattr(r, reg):08x}")
        self.round_vars["T1"].set(f"0x{r.T1:08x}")
        self.round_vars["T2"].set(f"0x{r.T2:08x}")
        self.round_vars["K"].set(f"0x{r.K:08x}")
        self.round_vars["W"].set(f"0x{r.W:08x}")
        try:
            self.spin_round.delete(0, tk.END)
            self.spin_round.insert(0, str(ridx))
        except Exception:
            pass
        self._update_visual(bidx, ridx)
        self._update_matrix(bidx, ridx)

    # --- Vue graphique (boîtes) ---
    def _update_visual(self, bidx: int, ridx: int):
        if not hasattr(self, "canvas") or not self._trace:
            return
        r = self._trace.rounds[bidx][ridx]
        for reg in "abcdefgh":
            _, txt = self.vis_regs[reg]
            self.canvas.itemconfigure(txt, text=f"0x{getattr(r, reg):08x}")
        for lab in ("T1", "T2", "K", "W"):
            _, txt = self.vis_misc[lab]
            self.canvas.itemconfigure(txt, text=f"0x{getattr(r, lab):08x}")
        self.canvas.itemconfigure(self.vis_round_label, text=f"Round: {ridx}")

    # --- Matrices de bits ---
    def _update_matrix(self, bidx: int, ridx: int):
        if not self._trace:
            return
        r = self._trace.rounds[bidx][ridx]
        # couleurs
        col1 = "#2563eb"   # 1 → bleu
        col0 = "#e5e7eb"   # 0 → gris clair
        bd1  = "#1d4ed8"
        bd0  = "#cbd5e1"
        for reg in "abcdefgh":
            val = getattr(r, reg) & 0xFFFFFFFF
            bits = f"{val:032b}"  # string 32 chars
            cells = self._matrix_cells[reg]
            for i, bit in enumerate(bits):
                fill = col1 if bit == "1" else col0
                outline = bd1 if bit == "1" else bd0
                self.matrix_canvas.itemconfigure(cells[i], fill=fill, outline=outline)
        # Légende du round courant
        # (on la place en haut à droite)
        self._matrix_round_text = getattr(self, "_matrix_round_text", None)
        if self._matrix_round_text is None:
            self._matrix_round_text = self.matrix_canvas.create_text(
                self.matrix_canvas.winfo_width() - 80, 16,
                text=f"Round: {ridx}", font=("Segoe UI", 11, "bold"), fill="#333"
            )
        else:
            self.matrix_canvas.itemconfigure(self._matrix_round_text, text=f"Round: {ridx}")

    # -------------------- Navigation --------------------
    def _jump_block(self, delta: int, rounds: bool = False):
        if not self._trace:
            return
        nb = len(self._trace.blocks)
        self._current_block = (self._current_block + delta) % nb
        self.spin_block.delete(0, tk.END); self.spin_block.insert(0, str(self._current_block))
        self.spin_block_r.delete(0, tk.END); self.spin_block_r.insert(0, str(self._current_block))
        self.spin_block_v.delete(0, tk.END); self.spin_block_v.insert(0, str(self._current_block))
        self.spin_block_m.delete(0, tk.END); self.spin_block_m.insert(0, str(self._current_block))
        self._fill_words(self._current_block)
        self._fill_schedule(self._current_block)
        self._show_round(self._current_block, self._current_round)
        if rounds:
            self.nb.select(self.tab_rounds)

    def _jump_round(self, delta: int):
        if not self._trace:
            return
        self._current_round = (self._current_round + delta) % 64
        self._show_round(self._current_block, self._current_round)
        # sync autres spin
        self.spin_round_v.delete(0, tk.END); self.spin_round_v.insert(0, str(self._current_round))
        self.spin_round_m.delete(0, tk.END); self.spin_round_m.insert(0, str(self._current_round))

    # Visual tab callbacks
    def _on_visual_block_change(self):
        if not self._trace:
            return
        try:
            b = int(float(self.spin_block_v.get()))
        except Exception:
            b = 0
        b = max(0, min(len(self._trace.blocks) - 1, b))
        self._current_block = b
        # sync autres spin
        for sp in (self.spin_block, self.spin_block_r, self.spin_block_m):
            sp.delete(0, tk.END); sp.insert(0, str(b))
        self._fill_words(b); self._fill_schedule(b); self._show_round(b, self._current_round)

    def _on_visual_round_change(self):
        if not self._trace:
            return
        try:
            r = int(float(self.spin_round_v.get()))
        except Exception:
            r = 0
        r = max(0, min(63, r))
        self._current_round = r
        # sync autres spin
        for sp in (self.spin_round, self.spin_round_m):
            sp.delete(0, tk.END); sp.insert(0, str(r))
        self._show_round(self._current_block, r)

    def _jump_round_visual(self, delta: int):
        if not self._trace:
            return
        self._current_round = (self._current_round + delta) % 64
        self.spin_round_v.delete(0, tk.END); self.spin_round_v.insert(0, str(self._current_round))
        self._show_round(self._current_block, self._current_round)

    # Matrix tab callbacks
    def _on_matrix_block_change(self):
        if not self._trace:
            return
        try:
            b = int(float(self.spin_block_m.get()))
        except Exception:
            b = 0
        b = max(0, min(len(self._trace.blocks) - 1, b))
        self._current_block = b
        # sync autres spin
        for sp in (self.spin_block, self.spin_block_r, self.spin_block_v):
            sp.delete(0, tk.END); sp.insert(0, str(b))
        self._fill_words(b); self._fill_schedule(b); self._show_round(b, self._current_round)

    def _on_matrix_round_change(self):
        if not self._trace:
            return
        try:
            r = int(float(self.spin_round_m.get()))
        except Exception:
            r = 0
        r = max(0, min(63, r))
        self._current_round = r
        # sync autres spin
        for sp in (self.spin_round, self.spin_round_v):
            sp.delete(0, tk.END); sp.insert(0, str(r))
        self._show_round(self._current_block, r)

    def _jump_round_matrix(self, delta: int):
        if not self._trace:
            return
        self._current_round = (self._current_round + delta) % 64
        self.spin_round_m.delete(0, tk.END); self.spin_round_m.insert(0, str(self._current_round))
        self._show_round(self._current_block, self._current_round)

    # Rounds tab callbacks (déjà existants)
    def on_block_changed(self):
        if not self._trace:
            return
        try:
            b = int(float(self.spin_block.get()))
        except Exception:
            b = 0
        b = max(0, min(len(self._trace.blocks) - 1, b))
        self._current_block = b
        # sync autres spin
        for sp in (self.spin_block_r, self.spin_block_v, self.spin_block_m):
            sp.delete(0, tk.END); sp.insert(0, str(b))
        self._fill_words(b); self._fill_schedule(b); self._show_round(b, self._current_round)

    def on_block_round_changed(self):
        if not self._trace:
            return
        try:
            b = int(float(self.spin_block_r.get()))
        except Exception:
            b = 0
        b = max(0, min(len(self._trace.blocks) - 1, b))
        self._current_block = b
        # sync autres spin
        for sp in (self.spin_block, self.spin_block_v, self.spin_block_m):
            sp.delete(0, tk.END); sp.insert(0, str(b))
        self._fill_words(b); self._fill_schedule(b); self._show_round(b, self._current_round)

    def on_round_changed(self):
        if not self._trace:
            return
        try:
            r = int(float(self.spin_round.get()))
        except Exception:
            r = 0
        r = max(0, min(63, r))
        self._current_round = r
        # sync autres spin
        for sp in (self.spin_round_v, self.spin_round_m):
            sp.delete(0, tk.END); sp.insert(0, str(r))
        self._show_round(self._current_block, r)

    # Auto play
    def auto_play(self):
        if not self._trace or self._auto:
            return
        self._auto = True
        self._tick()

    def _tick(self):
        if not self._auto:
            return
        self._jump_round(+1)
        self.after(220, self._tick)

    def auto_stop(self):
        self._auto = False

    # Utils
    def open_file(self):
        path = filedialog.askopenfilename(title="Choisir un fichier")
        if not path:
            return
        try:
            with open(path, "rb") as f:
                text = f.read().decode("utf-8", errors="replace")
            self.txt.delete("1.0", tk.END)
            self.txt.insert("1.0", text)
            self.status.set(f"Fichier chargé : {path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"{e}\n\n{traceback.format_exc()}")

    def _switch_theme(self, name: str):
        if UsingBootstrap:
            try:
                self.style.theme_use(name)
            except Exception:
                pass

    def _tweak_style(self):
        try:
            if not UsingBootstrap:
                style = tb.Style()
                style.theme_use("clam")
                style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
                style.configure("TButton", padding=6)
                style.configure("TLabel", padding=2)
                self.style = style
        except Exception:
            pass

    def _about(self):
        messagebox.showinfo(
            "À propos",
            "Démo SHA-256 pas-à-pas.\nUI moderne (ttkbootstrap si disponible),\nretour automatique sur ttk sinon."
        )

if __name__ == "__main__":
    ModernApp().mainloop()
