import tkinter as tk
from tkinter import ttk, messagebox
import random
import mysql.connector

# --- KONFIGURASI DATABASE XAMPP ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'chess_db'
}

PIECE_VALUES = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000,
    'p': -100, 'n': -320, 'b': -330, 'r': -500, 'q': -900, 'k': -20000
}

PAWN_TABLE = [
    [0,  0,  0,  0,  0,  0,  0,  0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5,  5, 10, 25, 25, 10,  5,  5],
    [0,  0,  0, 20, 20,  0,  0,  0],
    [5, -5,-10,  0,  0,-10, -5,  5],
    [5, 10, 10,-20,-20, 10, 10,  5],
    [0,  0,  0,  0,  0,  0,  0,  0]
]

KNIGHT_TABLE = [
    [-50,-40,-30,-30,-30,-30,-40,-50],
    [-40,-20,  0,  0,  0,  0,-20,-40],
    [-30,  0, 10, 15, 15, 10,  0,-30],
    [-30,  5, 15, 20, 20, 15,  5,-30],
    [-30,  0, 15, 20, 20, 15,  0,-30],
    [-30,  5, 10, 15, 15, 10,  5,-30],
    [-40,-20,  0,  5,  5,  0,-20,-40],
    [-50,-40,-30,-30,-30,-30,-40,-50]
]

BISHOP_TABLE = [
    [-20,-10,-10,-10,-10,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5, 10, 10,  5,  0,-10],
    [-10,  5,  5, 10, 10,  5,  5,-10],
    [-10,  0, 10, 10, 10, 10,  0,-10],
    [-10, 10, 10, 10, 10, 10, 10,-10],
    [-10,  5,  0,  0,  0,  0,  5,-10],
    [-20,-10,-10,-10,-10,-10,-10,-20]
]

BOARD_THEMES = {
    "Slate Classic (Sesuai Referensi)": {
        "light": "#e8eef6",
        "dark": "#4a6584",
        "last_light": "#bfdbfe",
        "last_dark": "#324861",
        "selected": "#7dd3fc",
        "border": "#1e293b",
        "coord_fg": "#94a3b8"
    },
    "Chess.com Classic Green": {
        "light": "#eeeed2",
        "dark": "#769656",
        "last_light": "#f7f783",
        "last_dark": "#baca44",
        "selected": "#f6f669",
        "border": "#3b5323",
        "coord_fg": "#6b8055"
    }
}

UNICODE_PIECES = {
    'white': {
        'K': '\u2654', 'Q': '\u2655', 'R': '\u2656',
        'B': '\u2657', 'N': '\u2658', 'P': '\u2659'
    },
    'black': {
        'k': '\u265A', 'q': '\u265B', 'r': '\u265C',
        'b': '\u265D', 'n': '\u265E', 'p': '\u265F'
    }
}


class UnicodePieceRenderer:
    @staticmethod
    def draw(canvas, cx, cy, piece, font_size=42, tag=None):
        is_white = piece.isupper()
        ptype = piece.upper()
        font_family = "Segoe UI Symbol"
        tag_kwargs = {"tags": tag} if tag else {}

        if is_white:
            char_white = UNICODE_PIECES['white'][ptype]
            char_black_mask = UNICODE_PIECES['black'][piece.lower()]

            canvas.create_text(cx, cy - 2, text=char_black_mask, fill="#ffffff",
                               font=(font_family, font_size), **tag_kwargs)

            canvas.create_text(cx + 0.6, cy - 2, text=char_white, fill="#1e293b",
                               font=(font_family, font_size), **tag_kwargs)
            canvas.create_text(cx - 0.6, cy - 2, text=char_white, fill="#1e293b",
                               font=(font_family, font_size), **tag_kwargs)

            canvas.create_text(cx, cy - 2, text=char_white, fill="#0f172a",
                               font=(font_family, font_size), **tag_kwargs)
        else:
            char_black = UNICODE_PIECES['black'][piece]

            for ox, oy in [(-0.8, 0), (0.8, 0), (0, -0.8), (0, 0.8)]:
                canvas.create_text(cx + ox, cy - 2 + oy, text=char_black, fill="#cbd5e1",
                                   font=(font_family, font_size), **tag_kwargs)

            canvas.create_text(cx, cy - 2, text=char_black, fill="#090d16",
                               font=(font_family, font_size), **tag_kwargs)


class SmoothChessGame:
    def __init__(self, root):
        self.root = root
        self.root.title("CHESS TEAM 2")
        self.root.configure(bg="#0b1120")
        self.root.minsize(920, 680)

        self.square_size = 72
        self.coord_margin = 24

        self.current_theme_name = "Slate Classic (Sesuai Referensi)"
        # Inisialisasi awal matriks 8x8 kosong agar tidak IndexError
        self.board_state = [['.' for _ in range(8)] for _ in range(8)]
        self.turn = 'white'
        self.selected_pos = None
        self.valid_moves = []
        self.game_active = False
        self.status_message = "MENUNGGU MULAI"
        self.bot_color = "black"
        self.player_color = "white"
        self.move_count = 0
        self.game_recorded = False

        self.ai_level = tk.StringVar(value="Menengah")
        self.last_move = None
        self.is_animating = False

        self.has_moved = {
            'white_king': False, 'white_rook_left': False, 'white_rook_right': False,
            'black_king': False, 'black_rook_left': False, 'black_rook_right': False
        }

        self.setup_ui()
        self.reset_game(record_abandoned=False)
        self.sync_player_roles()

    def is_flipped(self):
        """Membalik tampilan jika pemain mengendalikan bidak Hitam"""
        return self.player_color == "black"

    def board_to_screen(self, r, c):
        """Konversi baris/kolom papan catur ke posisi layar"""
        if self.is_flipped():
            return 7 - r, 7 - c
        return r, c

    def screen_to_board(self, sr, sc):
        """Konversi klik layar ke baris/kolom papan catur"""
        if self.is_flipped():
            return 7 - sr, 7 - sc
        return sr, sc

    def sync_player_roles(self, event=None):
        mode = self.mode_var.get()
        if "Manusia (Putih) vs Bot (Hitam)" in mode:
            self.player_color = "white"
            self.bot_color = "black"
            self.lbl_white_status.configure(text="PUTIH : PLAYER (ANDA)")
            self.lbl_black_status.configure(text="HITAM : BOT AI")
        elif "Bot (Putih) vs Manusia (Hitam)" in mode:
            self.player_color = "black"
            self.bot_color = "white"
            self.lbl_white_status.configure(text="PUTIH : BOT AI")
            self.lbl_black_status.configure(text="HITAM : PLAYER (ANDA)")
        else:
            self.player_color = "both"
            self.bot_color = None
            self.lbl_white_status.configure(text="PUTIH : PEMAIN 1")
            self.lbl_black_status.configure(text="HITAM : PEMAIN 2")
        self.update_turn_badges()
        self.draw_board()

    def update_turn_badges(self):
        if not self.game_active:
            self.lbl_white_turn.pack_forget()
            self.lbl_black_turn.pack_forget()
            self.lbl_white_dot.configure(fg="#64748b")
            self.lbl_black_dot.configure(fg="#64748b")
            return

        if self.turn == 'white':
            self.lbl_black_turn.pack_forget()
            self.lbl_white_turn.pack(side="right", padx=(4, 0))
            self.lbl_white_dot.configure(fg="#38bdf8")
            self.lbl_black_dot.configure(fg="#334155")
        else:
            self.lbl_white_turn.pack_forget()
            self.lbl_black_turn.pack(side="right", padx=(4, 0))
            self.lbl_black_dot.configure(fg="#ef4444")
            self.lbl_white_dot.configure(fg="#334155")

    def to_chess_notation(self, r, c):
        return f"{chr(ord('a') + c)}{8 - r}"

    def save_game_to_db(self, winner, reason):
        if self.game_recorded:
            return
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            query = """
                    INSERT INTO game_history (game_mode, winner, total_moves, status_reason)
                    VALUES (%s, %s, %s, %s)
                    """
            full_mode = f"{self.mode_var.get()} [{self.ai_level.get()}]"
            cursor.execute(query, (full_mode, winner, self.move_count, reason))
            conn.commit()
            cursor.close()
            conn.close()
            self.game_recorded = True
        except mysql.connector.Error as err:
            print(f"[DB ERROR] {err}")

    def save_move_to_db(self, move_num, player, piece, from_pos, to_pos):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            query = """
                    INSERT INTO chess_moves (move_number, player, piece, from_pos, to_pos)
                    VALUES (%s, %s, %s, %s, %s)
                    """
            cursor.execute(query, (move_num, player, piece, from_pos, to_pos))
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"[DB ERROR] {err}")

    def show_history_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Database Match History")
        popup.geometry("740x420")
        popup.configure(bg="#0b1120")
        popup.grab_set()

        header = tk.Label(popup, text="DATA RIWAYAT PERTANDINGAN (MYSQL)",
                          font=('Segoe UI', 12, 'bold'), fg="#38bdf8", bg="#0b1120")
        header.pack(pady=10)

        table_frame = tk.Frame(popup, bg="#0f172a")
        table_frame.pack(fill="both", expand=True, padx=15, pady=5)

        columns = ("id", "waktu", "mode", "pemenang", "langkah", "alasan")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        for col, title, w in [("id", "ID", 40), ("waktu", "Waktu", 130), ("mode", "Mode / Level", 220),
                              ("pemenang", "Pemenang", 90), ("langkah", "Langkah", 65), ("alasan", "Alasan", 120)]:
            tree.heading(col, text=title)
            tree.column(col, width=w, anchor="center" if col in ["id", "waktu", "pemenang", "langkah"] else "w")

        tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT id, played_at, game_mode, winner, total_moves, status_reason FROM game_history ORDER BY id DESC")
            for r in cursor.fetchall():
                tree.insert("", "end", values=(r[0], str(r[1]), r[2], r[3], r[4], r[5]))
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Gagal membaca dari database:\n{err}", parent=popup)

    def select_level(self, lvl):
        self.ai_level.set(lvl)
        self.update_level_cards()

    def update_level_cards(self):
        colors = {"Pemula": "#10b981", "Menengah": "#0284c7", "Master": "#ef4444"}
        active_lvl = self.ai_level.get()
        active_color = colors.get(active_lvl, "#38bdf8")

        for lvl, card in self.level_cards.items():
            card.delete("all")
            w, h = 260, 34
            if lvl == active_lvl:
                card.create_rectangle(1, 1, w - 1, h - 1, fill=active_color, outline="")
                card.create_text(16, h // 2, text="▶ " + lvl.upper(), anchor="w", font=('Segoe UI', 9, 'bold'), fill="#ffffff")
                card.create_text(w - 16, h // 2, text=self.level_stars[lvl], anchor="e", font=('Segoe UI', 9, 'bold'), fill="#ffffff")
            else:
                card.create_rectangle(1, 1, w - 1, h - 1, fill="#111827", outline="#1e293b")
                card.create_text(16, h // 2, text=lvl, anchor="w", font=('Segoe UI', 9), fill="#94a3b8")
                card.create_text(w - 16, h // 2, text=self.level_stars[lvl], anchor="e", font=('Segoe UI', 9), fill="#64748b")

    def change_theme(self, event=None):
        self.current_theme_name = self.theme_var.get()
        t = BOARD_THEMES[self.current_theme_name]
        self.board_container.configure(highlightbackground=t["border"])
        self.draw_board()

    def on_window_resize(self, event):
        if event.widget == self.board_container and not self.is_animating:
            w = self.board_container.winfo_width()
            h = self.board_container.winfo_height()
            dim = min(w, h) - 16
            if dim > 350:
                self.square_size = int((dim - 44) // 8)
                self.coord_margin = int((dim - (self.square_size * 8)) // 2)
                total_dim = self.square_size * 8 + self.coord_margin * 2
                self.canvas.config(width=total_dim, height=total_dim)
                self.draw_board()

    def setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)
        self.root.rowconfigure(0, weight=1)

        self.board_container = tk.Frame(self.root, bg="#0a0f1d", bd=0, padx=6, pady=6,
                                        highlightbackground=BOARD_THEMES[self.current_theme_name]["border"],
                                        highlightthickness=2)
        self.board_container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.board_container.bind("<Configure>", self.on_window_resize)

        total_dim = self.square_size * 8 + self.coord_margin * 2
        self.canvas = tk.Canvas(self.board_container, width=total_dim, height=total_dim,
                                bg="#060911", bd=0, highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        self.canvas.bind("<Button-1>", self.handle_canvas_click)

        hud = tk.Frame(self.root, bg="#0f172a", width=290, padx=16, pady=16,
                       highlightbackground="#1e293b", highlightthickness=1)
        hud.grid(row=0, column=1, sticky="ns", padx=(0, 16), pady=16)

        tk.Label(hud, text="CHESS TEAM 2", font=('Impact', 18), fg="#38bdf8", bg="#0f172a").pack(anchor="w")
        tk.Label(hud, text="DYNAMIC SCALE MOTION", font=('Consolas', 8, 'bold'),
                 fg="#64748b", bg="#0f172a").pack(anchor="w", pady=(0, 8))

        tk.Label(hud, text="TEMA PAPAN:", font=('Segoe UI', 8, 'bold'), fg="#64748b", bg="#0f172a").pack(anchor="w")
        self.theme_var = tk.StringVar(value=self.current_theme_name)
        theme_cb = ttk.Combobox(hud, textvariable=self.theme_var, state="readonly",
                                values=list(BOARD_THEMES.keys()), font=('Segoe UI', 8))
        theme_cb.pack(fill="x", pady=(2, 8))
        theme_cb.bind("<<ComboboxSelected>>", self.change_theme)

        vs_box = tk.Frame(hud, bg="#070a13", padx=12, pady=10, highlightbackground="#1e293b", highlightthickness=1)
        vs_box.pack(fill="x", pady=(0, 10))

        row_w = tk.Frame(vs_box, bg="#070a13")
        row_w.pack(fill="x", pady=2)
        self.lbl_white_dot = tk.Label(row_w, text="■", font=('Segoe UI', 9, 'bold'), fg="#f8fafc", bg="#070a13")
        self.lbl_white_dot.pack(side="left", padx=(0, 6))
        self.lbl_white_status = tk.Label(row_w, text="PUTIH : PLAYER", font=('Segoe UI', 9, 'bold'),
                                         fg="#f8fafc", bg="#070a13")
        self.lbl_white_status.pack(side="left")
        self.lbl_white_turn = tk.Label(row_w, text="[GILIRAN]", font=('Consolas', 7, 'bold'),
                                       fg="#38bdf8", bg="#070a13")

        row_b = tk.Frame(vs_box, bg="#070a13")
        row_b.pack(fill="x", pady=2)
        self.lbl_black_dot = tk.Label(row_b, text="■", font=('Segoe UI', 9, 'bold'), fg="#475569", bg="#070a13")
        self.lbl_black_dot.pack(side="left", padx=(0, 6))
        self.lbl_black_status = tk.Label(row_b, text="HITAM : BOT AI", font=('Segoe UI', 9, 'bold'),
                                         fg="#94a3b8", bg="#070a13")
        self.lbl_black_status.pack(side="left")
        self.lbl_black_turn = tk.Label(row_b, text="[GILIRAN]", font=('Consolas', 7, 'bold'),
                                       fg="#ef4444", bg="#070a13")

        tk.Frame(vs_box, bg="#1e293b", height=1).pack(fill="x", pady=(6, 6))

        self.lbl_game_state = tk.Label(vs_box, text="STATUS: MENUNGGU MULAI", font=('Consolas', 9, 'bold'),
                                       fg="#facc15", bg="#070a13", anchor="w")
        self.lbl_game_state.pack(fill="x")

        tk.Label(hud, text="TINGKAT KESULITAN:", font=('Segoe UI', 8, 'bold'),
                 fg="#64748b", bg="#0f172a").pack(anchor="w", pady=(2, 2))

        self.level_stars = {"Pemula": "★☆☆", "Menengah": "★★☆", "Master": "★★★"}
        self.level_cards = {}
        for lvl in self.level_stars.keys():
            c = tk.Canvas(hud, height=34, width=250, bg="#0f172a", bd=0, highlightthickness=0, cursor="hand2")
            c.pack(fill="x", pady=2)
            c.bind("<Button-1>", lambda e, l=lvl: self.select_level(l))
            self.level_cards[lvl] = c

        self.update_level_cards()

        tk.Label(hud, text="LOG PERGERAKAN:", font=('Segoe UI', 8, 'bold'), fg="#64748b", bg="#0f172a").pack(anchor="w", pady=(6, 2))
        self.log_text = tk.Text(hud, height=5, width=28, bg="#070a13", fg="#38bdf8", font=('Consolas', 8), bd=0, padx=6, pady=6)
        self.log_text.pack(fill="x", pady=(0, 6))

        self.mode_var = tk.StringVar(value="Manusia (Putih) vs Bot (Hitam)")
        mode_cb = ttk.Combobox(hud, textvariable=self.mode_var, state="readonly", values=[
            "Manusia (Putih) vs Bot (Hitam)",
            "Bot (Putih) vs Manusia (Hitam)",
            "Dua Pemain (Tanpa Bot)"
        ], font=('Segoe UI', 8))
        mode_cb.pack(fill="x", pady=(0, 8))
        mode_cb.bind("<<ComboboxSelected>>", self.sync_player_roles)

        tk.Button(hud, text="▶ MULAI PERTANDINGAN", font=('Segoe UI', 9, 'bold'), bg="#0284c7", fg="#ffffff",
                  activebackground="#0ea5e9", bd=0, pady=7, cursor="hand2", command=self.start_game).pack(fill="x", pady=2)
        tk.Button(hud, text="↺ RESET PAPAN", font=('Segoe UI', 9, 'bold'), bg="#dc2626", fg="#ffffff",
                  activebackground="#ef4444", bd=0, pady=7, cursor="hand2", command=lambda: self.reset_game(record_abandoned=True)).pack(fill="x", pady=2)
        tk.Button(hud, text="📊 RIWAYAT PERTANDINGAN", font=('Segoe UI', 9, 'bold'), bg="#059669", fg="#ffffff",
                  activebackground="#10b981", bd=0, pady=7, cursor="hand2", command=self.show_history_popup).pack(fill="x", pady=2)

    def start_game(self):
        if self.is_animating: return
        self.sync_player_roles()
        self.game_active = True
        self.game_recorded = False
        self.move_count = 0
        self.turn = 'white'
        self.selected_pos = None
        self.valid_moves = []
        self.last_move = None
        self.status_message = "BERJALAN"
        self.lbl_game_state.configure(text=f"STATUS: {self.status_message}", fg="#10b981")
        self.update_turn_badges()
        self.has_moved = {k: False for k in self.has_moved}
        self.board_state = [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        ]
        self.log_text.delete('1.0', tk.END)
        self.draw_board()
        self.check_bot_turn()

    def reset_game(self, record_abandoned=False):
        if self.is_animating: return
        if record_abandoned and self.game_active and self.move_count > 0:
            self.save_game_to_db("Dibatalkan", "Reset sebelum selesai")

        self.game_active = False
        self.turn = 'white'
        self.selected_pos = None
        self.valid_moves = []
        self.last_move = None
        self.status_message = "DIRESET"
        self.lbl_game_state.configure(text=f"STATUS: {self.status_message}", fg="#ef4444")
        self.update_turn_badges()
        self.has_moved = {k: False for k in self.has_moved}
        self.board_state = [['.' for _ in range(8)] for _ in range(8)]
        if hasattr(self, 'log_text'):
            self.log_text.delete('1.0', tk.END)
        self.draw_board()

    def get_piece_color(self, piece):
        if piece == '.': return None
        return 'white' if piece.isupper() else 'black'

    def raw_moves(self, board, r, c):
        piece = board[r][c]
        moves = []
        if piece == '.': return moves
        color = self.get_piece_color(piece)

        if piece.lower() == 'p':
            direction = -1 if color == 'white' else 1
            start_row = 6 if color == 'white' else 1
            nr = r + direction
            if 0 <= nr < 8 and board[nr][c] == '.':
                moves.append((nr, c))
                if r == start_row and board[r + 2 * direction][c] == '.':
                    moves.append((r + 2 * direction, c))
            for dc in [-1, 1]:
                nc = c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = board[nr][nc]
                    if target != '.' and self.get_piece_color(target) != color:
                        moves.append((nr, nc))

        elif piece.lower() in ['r', 'b', 'q']:
            directions = []
            if piece.lower() in ['r', 'q']: directions += [(-1, 0), (1, 0), (0, -1), (0, 1)]
            if piece.lower() in ['b', 'q']: directions += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                while 0 <= nr < 8 and 0 <= nc < 8:
                    target = board[nr][nc]
                    if target == '.':
                        moves.append((nr, nc))
                    else:
                        if self.get_piece_color(target) != color: moves.append((nr, nc))
                        break
                    nr += dr
                    nc += dc

        elif piece.lower() == 'n':
            for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = board[nr][nc]
                    if target == '.' or self.get_piece_color(target) != color:
                        moves.append((nr, nc))

        elif piece.lower() == 'k':
            for dr, dc in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = board[nr][nc]
                    if target == '.' or self.get_piece_color(target) != color:
                        moves.append((nr, nc))
        return moves

    def is_under_attack(self, board, r, c, attacker_color):
        for row in range(8):
            for col in range(8):
                p = board[row][col]
                if p != '.' and self.get_piece_color(p) == attacker_color:
                    if (r, c) in self.raw_moves(board, row, col):
                        return True
        return False

    def find_king(self, board, color):
        target = 'K' if color == 'white' else 'k'
        for r in range(8):
            for c in range(8):
                if board[r][c] == target:
                    return (r, c)
        return None

    def is_in_check(self, board, color):
        k = self.find_king(board, color)
        if not k: return False
        opp = 'black' if color == 'white' else 'white'
        return self.is_under_attack(board, k[0], k[1], opp)

    def get_castling_moves(self, board, r, c):
        piece = board[r][c]
        if piece.lower() != 'k': return []
        color = self.get_piece_color(piece)
        opp = 'black' if color == 'white' else 'white'
        if self.is_in_check(board, color): return []

        castles = []
        if color == 'white' and r == 7 and c == 4:
            if not self.has_moved['white_king'] and not self.has_moved['white_rook_right']:
                if board[7][5] == '.' and board[7][6] == '.' and board[7][7] == 'R':
                    if not self.is_under_attack(board, 7, 5, opp) and not self.is_under_attack(board, 7, 6, opp):
                        castles.append((7, 6))
            if not self.has_moved['white_king'] and not self.has_moved['white_rook_left']:
                if board[7][3] == '.' and board[7][2] == '.' and board[7][1] == '.' and board[7][0] == 'R':
                    if not self.is_under_attack(board, 7, 3, opp) and not self.is_under_attack(board, 7, 2, opp):
                        castles.append((7, 2))
        elif color == 'black' and r == 0 and c == 4:
            if not self.has_moved['black_king'] and not self.has_moved['black_rook_right']:
                if board[0][5] == '.' and board[0][6] == '.' and board[0][7] == 'r':
                    if not self.is_under_attack(board, 0, 5, opp) and not self.is_under_attack(board, 0, 6, opp):
                        castles.append((0, 6))
            if not self.has_moved['black_king'] and not self.has_moved['black_rook_left']:
                if board[0][3] == '.' and board[0][2] == '.' and board[0][1] == '.' and board[0][0] == 'r':
                    if not self.is_under_attack(board, 0, 3, opp) and not self.is_under_attack(board, 0, 2, opp):
                        castles.append((0, 2))
        return castles

    def get_legal_moves(self, board, r, c, current_turn):
        piece = board[r][c]
        if piece == '.' or self.get_piece_color(piece) != current_turn: return []
        color = self.get_piece_color(piece)
        potential_moves = self.raw_moves(board, r, c)
        if piece.lower() == 'k' and board == self.board_state:
            potential_moves += self.get_castling_moves(board, r, c)

        legal = []
        for mr, mc in potential_moves:
            temp = [row[:] for row in board]
            temp[mr][mc] = temp[r][c]
            temp[r][c] = '.'
            if not self.is_in_check(temp, color):
                legal.append((mr, mc))
        return legal

    def get_all_legal_moves_for(self, board, color):
        all_moves = []
        for r in range(8):
            for c in range(8):
                if board[r][c] != '.' and self.get_piece_color(board[r][c]) == color:
                    for m in self.get_legal_moves(board, r, c, color):
                        all_moves.append(((r, c), m))
        return all_moves

    def has_any_legal_moves(self, color):
        return len(self.get_all_legal_moves_for(self.board_state, color)) > 0

    def execute_move(self, sr, sc, r, c):
        self.is_animating = True
        self.move_count += 1
        moving_piece = self.board_state[sr][sc]

        from_sq = self.to_chess_notation(sr, sc)
        to_sq = self.to_chess_notation(r, c)
        player_tag = "Putih" if self.turn == 'white' else "Hitam"

        self.save_move_to_db(self.move_count, player_tag, moving_piece.upper(), from_sq, to_sq)
        self.log_text.insert(tk.END, f"{self.move_count:02d}. [{player_tag[0]}] {moving_piece.upper()} {from_sq}->{to_sq}\n")
        self.log_text.see(tk.END)

        self.last_move = ((sr, sc), (r, c))

        scr_sr, scr_sc = self.board_to_screen(sr, sc)
        scr_r, scr_c = self.board_to_screen(r, c)

        start_x = self.coord_margin + scr_sc * self.square_size + self.square_size // 2
        start_y = self.coord_margin + scr_sr * self.square_size + self.square_size // 2
        target_x = self.coord_margin + scr_c * self.square_size + self.square_size // 2
        target_y = self.coord_margin + scr_r * self.square_size + self.square_size // 2

        self.board_state[sr][sc] = '.'
        self.draw_board()

        total_frames = 12
        frame_interval_ms = 16
        base_font = int(self.square_size * 0.58)

        def animate_step(frame=0):
            if frame <= total_frames:
                t = frame / total_frames
                ease_t = t * t * (3 - 2 * t)
                curr_x = start_x + (target_x - start_x) * ease_t
                curr_y = start_y + (target_y - start_y) * ease_t

                scale_lift = 4 * t * (1 - t)
                dynamic_font_size = int(base_font + (base_font * 0.15) * scale_lift)

                self.canvas.delete("moving_piece_anim")
                UnicodePieceRenderer.draw(self.canvas, curr_x, curr_y, moving_piece,
                                          font_size=dynamic_font_size, tag="moving_piece_anim")

                self.root.after(frame_interval_ms, lambda: animate_step(frame + 1))
            else:
                self.canvas.delete("moving_piece_anim")
                self.finalize_move(sr, sc, r, c, moving_piece)

        animate_step()

    def finalize_move(self, sr, sc, r, c, moving_piece):
        if moving_piece == 'P' and r == 0:
            moving_piece = 'Q'
        elif moving_piece == 'p' and r == 7:
            moving_piece = 'q'

        if moving_piece.lower() == 'k' and abs(c - sc) == 2:
            rook_from = 7 if c > sc else 0
            rook_to = 5 if c > sc else 3
            row_idx = 7 if self.turn == 'white' else 0
            self.board_state[row_idx][rook_to] = self.board_state[row_idx][rook_from]
            self.board_state[row_idx][rook_from] = '.'

        if moving_piece == 'K':
            self.has_moved['white_king'] = True
        elif moving_piece == 'k':
            self.has_moved['black_king'] = True
        elif moving_piece == 'R':
            if sr == 7 and sc == 0: self.has_moved['white_rook_left'] = True
            if sr == 7 and sc == 7: self.has_moved['white_rook_right'] = True
        elif moving_piece == 'r':
            if sr == 0 and sc == 0: self.has_moved['black_rook_left'] = True
            if sr == 0 and sc == 7: self.has_moved['black_rook_right'] = True

        self.board_state[r][c] = moving_piece
        self.turn = 'black' if self.turn == 'white' else 'white'
        self.selected_pos = None
        self.valid_moves = []
        self.is_animating = False

        self.update_game_state()
        self.update_turn_badges()
        self.draw_board()
        self.check_bot_turn()

    def update_game_state(self):
        current_color = self.turn
        opponent = 'black' if self.turn == 'white' else 'white'
        in_check = self.is_in_check(self.board_state, current_color)
        has_moves = self.has_any_legal_moves(current_color)

        if in_check and not has_moves:
            self.game_active = False
            self.status_message = f"SKAKMAT! {opponent.upper()} MENANG"
            self.save_game_to_db(opponent.capitalize(), "Skakmat")
        elif not in_check and not has_moves:
            self.game_active = False
            self.status_message = "REMIS (STALEMATE)"
            self.save_game_to_db("Remis", "Stalemate")
        elif in_check:
            self.status_message = "WARNING: SKAK (CHECK)!"
        else:
            self.status_message = "SEDANG BERJALAN"

        self.lbl_game_state.configure(text=f"STATUS: {self.status_message}")

    def handle_canvas_click(self, event):
        if not self.game_active or self.is_animating or self.turn == self.bot_color:
            return

        sc = (event.x - self.coord_margin) // self.square_size
        sr = (event.y - self.coord_margin) // self.square_size

        if not (0 <= sr < 8 and 0 <= sc < 8):
            return

        r, c = self.screen_to_board(sr, sc)

        piece = self.board_state[r][c]

        if self.selected_pos is None:
            if piece != '.' and self.get_piece_color(piece) == self.turn:
                self.selected_pos = (r, c)
                self.valid_moves = self.get_legal_moves(self.board_state, r, c, self.turn)
        else:
            sr_board, sc_board = self.selected_pos
            if (r, c) in self.valid_moves:
                self.execute_move(sr_board, sc_board, r, c)
                return
            else:
                if piece != '.' and self.get_piece_color(piece) == self.turn:
                    self.selected_pos = (r, c)
                    self.valid_moves = self.get_legal_moves(self.board_state, r, c, self.turn)
                else:
                    self.selected_pos = None
                    self.valid_moves = []

        self.draw_board()

    # --- BOT ENGINE MINIMAX ---

    def evaluate_board(self, board):
        score = 0
        for r in range(8):
            for c in range(8):
                p = board[r][c]
                if p == '.': continue
                score += PIECE_VALUES[p]
                if p == 'P': score += PAWN_TABLE[r][c]
                elif p == 'p': score -= PAWN_TABLE[7 - r][c]
                elif p == 'N': score += KNIGHT_TABLE[r][c]
                elif p == 'n': score -= KNIGHT_TABLE[7 - r][c]
                elif p == 'B': score += BISHOP_TABLE[r][c]
                elif p == 'b': score -= BISHOP_TABLE[7 - r][c]
        return score

    def minimax(self, board, depth, alpha, beta, is_maximizing):
        if depth == 0:
            return self.evaluate_board(board), None

        color = 'white' if is_maximizing else 'black'
        moves = self.get_all_legal_moves_for(board, color)

        if not moves:
            if self.is_in_check(board, color):
                return (-99999 if is_maximizing else 99999), None
            return 0, None

        best_move = random.choice(moves)

        if is_maximizing:
            max_eval = -999999
            for start, end in moves:
                temp = [row[:] for row in board]
                temp[end[0]][end[1]] = temp[start[0]][start[1]]
                temp[start[0]][start[1]] = '.'
                eval_score, _ = self.minimax(temp, depth - 1, alpha, beta, False)
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = (start, end)
                alpha = max(alpha, eval_score)
                if beta <= alpha: break
            return max_eval, best_move
        else:
            min_eval = 999999
            for start, end in moves:
                temp = [row[:] for row in board]
                temp[end[0]][end[1]] = temp[start[0]][start[1]]
                temp[start[0]][start[1]] = '.'
                eval_score, _ = self.minimax(temp, depth - 1, alpha, beta, True)
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = (start, end)
                beta = min(beta, eval_score)
                if beta <= alpha: break
            return min_eval, best_move

    def check_bot_turn(self):
        if self.game_active and not self.is_animating and self.turn == self.bot_color:
            self.root.after(300, self.make_bot_move)

    def make_bot_move(self):
        if not self.game_active or self.is_animating: return
        is_maximizing = (self.bot_color == 'white')
        current_lvl = self.ai_level.get()
        all_moves = self.get_all_legal_moves_for(self.board_state, self.bot_color)
        if not all_moves: return

        best_move = None
        if current_lvl == "Pemula":
            if random.random() < 0.60:
                best_move = random.choice(all_moves)
            else:
                _, best_move = self.minimax(self.board_state, depth=1, alpha=-999999, beta=999999, is_maximizing=is_maximizing)
        elif current_lvl == "Menengah":
            _, best_move = self.minimax(self.board_state, depth=2, alpha=-999999, beta=999999, is_maximizing=is_maximizing)
        elif current_lvl == "Master":
            _, best_move = self.minimax(self.board_state, depth=3, alpha=-999999, beta=999999, is_maximizing=is_maximizing)

        if best_move:
            (sr, sc), (r, c) = best_move
            self.execute_move(sr, sc, r, c)

    def draw_board(self):
        # Pengaman jika board_state belum terisi
        if not hasattr(self, 'board_state') or not self.board_state:
            return

        self.canvas.delete("all")
        theme = BOARD_THEMES[self.current_theme_name]
        total_board_size = self.square_size * 8

        self.canvas.create_rectangle(self.coord_margin - 2, self.coord_margin - 2,
                                     self.coord_margin + total_board_size + 2, self.coord_margin + total_board_size + 2,
                                     outline=theme["border"], width=3)

        flipped = self.is_flipped()
        files = ['h', 'g', 'f', 'e', 'd', 'c', 'b', 'a'] if flipped else ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        ranks = [str(i) for i in range(1, 9)] if flipped else [str(8 - i) for i in range(8)]

        font_coord_size = max(8, int(self.square_size * 0.12))
        for idx in range(8):
            pos = self.coord_margin + idx * self.square_size + self.square_size // 2
            self.canvas.create_text(pos, self.coord_margin // 2, text=files[idx].upper(),
                                    fill=theme["coord_fg"], font=('Segoe UI', font_coord_size, 'bold'))
            self.canvas.create_text(pos, self.coord_margin + total_board_size + (self.coord_margin // 2), text=files[idx].upper(),
                                    fill=theme["coord_fg"], font=('Segoe UI', font_coord_size, 'bold'))

            self.canvas.create_text(self.coord_margin // 2, pos, text=ranks[idx],
                                    fill=theme["coord_fg"], font=('Segoe UI', font_coord_size, 'bold'))
            self.canvas.create_text(self.coord_margin + total_board_size + (self.coord_margin // 2), pos, text=ranks[idx],
                                    fill=theme["coord_fg"], font=('Segoe UI', font_coord_size, 'bold'))

        king_in_check_pos = None
        if self.game_active and self.is_in_check(self.board_state, self.turn):
            king_in_check_pos = self.find_king(self.board_state, self.turn)

        piece_font_size = int(self.square_size * 0.58)

        for scr_r in range(8):
            for scr_c in range(8):
                r, c = self.screen_to_board(scr_r, scr_c)

                x1 = self.coord_margin + scr_c * self.square_size
                y1 = self.coord_margin + scr_r * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                is_light = (r + c) % 2 == 0
                bg_color = theme["light"] if is_light else theme["dark"]

                if self.last_move and ((r, c) == self.last_move[0] or (r, c) == self.last_move[1]):
                    bg_color = theme["last_light"] if is_light else theme["last_dark"]

                if self.selected_pos == (r, c):
                    bg_color = theme["selected"]

                if king_in_check_pos and (r, c) == king_in_check_pos:
                    bg_color = "#f87171"

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_color, width=0)

                if (r, c) in self.valid_moves:
                    target_piece = self.board_state[r][c]
                    cx = x1 + self.square_size // 2
                    cy = y1 + self.square_size // 2
                    marker_rad = max(5, int(self.square_size * 0.1))
                    if target_piece == '.':
                        self.canvas.create_oval(cx - marker_rad, cy - marker_rad, cx + marker_rad, cy + marker_rad,
                                                fill="#0284c7", outline="")
                    else:
                        self.canvas.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y2 - 2,
                                                     outline="#ef4444", width=3)

                piece = self.board_state[r][c]
                if piece != '.':
                    cx = x1 + self.square_size // 2
                    cy = y1 + self.square_size // 2
                    UnicodePieceRenderer.draw(self.canvas, cx, cy, piece, font_size=piece_font_size)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1024x720")
    root.resizable(True, True)

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TCombobox",
                    fieldbackground="#0f172a",
                    background="#1e293b",
                    foreground="#38bdf8",
                    arrowcolor="#38bdf8",
                    bordercolor="#334155")
    root.option_add('*TCombobox*Listbox.background', '#0f172a')
    root.option_add('*TCombobox*Listbox.foreground', '#ffffff')
    root.option_add('*TCombobox*Listbox.selectBackground', '#0284c7')
    root.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')

    game = SmoothChessGame(root)
    root.mainloop()

    # SERVER
    from flask import Flask, render_template
    from flask_socketio import SocketIO, join_room, emit

    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'kunci-rahasia-catur'
    socketio = SocketIO(app, cors_allowed_origins="*")

    # Menyimpan status kamar: {room_id: {'white': sid, 'black': sid}}
    rooms = {}


    @socketio.on('join_game')
    def handle_join(data):
        room = data['room']
        join_room(room)

        if room not in rooms:
            rooms[room] = {'players': [request.sid], 'names': [data.get('username', 'Player 1')]}
            emit('player_assigned', {'color': 'white', 'room': room})
        elif len(rooms[room]['players']) == 1:
            rooms[room]['players'].append(request.sid)
            emit('player_assigned', {'color': 'black', 'room': room})
            # Beritahu kedua pemain bahwa game siap dimulai
            emit('start_game', {'message': 'Game dimulai!'}, room=room)
        else:
            emit('room_full', {'message': 'Room sudah penuh! Pembaca saja.'})


    @socketio.on('make_move')
    def handle_move(data):
        room = data['room']
        # Teruskan langkah ke lawan di room yang sama
        emit('opponent_move', {
            'from': data['from'],
            'to': data['to'],
            'promotion': data.get('promotion', 'q')
        }, room=room, include_self=False)


    if __name__ == '__main__':
        socketio.run(app, host='0.0.0.0', port=5000)

        from flask import Flask, render_template
        from flask_socketio import SocketIO, join_room, emit

        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'kunci-rahasia-catur'
        socketio = SocketIO(app, cors_allowed_origins="*")

        # Menyimpan status kamar: {room_id: {'white': sid, 'black': sid}}
        rooms = {}


        @socketio.on('join_game')
        def handle_join(data):
            room = data['room']
            join_room(room)

            if room not in rooms:
                rooms[room] = {'players': [request.sid], 'names': [data.get('username', 'Player 1')]}
                emit('player_assigned', {'color': 'white', 'room': room})
            elif len(rooms[room]['players']) == 1:
                rooms[room]['players'].append(request.sid)
                emit('player_assigned', {'color': 'black', 'room': room})
                # Beritahu kedua pemain bahwa game siap dimulai
                emit('start_game', {'message': 'Game dimulai!'}, room=room)
            else:
                emit('room_full', {'message': 'Room sudah penuh! Pembaca saja.'})


        @socketio.on('make_move')
        def handle_move(data):
            room = data['room']
            # Teruskan langkah ke lawan di room yang sama
            emit('opponent_move', {
                'from': data['from'],
                'to': data['to'],
                'promotion': data.get('promotion', 'q')
            }, room=room, include_self=False)


        if __name__ == '__main__':
            socketio.run(app, host='0.0.0.0', port=5000)