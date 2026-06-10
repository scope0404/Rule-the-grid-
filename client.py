
import pygame
import socket
import threading
import json
import sys
import os
import random
import math


SCREEN_W, SCREEN_H = 1280, 800
CELL_SIZE = 36
PORT = 5555
FPS = 60


LIGHT = {
    "bg":         (240, 242, 245),
    "sidebar":    (45,  175, 225),
    "sidebar2":   (30,  150, 200),
    "panel":      (45,  175, 225),
    "panel2":     (30,  150, 200),
    "ocean":      (100, 170, 220),
    "land":       (195, 215, 150),
    "mountain":   (160, 140, 110),
    "shore":      (220, 210, 160),
    "grid_line":  (100, 100, 110),
    "text":       (20,  20,  20),
    "text_light": (255, 255, 255),
    "btn":        (45,  175, 225),
    "btn_hover":  (30,  150, 200),
    "war_bg":     (200, 50,  50),
    "title_orange": (255, 140, 0),
}

DARK = {
    "bg":         (18,  18,  18),
    "sidebar":    (35,  35,  38),
    "sidebar2":   (28,  28,  30),
    "panel":      (45,  45,  50),
    "panel2":     (35,  35,  40),
    "ocean":      (15,  40,  80),
    "land":       (40,  70,  30),
    "mountain":   (60,  55,  50),
    "shore":      (70,  65,  45),
    "grid_line":  (80,  80,  90),
    "text":       (230, 230, 230),
    "text_light": (255, 255, 255),
    "btn":        (55,  55,  65),
    "btn_hover":  (75,  75,  85),
    "war_bg":     (150, 30,  30),
    "title_orange": (255, 140, 0),
}

# Power-up definitions (mirrored from server)
POWERUPS = [
    {"id": "multiplication_land",  "name": "Multiplication Rate on Land",   "symbol": "X",  "color": (255, 165,   0)},
    {"id": "multiplication",       "name": "Multiplication Rate",            "symbol": "×",  "color": (255, 140,   0)},
    {"id": "border_dur",           "name": "Border Durability",             "symbol": "B",  "color": (100, 200, 100)},
    {"id": "sorcerers_tower",      "name": "Sorcerer's Tower",              "symbol": "T",  "color": (180,   0, 255)},
    {"id": "mountain_range",       "name": "Mountain Range",                "symbol": "M",  "color": (120, 100,  80)},
    {"id": "the_shore",            "name": "The Shore",                     "symbol": "S",  "color": (  0, 180, 220)},
    {"id": "mines_mogul",          "name": "Mines Mogul",                   "symbol": "⛏",  "color": (200, 180,  50)},
    {"id": "mount_doom",           "name": "Mount Doom",                    "symbol": "D",  "color": (220,  60,  20)},
    {"id": "sunder",               "name": "Sunder",                        "symbol": "Z",  "color": (255, 220,   0)},
    {"id": "the_lonely_mountain",  "name": "The Lonely Mountain",           "symbol": "L",  "color": (150, 130, 110)},
    {"id": "rivendell",            "name": "Rivendell",                     "symbol": "R",  "color": ( 80, 180,  80)},
    {"id": "gold_goblin",          "name": "Gold Goblin",                   "symbol": "G",  "color": (220, 200,   0)},
    {"id": "white_horse",          "name": "White Horse",                   "symbol": "H",  "color": (240, 240, 240)},
    {"id": "outpost",              "name": "Outpost",                       "symbol": "O",  "color": (180, 160, 140)},
]
POWERUP_MAP = {p["id"]: p for p in POWERUPS}

POWERUP_DESCS = {
    "multiplication_land":  "Multiplies your expansion rate on land tiles.",
    "multiplication":       "Multiplies overall territory expansion rate.",
    "border_dur":           "Allowed to cross any medium (ignore movement penalty).",
    "sorcerers_tower":      "Create 2 outposts anywhere; cross water at black rate anytime.",
    "mountain_range":       "Units cannot pass blocks covered by mountains.",
    "the_shore":            "No fighting here, but capital cannot be placed on shore.",
    "mines_mogul":          "Place 10 squares in one straight line (once, from Mines).",
    "mount_doom":           "Each square of holder is worth 2 squares in war.",
    "sunder":               "When attacked in war, summon an ally within 6 blocks.",
    "the_lonely_mountain":  "Grants OP defensive position bonus.",
    "rivendell":            "Enemies can only expand 1 square per turn.",
    "gold_goblin":          "Allows double expansion range.",
    "white_horse":          "Allows you to drop 6 squares anywhere on the map.",
    "outpost":              "Allows ocean crossing from this point.",
}

AVATAR_COLORS = [
    (231, 76,  60),   # red
    (52,  152, 219),  # blue
    (46,  204, 113),  # green
    (243, 156,  18),  # orange
    (155, 89,  182),  # purple
    (26,  188, 156),  # teal
    (230, 126,  34),  # dark orange
    (233, 30,  99),   # pink
]

AVATARS = ["warrior", "wizard", "knight", "archer", "rogue", "paladin", "bard", "ranger"]


# NETWORK CLIENT

class NetworkClient:
    def __init__(self, host, username, callback):
        self.host = host
        self.username = username
        self.callback = callback
        self.sock = None
        self.connected = False
        self.buffer = ""

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, PORT))
            self.connected = True
            t = threading.Thread(target=self._recv_loop, daemon=True)
            t.start()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def send(self, msg):
        if self.connected:
            try:
                self.sock.sendall((json.dumps(msg) + "\n").encode())
            except:
                self.connected = False

    def _recv_loop(self):
        while self.connected:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                self.buffer += data
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if line.strip():
                        msg = json.loads(line)
                        self.callback(msg)
            except:
                break
        self.connected = False


# GAME SCREENS

class Screen:
    def __init__(self, game):
        self.game = game

    def handle_event(self, event): pass
    def update(self): pass
    def draw(self, surface): pass


# ---- LOGIN SCREEN ----
class LoginScreen(Screen):
    def __init__(self, game):
        super().__init__(game)
        self.username = ""
        self.server_ip = ""
        self.selected_avatar = 0
        self.active_field = None
        self.error = ""
        self.is_host = False
        self.fade_alpha = 0

    def handle_event(self, event):
        T = self.game.theme
        if event.type == pygame.KEYDOWN:
            if self.active_field == "username":
                if event.key == pygame.K_BACKSPACE:
                    self.username = self.username[:-1]
                elif event.key == pygame.K_TAB:
                    self.active_field = "ip"
                elif len(self.username) < 16 and event.unicode.isprintable():
                    self.username += event.unicode
            elif self.active_field == "ip":
                if event.key == pygame.K_BACKSPACE:
                    self.server_ip = self.server_ip[:-1]
                elif event.key == pygame.K_TAB:
                    self.active_field = "username"
                elif len(self.server_ip) < 20 and event.unicode.isprintable():
                    self.server_ip += event.unicode

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            W, H = SCREEN_W, SCREEN_H
            cx = W // 2

            # Click username field
            if cx - 160 <= mx <= cx + 160 and H//2 - 60 <= my <= H//2 - 30:
                self.active_field = "username"
            # Click IP field
            elif cx - 160 <= mx <= cx + 160 and H//2 + 10 <= my <= H//2 + 40:
                self.active_field = "ip"
            # Avatar arrows
            elif cx - 80 <= mx <= cx - 50 and H//2 + 60 <= my <= H//2 + 90:
                self.selected_avatar = (self.selected_avatar - 1) % len(AVATARS)
            elif cx + 50 <= mx <= cx + 80 and H//2 + 60 <= my <= H//2 + 90:
                self.selected_avatar = (self.selected_avatar + 1) % len(AVATARS)
            # Theme toggle
            elif W - 155 <= mx <= W - 10 and 8 <= my <= 36:
                self.game.toggle_theme()
            # Host button
            elif cx - 160 <= mx <= cx - 10 and H//2 + 120 <= my <= H//2 + 155:
                self._try_connect(host=True)
            # Join button
            elif cx + 10 <= mx <= cx + 160 and H//2 + 120 <= my <= H//2 + 155:
                self._try_connect(host=False)

    def _try_connect(self, host):
        if not self.username.strip():
            self.error = "Please enter a username!"
            return
        if not host and not self.server_ip.strip():
            self.error = "Please enter the host's IP!"
            return
        self.error = ""
        if host:
            import subprocess
            import sys
            server_path = os.path.join(os.path.dirname(__file__), "..", "server", "server.py")
            subprocess.Popen([sys.executable, server_path],
                             creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            import time; time.sleep(3)
            ip = "127.0.0.1"
        else:
            ip = self.server_ip.strip()

        net = NetworkClient(ip, self.username, self.game.on_network_message)
        if net.connect():
            self.game.net = net
            self.game.my_username = self.username
            self.game.my_avatar = AVATARS[self.selected_avatar]
            net.send({"type": "join", "username": self.username,
                      "avatar": AVATARS[self.selected_avatar]})
            self.game.set_screen("lobby")
        else:
            self.error = "Could not connect! Check IP and that server is running."

    def draw(self, surface):
        T = self.game.theme
        surface.fill(T["bg"])
        W, H = SCREEN_W, SCREEN_H
        cx = W // 2

        # Background grid pattern
        for x in range(0, W, 40):
            pygame.draw.line(surface, (*T["grid_line"], 40), (x, 0), (x, H), 1)
        for y in range(0, H, 40):
            pygame.draw.line(surface, (*T["grid_line"], 40), (0, y), (W, y), 1)

        # Title
        title1 = self.game.font_xl.render("RULE", True, T["title_orange"])
        title2 = self.game.font_lg.render("The Grid", True, T["text"])
        surface.blit(title1, (cx - title1.get_width()//2, H//2 - 200))
        surface.blit(title2, (cx - title2.get_width()//2, H//2 - 145))

        # Username field
        self._draw_field(surface, cx - 160, H//2 - 65, 320, 35,
                         self.username, "Username", self.active_field == "username")
        # IP field
        self._draw_field(surface, cx - 160, H//2 + 5, 320, 35,
                         self.server_ip, "Host IP (for joining)", self.active_field == "ip")

        # Avatar selection
        av_y = H//2 + 60
        av_color = AVATAR_COLORS[self.selected_avatar]
        pygame.draw.circle(surface, av_color, (cx, av_y + 15), 20)
        av_name = self.game.font_sm.render(AVATARS[self.selected_avatar].capitalize(), True, T["text"])
        surface.blit(av_name, (cx - av_name.get_width()//2, av_y + 40))
        # Arrows
        self._draw_btn(surface, cx - 80, av_y, 30, 30, "<")
        self._draw_btn(surface, cx + 50, av_y, 30, 30, ">")

        # Host / Join buttons
        self._draw_btn(surface, cx - 160, H//2 + 120, 148, 35, "HOST GAME")
        self._draw_btn(surface, cx + 10,  H//2 + 120, 148, 35, "JOIN GAME")

        # Error
        if self.error:
            err = self.game.font_sm.render(self.error, True, (220, 60, 60))
            surface.blit(err, (cx - err.get_width()//2, H//2 + 170))

        # Theme toggle button (top-right corner)
        theme_label = "☀  Light mode" if self.game.dark_mode else "🌙  Dark mode"
        pygame.draw.rect(surface, T["panel"], (W - 155, 8, 145, 28), border_radius=6)
        pygame.draw.rect(surface, T["text"], (W - 155, 8, 145, 28), border_radius=6, width=1)
        toggle_txt = self.game.font_sm.render(theme_label, True, T["text"])
        surface.blit(toggle_txt, (W - 148, 14))



    def _draw_field(self, surface, x, y, w, h, value, placeholder, active):
        T = self.game.theme
        color = T["btn_hover"] if active else T["panel"]
        pygame.draw.rect(surface, color, (x, y, w, h), border_radius=8)
        pygame.draw.rect(surface, T["sidebar"], (x, y, w, h), 2, border_radius=8)
        display = value if value else placeholder
        col = T["text_light"] if value else (*(min(c+80,255) for c in T["text"][:2]), T["text"][2])
        txt = self.game.font_sm.render(display, True, T["text_light"] if value else (150,150,150))
        surface.blit(txt, (x + 8, y + 8))
        if active and value:
            cx2 = x + 8 + self.game.font_sm.size(value)[0]
            pygame.draw.line(surface, T["text_light"], (cx2, y+6), (cx2, y+h-6), 2)

    def _draw_btn(self, surface, x, y, w, h, label):
        T = self.game.theme
        mx, my = pygame.mouse.get_pos()
        hov = x <= mx <= x+w and y <= my <= y+h
        pygame.draw.rect(surface, T["btn_hover"] if hov else T["btn"], (x,y,w,h), border_radius=8)
        txt = self.game.font_sm.render(label, True, T["text_light"])
        surface.blit(txt, (x + w//2 - txt.get_width()//2, y + h//2 - txt.get_height()//2))


# ---- LOBBY SCREEN ----
class LobbyScreen(Screen):
    def __init__(self, game):
        super().__init__(game)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            W, H = SCREEN_W, SCREEN_H
            cx = W // 2
            # Start game button (only visible if 2+ players)
            players = self.game.state.get("players", {})
            if len(players) >= 2:
                if cx - 100 <= mx <= cx + 100 and H - 100 <= my <= H - 60:
                    self.game.net.send({"type": "start_game"})

    def draw(self, surface):
        T = self.game.theme
        surface.fill(T["bg"])
        W, H = SCREEN_W, SCREEN_H
        cx = W // 2

        title = self.game.font_lg.render("RULE THE GRID — Lobby", True, T["title_orange"])
        surface.blit(title, (cx - title.get_width()//2, 60))

        sub = self.game.font_sm.render("Waiting for players to join...", True, T["text"])
        surface.blit(sub, (cx - sub.get_width()//2, 120))

        players = self.game.state.get("players", {})
        for i, (uname, pdata) in enumerate(players.items()):
            y = 180 + i * 60
            color = pygame.Color(pdata["color"])
            pygame.draw.circle(surface, color, (cx - 200, y + 18), 18)
            txt = self.game.font_md.render(f"{uname}  ({pdata['avatar']})", True, T["text"])
            surface.blit(txt, (cx - 170, y + 6))

        if len(players) >= 2:
            self._draw_btn(surface, cx - 100, H - 100, 200, 40, "START GAME")
        else:
            hint = self.game.font_sm.render("Need at least 2 players to start", True, (150,150,150))
            surface.blit(hint, (cx - hint.get_width()//2, H - 80))

        ip_txt = self.game.font_sm.render(f"Share your IP with friends to join!", True, (150,150,150))
        surface.blit(ip_txt, (cx - ip_txt.get_width()//2, H - 40))

    def _draw_btn(self, surface, x, y, w, h, label):
        T = self.game.theme
        mx, my = pygame.mouse.get_pos()
        hov = x <= mx <= x+w and y <= my <= y+h
        pygame.draw.rect(surface, T["btn_hover"] if hov else T["btn"], (x,y,w,h), border_radius=10)
        txt = self.game.font_md.render(label, True, T["text_light"])
        surface.blit(txt, (x + w//2 - txt.get_width()//2, y + h//2 - txt.get_height()//2))


# ---- MAIN GAME SCREEN ----
class GameScreen(Screen):
    def __init__(self, game):
        super().__init__(game)
        self.camera_x = 0
        self.camera_y = 0
        self.dragging = False
        self.drag_start = (0, 0)
        self.cam_start = (0, 0)
        self.show_rules = False
        self.show_powerups = False
        self.chat_input = ""
        self.chat_active = False
        self.chat_log = []
        self.war_popup = None       # dict with war data
        self.rps_choice = None
        self.zoom = 1.0

        # Setup capital placement mode
        self.placing_capital = False

    def _current_player(self):
        s = self.game.state
        to = s.get("turn_order", [])
        ct = s.get("current_turn", 0)
        players = s.get("players", {})
        if not to:
            return None
        while True:
            cp = to[ct % len(to)]
            if players.get(cp, {}).get("active", True):
                return cp
            ct += 1

    def _is_my_turn(self):
        return self._current_player() == self.game.my_username

    def _grid_to_screen(self, gx, gy):
        cs = int(CELL_SIZE * self.zoom)
        sx = gx * cs - self.camera_x + 260
        sy = gy * cs - self.camera_y
        return sx, sy

    def _screen_to_grid(self, sx, sy):
        cs = int(CELL_SIZE * self.zoom)
        gx = (sx - 260 + self.camera_x) // cs
        gy = (sy + self.camera_y) // cs
        return int(gx), int(gy)

    def handle_event(self, event):
        s = self.game.state
        T = self.game.theme

        # War popup handling
        if self.war_popup:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                W, H = SCREEN_W, SCREEN_H
                cx, cy = W//2, H//2
                # RPS buttons
                choices = ["Rock", "Paper", "Scissors"]
                for i, ch in enumerate(choices):
                    bx = cx - 150 + i * 100
                    if bx <= mx <= bx+90 and cy+20 <= my <= cy+55:
                        self._resolve_rps(ch.lower())
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            W, H = SCREEN_W, SCREEN_H

            # Theme toggle
            if W - 155 <= mx <= W - 10 and 8 <= my <= 36:
                self.game.toggle_theme()
                return

            # Rules button (top-left sidebar icon area)
            if 5 <= mx <= 55 and 10 <= my <= 60:
                self.show_rules = not self.show_rules
                self.show_powerups = False
                return

            # Power-ups list button
            if 5 <= mx <= 55 and 70 <= my <= 120:
                self.show_powerups = not self.show_powerups
                self.show_rules = False
                return

            # Close overlay panels
            if self.show_rules or self.show_powerups:
                self.show_rules = False
                self.show_powerups = False
                return

            # Chat area
            if 260 <= mx <= 500 and H - 40 <= my <= H - 5:
                self.chat_active = not self.chat_active
                return

            # End turn button
            if W - 160 <= mx <= W - 10 and H - 55 <= my <= H - 15:
                if self._is_my_turn():
                    self.game.net.send({"type": "end_turn",
                                        "username": self.game.my_username})
                return

            # Map click
            if mx > 260:
                gx, gy = self._screen_to_grid(mx, my)
                grid = s.get("grid", [])
                if not grid or not (0 <= gy < len(grid) and 0 <= gx < len(grid[0])):
                    return

                phase = s.get("phase", "")
                territory = {tuple(int(v) for v in k.split(",")): val
                             for k, val in s.get("territory", {}).items()}
                powerup_locs = {tuple(int(v) for v in k.split(",")): val
                                for k, val in s.get("powerup_locs", {}).items()}

                # Setup phase: place capital
                if phase == "setup":
                    me = s["players"].get(self.game.my_username, {})
                    if not me.get("capital"):
                        self.game.net.send({
                            "type": "place_capital",
                            "username": self.game.my_username,
                            "x": gx, "y": gy
                        })
                    return

                # Playing phase
                if phase == "playing" and self._is_my_turn():
                    owner = territory.get((gx, gy))
                    if owner and owner != self.game.my_username:
                        # War option if adjacent
                        me_adj = any(
                            territory.get((gx+dx, gy+dy)) == self.game.my_username
                            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]
                        )
                        if me_adj and s.get("moves_this_turn", 0) == 0 and not s.get("war_this_turn"):
                            self.game.net.send({
                                "type": "wage_war",
                                "username": self.game.my_username,
                                "target": owner,
                                "x": gx, "y": gy
                            })
                    elif not owner:
                        self.game.net.send({
                            "type": "expand",
                            "username": self.game.my_username,
                            "x": gx, "y": gy
                        })

            elif event.button == 3:
                # Right click drag init
                self.dragging = True
                self.drag_start = event.pos
                self.cam_start = (self.camera_x, self.camera_y)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3:
                self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                dx = event.pos[0] - self.drag_start[0]
                dy = event.pos[1] - self.drag_start[1]
                self.camera_x = self.cam_start[0] - dx
                self.camera_y = self.cam_start[1] - dy

        elif event.type == pygame.MOUSEWHEEL:
            self.zoom = max(0.5, min(2.0, self.zoom + event.y * 0.1))

        elif event.type == pygame.KEYDOWN:
            if self.chat_active:
                if event.key == pygame.K_RETURN:
                    if self.chat_input.strip():
                        self.game.net.send({"type": "chat",
                                            "sender": self.game.my_username,
                                            "text": self.chat_input})
                        self.chat_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.chat_input = self.chat_input[:-1]
                elif event.unicode.isprintable() and len(self.chat_input) < 60:
                    self.chat_input += event.unicode
            else:
                # Camera pan with arrow keys
                speed = 20
                if event.key == pygame.K_LEFT:  self.camera_x -= speed
                if event.key == pygame.K_RIGHT: self.camera_x += speed
                if event.key == pygame.K_UP:    self.camera_y -= speed
                if event.key == pygame.K_DOWN:  self.camera_y += speed

    def on_war_declared(self, data):
        self.war_popup = data

    def _resolve_rps(self, choice):
        if not self.war_popup:
            return
        wp = self.war_popup
        # Simple AI or wait for other player — for now: server-side random
        import random
        opp_choice = random.choice(["rock", "paper", "scissors"])
        beats = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

        if beats[choice] == opp_choice:
            winner = wp["attacker"]
            loser  = wp["defender"]
        elif beats[opp_choice] == choice:
            winner = wp["defender"]
            loser  = wp["attacker"]
        else:
            winner = wp["attacker"]  # tie goes to attacker
            loser  = wp["defender"]

        self.game.net.send({
            "type": "war_result",
            "winner": winner,
            "loser": loser,
            "x": wp["x"],
            "y": wp["y"]
        })
        self.war_popup = None

    def draw(self, surface):
        T = self.game.theme
        s = self.game.state
        W, H = SCREEN_W, SCREEN_H

        surface.fill(T["bg"])

        # ---- Draw Map ----
        self._draw_map(surface)

        # ---- Left Sidebar ----
        pygame.draw.rect(surface, T["sidebar"], (0, 0, 255, H))
        # Gradient effect
        for i in range(10):
            alpha_rect = pygame.Surface((5, H), pygame.SRCALPHA)
            alpha_rect.fill((0, 0, 0, 20))
            surface.blit(alpha_rect, (250 + i, 0))

        # Logo
        logo1 = self.game.font_lg.render("RULE", True, T["title_orange"])
        logo2 = self.game.font_md.render("The Grid", True, T["text_light"])
        surface.blit(logo1, (15, 15))
        surface.blit(logo2, (15, 55))

        # Rules icon button
        self._draw_icon_btn(surface, 5, 10, 50, 50, "📋", "Rules")
        # Power-ups list button
        self._draw_icon_btn(surface, 5, 70, 50, 50, "⚡", "Power-Ups")

        # Player list
        players = s.get("players", {})
        turn_order = s.get("turn_order", [])
        current_turn = s.get("current_turn", 0)
        y_offset = 145
        header = self.game.font_sm.render("PLAYERS", True, T["text_light"])
        surface.blit(header, (10, y_offset))
        y_offset += 22

        for i, uname in enumerate(turn_order or list(players.keys())):
            pdata = players.get(uname, {})
            if not pdata:
                continue
            is_current = (turn_order and uname == turn_order[current_turn % len(turn_order)])
            bg = T["sidebar2"] if not is_current else T["btn_hover"]
            pygame.draw.rect(surface, bg, (5, y_offset, 243, 38), border_radius=6)
            if is_current:
                pygame.draw.rect(surface, T["title_orange"], (5, y_offset, 4, 38), border_radius=3)
            try:
                col = pygame.Color(pdata["color"])
            except:
                col = (200, 200, 200)
            pygame.draw.circle(surface, col, (22, y_offset + 19), 10)
            name_txt = self.game.font_sm.render(
                uname[:14] + ("" if len(uname)<=14 else ".."), True, T["text_light"])
            surface.blit(name_txt, (36, y_offset + 4))
            # Territory count
            terr_count = sum(1 for v in s.get("territory", {}).values() if v == uname)
            ct_txt = self.game.font_sm.render(str(terr_count), True, T["title_orange"])
            surface.blit(ct_txt, (220, y_offset + 10))
            # Alliance indicator
            my_allies = players.get(self.game.my_username, {}).get("alliances", [])
            if uname in my_allies:
                ally_txt = self.game.font_sm.render("✓", True, (100, 255, 100))
                surface.blit(ally_txt, (200, y_offset + 10))

            y_offset += 44

        # ---- Bottom Bar ----
        pygame.draw.rect(surface, T["panel"], (260, H - 80, W - 260, 80))

        # Last played
        to = s.get("turn_order", [])
        ct = s.get("current_turn", 0)
        if to and ct > 0:
            last = to[(ct - 1) % len(to)]
        else:
            last = "—"
        pygame.draw.rect(surface, T["panel2"], (270, H - 75, 200, 68), border_radius=10)
        lp1 = self.game.font_sm.render("last played", True, T["text_light"])
        lp2 = self.game.font_md.render(last[:14], True, T["text_light"])
        surface.blit(lp1, (370 - lp1.get_width()//2, H - 68))
        surface.blit(lp2, (370 - lp2.get_width()//2, H - 45))

        # Current user profile
        me = players.get(self.game.my_username, {})
        pygame.draw.rect(surface, T["panel2"], (480, H - 75, 280, 68), border_radius=10)
        try:
            me_col = pygame.Color(me.get("color", "#888888"))
        except:
            me_col = (136, 136, 136)
        pygame.draw.circle(surface, me_col, (510, H - 41), 20)
        un_txt = self.game.font_md.render(self.game.my_username[:14], True, T["text_light"])
        ep_txt = self.game.font_sm.render("Edit profile", True, (200, 200, 200))
        surface.blit(un_txt, (540, H - 60))
        surface.blit(ep_txt, (540, H - 36))

        # Moves left
        moves_left_val = 4 - s.get("moves_this_turn", 0)
        pygame.draw.rect(surface, T["panel2"], (775, H - 75, 220, 68), border_radius=10)
        ml1 = self.game.font_sm.render("Moves left", True, T["text_light"])
        ml2 = self.game.font_xl.render(str(max(0, moves_left_val)), True, T["text_light"])
        surface.blit(ml1, (830, H - 65))
        surface.blit(ml2, (900, H - 68))

        # End turn button
        if self._is_my_turn() and s.get("phase") == "playing":
            pygame.draw.rect(surface, (200, 60, 60), (W - 160, H - 55, 148, 40), border_radius=10)
            et = self.game.font_sm.render("END TURN", True, (255,255,255))
            surface.blit(et, (W - 160 + 74 - et.get_width()//2, H - 43))

        # Chat
        self._draw_chat(surface)

        # Phase indicator
        phase = s.get("phase", "")
        if phase == "setup":
            me_data = players.get(self.game.my_username, {})
            if not me_data.get("capital"):
                hint = self.game.font_md.render("Click on a LAND tile to place your Capital!", True, T["title_orange"])
                pygame.draw.rect(surface, T["sidebar"], (W//2 - hint.get_width()//2 - 10,
                                                          40, hint.get_width()+20, 36), border_radius=8)
                surface.blit(hint, (W//2 - hint.get_width()//2, 46))

        # Whose turn indicator
        if phase == "playing":
            cp = self._current_player()
            col_str = players.get(cp, {}).get("color", "#888")
            try:
                cp_col = pygame.Color(col_str)
            except:
                cp_col = (136,136,136)
            turn_label = "YOUR TURN!" if cp == self.game.my_username else cp + "'s turn"
            turn_txt = self.game.font_md.render(turn_label, True,
                (255,255,100) if cp == self.game.my_username else T["text_light"])
            bg_w = turn_txt.get_width() + 20
            pygame.draw.rect(surface, cp_col,
                             (W//2 - bg_w//2, 5, bg_w, 30), border_radius=6)
            surface.blit(turn_txt, (W//2 - turn_txt.get_width()//2, 8))

        # Theme toggle button (drawn to match click zone: W-160 to W-10, y 10-40)
        theme_label = "☀  Light mode" if self.game.dark_mode else "🌙  Dark mode"
        pygame.draw.rect(surface, T["panel"], (W - 155, 8, 145, 28), border_radius=6)
        pygame.draw.rect(surface, T["text"], (W - 155, 8, 145, 28), border_radius=6, width=1)
        toggle_txt = self.game.font_sm.render(theme_label, True, T["text"])
        surface.blit(toggle_txt, (W - 148, 14))

        # ---- Overlays ----
        if self.show_rules:
            self._draw_rules_panel(surface)
        elif self.show_powerups:
            self._draw_powerups_panel(surface)
        elif self.war_popup:
            self._draw_war_popup(surface)

        # Game over
        if s.get("phase") == "ended":
            self._draw_game_over(surface)

    def _draw_map(self, surface):
        s = self.game.state
        T = self.game.theme
        grid = s.get("grid", [])
        if not grid:
            return
        territory = {tuple(int(v) for v in k.split(",")): val
                     for k, val in s.get("territory", {}).items()}
        powerup_locs = {tuple(int(v) for v in k.split(",")): val
                        for k, val in s.get("powerup_locs", {}).items()}
        players = s.get("players", {})
        cs = int(CELL_SIZE * self.zoom)
        map_rect = pygame.Rect(260, 0, SCREEN_W - 260, SCREEN_H - 80)
        surface.set_clip(map_rect)

        TILE_COLORS = {
            "ocean":    T["ocean"],
            "land":     T["land"],
            "mountain": T["mountain"],
            "shore":    T["shore"],
        }

        for gy, row in enumerate(grid):
            for gx, tile in enumerate(row):
                sx, sy = self._grid_to_screen(gx, gy)
                if sx + cs < 260 or sx > SCREEN_W or sy + cs < 0 or sy > SCREEN_H - 80:
                    continue
                base = TILE_COLORS.get(tile, T["ocean"])
                owner = territory.get((gx, gy))
                if owner:
                    try:
                        pcol = pygame.Color(players[owner]["color"])
                        r = int(pcol.r * 0.6 + base[0] * 0.4)
                        g = int(pcol.g * 0.6 + base[1] * 0.4)
                        b = int(pcol.b * 0.6 + base[2] * 0.4)
                        draw_col = (r, g, b)
                    except:
                        draw_col = base
                else:
                    draw_col = base
                pygame.draw.rect(surface, draw_col, (sx, sy, cs, cs))
                pygame.draw.rect(surface, T["grid_line"], (sx, sy, cs, cs), 1)

                # Capital star
                cap_owners = [p for p in players.values() if p.get("capital") == [gx, gy]]
                if cap_owners:
                    try:
                        sc = pygame.Color(cap_owners[0]["color"])
                    except:
                        sc = (255, 255, 0)
                    mid = cs // 2
                    self._draw_star(surface, sx + mid, sy + mid, int(cs * 0.35), sc)

                # Power-up symbol
                pu = powerup_locs.get((gx, gy))
                if pu and cs >= 12:
                    pu_data = POWERUP_MAP.get(pu)
                    if pu_data:
                        pu_surf = self.game.font_sm.render(pu_data["symbol"], True, pu_data["color"])
                        surface.blit(pu_surf, (sx + cs//2 - pu_surf.get_width()//2,
                                               sy + cs//2 - pu_surf.get_height()//2))

        surface.set_clip(None)

    def _draw_star(self, surface, cx, cy, r, color):
        points = []
        for i in range(10):
            angle = math.pi / 5 * i - math.pi / 2
            rad = r if i % 2 == 0 else r // 2
            points.append((cx + rad * math.cos(angle), cy + rad * math.sin(angle)))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, (255, 255, 255), points, 1)

    def _draw_icon_btn(self, surface, x, y, w, h, icon, label):
        T = self.game.theme
        mx, my = pygame.mouse.get_pos()
        hov = x <= mx <= x+w and y <= my <= y+h
        col = T["sidebar2"] if not hov else T["btn_hover"]
        pygame.draw.rect(surface, col, (x, y, w, h), border_radius=8)
        icon_txt = self.game.font_md.render(icon, True, T["text_light"])
        surface.blit(icon_txt, (x + w//2 - icon_txt.get_width()//2,
                                y + h//2 - icon_txt.get_height()//2))

    def _draw_chat(self, surface):
        T = self.game.theme
        W, H = SCREEN_W, SCREEN_H
        # Chat log (small, bottom left of map area)
        chat_x, chat_y = 265, H - 200
        for i, msg in enumerate(self.chat_log[-4:]):
            ct = self.game.font_sm.render(msg, True, T["text_light"])
            s2 = pygame.Surface((ct.get_width()+6, ct.get_height()+4), pygame.SRCALPHA)
            s2.fill((0,0,0,120))
            surface.blit(s2, (chat_x, chat_y + i*22))
            surface.blit(ct, (chat_x+3, chat_y + i*22 + 2))

        if self.chat_active:
            pygame.draw.rect(surface, T["panel"], (265, H-82, 200, 26), border_radius=5)
            ci = self.game.font_sm.render(self.chat_input or "Type message...", True, T["text_light"])
            surface.blit(ci, (270, H-78))

    def _draw_rules_panel(self, surface):
        T = self.game.theme
        W, H = SCREEN_W, SCREEN_H
        panel = pygame.Surface((W - 260, H - 80), pygame.SRCALPHA)
        panel.fill((*[int(c) for c in [T["bg"][0],T["bg"][1],T["bg"][2]]], 235))
        surface.blit(panel, (260, 0))

        title = self.game.font_lg.render("📋 RULES", True, T["title_orange"])
        surface.blit(title, (W//2 - title.get_width()//2, 20))

        rules = [
            "1. Each player starts by placing a Capital on a land tile.",
            "2. Capital must be 10+ squares from any power-up location.",
            "3. Capital must be 10+ squares from other capitals.",
            "4. On your turn: expand up to 4 squares on land, 2 on water.",
            "5. All new squares must connect to YOUR existing territory.",
            "6. You can also expand from an ally's territory.",
            "7. WAR: click an enemy tile adjacent to yours (0 moves used).",
            "8. War uses rock-paper-scissors. Winner claims that square.",
            "9. War counts as your full turn — next player goes after.",
            "10. If your CAPITAL is captured, you are ELIMINATED.",
            "11. Last player standing wins the game!",
            "12. Alliances: agree in chat, then expand from ally territory.",
        ]
        for i, rule in enumerate(rules):
            col = T["text"] if i % 2 == 0 else (*(max(c-20,0) for c in T["text"]),)
            r = self.game.font_sm.render(rule, True, col)
            surface.blit(r, (280, 80 + i * 32))

        close = self.game.font_sm.render("Click anywhere to close", True, (150,150,150))
        surface.blit(close, (W//2 - close.get_width()//2, H - 110))

    def _draw_powerups_panel(self, surface):
        T = self.game.theme
        W, H = SCREEN_W, SCREEN_H
        panel = pygame.Surface((W - 260, H - 80), pygame.SRCALPHA)
        panel.fill((*[int(c) for c in [T["bg"][0],T["bg"][1],T["bg"][2]]], 235))
        surface.blit(panel, (260, 0))

        title = self.game.font_lg.render("⚡ POWER-UP LOCATIONS", True, T["title_orange"])
        surface.blit(title, (W//2 - title.get_width()//2, 15))

        cols = 2
        col_w = (W - 280) // cols
        for i, pu in enumerate(POWERUPS):
            col = i % cols
            row = i // cols
            px = 270 + col * col_w
            py = 65 + row * 52

            pygame.draw.rect(surface, T["panel2"], (px, py, col_w - 10, 48), border_radius=8)
            sym = self.game.font_md.render(pu["symbol"], True, pu["color"])
            surface.blit(sym, (px + 8, py + 10))
            name_t = self.game.font_sm.render(pu["name"], True, T["text_light"])
            surface.blit(name_t, (px + 36, py + 5))
            desc_t = self.game.font_sm.render(POWERUP_DESCS.get(pu["id"], "")[:55], True, (180,180,180))
            surface.blit(desc_t, (px + 36, py + 26))

        close = self.game.font_sm.render("Click anywhere to close", True, (150,150,150))
        surface.blit(close, (W//2 - close.get_width()//2, H - 110))

    def _draw_war_popup(self, surface):
        T = self.game.theme
        W, H = SCREEN_W, SCREEN_H
        wp = self.war_popup
        # Dim background
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surface.blit(dim, (0, 0))

        cx, cy = W//2, H//2
        pw, ph = 440, 260
        pygame.draw.rect(surface, T["war_bg"], (cx-pw//2, cy-ph//2, pw, ph), border_radius=14)
        pygame.draw.rect(surface, T["title_orange"], (cx-pw//2, cy-ph//2, pw, ph), 3, border_radius=14)

        t1 = self.game.font_lg.render("⚔ WAR DECLARED!", True, (255,255,255))
        surface.blit(t1, (cx - t1.get_width()//2, cy - ph//2 + 15))

        t2 = self.game.font_md.render(
            f"{wp['attacker']} vs {wp['defender']}", True, (255,220,150))
        surface.blit(t2, (cx - t2.get_width()//2, cy - ph//2 + 60))

        t3 = self.game.font_sm.render(
            f"Odds — Attacker: {wp['attacker_odds']}  Defender: {wp['defender_odds']}",
            True, (230,230,230))
        surface.blit(t3, (cx - t3.get_width()//2, cy - ph//2 + 95))

        # Only show RPS to the attacker (or both — simplified)
        rps = self.game.font_sm.render("Choose your move:", True, (255,255,255))
        surface.blit(rps, (cx - rps.get_width()//2, cy - 20))

        choices = [("✊ Rock","rock"), ("✋ Paper","paper"), ("✌ Scissors","scissors")]
        for i, (label, _) in enumerate(choices):
            bx = cx - 150 + i * 100
            mx2, my2 = pygame.mouse.get_pos()
            hov = bx <= mx2 <= bx+90 and cy+20 <= my2 <= cy+55
            pygame.draw.rect(surface, (255,255,255) if hov else (200,200,200),
                             (bx, cy+20, 90, 35), border_radius=8)
            bt = self.game.font_sm.render(label, True, (30,30,30))
            surface.blit(bt, (bx+45 - bt.get_width()//2, cy+28))

    def _draw_game_over(self, surface):
        T = self.game.theme
        W, H = SCREEN_W, SCREEN_H
        s = self.game.state
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        surface.blit(dim, (0, 0))
        winner = s.get("winner", "Unknown")
        t1 = self.game.font_xl.render("🏆 GAME OVER", True, T["title_orange"])
        t2 = self.game.font_lg.render(f"{winner} RULES THE GRID!", True, (255, 255, 255))
        surface.blit(t1, (W//2 - t1.get_width()//2, H//2 - 80))
        surface.blit(t2, (W//2 - t2.get_width()//2, H//2 - 20))


# ----------------------------------------
# MAIN GAME CLASS
# ----------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
        pygame.display.set_caption("Rule The Grid")
        self.clock = pygame.time.Clock()

        self.dark_mode = False
        self.theme = LIGHT

        # Fonts
        pygame.font.init()
        self._load_fonts()

        self.net = None
        self.my_username = ""
        self.my_avatar = "warrior"
        self.state = {}
        self._msg_queue = []
        self._lock = threading.Lock()

        self.screens = {}
        self._build_screens()
        self.current_screen = "login"

    def _load_fonts(self):
        try:
            self.font_xl = pygame.font.SysFont("Impact", 52)
            self.font_lg = pygame.font.SysFont("Impact", 36)
            self.font_md = pygame.font.SysFont("Arial Bold", 20)
            self.font_sm = pygame.font.SysFont("Arial", 16)
        except:
            self.font_xl = pygame.font.Font(None, 52)
            self.font_lg = pygame.font.Font(None, 36)
            self.font_md = pygame.font.Font(None, 22)
            self.font_sm = pygame.font.Font(None, 18)

    def _build_screens(self):
        self.screens["login"] = LoginScreen(self)
        self.screens["lobby"] = LobbyScreen(self)
        self.screens["game"]  = GameScreen(self)

    def set_screen(self, name):
        self.current_screen = name

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme = DARK if self.dark_mode else LIGHT

    def on_network_message(self, msg):
        with self._lock:
            self._msg_queue.append(msg)

    def process_messages(self):
        with self._lock:
            msgs = self._msg_queue[:]
            self._msg_queue.clear()

        game_scr = self.screens.get("game")
        for msg in msgs:
            t = msg.get("type")
            if t == "state":
                self.state = msg
                if msg.get("phase") in ("setup", "playing", "ended"):
                    self.set_screen("game")
                elif msg.get("phase") == "lobby":
                    self.set_screen("lobby")
            elif t == "player_joined":
                self.state["players"] = msg["players"]
            elif t == "war_declared" and game_scr:
                game_scr.on_war_declared(msg)
            elif t == "chat" and game_scr:
                game_scr.chat_log.append(f"{msg['sender']}: {msg['text']}")
            elif t == "game_over":
                self.state["phase"] = "ended"
                self.state["winner"] = msg["winner"]
            elif t == "player_eliminated" and game_scr:
                game_scr.chat_log.append(f"💀 {msg['username']} has been ELIMINATED!")

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                    self.toggle_theme()
                else:
                    scr = self.screens.get(self.current_screen)
                    if scr:
                        scr.handle_event(event)

            self.process_messages()

            scr = self.screens.get(self.current_screen)
            if scr:
                scr.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()