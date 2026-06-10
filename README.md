## RULE THE GRID

A turn-based territory conquest game for 2–8 players over LAN.



📦 SETUP (do this once on every laptop)

1. Make sure Python 3.8+ is installed: https://python.org
2. Install the only dependency:
   ```
   pip install pygame
   ```
3. Download/copy this entire `rule_the_grid` folder onto each laptop.

HOW TO START A GAME

- Enter your username & pick an avatar
- Click **HOST GAME**
- A server window will open automatically
- Your IP address is printed in that window — **share it with friends**

 Every OTHER player:
```
python client/client.py
```
- Enter your username & pick an avatar
- Type the host's IP address in the "Host IP" field
- Click **JOIN GAME**



 GAME RULES

1. **Place your Capital** — click any land tile (must be 10+ squares from power-ups and other capitals)
2. **Expand your empire** — click adjacent empty tiles to claim them (4 moves on land, 2 on water)
3. **Wage War** — click an enemy tile adjacent to yours *before making any moves*. Play rock-paper-scissors to decide who claims the square
4. **Alliances** — agree in chat, then both players can expand from each other's territory
5. **Power-Ups** — step on special tiles to gain abilities (see the ⚡ button in-game)
6. **Elimination** — if your Capital is captured, you're out
7. **Victory** — last player standing wins!



 CONTROLS

| Action | Control |
|---|---|
| Move camera | Right-click + drag, or Arrow keys |
| Zoom in/out | Mouse scroll wheel |
| Place capital / expand | Left-click on map tile |
| War | Left-click enemy tile adjacent to yours |
| End turn | Click END TURN button |
| Rules | Click 📋 icon (left sidebar) |
| Power-ups list | Click ⚡ icon (left sidebar) |
| Chat | Click chat area, type, press Enter |
| Light/Dark mode | Press F5 or click 🌙/☀ |



 FILE STRUCTURE

```
rule_the_grid/
├── client/
│   └── client.py       ← Run this on every laptop
├── server/
│   └── server.py       ← Auto-started by host; or run manually
├── requirements.txt
└── README.md
```

The server creates `game.db` (SQLite) to store players, moves, and map data.



 TROUBLESHOOTING

**"Could not connect"** — Make sure the host ran the game first and all players are on the same WiFi network. Check that no firewall is blocking port 5555.

**Pygame not found** — Run `pip install pygame` in your terminal.

**Server window doesn't open** — Run `python server/server.py` manually in a separate terminal before launching the client.
