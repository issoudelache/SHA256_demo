# UI moderne (ttkbootstrap si disponible, sinon ttk standard)
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.scrolledtext import ScrolledText

# try ttkbootstrap, fallback to ttk
try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
    UsingBootstrap = True
    from ttkbootstrap.constants import (
        LEFT, RIGHT, TOP, BOTTOM, X, Y, BOTH, VERTICAL, HORIZONTAL,
        CENTER, E, W, N, S, NW, NE, SW, SE
    )
except ImportError:
    import tkinter.ttk as tb
    from tkinter.constants import *
    UsingBootstrap = False
    from tkinter.constants import (
        LEFT, RIGHT, TOP, BOTTOM, X, Y, BOTH, VERTICAL, HORIZONTAL,
        CENTER, E, W, N, S, NW, NE, SW, SE
    )

from sha256 import sha256_trace

# Constants de l'application
SPEED_MIN = 0.1  # Très rapide
SPEED_MAX = 2.0  # Très lent
SPEED_DEFAULT = 0.5


class ModernApp(tb.Window if UsingBootstrap else tk.Tk):
    def __init__(self):
        # Initialisation des variables d'état AVANT tout appel de méthode ou création de widget
        self._trace = None
        self._trace2 = None  # Pour la comparaison
        self._current_block = 0
        self._current_round = 0
        self._auto = False
        self._speed = SPEED_DEFAULT
        self._speed_range = (SPEED_MIN, SPEED_MAX)
        self._step_explanations = {
            "padding": "Le padding ajoute des bits pour atteindre une taille multiple de 512 bits:\n- Ajout d'un bit '1'\n- Ajout de zéros\n- Ajout de la longueur du message sur 64 bits",
            "blocks": "Le message est découpé en blocs de 512 bits,\nchaque bloc est traité en séquence",
            "schedule": "Création du schedule W[0..63]:\n- W[0..15] = mots du bloc\n- W[16..63] = expansion avec mélange des mots précédents",
            "rounds": "64 rounds de compression:\n- Mise à jour des registres a..h\n- Utilisation de fonctions non-linéaires\n- Addition modulo 2^32\n- Rotation et décalage de bits",
            "comparison": "Comparaison de deux hash :\n- Visualisation bit à bit des différences\n- Calcul du pourcentage de différence\n- Impact des changements sur le résultat final"
        }
        self._hash1 = None
        self._hash2 = None
        self._comparison_result = None

        if UsingBootstrap:
            super().__init__(themename="darkly")
        else:
            super().__init__()
        # Couleur de texte pour les zones explicatives et les canvases (adaptée au thème)
        if UsingBootstrap:
            self._text_color = "#ffffff"  # thème sombre → texte clair
        else:
            self._text_color = "#334"     # thème clair → texte sombre

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
        toolbar.pack(side=TOP, fill=X, padx=10, pady=8)  # Corrected types
        btn_open = tb.Button(toolbar, text="Ouvrir…", command=self.open_file, width=12)
        btn_hash = tb.Button(toolbar, text="Hacher", command=self.do_hash, width=12)
        btn_trace = tb.Button(toolbar, text="Tracer étapes", command=self.do_trace, width=16)
        for w in (btn_open, btn_hash, btn_trace):
            w.pack(side=LEFT, padx=5)  # Corrected types

        # Message input + digest
        top_frame = tb.Labelframe(self, text="Message")
        top_frame.pack(side=TOP, fill=BOTH, expand=True, padx=12, pady=(0, 10))  # Corrected types
        self.txt = ScrolledText(top_frame, height=6, wrap=tk.WORD)
        self.txt.pack(side=TOP, fill=BOTH, expand=True, padx=10, pady=10)  # Corrected types
        digest_row = tb.Frame(top_frame)
        digest_row.pack(side=TOP, fill=X, padx=10, pady=(0, 10))  # Corrected types
        tb.Label(digest_row, text="Digest (hex)").pack(side=LEFT)  # Corrected types
        self.var_hex = tk.StringVar(value="—")
        self.entry_hex = tb.Entry(digest_row, textvariable=self.var_hex, state="readonly")
        self.entry_hex.pack(side=LEFT, fill=X, expand=True, padx=10)  # Corrected types

        # Notebook
        nb = tb.Notebook(self)
        nb.pack(side=TOP, fill=BOTH, expand=True, padx=12, pady=0)  # Corrected types
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


    # --- Event Handlers ---
    def on_block_changed(self):
        """Gestionnaire de changement de bloc"""
        try:
            block = int(self.spin_block.get())
            self._current_block = block
            self.update_all_views()
        except (ValueError, tk.TclError):
            pass

    def on_round_changed(self):
        """Gestionnaire de changement de round"""
        try:
            round_val = int(self.spin_round.get())
            self._current_round = round_val
            self.update_all_views()
        except (ValueError, tk.TclError):
            pass

    def on_speed_changed(self, value):
        """Gestionnaire de changement de vitesse"""
        try:
            self._speed = float(value)
            if self._auto:
                self.auto_stop()
                self.auto_play()
        except (ValueError, tk.TclError):
            pass

    def on_block_round_changed(self):
        """Gestionnaire de changement de bloc dans la vue rounds"""
        try:
            block = int(self.spin_block_r.get())
            self._current_block = block
            self.update_all_views()
        except (ValueError, tk.TclError):
            pass

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

        # Ajout des contrôles de lecture
        ctrl, block_spin, round_spin = self._build_playback_controls(f)
        ctrl.pack(side=TOP, fill=X, padx=12, pady=(12, 6))
        self.spin_block_s = block_spin
        self.spin_round_s = round_spin
        self.spin_block_s.config(command=self._on_schedule_block_change)
        self.spin_round_s.config(command=self._on_schedule_round_change)

        # Reste du code existant
        header = tb.Frame(f)
        header.pack(side=TOP, fill=X, padx=12, pady=(12, 0))
        self.lbl_sched_block = tb.Label(header, text="Bloc 0"); self.lbl_sched_block.pack(side=LEFT)
        self.tbl_sched = tb.Treeview(f, columns=("i", "W"), show="headings", height=18)
        self.tbl_sched.heading("i", text="i"); self.tbl_sched.column("i", width=70, anchor="center")
        self.tbl_sched.heading("W", text="W[i]"); self.tbl_sched.column("W", width=260, anchor="w")
        self.tbl_sched.pack(side=TOP, fill=BOTH, expand=True, padx=12, pady=12)
        return f

    def _build_tab_rounds(self):
        f = tb.Frame(self.nb); self.nb.add(f, text="Rounds (0..63)")

        # Panneau d'explications à droite
        explanation = tb.Labelframe(f, text="Explications")
        explanation.pack(side=RIGHT, fill=Y, padx=(0, 12), pady=12)

        # Zone de texte pour les explications (texte coloré selon le thème)
        self.explain_text = ScrolledText(explanation, width=40, height=15, wrap=tk.WORD, fg=self._text_color)
        self.explain_text.pack(padx=8, pady=8)
        self.explain_text.insert("1.0", "SHA-256 Explications:\n\n")
        for title, text in self._step_explanations.items():
            self.explain_text.insert(tk.END, f"• {title.title()}\n{text}\n\n")
        self.explain_text.configure(state="disabled")

        main_frame = tb.Frame(f)
        main_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=12, pady=12)

        ctrl = tb.Frame(main_frame)
        ctrl.pack(side=TOP, fill=X)

        # Contrôles de bloc et round (comme avant)
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
        tb.Button(ctrl, text="⏸ Pause", command=self.auto_stop).pack(side=LEFT, padx=(6, 12))

        # Contrôle de vitesse modifié
        speed_frame = tb.Labelframe(ctrl, text="Vitesse")
        speed_frame.pack(side=LEFT, padx=(6, 0), fill=Y)
        self.speed_scale = tb.Scale(speed_frame, from_=SPEED_MAX, to=SPEED_MIN,  # Inversé : plus haut = plus lent
                                  value=self._speed, orient="vertical", length=60,
                                  command=self.on_speed_changed)
        self.speed_scale.pack(padx=8, pady=4)

        # Zone principale pour les registres et valeurs
        body = tb.Frame(main_frame)
        body.pack(side=TOP, fill=BOTH, expand=True, pady=6)

        # Ajouter une visualisation des opérations
        ops_frame = tb.Labelframe(body, text="Opérations du round")
        ops_frame.pack(side=TOP, fill=X, pady=(0, 8))
        self.ops_canvas = tk.Canvas(ops_frame, height=120, background="#F2FAFF")
        self.ops_canvas.pack(fill=X, padx=8, pady=8)

        # Registres et variables (comme avant)
        regs_frame = tb.Frame(body)
        regs_frame.pack(side=TOP, fill=BOTH, expand=True)
        left = tb.Labelframe(regs_frame, text="Registres a..h")
        left.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 8))
        right = tb.Labelframe(regs_frame, text="T1 / T2 / K / W")
        right.pack(side=LEFT, fill=BOTH, expand=True, padx=(8, 0))
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
        self.canvas = tk.Canvas(f, height=360, background="#F2FAFF")
        self.canvas.pack(fill=BOTH, expand=True, padx=8, pady=8)
        # draw registers a..h
        self.vis_regs = {}
        x0, y0, w, h, gap = 40, 80, 110, 48, 18
        for i, reg in enumerate("abcdefgh"):
            x = x0 + i*(w+gap)
            rect = self.canvas.create_rectangle(x, y0, x+w, y0+h, fill="#e8eefc", outline="#4776e6", width=2)
            self.canvas.create_text(x+w/2, y0-16, text=reg, font=("Segoe UI", 11, "bold"), fill=self._text_color)
            txt = self.canvas.create_text(x+w/2, y0+h/2, text="—", font=("Consolas", 11), fill=self._text_color)
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
            self.canvas.create_text(xx+w/2, my0-16, text=lab, font=("Segoe UI", 11, "bold"), fill=self._text_color)
            txt = self.canvas.create_text(xx+w/2, my0+h/2, text="—", font=("Consolas", 11), fill=self._text_color)
            self.vis_misc[lab] = (rect, txt)
        self.vis_round_label = self.canvas.create_text(980, 24, text="Round: –", font=("Segoe UI", 12, "bold"), fill=self._text_color)
        return f

    # ---------- NOUVEL ONGLET : Matrices de bits ----------
    def _build_tab_matrix(self):
        f = tb.Frame(self.nb)
        self.nb.add(f, text="Comparaison")

        # Panneau de contrôle
        ctrl = tb.Frame(f)
        ctrl.pack(side=TOP, fill=X, padx=12, pady=12)

        # Entrées pour les deux hash
        input_frame = tb.Labelframe(f, text="Entrées à comparer")
        input_frame.pack(side=TOP, fill=X, padx=12, pady=(0, 12))

        # Premier message
        msg1_frame = tb.Frame(input_frame)
        msg1_frame.pack(side=TOP, fill=X, padx=8, pady=8)
        tb.Label(msg1_frame, text="Message 1:").pack(side=LEFT)
        self.txt_msg1 = ScrolledText(msg1_frame, height=3, width=50)
        self.txt_msg1.pack(side=LEFT, fill=X, expand=True, padx=(8, 0))

        # Deuxième message
        msg2_frame = tb.Frame(input_frame)
        msg2_frame.pack(side=TOP, fill=X, padx=8, pady=8)
        tb.Label(msg2_frame, text="Message 2:").pack(side=LEFT)
        self.txt_msg2 = ScrolledText(msg2_frame, height=3, width=50)
        self.txt_msg2.pack(side=LEFT, fill=X, expand=True, padx=(8, 0))

        # Bouton de comparaison
        btn_frame = tb.Frame(input_frame)
        btn_frame.pack(side=TOP, fill=X, padx=8, pady=(0, 8))
        tb.Button(btn_frame, text="Comparer", command=self.compare_hashes).pack(side=RIGHT)

        # Zone de résultats
        results_frame = tb.Labelframe(f, text="Résultats de la comparaison")
        results_frame.pack(side=TOP, fill=BOTH, expand=True, padx=12, pady=(0, 12))

        # Affichage des différences
        self.diff_canvas = tk.Canvas(results_frame, background='white')
        self.diff_canvas.pack(side=TOP, fill=BOTH, expand=True, padx=8, pady=8)

        # Statistiques
        stats_frame = tb.Frame(results_frame)
        stats_frame.pack(side=BOTTOM, fill=X, padx=8, pady=8)
        self.var_diff_percent = tk.StringVar(value="Différence: ---%")
        tb.Label(stats_frame, textvariable=self.var_diff_percent).pack(side=LEFT)

        return f

    # --- Action methods ---
    def compare_hashes(self):
        """Compare deux messages et affiche leurs différences"""
        try:
            msg1 = self.txt_msg1.get("1.0", tk.END).strip().encode()
            msg2 = self.txt_msg2.get("1.0", tk.END).strip().encode()

            self._hash1 = sha256_trace(msg1)
            self._hash2 = sha256_trace(msg2)

            # Calcul des différences
            h1 = int(self._hash1['digest'], 16)
            h2 = int(self._hash2['digest'], 16)
            diff = h1 ^ h2
            diff_bits = bin(diff)[2:].zfill(256)
            diff_count = diff_bits.count('1')
            diff_percent = (diff_count / 256) * 100

            self.var_diff_percent.set(f"Différence: {diff_percent:.2f}%")

            # Mise à jour du canvas
            self.draw_hash_comparison(self._hash1['digest'], self._hash2['digest'])

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la comparaison: {str(e)}")

    def draw_hash_comparison(self, hash1, hash2):
        """Dessine la visualisation des différences entre les deux hash"""
        self.diff_canvas.delete("all")
        width = self.diff_canvas.winfo_width()
        height = self.diff_canvas.winfo_height()

        # Conversion en binaire
        bin1 = bin(int(hash1, 16))[2:].zfill(256)
        bin2 = bin(int(hash2, 16))[2:].zfill(256)

        # Dimensions de la matrice
        cols = 32
        rows = 8
        cell_w = width / cols
        cell_h = height / rows

        for i in range(256):
            row = i // cols
            col = i % cols
            x = col * cell_w
            y = row * cell_h

            # Couleurs basées sur les différences
            if bin1[i] != bin2[i]:
                color = "#ff6b6b"  # Rouge pour les différences
            else:
                color = "#4CAF50" if bin1[i] == "1" else "#90A4AE"

            self.diff_canvas.create_rectangle(
                x, y, x + cell_w, y + cell_h,
                fill=color, outline="white"
            )

    def _update_speed(self, value):
        """Met à jour la vitesse d'animation"""
        try:
            self._speed = float(value)
            if self._auto:
                self.auto_stop()
                self.auto_play()
        except ValueError:
            pass

    def _build_playback_controls(self, parent):
        """Construit les contrôles de lecture standardisés"""
        ctrl = tb.Frame(parent)

        # Contrôles de bloc
        tb.Label(ctrl, text="Bloc:").pack(side=LEFT)
        block_spin = tk.Spinbox(ctrl, from_=0, to=0, width=6)
        block_spin.pack(side=LEFT, padx=(6, 12))

        # Contrôles de round
        tb.Label(ctrl, text="Round:").pack(side=LEFT)
        round_spin = tk.Spinbox(ctrl, from_=0, to=63, width=6)
        round_spin.pack(side=LEFT, padx=6)

        # Boutons de navigation
        nav_frame = tb.Frame(ctrl)
        nav_frame.pack(side=LEFT, padx=12)
        tb.Button(nav_frame, text="◀", width=3, command=lambda: self._jump_round(-1)).pack(side=LEFT)
        tb.Button(nav_frame, text="▶", width=3, command=lambda: self._jump_round(+1)).pack(side=LEFT, padx=(4, 0))

        # Boutons lecture/pause
        play_frame = tb.Frame(ctrl)
        play_frame.pack(side=LEFT, padx=12)
        tb.Button(play_frame, text="▶▶ Play", command=self.auto_play).pack(side=LEFT)
        tb.Button(play_frame, text="⏸ Pause", command=self.auto_stop).pack(side=LEFT, padx=(6, 0))

        # Contrôle de vitesse
        speed_frame = self._build_speed_control(parent)
        speed_frame.pack(side=LEFT, padx=12, fill=Y)

        return ctrl, block_spin, round_spin

    def _advance_animation(self):
        """Fait avancer l'animation d'un pas"""
        if not self._auto:
            return

        # Avance au round suivant
        if self._current_round < 63:
            self._current_round += 1
        else:
            if self._current_block < len(self._trace['blocks']) - 1:
                self._current_block += 1
                self._current_round = 0
            else:
                self.auto_stop()
                return

        self.update_all_views()

        # Programme le prochain pas
        if self._auto:
            self.after(int(self._speed * 1000), self._advance_animation)

    def auto_play(self):
        """Démarre la lecture automatique"""
        if not self._auto:
            self._auto = True
            self._advance_animation()
            self.status.set("Lecture automatique...")

    def auto_stop(self):
        """Arrête la lecture automatique"""
        self._auto = False
        self.status.set("Pause")

    def _validate_input(self, input_text):
        """Valide l'entrée utilisateur"""
        if not input_text.strip():
            raise ValueError("Le message ne peut pas être vide")
        return input_text.strip().encode()

    def do_hash(self):
        """Calcule le hash du message avec validation"""
        try:
            message = self._validate_input(self.txt.get("1.0", tk.END))
            result = sha256_trace(message)
            self.var_hex.set(result['digest'])
            self.status.set("Hash calculé avec succès")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du calcul du hash : {str(e)}")
            self.status.set("Erreur lors du calcul")

    def do_trace(self):
        """Trace les étapes avec validation"""
        try:
            message = self._validate_input(self.txt.get("1.0", tk.END))
            self._trace = sha256_trace(message)
            self._current_block = 0
            self._current_round = 0
            self.var_hex.set(self._trace['digest'])
            self.update_all_views()
            self.status.set("Trace initialisée")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du traçage : {str(e)}")
            self.status.set("Erreur lors du traçage")

    def update_all_views(self):
        """Met à jour toutes les vues avec gestion des erreurs"""
        try:
            if not self._trace:
                return

            # Mise à jour des contrôles de bloc
            max_block = len(self._trace['blocks']) - 1
            self._current_block = max(0, min(self._current_block, max_block))
            self._current_round = max(0, min(self._current_round, 63))

            # Met à jour tous les spinbox de bloc
            for spin in [self.spin_block, self.spin_block_s, self.spin_block_r, self.spin_block_v]:
                spin.config(to=max_block)
                spin.delete(0, tk.END)
                spin.insert(0, str(self._current_block))

            # Met à jour tous les spinbox de round
            for spin in [self.spin_round, self.spin_round_s, self.spin_round_v]:
                spin.delete(0, tk.END)
                spin.insert(0, str(self._current_round))

            # Met à jour les vues spécifiques
            self._update_padding_view()
            self._update_blocks_view()
            self._update_schedule_view()
            self._update_rounds_view()
            self._update_visual_view()

            self.status.set(f"Bloc {self._current_block}, Round {self._current_round}")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour des vues : {str(e)}")
            self.status.set("Erreur de mise à jour")

    def _update_padding_view(self):
        """Met à jour la vue de padding"""
        try:
            if not self._trace:
                return
            padding_info = self._trace['padding']
            self.pad_vars['data_bits'].set(str(padding_info['data_bits']))
            self.pad_vars['one_bit'].set("1")
            self.pad_vars['zero_pad_bits'].set(str(padding_info['zero_bits']))
            self.pad_vars['len_field_bits'].set(str(padding_info['len_bits']))
            self.pad_vars['total_bits'].set(str(padding_info['total_bits']))
            self.pad_vars['blocks'].set(str(len(self._trace['blocks'])))
        except Exception as e:
            self.status.set("Erreur d'affichage padding")
            raise

    def _update_blocks_view(self):
        """Met à jour la vue des blocs"""
        try:
            if not self._trace or not self._trace['blocks']:
                return
            block = self._trace['blocks'][self._current_block]
            words = block['words']
            # Efface la table
            for item in self.tbl_words.get_children():
                self.tbl_words.delete(item)
            # Ajoute une ligne avec les mots du bloc
            self.tbl_words.insert("", "end", values=words)
        except Exception as e:
            self.status.set("Erreur d'affichage blocs")
            raise

    def _update_schedule_view(self):
        """Met à jour la vue du schedule"""
        try:
            if not self._trace or not self._trace['blocks']:
                return
            block = self._trace['blocks'][self._current_block]
            schedule = block['schedule']
            # Efface la table
            for item in self.tbl_sched.get_children():
                self.tbl_sched.delete(item)
            # Ajoute les lignes pour chaque mot du schedule
            for i, w in enumerate(schedule):
                self.tbl_sched.insert("", "end", values=(i, f"0x{w:08x}"))
            # Met en évidence le round actuel si dans les limites
            if 0 <= self._current_round < len(schedule):
                self.highlight_schedule_row(self._current_round)
        except Exception as e:
            self.status.set("Erreur d'affichage schedule")
            raise

    def _update_rounds_view(self):
        """Met à jour la vue des rounds"""
        try:
            if not self._trace or not self._trace['blocks']:
                return
            block = self._trace['blocks'][self._current_block]
            round_info = block['rounds'][self._current_round]

            # Mise à jour des registres
            for reg in "abcdefgh":
                self.round_vars[reg].set(f"0x{round_info[reg]:08x}")

            # Mise à jour des variables T1, T2, K, W
            self.round_vars["T1"].set(f"0x{round_info['T1']:08x}")
            self.round_vars["T2"].set(f"0x{round_info['T2']:08x}")
            self.round_vars["K"].set(f"0x{round_info['K']:08x}")
            self.round_vars["W"].set(f"0x{round_info['W']:08x}")

            # Mise à jour du canvas d'opérations
            self._draw_round_operations(round_info)
        except Exception as e:
            self.status.set("Erreur d'affichage rounds")
            raise

    def _update_visual_view(self):
        """Met à jour la vue graphique"""
        try:
            if not self._trace or not self._trace['blocks']:
                return
            block = self._trace['blocks'][self._current_block]
            round_info = block['rounds'][self._current_round]

            # Mise à jour des registres
            for reg, (rect, txt) in self.vis_regs.items():
                value = f"0x{round_info[reg]:08x}"
                self.canvas.itemconfig(txt, text=value)

            # Mise à jour des variables
            for var in ["T1", "T2", "K", "W"]:
                rect, txt = self.vis_misc[var]
                value = f"0x{round_info[var]:08x}"
                self.canvas.itemconfig(txt, text=value)

            # Mise à jour du label de round
            self.canvas.itemconfig(
                self.vis_round_label,
                text=f"Round {self._current_round}: 0x{round_info['h']:08x}"
            )
        except Exception as e:
            self.status.set("Erreur d'affichage graphique")
            raise

    def _draw_round_operations(self, round_info):
        """Dessine les opérations du round actuel"""
        try:
            self.ops_canvas.delete("all")
            # Configuration du dessin
            width = self.ops_canvas.winfo_width()
            height = self.ops_canvas.winfo_height()

            # Dessine les opérations principales
            x1, y1 = 20, 20
            self.ops_canvas.create_text(x1, y1, text="Ch(e,f,g)", anchor="w", fill=self._text_color)
            self.ops_canvas.create_text(x1, y1+20, text=f"0x{round_info['Ch']:08x}", anchor="w", fill=self._text_color)

            x2 = width // 3
            self.ops_canvas.create_text(x2, y1, text="Σ1(e)", anchor="w", fill=self._text_color)
            self.ops_canvas.create_text(x2, y1+20, text=f"0x{round_info['Sigma1']:08x}", anchor="w", fill=self._text_color)

            x3 = 2 * width // 3
            self.ops_canvas.create_text(x3, y1, text="Maj(a,b,c)", anchor="w", fill=self._text_color)
            self.ops_canvas.create_text(x3, y1+20, text=f"0x{round_info['Maj']:08x}", anchor="w", fill=self._text_color)

            # Dessine les flèches d'opération
            y2 = height - 30
            self.ops_canvas.create_line(x1+60, y1+30, x1+60, y2, arrow="last")
            self.ops_canvas.create_line(x2+60, y1+30, x2+60, y2, arrow="last")
            self.ops_canvas.create_line(x3+60, y1+30, x3+60, y2, arrow="last")

        except Exception as e:
            self.status.set("Erreur d'affichage opérations")
            raise

    def highlight_schedule_row(self, row_index):
        """Met en évidence une ligne dans le tableau du schedule"""
        try:
            for item in self.tbl_sched.get_children():
                tags = ()
                if self.tbl_sched.index(item) == row_index:
                    tags = ("highlight",)
                self.tbl_sched.item(item, tags=tags)
        except Exception as e:
            self.status.set("Erreur de surbrillance")
            raise

    def _tweak_style(self):
        """Ajuste le style de l'interface"""
        if UsingBootstrap:
            style = self.style
        else:
            style = tb.Style()

        # Configure les styles des tableaux
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        # Style pour les lignes surlignées
        style.map("Treeview",
            foreground=[("selected", "#ffffff")],
            background=[("selected", "#4776e6")])

        # Configure le tag de surbrillance
        self.tbl_sched.tag_configure("highlight", background="#e8eefc")

    def _switch_theme(self, theme):
        """Change le thème de l'application"""
        if UsingBootstrap:
            self.style.theme_use(theme)

    def _about(self):
        """Affiche la boîte de dialogue À propos"""
        messagebox.showinfo(
            "À propos",
            "SHA-256 — Démo pas-à-pas\n\n"
            "Une application pédagogique pour comprendre\n"
            "le fonctionnement de l'algorithme SHA-256"
        )

    def open_file(self):
        """Ouvre un fichier et charge son contenu"""
        try:
            filename = filedialog.askopenfilename(
                title="Ouvrir un fichier",
                filetypes=[("Tous les fichiers", "*.*")]
            )
            if filename:
                with open(filename, 'rb') as f:
                    data = f.read()
                self.txt.delete("1.0", tk.END)
                self.txt.insert("1.0", data.decode('utf-8', errors='replace'))
                self.status.set(f"Fichier chargé : {filename}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le fichier : {str(e)}")

    def _build_speed_control(self, parent):
        """Construit le contrôle de vitesse"""
        frame = tb.Labelframe(parent, text="Vitesse")
        scale = tb.Scale(
            frame,
            from_=SPEED_MAX,
            to=SPEED_MIN,
            value=self._speed,
            orient="vertical",
            length=60,
            command=self._update_speed
        )
        scale.pack(padx=8, pady=4)
        return frame

    def _jump_block(self, delta, rounds=False):
        """Saute au bloc suivant/précédent"""
        try:
            if not self._trace:
                return
            new_block = self._current_block + delta
            if 0 <= new_block < len(self._trace['blocks']):
                self._current_block = new_block
                self.update_all_views()
        except Exception as e:
            self.status.set(f"Erreur de navigation : {str(e)}")

    def _jump_round(self, delta):
        """Saute au round suivant/précédent"""
        try:
            if not self._trace:
                return
            new_round = self._current_round + delta
            if 0 <= new_round < 64:
                self._current_round = new_round
                self.update_all_views()
        except Exception as e:
            self.status.set(f"Erreur de navigation : {str(e)}")

    def _jump_round_visual(self, delta):
        """Saute au round suivant/précédent dans la vue graphique"""
        try:
            if not self._trace:
                return
            new_round = int(self.spin_round_v.get()) + delta
            if 0 <= new_round < 64:
                self.spin_round_v.delete(0, tk.END)
                self.spin_round_v.insert(0, str(new_round))
                self._current_round = new_round
                self.update_all_views()
        except Exception as e:
            self.status.set(f"Erreur de navigation : {str(e)}")

    def _on_schedule_block_change(self):
        """Gestionnaire de changement de bloc dans la vue schedule"""
        try:
            block = int(self.spin_block_s.get())
            self._current_block = block
            self.update_all_views()
        except (ValueError, tk.TclError):
            pass

    def _on_schedule_round_change(self):
        """Gestionnaire de changement de round dans la vue schedule"""
        try:
            round_val = int(self.spin_round_s.get())
            self._current_round = round_val
            self.update_all_views()
        except (ValueError, tk.TclError):
            pass

    def _on_visual_block_change(self):
        """Gestionnaire de changement de bloc dans la vue graphique"""
        try:
            block = int(self.spin_block_v.get())
            self._current_block = block
            self.update_all_views()
        except (ValueError, tk.TclError):
            pass

    def _on_visual_round_change(self):
        """Gestionnaire de changement de round dans la vue graphique"""
        try:
            round_val = int(self.spin_round_v.get())
            self._current_round = round_val
            self.update_all_views()
        except (ValueError, tk.TclError):
            pass


if __name__ == "__main__":
    app = None
    try:
        app = ModernApp()
        app.mainloop()
    except Exception as e:
        if app and hasattr(app, 'status'):
            app.status.set(f"Erreur : {str(e)}")
            messagebox.showerror("Erreur", f"Une erreur fatale est survenue : {str(e)}")
        else:
            print(f"Erreur de démarrage : {str(e)}")
            messagebox.showerror("Erreur de démarrage", f"Impossible de lancer l'application : {str(e)}")
