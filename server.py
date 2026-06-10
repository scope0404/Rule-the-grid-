"""
# RULE THE GRID - Game Server
# Hosts the game over LAN. One player runs this,
# others connect via IP address.
"""

import socket
import threading
import json
import sqlite3
import random
import time
import os


# SERVER CONFIG

PORT = 5555
DB_PATH = os.path.join(os.path.dirname(__file__), "game.db")


# DATABASE SETUP

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        avatar TEXT,
        color TEXT,
        capital_x INTEGER,
        capital_y INTEGER,
        active INTEGER DEFAULT 1,
        powerups TEXT DEFAULT "[]",
        alliances TEXT DEFAULT "[]"
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS game_state (
        id INTEGER PRIMARY KEY DEFAULT 1,
        map_data TEXT,
        turn_order TEXT,
        current_turn INTEGER DEFAULT 0,
        phase TEXT DEFAULT "setup",
        winner TEXT DEFAULT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS moves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player TEXT,
        move_type TEXT,
        x INTEGER,
        y INTEGER,
        timestamp TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS territory (
        x INTEGER,
        y INTEGER,
        owner TEXT,
        tile_type TEXT,
        powerup TEXT DEFAULT NULL,
        PRIMARY KEY (x, y)
    )''')

    conn.commit()
    conn.close()

# MAP GENERATION

GRID_W = 40
GRID_H = 30

# Power-up types matching the handwritten notes
POWERUPS = [
    {"id": "multiplication_land", "name": "Multiplication Rate on Land",
     "symbol": "✕", "color": (255, 165, 0), "desc": "Multiplies your expansion rate on land"},
    {"id": "multiplication",      "name": "Multiplication Rate",
     "symbol": "×", "color": (255, 140, 0), "desc": "General multiplication of territory rate"},
    {"id": "border_dur",          "name": "Border Durability",
     "symbol": "🛡", "color": (100, 200, 100), "desc": "Allowed to cross any medium (ignore free)"},
    {"id": "sorcerers_tower",     "name": "Sorcerer's Tower",
     "symbol": "🗼", "color": (180, 0, 255), "desc": "Create 2 outposts anywhere; cross water at the black rate anytime (ignore range)"},
    {"id": "mountain_range",      "name": "Mountain Range",
     "symbol": "⛰", "color": (120, 100, 80), "desc": "Units cannot pass blocks covered by mountains"},
    {"id": "the_shore",           "name": "The Shore",
     "symbol": "🌊", "color": (0, 180, 220), "desc": "No fighting but capital cannot be placed there"},
    {"id": "mines_mogul",         "name": "Mines Mogul",
     "symbol": "⛏", "color": (200, 180, 50), "desc": "Place 10 squares in one straight line in any direction (once, from Mines)"},
    {"id": "mount_doom",          "name": "Mount Doom",
     "symbol": "🌋", "color": (220, 60, 20), "desc": "Each square of someone who has Magceas rule is worth 2 squares"},
    {"id": "sunder",              "name": "Sunder",
     "symbol": "⚡", "color": (255, 220, 0), "desc": "When attacked in war, summon an ally (6 blocks). Ready to carry out sorry calls"},
    {"id": "the_lonely_mountain", "name": "The Lonely Mountain",
     "symbol": "🏔", "color": (150, 130, 110), "desc": "Has OP position"},
    {"id": "rivendell",           "name": "Rivendell",
     "symbol": "🌿", "color": (80, 180, 80), "desc": "Enemies only multiply 1 square per turn"},
    {"id": "gold_goblin",         "name": "Gold Goblin",
     "symbol": "👺", "color": (220, 200, 0), "desc": "Allows double expansion in range"},
    {"id": "white_horse",         "name": "White Horse",
     "symbol": "🐴", "color": (240, 240, 240), "desc": "Allows you to drop 6 squares anywhere"},
    {"id": "outpost",             "name": "Outpost",
     "symbol": "🏰", "color": (180, 160, 140), "desc": "Allows ocean crossing from this point"},
]

POWERUP_IDS = [p["id"] for p in POWERUPS]

def generate_map():
    """Generate a random island map with ocean, land, mountains, shores."""
    grid = [["ocean"] * GRID_W for _ in range(GRID_H)]

    # Place several islands using random blob generation
    num_islands = random.randint(4, 7)
    islands = []

    for _ in range(num_islands):
        # Island seed
        cx = random.randint(5, GRID_W - 5)
        cy = random.randint(5, GRID_H - 5)
        size = random.randint(20, 60)
        land_cells = set()
        frontier = [(cx, cy)]
        while len(land_cells) < size and frontier:
            cell = random.choice(frontier)
            frontier.remove(cell)
            x, y = cell
            if 0 <= x < GRID_W and 0 <= y < GRID_H:
                land_cells.add((x, y))
                for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx, ny = x+dx, y+dy
                    if (nx, ny) not in land_cells and random.random() < 0.6:
                        frontier.append((nx, ny))
        islands.append(land_cells)
        for (x, y) in land_cells:
            grid[y][x] = "land"

    # Add shore tiles around coastlines
    for y in range(GRID_H):
        for x in range(GRID_W):
            if grid[y][x] == "ocean":
                for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny][nx] == "land":
                        grid[y][x] = "shore"
                        break

    # Add mountain clusters on land
    for _ in range(random.randint(3, 6)):
        mx = random.randint(2, GRID_W - 2)
        my = random.randint(2, GRID_H - 2)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                nx, ny = mx+dx, my+dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny][nx] == "land":
                    if random.random() < 0.6:
                        grid[ny][nx] = "mountain"

    # Place power-ups on land tiles
    land_tiles = [(x, y) for y in range(GRID_H) for x in range(GRID_W)
                  if grid[y][x] == "land"]
    random.shuffle(land_tiles)

    powerup_locations = {}
    for i, pid in enumerate(POWERUP_IDS):
        if i < len(land_tiles):
            px, py = land_tiles[i]
            powerup_locations[(px, py)] = pid

    return grid, powerup_locations


# GAME STATE (in-memory + DB sync)
class GameServer:
    def __init__(self):
        init_db()
        self.clients = {}      # addr -> socket
        self.players = {}      # username -> player dict
        self.turn_order = []
        self.current_turn = 0
        self.phase = "lobby"   # lobby -> setup -> playing -> ended
        self.grid = None
        self.powerup_locs = {}
        self.territory = {}    # (x,y) -> username
        self.moves_this_turn = 0
        self.war_this_turn = False
        self.lock = threading.Lock()

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()

    def broadcast(self, msg, exclude=None):
        data = (json.dumps(msg) + "\n").encode()
        dead = []
        for addr, sock in list(self.clients.items()):
            if addr == exclude:
                continue
            try:
                sock.sendall(data)
            except:
                dead.append(addr)
        for a in dead:
            self.clients.pop(a, None)

    def send_to(self, addr, msg):
        sock = self.clients.get(addr)
        if sock:
            try:
                sock.sendall((json.dumps(msg) + "\n").encode())
            except:
                pass

    def full_state(self):
        """Build complete game state to send to clients."""
        return {
            "type": "state",
            "phase": self.phase,
            "players": self.players,
            "turn_order": self.turn_order,
            "current_turn": self.current_turn,
            "grid": self.grid,
            "territory": {f"{k[0]},{k[1]}": v for k, v in self.territory.items()},
            "powerup_locs": {f"{k[0]},{k[1]}": v for k, v in self.powerup_locs.items()},
            "moves_this_turn": self.moves_this_turn,
            "war_this_turn": self.war_this_turn,
        }

    def handle_message(self, addr, msg):
        with self.lock:
            t = msg.get("type")

            # ---- JOIN / REGISTER ----
            if t == "join":
                username = msg["username"]
                avatar = msg.get("avatar", "default")
                colors = ["#e74c3c","#3498db","#2ecc71","#f39c12",
                          "#9b59b6","#1abc9c","#e67e22","#e91e63"]
                used = [p["color"] for p in self.players.values()]
                color = next((c for c in colors if c not in used), colors[0])
                self.players[username] = {
                    "username": username, "avatar": avatar,
                    "color": color, "capital": None,
                    "active": True, "powerups": [], "alliances": []
                }
                self.clients[addr] = self.clients.get(addr)
                # save addr->username mapping
                self.clients[addr + "_name"] = username
                self.broadcast({"type": "player_joined", "username": username, "players": self.players})
                self.send_to(addr, self.full_state())
                self._save_player(username)

            # ---- START GAME ----
            elif t == "start_game":
                if self.phase == "lobby" and len(self.players) >= 2:
                    self.grid, self.powerup_locs = generate_map()
                    self.turn_order = list(self.players.keys())
                    random.shuffle(self.turn_order)
                    self.current_turn = 0
                    self.phase = "setup"
                    self.moves_this_turn = 0
                    self.war_this_turn = False
                    self._save_map()
                    self.broadcast(self.full_state())

            # ---- PLACE CAPITAL ----
            elif t == "place_capital":
                username = msg["username"]
                x, y = msg["x"], msg["y"]
                if self._can_place_capital(username, x, y):
                    self.players[username]["capital"] = [x, y]
                    self.territory[(x, y)] = username
                    self._log_move(username, "capital", x, y)
                    # Check if all players placed capitals
                    all_placed = all(p["capital"] for p in self.players.values() if p["active"])
                    if all_placed:
                        self.phase = "playing"
                    self.broadcast(self.full_state())

            # ---- EXPAND TERRITORY ----
            elif t == "expand":
                username = msg["username"]
                x, y = msg["x"], msg["y"]
                current_player = self.turn_order[self.current_turn % len(self.turn_order)]
                if username == current_player and not self.war_this_turn:
                    tile = self.grid[y][x]
                    max_moves = 2 if tile in ("ocean", "shore") else 4
                    if self.moves_this_turn < max_moves and self._is_adjacent_to(username, x, y):
                        if (x, y) not in self.territory:
                            self.territory[(x, y)] = username
                            self.moves_this_turn += 1
                            # Check powerup
                            pu = self.powerup_locs.get((x, y))
                            if pu and pu not in self.players[username]["powerups"]:
                                self.players[username]["powerups"].append(pu)
                            self._log_move(username, "expand", x, y)
                            self.broadcast(self.full_state())

            # ---- END TURN ----
            elif t == "end_turn":
                username = msg["username"]
                current_player = self.turn_order[self.current_turn % len(self.turn_order)]
                if username == current_player:
                    self.current_turn += 1
                    self.moves_this_turn = 0
                    self.war_this_turn = False
                    # Skip eliminated players
                    while True:
                        cp = self.turn_order[self.current_turn % len(self.turn_order)]
                        if self.players[cp]["active"]:
                            break
                        self.current_turn += 1
                    self.broadcast(self.full_state())

            # ---- WAR ----
            elif t == "wage_war":
                username = msg["username"]
                target = msg["target"]
                x, y = msg["x"], msg["y"]
                current_player = self.turn_order[self.current_turn % len(self.turn_order)]
                if username == current_player and self.moves_this_turn == 0 and not self.war_this_turn:
                    own = sum(1 for v in self.territory.values() if v == username)
                    opp = sum(1 for v in self.territory.values() if v == target)
                    radius_own = sum(1 for (tx,ty),v in self.territory.items()
                                     if v == username and abs(tx-x)<=5 and abs(ty-y)<=5)
                    radius_opp = sum(1 for (tx,ty),v in self.territory.items()
                                     if v == target and abs(tx-x)<=5 and abs(ty-y)<=5)
                    self.war_this_turn = True
                    self.broadcast({
                        "type": "war_declared",
                        "attacker": username,
                        "defender": target,
                        "x": x, "y": y,
                        "attacker_odds": radius_own,
                        "defender_odds": radius_opp
                    })

            # ---- WAR RESULT ----
            elif t == "war_result":
                winner = msg["winner"]
                loser = msg["loser"]
                x, y = msg["x"], msg["y"]
                if (x, y) in self.territory:
                    self.territory[(x, y)] = winner
                # Check if loser's capital is taken
                loser_capital = self.players[loser].get("capital")
                if loser_capital and tuple(loser_capital) not in self.territory:
                    self.players[loser]["active"] = False
                    self.broadcast({"type": "player_eliminated", "username": loser})
                # Check win condition
                active = [p for p in self.players.values() if p["active"]]
                if len(active) == 1:
                    self.phase = "ended"
                    self.broadcast({"type": "game_over", "winner": active[0]["username"]})
                else:
                    # End turn after war
                    self.current_turn += 1
                    self.moves_this_turn = 0
                    self.war_this_turn = False
                    self.broadcast(self.full_state())

            # ---- ALLIANCE ----
            elif t == "alliance":
                a = msg["player1"]
                b = msg["player2"]
                if b not in self.players[a]["alliances"]:
                    self.players[a]["alliances"].append(b)
                if a not in self.players[b]["alliances"]:
                    self.players[b]["alliances"].append(a)
                self.broadcast({"type": "alliance_formed", "player1": a, "player2": b})
                self.broadcast(self.full_state())

            # ---- CHAT ----
            elif t == "chat":
                self.broadcast({"type": "chat",
                                 "sender": msg["sender"],
                                 "text": msg["text"]})

    def _can_place_capital(self, username, x, y):
        if self.grid[y][x] not in ("land",):
            return False
        if (x, y) in self.territory:
            return False
        # Must be 10+ blocks from powerups
        for (px, py) in self.powerup_locs:
            if abs(px - x) + abs(py - y) < 10:
                return False
        # Must be 10+ blocks from other capitals
        for p in self.players.values():
            if p["capital"]:
                cx, cy = p["capital"]
                if abs(cx - x) + abs(cy - y) < 10:
                    return False
        return True

    def _is_adjacent_to(self, username, x, y):
        """Check if (x,y) is adjacent to username's territory or ally's territory."""
        allies = self.players[username].get("alliances", [])
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            owner = self.territory.get((nx, ny))
            if owner == username or owner in allies:
                return True
        return False

    def _log_move(self, player, move_type, x, y):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO moves(player,move_type,x,y,timestamp) VALUES(?,?,?,?,?)",
                     (player, move_type, x, y, time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    def _save_player(self, username):
        p = self.players[username]
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''INSERT OR REPLACE INTO players(username,avatar,color)
                        VALUES(?,?,?)''',
                     (username, p["avatar"], p["color"]))
        conn.commit()
        conn.close()

    def _save_map(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM game_state")
        conn.execute("INSERT INTO game_state(id,map_data,turn_order,current_turn,phase) VALUES(1,?,?,?,?)",
                     (json.dumps(self.grid), json.dumps(self.turn_order),
                      self.current_turn, self.phase))
        conn.commit()
        conn.close()

    def handle_client(self, conn, addr):
        buffer = ""
        while True:
            try:
                data = conn.recv(4096).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        msg = json.loads(line)
                        self.handle_message(addr, msg)
            except Exception as e:
                break
        conn.close()
        self.clients.pop(addr, None)

    def run(self):
        ip = self.get_local_ip()
        print(f"\n{'='*45}")
        print(f"  RULE THE GRID - Server Started")
        print(f"  Host IP: {ip}:{PORT}")
        print(f"  Share this IP with other players!")
        print(f"{'='*45}\n")

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("0.0.0.0", PORT))
        server_sock.listen(8)

        while True:
            conn, addr = server_sock.accept()
            addr_str = f"{addr[0]}:{addr[1]}"
            self.clients[addr_str] = conn
            print(f"[+] Player connected: {addr_str}")
            t = threading.Thread(target=self.handle_client, args=(conn, addr_str), daemon=True)
            t.start()


if __name__ == "__main__":
    gs = GameServer()
    gs.run()
