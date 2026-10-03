"""
=============================================================
             AUTUMN TRANQUILITY — FALLING LEAVES SIMULATION
=============================================================
An atmospheric, interactive physics simulation of autumn foliage.

Features:
  - 3D Tumbling Leaf Physics: Realistic fluttering, air drag, and 3D coin-flip tumbling
  - Dynamic Wind Engine: Natural wind gusts with smooth directional shifts
  - Interactive Mouse Wind: Move your mouse or click to blow leaves around
  - 3 Beautiful Atmospheric Themes: Golden Dusk, Crimson Sunset, Moonlit Night
  - Multi-Layered Autumn Scenery: Branching silhouette trees, rolling hills, and leaf accumulation
  - Leaf Diversity: Distinct shapes (Maple & Oak/Birch), veins, stems, and rich autumn palette
  - Interactive Controls HUD: Wind bursts, leaf density, theme cycling, and pause/play
=============================================================
"""

import tkinter as tk
import random
import math

# -------------------------------------------------------------
# Color Themes & Palettes
# -------------------------------------------------------------
THEMES = {
    "Golden Dusk": {
        "sky_top": "#0d1b2a",
        "sky_mid": "#1b263b",
        "sky_bottom": "#415a77",
        "horizon": "#e07a5f",
        "sun_color": "#f4a261",
        "sun_glow": "#e76f51",
        "hill_back": "#1a2536",
        "hill_front": "#2c1810",
        "ground": "#3d1f14",
        "tree_bark": "#1c110b",
        "foliage": ["#d9480f", "#e8590c", "#f76707", "#e67700", "#d4380d"],
        "hud_color": "#f8f9fa",
        "show_moon": False,
    },
    "Crimson Sunset": {
        "sky_top": "#1a0933",
        "sky_mid": "#3d1346",
        "sky_bottom": "#6b1b47",
        "horizon": "#bf360c",
        "sun_color": "#ff7043",
        "sun_glow": "#d84315",
        "hill_back": "#28102e",
        "hill_front": "#3a131b",
        "ground": "#2d0e12",
        "tree_bark": "#150608",
        "foliage": ["#c92a2a", "#e03131", "#f03e3e", "#ff6b6b", "#a61e4d"],
        "hud_color": "#ffc9c9",
        "show_moon": False,
    },
    "Moonlit Night": {
        "sky_top": "#050811",
        "sky_mid": "#0b1326",
        "sky_bottom": "#13223f",
        "horizon": "#1a2e51",
        "sun_color": "#e0e7ff",
        "sun_glow": "#a5b4fc",
        "hill_back": "#08101d",
        "hill_front": "#0d1829",
        "ground": "#0a1320",
        "tree_bark": "#050a12",
        "foliage": ["#3b5bdb", "#4c6ef5", "#748ffc", "#a5d8ff", "#ffd43b"],
        "hud_color": "#e0e7ff",
        "show_moon": True,
    },
}

LEAF_PALETTES = {
    "Golden Dusk": [
        "#d9480f", "#e8590c", "#f76707", "#f59f00", "#fcc419",
        "#ae2012", "#c92a2a", "#8d4925", "#b05e27", "#e76f51"
    ],
    "Crimson Sunset": [
        "#9b2226", "#ae2012", "#c92a2a", "#d90429", "#ef233c",
        "#f77f00", "#fcbf49", "#581845", "#900c3f", "#c70039"
    ],
    "Moonlit Night": [
        "#ffd43b", "#fcc419", "#fab005", "#f59f00", "#d9480f",
        "#4dabf7", "#339af0", "#748ffc", "#9775fa", "#e9ecef"
    ]
}


# -------------------------------------------------------------
# Leaf Particle Class
# -------------------------------------------------------------
class Leaf:
    def __init__(self, width, height, theme_name, spawn_at_top=True):
        self.w = width
        self.h = height
        self.theme_name = theme_name
        self.reset(spawn_at_top=spawn_at_top)

    def reset(self, spawn_at_top=True):
        self.x = random.uniform(-50, self.w + 50)
        self.y = random.uniform(-80, -10) if spawn_at_top else random.uniform(0, self.h - 50)
        
        # Depth layers: 0.6 (distant/small/slow) to 1.3 (foreground/large/fast)
        self.depth = random.uniform(0.6, 1.3)
        self.base_size = random.uniform(7, 13) * self.depth
        self.speed_y = random.uniform(1.2, 2.6) * self.depth
        
        # Sway & 3D rotation properties
        self.flutter_phase = random.uniform(0, math.tau)
        self.flutter_speed = random.uniform(0.03, 0.07)
        self.sway_amplitude = random.uniform(1.5, 3.5) * self.depth
        
        self.tumble_angle = random.uniform(0, math.tau)
        self.tumble_speed = random.uniform(0.04, 0.09)
        self.spin_angle = random.uniform(0, math.tau)
        self.spin_speed = random.uniform(-0.03, 0.03)

        # Style & Shape (0: Oval / Birch, 1: Pointed Maple)
        self.shape_type = random.choice([0, 0, 1])
        palette = LEAF_PALETTES.get(self.theme_name, LEAF_PALETTES["Golden Dusk"])
        self.color = random.choice(palette)

    def update(self, wind_x, wind_y, mouse_x, mouse_y, mouse_active):
        # 1. Base gravity and flutter sway
        self.flutter_phase += self.flutter_speed
        self.tumble_angle += self.tumble_speed
        self.spin_angle += self.spin_speed

        sway_offset = math.sin(self.flutter_phase) * self.sway_amplitude
        
        # 2. Wind contribution scaled by depth
        self.x += sway_offset + (wind_x * self.depth)
        self.y += self.speed_y + (wind_y * self.depth)

        # 3. Mouse wake effect (blowing leaves away on hover)
        if mouse_active and mouse_x is not None and mouse_y is not None:
            dx = self.x - mouse_x
            dy = self.y - mouse_y
            dist_sq = dx * dx + dy * dy
            radius = 120
            if dist_sq < radius * radius and dist_sq > 0.1:
                dist = math.sqrt(dist_sq)
                force = (1.0 - (dist / radius)) * 6.0
                self.x += (dx / dist) * force
                self.y += (dy / dist) * force - 1.5

        # 4. Respawn when off-screen
        if self.y > self.h + 20 or self.x < -100 or self.x > self.w + 100:
            self.reset(spawn_at_top=True)

    def render(self, canvas):
        # Calculate 3D foreshortening using cosine of tumble angle
        cos_tumble = math.cos(self.tumble_angle)
        scale_x = abs(cos_tumble)  # Width collapses to 0 when edge-on
        if scale_x < 0.15:
            scale_x = 0.15  # Keep small sliver visible

        # Rotate coordinates
        cos_spin = math.cos(self.spin_angle)
        sin_spin = math.sin(self.spin_angle)

        size_x = self.base_size * scale_x
        size_y = self.base_size

        if self.shape_type == 0:
            # Elliptical Leaf with Center Vein
            pts = []
            steps = 10
            for i in range(steps):
                theta = (i / steps) * math.tau
                local_x = size_x * math.cos(theta)
                local_y = size_y * 0.55 * math.sin(theta)
                # Apply 2D spin rotation
                rx = local_x * cos_spin - local_y * sin_spin
                ry = local_x * sin_spin + local_y * cos_spin
                pts.extend([self.x + rx, self.y + ry])

            canvas.create_polygon(pts, fill=self.color, outline="", smooth=True)

            # Center stem line
            vx1 = -size_x * cos_spin
            vy1 = -size_x * sin_spin
            vx2 = size_x * cos_spin
            vy2 = size_x * sin_spin
            canvas.create_line(
                self.x + vx1, self.y + vy1,
                self.x + vx2, self.y + vy2,
                fill="#3e1c0c", width=max(1, int(self.depth))
            )
        else:
            # Maple-styled multi-point Leaf
            pts = []
            # 7-point star/maple contour
            angles_radii = [
                (0, 0.4), (0.4, 0.9), (0.9, 0.5), (1.57, 1.2),
                (2.2, 0.5), (2.7, 0.9), (3.14, 0.4), (3.6, 0.2),
                (4.71, 0.15), (5.8, 0.2)
            ]
            for th, rad in angles_radii:
                lx = size_x * rad * math.cos(th)
                ly = size_y * rad * math.sin(th)
                rx = lx * cos_spin - ly * sin_spin
                ry = lx * sin_spin + ly * cos_spin
                pts.extend([self.x + rx, self.y + ry])

            canvas.create_polygon(pts, fill=self.color, outline="", smooth=True)


# -------------------------------------------------------------
# Main Application Window
# -------------------------------------------------------------
class AutumnApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Autumn Leaves — Atmospheric Wind & Leaf Simulation")
        
        self.width = 900
        self.height = 650
        self.root.geometry(f"{self.width}x{self.height}")
        self.root.resizable(False, False)

        # Theme & Settings
        self.theme_names = list(THEMES.keys())
        self.theme_idx = 0
        self.current_theme = THEMES[self.theme_names[self.theme_idx]]

        self.num_leaves = 110
        self.leaves = []
        self.running = True
        self.show_hud = True

        # Wind Simulation
        self.target_wind_x = 1.8
        self.current_wind_x = 1.0
        self.wind_gust_timer = 0

        # Mouse Interaction
        self.mouse_x = None
        self.mouse_y = None
        self.mouse_inside = False

        # Stars for night mode
        self.stars = [(random.randint(10, self.width - 10), random.randint(10, 240), random.uniform(1, 2.5))
                      for _ in range(60)]

        # Canvas Setup
        self.canvas = tk.Canvas(
            root,
            width=self.width,
            height=self.height,
            highlightthickness=0,
            bg=self.current_theme["sky_mid"]
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Initialize leaves
        self.init_leaves()

        # Pre-seed decorative ground leaves
        self.ground_leaves = []
        for _ in range(45):
            gx = random.randint(0, self.width)
            gy = random.randint(self.height - 70, self.height - 10)
            sz = random.randint(4, 9)
            col = random.choice(LEAF_PALETTES[self.theme_names[self.theme_idx]])
            self.ground_leaves.append((gx, gy, sz, col, random.uniform(0, math.pi)))

        # Event Bindings
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Leave>", self.on_mouse_leave)
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.root.bind("<space>", self.trigger_gust)
        self.root.bind("<t>", self.cycle_theme)
        self.root.bind("<T>", self.cycle_theme)
        self.root.bind("<h>", self.toggle_hud)
        self.root.bind("<H>", self.toggle_hud)
        self.root.bind("<p>", self.toggle_pause)
        self.root.bind("<P>", self.toggle_pause)
        self.root.bind("<plus>", self.add_leaves)
        self.root.bind("<equal>", self.add_leaves)
        self.root.bind("<minus>", self.remove_leaves)

        # Start Animation Loop
        self.animate()

    def init_leaves(self):
        theme_name = self.theme_names[self.theme_idx]
        self.leaves = [
            Leaf(self.width, self.height, theme_name, spawn_at_top=False)
            for _ in range(self.num_leaves)
        ]

    # ---------------------------------------------------------
    # Input Event Handlers
    # ---------------------------------------------------------
    def on_mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y
        self.mouse_inside = True

    def on_mouse_leave(self, event):
        self.mouse_inside = False

    def on_mouse_click(self, event):
        """Clicking scatters a burst of leaves around cursor."""
        for _ in range(12):
            leaf = Leaf(self.width, self.height, self.theme_names[self.theme_idx], spawn_at_top=False)
            leaf.x = event.x + random.uniform(-25, 25)
            leaf.y = event.y + random.uniform(-25, 25)
            leaf.speed_y = random.uniform(-3.5, 0.5)
            self.leaves.append(leaf)

    def trigger_gust(self, event=None):
        """Spacebar triggers a strong gust of wind."""
        self.target_wind_x = random.choice([4.5, 5.5, -3.5])
        self.wind_gust_timer = 45

    def cycle_theme(self, event=None):
        self.theme_idx = (self.theme_idx + 1) % len(self.theme_names)
        theme_name = self.theme_names[self.theme_idx]
        self.current_theme = THEMES[theme_name]
        
        # Update existing leaves palette
        palette = LEAF_PALETTES[theme_name]
        for leaf in self.leaves:
            leaf.theme_name = theme_name
            leaf.color = random.choice(palette)

        # Update ground leaves
        for i, (gx, gy, sz, _, ang) in enumerate(self.ground_leaves):
            self.ground_leaves[i] = (gx, gy, sz, random.choice(palette), ang)

    def toggle_hud(self, event=None):
        self.show_hud = not self.show_hud

    def toggle_pause(self, event=None):
        self.running = not self.running
        if self.running:
            self.animate()

    def add_leaves(self, event=None):
        theme_name = self.theme_names[self.theme_idx]
        for _ in range(15):
            self.leaves.append(Leaf(self.width, self.height, theme_name, spawn_at_top=True))
        self.num_leaves = len(self.leaves)

    def remove_leaves(self, event=None):
        if len(self.leaves) > 20:
            self.leaves = self.leaves[:-15]
            self.num_leaves = len(self.leaves)

    # ---------------------------------------------------------
    # Drawing Background & Scenic Elements
    # ---------------------------------------------------------
    def draw_scenery(self):
        t = self.current_theme

        # 1. Sky Gradient Bands
        gradient_bands = [
            (0, 180, t["sky_top"]),
            (180, 360, t["sky_mid"]),
            (360, 480, t["sky_bottom"]),
            (480, 560, t["horizon"]),
        ]
        for y1, y2, color in gradient_bands:
            self.canvas.create_rectangle(0, y1, self.width, y2, fill=color, outline="")

        # 2. Moon / Sun
        if t["show_moon"]:
            # Crescent Moon & Stars
            for sx, sy, srad in self.stars:
                self.canvas.create_oval(sx, sy, sx + srad, sy + srad, fill="#ffffff", outline="")
            # Glowing moon disc
            self.canvas.create_oval(680, 70, 770, 160, fill="#f8fafc", outline="")
            self.canvas.create_oval(705, 65, 785, 155, fill=t["sky_top"], outline="")
        else:
            # Glowing Sunset Sun with soft outer halo
            self.canvas.create_oval(640, 200, 760, 320, fill=t["sun_glow"], outline="")
            self.canvas.create_oval(655, 215, 745, 305, fill=t["sun_color"], outline="")

        # 3. Rolling Distant Hills
        hill_back_pts = [
            0, 480,
            200, 430,
            460, 460,
            720, 420,
            self.width, 460,
            self.width, 650,
            0, 650
        ]
        self.canvas.create_polygon(hill_back_pts, fill=t["hill_back"], outline="", smooth=True)

        hill_front_pts = [
            0, 520,
            280, 480,
            580, 510,
            self.width, 470,
            self.width, 650,
            0, 650
        ]
        self.canvas.create_polygon(hill_front_pts, fill=t["hill_front"], outline="", smooth=True)

        # 4. Foreground Forest Floor
        self.canvas.create_rectangle(0, 550, self.width, self.height, fill=t["ground"], outline="")

        # 5. Natural Branching Trees (Left & Right Silhouettes)
        self.draw_tree(90, 560, trunk_w=24, height=310, is_left=True)
        self.draw_tree(810, 560, trunk_w=28, height=330, is_left=False)

        # 6. Fallen Leaves on the Ground
        for gx, gy, sz, col, ang in self.ground_leaves:
            self.canvas.create_oval(
                gx - sz, gy - sz * 0.4,
                gx + sz, gy + sz * 0.4,
                fill=col, outline=""
            )

    def draw_tree(self, root_x, root_y, trunk_w, height, is_left=True):
        t = self.current_theme
        bark = t["tree_bark"]
        leaf_colors = t["foliage"]

        # Main Trunk
        top_y = root_y - height
        lean = 40 if is_left else -40

        trunk_poly = [
            root_x - trunk_w, root_y,
            root_x + trunk_w, root_y,
            root_x + lean + trunk_w * 0.4, top_y + 120,
            root_x + lean - trunk_w * 0.4, top_y + 120,
        ]
        self.canvas.create_polygon(trunk_poly, fill=bark, outline="", smooth=True)

        # Primary Branches
        branches = [
            (root_x + lean * 0.5, root_y - 120, root_x + lean * 1.8 - 50, root_y - 210, 10),
            (root_x + lean * 0.7, root_y - 170, root_x + lean * 2.2 + 40, root_y - 250, 8),
            (root_x + lean * 0.9, root_y - 210, root_x + lean * 1.4, top_y, 7),
            (root_x + lean, root_y - 230, root_x + lean * 0.2, top_y + 20, 6)
        ]

        for bx1, by1, bx2, by2, b_thick in branches:
            self.canvas.create_line(bx1, by1, bx2, by2, fill=bark, width=b_thick, capstyle=tk.ROUND)
            # Foliage clusters along branch tips
            for _ in range(4):
                fx = bx2 + random.uniform(-25, 25)
                fy = by2 + random.uniform(-20, 20)
                frad = random.uniform(22, 38)
                self.canvas.create_oval(
                    fx - frad, fy - frad * 0.7,
                    fx + frad, fy + frad * 0.7,
                    fill=random.choice(leaf_colors),
                    outline=""
                )

    def draw_hud(self):
        if not self.show_hud:
            return

        t = self.current_theme
        txt_col = t["hud_color"]

        # Elegant semi-transparent status overlay
        hud_bg = [15, 15, 330, 115]
        self.canvas.create_rectangle(hud_bg, fill="#0b0f19", outline="#334155", width=1)

        # Title & Stats
        theme_name = self.theme_names[self.theme_idx]
        self.canvas.create_text(
            30, 32,
            text=f"🍂 Autumn Foliage | {theme_name}",
            anchor="w", fill=txt_col, font=("Helvetica", 11, "bold")
        )

        wind_direction = "→" if self.current_wind_x >= 0 else "←"
        wind_desc = f"{abs(self.current_wind_x):.1f} km/h {wind_direction}"
        self.canvas.create_text(
            30, 56,
            text=f"Leaves: {len(self.leaves)}   •   Wind: {wind_desc}",
            anchor="w", fill="#cbd5e1", font=("Helvetica", 9)
        )

        self.canvas.create_text(
            30, 78,
            text="[Space] Wind Gust   •   [T] Theme   •   [+/-] Leaves",
            anchor="w", fill="#94a3b8", font=("Helvetica", 8)
        )
        self.canvas.create_text(
            30, 96,
            text="[Click/Drag] Swirl Leaves   •   [H] Hide Controls",
            anchor="w", fill="#64748b", font=("Helvetica", 8)
        )

    # ---------------------------------------------------------
    # Main Animation Engine (60 FPS)
    # ---------------------------------------------------------
    def animate(self):
        if not self.running:
            return

        # 1. Update Wind Dynamics
        if self.wind_gust_timer > 0:
            self.wind_gust_timer -= 1
        else:
            # Natural gentle wind shifts between 0.8 and 2.5
            if random.random() < 0.02:
                self.target_wind_x = random.uniform(0.6, 2.6)

        # Smooth interpolation towards target wind
        self.current_wind_x += (self.target_wind_x - self.current_wind_x) * 0.05
        wind_y = 0.1 * math.sin(self.current_wind_x)

        # 2. Clear canvas and redraw scene
        self.canvas.delete("all")
        self.draw_scenery()

        # 3. Update & render each leaf
        for leaf in self.leaves:
            leaf.update(
                self.current_wind_x,
                wind_y,
                self.mouse_x,
                self.mouse_y,
                self.mouse_inside
            )
            leaf.render(self.canvas)

        # 4. Render HUD
        self.draw_hud()

        # Target ~60 FPS (approx 16ms)
        self.root.after(16, self.animate)


# -------------------------------------------------------------
# Entry Point
# -------------------------------------------------------------
if __name__ == "__main__":
    tk_root = tk.Tk()
    app = AutumnApp(tk_root)
    tk_root.mainloop()

