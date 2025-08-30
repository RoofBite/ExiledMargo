import pygame
import os
import csv
import json
import re
import sys
import math

# --- USTAWIENIA EDYTORA ---
SCREEN_WIDTH, SCREEN_HEIGHT = 2050, 980 # Orientacja pozioma (Landscape)
GRID_TILE_SIZE = 80
PALETTE_WIDTH = 320
TOP_BAR_HEIGHT = 90
BOTTOM_BAR_HEIGHT = 90

# --- KOLORY ---
COLOR_BACKGROUND = (50, 50, 50)
COLOR_GRID_LINES = (80, 80, 80)
COLOR_PALETTE_BG = (70, 70, 70)
COLOR_TEXT = (240, 240, 240)
COLOR_BUTTON = (100, 100, 100)
COLOR_BUTTON_HOVER = (150, 150, 150)
COLOR_BUTTON_ACTIVE = (0, 150, 255)
COLOR_DIALOG_BG = (40, 40, 60, 230)
COLOR_TOOLTIP_BG = (20, 20, 30, 240)

DEFAULT_GRID_WIDTH, DEFAULT_GRID_HEIGHT = 20, 30

OBJECT_COLORS = {
    "wall": (100, 100, 100), "monster": (220, 50, 50), "npc_merchant": (50, 220, 50),
    "npc_healer": (100, 180, 255), "portal": (200, 100, 255), "decoration": (0, 150, 100),
    "pickup_item": (255, 215, 0), "default": (200, 200, 200)
}

# === SKOPIOWANE DEFINICJE OBIEKTÓW Z GRY ===
w = {"id": 1, "z": 0}; w2 = {"id": 2, "z": 0}; s1 = {"id": 5, "z": 0}; b1 = {"id": 13, "z": 0};
b2 =  {"id": 12, "z":0}; rat = {"id": 3, "z": 0}; deer = {"id": 14, "z": 0}; bear = {"id": 15, "z": 0};
merchant = {"id": 20, "z": 0}; healer = {"id": 21, "z": 0}; rat_king = {"id": 22, "z": 0};
barell = {"id": 23, "z": 0}; st_up = {"id": 40, "z": 0}; st_down = {"id": 41, "z": 0};
st_up_0 = {"id": 42, "z": 0}; portal_to_las = {"id": 43, "z": 0}; portal_back = {"id": 11, "z": 0, "target": 0};
sztylet = {"id": 101, "z": 0}; pink_shell = {"id": 102, "z": 0}; stone = {"id": 201, "z": 0};
stick =  {"id": 103, "z": 0}

SPRITE_PROPERTIES = {
    1: {"type": "wall", "name": "Ściana"}, 2: {"type": "wall", "name": "Ściana Piwnicy"}, 98: {"type": "wall", "name": "Ściana 98"}, 99: {"type": "wall", "name": "Ściana 99"}, 95: {"type": "wall", "name": "Ściana 95"}, 96: {"type": "wall", "name": "Drzwi"},
    40: {"type": "portal", "name": "Schody góra"}, 41: {"type": "portal", "name": "Schody dół"}, 42: {"type": "portal", "name": "Schody góra (0)"}, 43: {"type": "portal", "name": "Portal do Lasu"}, 10: {"type": "portal"}, 11: {"type": "portal"},
    3: {"type": "monster", "name": "Szczur"}, 14: {"type": "monster", "name": "Jeleń"}, 15: {"type": "monster", "name": "Niedźwiedź"},
    16: {"type": "monster", "name": "Niedźwiedź 2"}, 22: {"type": "monster", "name": "Król Szczurów"}, 23: {"type": "monster", "name": "Beczka"},
    24: {"type": "monster", "name": "Beczka 2"}, 20: {"type": "npc_merchant", "name": "Handlarz"}, 21: {"type": "npc_healer", "name": "Uzdrowicielka"},
    201: {"type": "decoration", "name": "Kamień"}, 12: {"type": "decoration", "name": "Krzak 1"}, 13: {"type": "decoration", "name": "Krzak 2"},
    5: {"type": "decoration", "name": "Drzewo 1"}, 6: {"type": "decoration", "name": "Drzewo 2"}, 7: {"type": "decoration", "name": "Drzewo 3"},
    101: {"type": "pickup_item", "name": "Sztylet"}, 102: {"type": "pickup_item", "name": "Muszelka"}, 103: {"type": "pickup_item", "name": "Rózga"},
    50: {"type": "floor_custom", "name": "Niest. Podłoga"}, 60: {"type": "ceiling_custom", "name": "Niest. Sufit"}
}

PALETTE_ITEMS = {
    "Gumka": "ERASER", "Ściana (w)": 'w', "Ściana Piwnicy (w2)": 'w2', "Szczur (rat)": 'rat', "Jeleń (deer)": 'deer',
    "Niedźwiedź (bear)": 'bear', "Król Szczurów": 'rat_king', "Beczka": 'barell', "Drzewo (s1)": 's1', "Krzak (b1)": 'b1',
    "Krzak (b2)": 'b2', "Kamień (stone)": 'stone', "Handlarz": 'merchant', "Uzdrowicielka": 'healer',
    "Schody Góra (do 1)": {"id": 40, "z": 0}, "Schody Dół (do -1)": {"id": 41, "z": 0}, "Schody Góra (do 0)": {"id": 42, "z": 0},
    "Portal do Lasu (2)": {"id": 43, "z": 0}, "Portal Powrotny (0)": {"id": 11, "z": 0, "target": 0},
    "Sztylet (item)": 'sztylet', "Różdżka (item)": 'stick', "Niest. Podłoga (50)": {"id": 50, "z": 0},
    "Niest. Sufit (60)": {"id": 60, "z": 0}, "Ściana z H": {"id": 95, "z": 1, "h": 0.5}, "Drzwi": {"id": 96, "z": 0, "target": 0}
}
# === FUNKCJE POMOCNICZE ===
def process_map_cell(cell):
    if not isinstance(cell, str):
        if isinstance(cell, dict): return [cell]
        if isinstance(cell, list) and all(isinstance(el, dict) for el in cell): return cell
        return []
    s = cell.strip()
    if not s: return []
    dicts = re.findall(r'\{[^}]+\}', s)
    if len(dicts) >= 2 and all(d in s for d in dicts):
        wrapped = '[' + s + ']'
        try:
            data = json.loads(wrapped)
            if isinstance(data, list) and all(isinstance(el, dict) for el in data): return data
        except json.JSONDecodeError: pass
    if (s.startswith('[') and s.endswith(']')) or (s.startswith('{') and s.endswith('}')):
        try:
            data = json.loads(s)
            if isinstance(data, dict): return [data]
            if isinstance(data, list) and all(isinstance(el, dict) for el in data): return data
        except json.JSONDecodeError: pass
    mod = sys.modules[__name__]
    if hasattr(mod, s):
        ref = getattr(mod, s)
        if isinstance(ref, dict): return [ref]
        if isinstance(ref, list) and all(isinstance(el, dict) for el in ref): return ref
    return []

def cell_to_string(cell_data):
    if not cell_data: return ""
    if len(cell_data) == 1 and isinstance(cell_data[0], str): return cell_data[0]
    try:
        return json.dumps(cell_data, separators=(',', ':'))
    except TypeError:
        return ""

class MapEditorTouch:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Edytor Map (Landscape, v3)")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("Arial", 18)
        self.font_medium = pygame.font.SysFont("Arial", 28)
        self.font_large = pygame.font.SysFont("Arial", 36)
        self.font_tooltip = pygame.font.SysFont("Consolas", 22)

        self.camera_x, self.camera_y = 0, 0
        self.zoom = 1.0
        self.place_z_level = 0
        self.view_z_level = None 
        self.edit_modes = ["pan", "paint_tap", "paint_drag"]
        self.edit_mode_idx = 1
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.last_painted_tile = None
        
        self.tooltip_text = None

        self.current_map_data = []
        self.current_map_name = "untitled.csv"
        self.create_new_map(DEFAULT_GRID_WIDTH, DEFAULT_GRID_HEIGHT)

        self.current_tool = "ERASER"
        self.palette_rects = {}
        self.palette_scroll_y = 0
        self.total_palette_height = len(PALETTE_ITEMS) * 60

        self.ui_buttons = {}
        self.dialog_mode = None
        self.dialog_widgets = {}
        self.input_text = ""
        self.new_map_width = DEFAULT_GRID_WIDTH
        self.new_map_height = DEFAULT_GRID_HEIGHT
        self.available_files = []
        self.dialog_scroll_y = 0
        
        self.running = True

    def create_new_map(self, width, height):
        self.current_map_data = [[[] for _ in range(width)] for _ in range(height)]
        self.current_map_name = "untitled.csv"

    def run(self):
        while self.running:
            self.handle_input()
            self.draw()
            self.clock.tick(60)
        pygame.quit()

    def handle_input(self):
        pos = pygame.mouse.get_pos()
        self.tooltip_text = None
        
        if self.dialog_mode is None:
            # Sprawdzanie tooltipu na siatce
            if pos[0] < SCREEN_WIDTH - PALETTE_WIDTH and pos[1] > TOP_BAR_HEIGHT and pos[1] < SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT:
                grid_x, grid_y = self.screen_to_grid(pos)
                if 0 <= grid_y < len(self.current_map_data) and 0 <= grid_x < len(self.current_map_data[0]):
                    cell_data = self.current_map_data[grid_y][grid_x]
                    if cell_data:
                        visible_objects = self.get_visible_objects_in_cell(cell_data)
                        if visible_objects:
                            self.set_tooltip_from_object(visible_objects[-1])
            # Sprawdzanie tooltipu na palecie
            elif pos[0] > SCREEN_WIDTH - PALETTE_WIDTH:
                for name, rect in self.palette_rects.items():
                    if rect.collidepoint(pos):
                        self.set_tooltip_from_palette(name)
                        break

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            
            if self.dialog_mode:
                self.handle_dialog_input(event)
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.is_dragging = True
                self.drag_start_pos = event.pos
                self.last_painted_tile = None
                if self.handle_ui_click(event.pos):
                    self.is_dragging = False

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.is_dragging:
                    drag_dist = math.hypot(event.pos[0] - self.drag_start_pos[0], event.pos[1] - self.drag_start_pos[1])
                    if drag_dist < 20 and not self.drag_start_pos[0] > SCREEN_WIDTH-PALETTE_WIDTH:
                        if self.get_edit_mode() == 'paint_tap':
                            self.handle_tap(event.pos)
                self.is_dragging = False

            if event.type == pygame.MOUSEMOTION and self.is_dragging:
                mode = self.get_edit_mode()
                if self.drag_start_pos[0] < SCREEN_WIDTH - PALETTE_WIDTH: # Drag na siatce
                    if mode == 'pan':
                        self.camera_x -= event.rel[0]
                        self.camera_y -= event.rel[1]
                    elif mode == 'paint_drag':
                        self.handle_drag_paint(event.pos)
                else: # Drag na palecie
                    self.palette_scroll_y += event.rel[1]
                    max_scroll = self.total_palette_height - SCREEN_HEIGHT + 200
                    self.palette_scroll_y = max(min(self.palette_scroll_y, 0), -max_scroll if max_scroll > 0 else 0)

    def get_visible_objects_in_cell(self, cell_data):
        if self.view_z_level is None:
             return sorted(cell_data, key=lambda i: i.get('z', 0) if isinstance(i, dict) else 0)
        else:
            return [obj for obj in cell_data if isinstance(obj, dict) and obj.get('z', 0) == self.view_z_level]

    def set_tooltip_from_palette(self, palette_name):
        item_data = PALETTE_ITEMS[palette_name]
        if item_data == "ERASER":
            self.tooltip_text = "Gumka: Usuwa najwyższy obiekt z pola"
            return
        
        obj_def = None
        if isinstance(item_data, str) and item_data in globals():
            obj_def = globals()[item_data]
        elif isinstance(item_data, dict):
            obj_def = item_data
        
        if obj_def:
            self.set_tooltip_from_object(obj_def, palette_name)
    
    def set_tooltip_from_object(self, obj_data, name_override=None):
        obj_id = obj_data.get('id') if isinstance(obj_data, dict) else None
        if isinstance(obj_data, str) and obj_data in globals():
             obj_id = globals()[obj_data].get('id')

        props = SPRITE_PROPERTIES.get(obj_id, {})
        name = name_override if name_override else props.get('name', 'Nieznany')
        
        self.tooltip_text = f"{name} (ID: {obj_id}) | Właściwości: {str(obj_data)}"

    def get_edit_mode(self):
        return self.edit_modes[self.edit_mode_idx]

    def handle_ui_click(self, pos):
        for name, rect in self.palette_rects.items():
            if rect.collidepoint(pos):
                self.current_tool = PALETTE_ITEMS[name]
                return True
        for name, rect in self.ui_buttons.items():
            if rect.collidepoint(pos):
                if name == "toggle_mode": self.edit_mode_idx = (self.edit_mode_idx + 1) % len(self.edit_modes)
                elif name == "zoom_in": self.zoom = min(self.zoom * 1.2, 3.0)
                elif name == "zoom_out": self.zoom = max(self.zoom * 0.8, 0.25)
                elif name == "place_z_plus": self.place_z_level += 1
                elif name == "place_z_minus": self.place_z_level -= 1
                elif name == "view_z_plus": self.view_z_level = (self.view_z_level if self.view_z_level is not None else -1) + 1
                elif name == "view_z_minus": self.view_z_level = (self.view_z_level if self.view_z_level is not None else 1) - 1
                elif name == "view_z_all": self.view_z_level = None
                elif name == "new": self.dialog_mode = 'new_map'
                elif name == "load":
                    self.dialog_mode = 'load_browser'
                    try: self.available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
                    except Exception: self.available_files = []
                    self.dialog_scroll_y = 0
                elif name == "save": self.save_map_to_csv(self.current_map_name)
                elif name == "save_as": 
                    self.dialog_mode = 'save_as_keyboard'
                    self.input_text = self.current_map_name.replace(".csv","")
                return True
        return False
    
    def handle_tap(self, pos):
        if pos[0] < SCREEN_WIDTH - PALETTE_WIDTH:
            grid_x, grid_y = self.screen_to_grid(pos)
            self.place_object_on_grid(grid_x, grid_y)

    def handle_drag_paint(self, pos):
        if pos[0] < SCREEN_WIDTH - PALETTE_WIDTH:
            grid_x, grid_y = self.screen_to_grid(pos)
            if (grid_x, grid_y) != self.last_painted_tile:
                self.place_object_on_grid(grid_x, grid_y)
                self.last_painted_tile = (grid_x, grid_y)

    def screen_to_grid(self, screen_pos):
        effective_tile_size = GRID_TILE_SIZE * self.zoom
        if effective_tile_size == 0: return -1, -1
        grid_x = math.floor((screen_pos[0] + self.camera_x) / effective_tile_size)
        grid_y = math.floor((screen_pos[1] + self.camera_y) / effective_tile_size)
        return grid_x, grid_y
    
    def place_object_on_grid(self, x, y):
        current_map = self.current_map_data
        if not (0 <= y < len(current_map) and 0 <= x < len(current_map[0])): return
        
        cell = current_map[y][x]
        tool = self.current_tool
        
        if tool == "ERASER":
            if cell:
                cell.sort(key=lambda item: item.get('z', -99) if isinstance(item, dict) else -99, reverse=True)
                cell.pop(0)
            return
            
        obj_to_place = None
        if isinstance(tool, str) and tool in globals():
            obj_to_place = globals()[tool].copy()
        elif isinstance(tool, dict):
            obj_to_place = tool.copy()
        
        if obj_to_place is not None:
            obj_to_place['z'] = self.place_z_level
            if obj_to_place not in cell:
                cell.append(obj_to_place)

    def draw(self):
        self.screen.fill(COLOR_BACKGROUND)
        self.draw_grid_and_content()
        self.draw_palette()
        self.draw_ui()
        if self.tooltip_text:
            self.draw_tooltip()
        if self.dialog_mode:
            self.draw_dialog()
        pygame.display.flip()

    def draw_grid_and_content(self):
        effective_tile_size = int(GRID_TILE_SIZE * self.zoom)
        if effective_tile_size < 4: return 

        grid_surface_width = SCREEN_WIDTH - PALETTE_WIDTH
        start_x = math.floor(self.camera_x / effective_tile_size)
        end_x = math.ceil((self.camera_x + grid_surface_width) / effective_tile_size)
        start_y = math.floor(self.camera_y / effective_tile_size)
        end_y = math.ceil((self.camera_y + SCREEN_HEIGHT) / effective_tile_size)
        
        current_map = self.current_map_data
        if not current_map: return

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if not (0 <= y < len(current_map) and 0 <= x < len(current_map[0])): continue
                
                screen_x = int(x * effective_tile_size - self.camera_x)
                screen_y = int(y * effective_tile_size - self.camera_y)
                rect = pygame.Rect(screen_x, screen_y, effective_tile_size, effective_tile_size)
                
                if effective_tile_size > 8:
                    pygame.draw.rect(self.screen, COLOR_GRID_LINES, rect, 1)
                
                visible_objects = self.get_visible_objects_in_cell(current_map[y][x])

                if visible_objects:
                    obj_to_draw = visible_objects[-1]
                    
                    obj_id = obj_to_draw.get('id') if isinstance(obj_to_draw, dict) else None
                    obj_z = obj_to_draw.get('z', 0) if isinstance(obj_to_draw, dict) else 0
                    if isinstance(obj_to_draw, str) and obj_to_draw in globals(): 
                        obj_def = globals()[obj_to_draw]
                        obj_id = obj_def.get('id'); obj_z = obj_def.get('z', 0)

                    props = SPRITE_PROPERTIES.get(obj_id, {})
                    color = OBJECT_COLORS.get(props.get("type", "default"), OBJECT_COLORS["default"])
                    pygame.draw.rect(self.screen, color, rect.inflate(-2, -2))
                    
                    if effective_tile_size > 40:
                        id_text = f"ID:{obj_id}" if obj_id is not None else '?'; self.screen.blit(self.font_small.render(id_text, True, COLOR_TEXT), (rect.x + 5, rect.y + 5))
                        z_text = f"Z:{obj_z}"; self.screen.blit(self.font_small.render(z_text, True, COLOR_TEXT), (rect.x + 5, rect.y + 25))
                    
                    if len(current_map[y][x]) > 1:
                        pygame.draw.circle(self.screen, (255, 255, 0), rect.topright, int(effective_tile_size * 0.15))

    def draw_palette(self):
        palette_x = SCREEN_WIDTH - PALETTE_WIDTH
        pygame.draw.rect(self.screen, COLOR_PALETTE_BG, (palette_x, 0, PALETTE_WIDTH, SCREEN_HEIGHT))
        y_offset = 20 + self.palette_scroll_y
        self.palette_rects.clear()
        for name, item_data in PALETTE_ITEMS.items():
            if y_offset > -50 and y_offset < SCREEN_HEIGHT:
                rect = pygame.Rect(palette_x + 15, y_offset, PALETTE_WIDTH - 30, 50)
                self.palette_rects[name] = rect
                color = COLOR_BUTTON_ACTIVE if self.current_tool == item_data else COLOR_BUTTON
                pygame.draw.rect(self.screen, color, rect, border_radius=8)
                self.screen.blit(self.font_medium.render(name, True, COLOR_TEXT), self.font_medium.render(name, True, COLOR_TEXT).get_rect(center=rect.center))
            y_offset += 60

    def draw_ui(self):
        # Górny pasek
        pygame.draw.rect(self.screen, (40,40,40), (0,0,SCREEN_WIDTH - PALETTE_WIDTH, TOP_BAR_HEIGHT))
        x_offset, top_y = 20, (TOP_BAR_HEIGHT - 70) // 2
        btn_w, btn_h, margin = 180, 70, 10
        self.ui_buttons["new"] = pygame.Rect(x_offset, top_y, btn_w, btn_h)
        self.ui_buttons["load"] = pygame.Rect(x_offset + btn_w + margin, top_y, btn_w, btn_h)
        self.ui_buttons["save"] = pygame.Rect(x_offset + (btn_w + margin)*2, top_y, btn_w, btn_h)
        self.ui_buttons["save_as"] = pygame.Rect(x_offset + (btn_w + margin)*3, top_y, btn_w, btn_h)

        pygame.draw.rect(self.screen, COLOR_BUTTON, self.ui_buttons["new"], border_radius=8); self.screen.blit(self.font_medium.render("Nowa", True, COLOR_TEXT), self.font_medium.render("Nowa", True, COLOR_TEXT).get_rect(center=self.ui_buttons["new"].center))
        pygame.draw.rect(self.screen, COLOR_BUTTON, self.ui_buttons["load"], border_radius=8); self.screen.blit(self.font_medium.render("Wczytaj", True, COLOR_TEXT), self.font_medium.render("Wczytaj", True, COLOR_TEXT).get_rect(center=self.ui_buttons["load"].center))
        pygame.draw.rect(self.screen, (0, 130, 0), self.ui_buttons["save"], border_radius=8); self.screen.blit(self.font_medium.render("Zapisz", True, COLOR_TEXT), self.font_medium.render("Zapisz", True, COLOR_TEXT).get_rect(center=self.ui_buttons["save"].center))
        pygame.draw.rect(self.screen, COLOR_BUTTON, self.ui_buttons["save_as"], border_radius=8); self.screen.blit(self.font_medium.render("Zapisz jako", True, COLOR_TEXT), self.font_medium.render("Zapisz jako", True, COLOR_TEXT).get_rect(center=self.ui_buttons["save_as"].center))
        
        # Dolny pasek
        pygame.draw.rect(self.screen, (40,40,40), (0, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT, SCREEN_WIDTH - PALETTE_WIDTH, BOTTOM_BAR_HEIGHT))
        bottom_y = SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + (BOTTOM_BAR_HEIGHT - 70) // 2
        
        mode_rect = pygame.Rect(20, bottom_y, 360, 70)
        self.ui_buttons["toggle_mode"] = mode_rect
        mode_texts = {"pan": "🖐️ Tryb: Przesuwanie", "paint_tap": "👆 Tryb: Stawianie", "paint_drag": "🎨 Tryb: Rysuj"}
        pygame.draw.rect(self.screen, COLOR_BUTTON, mode_rect, border_radius=8); self.screen.blit(self.font_medium.render(mode_texts[self.get_edit_mode()], True, COLOR_TEXT), self.font_medium.render(mode_texts[self.get_edit_mode()], True, COLOR_TEXT).get_rect(center=mode_rect.center))

        zoom_x = mode_rect.right + 20
        self.ui_buttons["zoom_out"] = pygame.Rect(zoom_x, bottom_y, 70, 70); pygame.draw.rect(self.screen, COLOR_BUTTON, self.ui_buttons["zoom_out"], border_radius=8); self.screen.blit(self.font_large.render("-", True, COLOR_TEXT), self.font_large.render("-", True, COLOR_TEXT).get_rect(center=self.ui_buttons["zoom_out"].center))
        zoom_text_surf = self.font_medium.render(f"Zoom: {self.zoom:.1f}x", True, COLOR_TEXT); self.screen.blit(zoom_text_surf, (zoom_x + 80, bottom_y + 20))
        self.ui_buttons["zoom_in"] = pygame.Rect(zoom_x + 80 + zoom_text_surf.get_width() + 10, bottom_y, 70, 70); pygame.draw.rect(self.screen, COLOR_BUTTON, self.ui_buttons["zoom_in"], border_radius=8); self.screen.blit(self.font_large.render("+", True, COLOR_TEXT), self.font_large.render("+", True, COLOR_TEXT).get_rect(center=self.ui_buttons["zoom_in"].center))
        
        place_z_x = self.ui_buttons["zoom_in"].right + 20
        self.ui_buttons["place_z_minus"] = pygame.Rect(place_z_x, bottom_y, 70, 70); pygame.draw.rect(self.screen, COLOR_BUTTON, self.ui_buttons["place_z_minus"], border_radius=8); self.screen.blit(self.font_large.render("-", True, COLOR_TEXT), self.font_large.render("-", True, COLOR_TEXT).get_rect(center=self.ui_buttons["place_z_minus"].center))
        place_z_text = f"Poziom Z: {self.place_z_level}"; text_surf = self.font_medium.render(place_z_text, True, COLOR_TEXT); self.screen.blit(text_surf, (place_z_x + 80, bottom_y + 20))
        self.ui_buttons["place_z_plus"] = pygame.Rect(place_z_x + 80 + text_surf.get_width() + 10, bottom_y, 70, 70); pygame.draw.rect(self.screen, COLOR_BUTTON, self.ui_buttons["place_z_plus"], border_radius=8); self.screen.blit(self.font_large.render("+", True, COLOR_TEXT), self.font_large.render("+", True, COLOR_TEXT).get_rect(center=self.ui_buttons["place_z_plus"].center))

        view_z_x = self.ui_buttons["place_z_plus"].right + 20
        self.ui_buttons["view_z_minus"] = pygame.Rect(view_z_x, bottom_y, 70, 70); pygame.draw.rect(self.screen, COLOR_BUTTON, self.ui_buttons["view_z_minus"], border_radius=8); self.screen.blit(self.font_large.render("-", True, COLOR_TEXT), self.font_large.render("-", True, COLOR_TEXT).get_rect(center=self.ui_buttons["view_z_minus"].center))
        view_z_text_str = f"Widok Z: {self.view_z_level if self.view_z_level is not None else 'All'}"
        view_text_surf = self.font_medium.render(view_z_text_str, True, COLOR_TEXT)
        self.ui_buttons["view_z_all"] = pygame.Rect(view_z_x + 80, bottom_y, view_text_surf.get_width()+20, 70); pygame.draw.rect(self.screen, COLOR_BUTTON_ACTIVE if self.view_z_level is None else COLOR_BUTTON, self.ui_buttons["view_z_all"], border_radius=8); self.screen.blit(view_text_surf, (view_z_x + 90, bottom_y + 20))
        self.ui_buttons["view_z_plus"] = pygame.Rect(self.ui_buttons["view_z_all"].right + 10, bottom_y, 70, 70); pygame.draw.rect(self.screen, COLOR_BUTTON, self.ui_buttons["view_z_plus"], border_radius=8); self.screen.blit(self.font_large.render("+", True, COLOR_TEXT), self.font_large.render("+", True, COLOR_TEXT).get_rect(center=self.ui_buttons["view_z_plus"].center))

        map_info = f"Mapa: {self.current_map_name} [{len(self.current_map_data[0]) if self.current_map_data and self.current_map_data[0] else 0}x{len(self.current_map_data)}]"
        self.screen.blit(self.font_medium.render(map_info, True, COLOR_TEXT), (20, TOP_BAR_HEIGHT + 10))

    def draw_tooltip(self):
        if not self.tooltip_text: return
        
        s = self.font_tooltip.render(self.tooltip_text, True, COLOR_TEXT)
        rect = s.get_rect(centerx= (SCREEN_WIDTH-PALETTE_WIDTH)/2, top=TOP_BAR_HEIGHT + 10)
        
        bg_rect = rect.inflate(20, 10)
        
        tooltip_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        tooltip_surf.fill(COLOR_TOOLTIP_BG)
        
        self.screen.blit(tooltip_surf, bg_rect)
        self.screen.blit(s, rect)
        
    def handle_dialog_input(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            pos = event.pos
            for name, data in self.dialog_widgets.items():
                rect = data['rect']
                if rect.collidepoint(pos):
                    if self.dialog_mode == 'new_map':
                        if name == 'w_plus': self.new_map_width += 1
                        elif name == 'w_minus': self.new_map_width = max(1, self.new_map_width - 1)
                        elif name == 'h_plus': self.new_map_height += 1
                        elif name == 'h_minus': self.new_map_height = max(1, self.new_map_height - 1)
                        elif name == 'create': self.create_new_map(self.new_map_width, self.new_map_height); self.dialog_mode = None
                        elif name == 'cancel': self.dialog_mode = None
                    elif self.dialog_mode == 'load_browser':
                        if name == 'cancel': self.dialog_mode = None
                        elif name.startswith("file_"): self.load_map_from_csv(data['filename']); self.dialog_mode = None
                    elif self.dialog_mode == 'save_as_keyboard':
                        if name == 'ok': self.save_map_to_csv(self.input_text); self.dialog_mode = None
                        elif name == 'cancel': self.dialog_mode = None
                        elif name == 'backspace': self.input_text = self.input_text[:-1]
                        else: self.input_text += data['char']
        
        if event.type == pygame.MOUSEMOTION and self.is_dragging and self.dialog_mode == 'load_browser':
             self.dialog_scroll_y += event.rel[1]
             max_scroll = len(self.available_files) * 60 - 500
             self.dialog_scroll_y = max(min(self.dialog_scroll_y, 0), -max_scroll if max_scroll > 0 else 0)

    def draw_dialog(self):
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); s.fill(COLOR_DIALOG_BG); self.screen.blit(s, (0,0))
        self.dialog_widgets.clear()
        
        box_w, box_h = 1000, 800
        box_x, box_y = (SCREEN_WIDTH - box_w)/2, (SCREEN_HEIGHT - box_h)/2
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, (30,30,40), box_rect, border_radius=15)
        pygame.draw.rect(self.screen, COLOR_BUTTON_ACTIVE, box_rect, 5, border_radius=15)

        cancel_btn_rect = pygame.Rect(box_x + box_w - 300, box_y + box_h - 120, 250, 80)
        
        if self.dialog_mode == 'new_map':
            title = self.font_large.render("Nowa Mapa", True, COLOR_TEXT); self.screen.blit(title, (box_rect.centerx - title.get_width()/2, box_y + 40))
            w_text = self.font_medium.render(f"Szerokość: {self.new_map_width}", True, COLOR_TEXT); self.screen.blit(w_text, (box_x + 100, box_y + 150))
            self.dialog_widgets['w_minus'] = {'rect':pygame.Rect(box_x + 550, box_y+140, 80, 80)}; self.dialog_widgets['w_plus'] = {'rect':pygame.Rect(box_x + 650, box_y+140, 80, 80)}
            h_text = self.font_medium.render(f"Wysokość: {self.new_map_height}", True, COLOR_TEXT); self.screen.blit(h_text, (box_x + 100, box_y + 250))
            self.dialog_widgets['h_minus'] = {'rect':pygame.Rect(box_x + 550, box_y+240, 80, 80)}; self.dialog_widgets['h_plus'] = {'rect':pygame.Rect(box_x + 650, box_y+240, 80, 80)}

            for name, data in self.dialog_widgets.items():
                pygame.draw.rect(self.screen, COLOR_BUTTON, data['rect'], border_radius=8)
                label = "-" if "minus" in name else "+"; self.screen.blit(self.font_large.render(label, True, COLOR_TEXT), self.font_large.render(label, True, COLOR_TEXT).get_rect(center=data['rect'].center))
            
            ok_btn = pygame.Rect(box_x + 50, box_y + box_h - 120, 250, 80)
            self.dialog_widgets['create'] = {'rect':ok_btn}; self.dialog_widgets['cancel'] = {'rect':cancel_btn_rect}
            pygame.draw.rect(self.screen, (0,150,0), ok_btn, border_radius=8); self.screen.blit(self.font_medium.render("Stwórz", True, COLOR_TEXT), self.font_medium.render("Stwórz", True, COLOR_TEXT).get_rect(center=ok_btn.center))
            pygame.draw.rect(self.screen, (150,0,0), cancel_btn_rect, border_radius=8); self.screen.blit(self.font_medium.render("Anuluj", True, COLOR_TEXT), self.font_medium.render("Anuluj", True, COLOR_TEXT).get_rect(center=cancel_btn_rect.center))

        elif self.dialog_mode == 'load_browser':
            title = self.font_large.render("Wczytaj Mapę", True, COLOR_TEXT); self.screen.blit(title, (box_rect.centerx - title.get_width()/2, box_y + 40))
            self.dialog_widgets['cancel'] = {'rect':cancel_btn_rect}; pygame.draw.rect(self.screen, (150,0,0), cancel_btn_rect, border_radius=8); self.screen.blit(self.font_medium.render("Anuluj", True, COLOR_TEXT), self.font_medium.render("Anuluj", True, COLOR_TEXT).get_rect(center=cancel_btn_rect.center))

            y_offset = box_y + 120 + self.dialog_scroll_y
            for filename in self.available_files:
                if y_offset > box_y + 100 and y_offset < box_y + box_h - 140:
                    file_rect = pygame.Rect(box_x + 50, y_offset, box_w - 100, 50)
                    self.dialog_widgets[f"file_{filename}"] = {'rect':file_rect, 'filename': filename}
                    pygame.draw.rect(self.screen, COLOR_BUTTON, file_rect, border_radius=8)
                    self.screen.blit(self.font_medium.render(filename, True, COLOR_TEXT), self.font_medium.render(filename, True, COLOR_TEXT).get_rect(center=file_rect.center))
                y_offset += 60

        elif self.dialog_mode == 'save_as_keyboard':
            title = self.font_large.render("Zapisz jako...", True, COLOR_TEXT); self.screen.blit(title, (box_rect.centerx - title.get_width()/2, box_y + 40))
            input_rect = pygame.Rect(box_x + 50, box_y + 120, box_w - 100, 80)
            pygame.draw.rect(self.screen, (20,20,20), input_rect, border_radius=8); pygame.draw.rect(self.screen, COLOR_TEXT, input_rect, 2, border_radius=8)
            cursor = "|" if int(pygame.time.get_ticks()/500) % 2 == 0 else ""; self.screen.blit(self.font_medium.render(self.input_text + cursor, True, COLOR_TEXT), (input_rect.x + 15, input_rect.y + 20))

            keys = "qwertyuiopasdfghjklzxcvbnm_1234567890"
            key_size, margin = 75, 10
            start_kx, start_ky = box_x + (box_w - 10 * (key_size + margin) + margin)/2, box_y + 250
            kx, ky = start_kx, start_ky
            for i, char in enumerate(keys):
                if i == 10 or i == 19: kx, ky = start_kx, ky + key_size + margin
                key_rect = pygame.Rect(kx, ky, key_size, key_size)
                self.dialog_widgets[f"key_{char}"] = {'rect':key_rect, 'char':char}
                pygame.draw.rect(self.screen, COLOR_BUTTON, key_rect, border_radius=8)
                self.screen.blit(self.font_medium.render(char, True, COLOR_TEXT), self.font_medium.render(char, True, COLOR_TEXT).get_rect(center=key_rect.center))
                kx += key_size + margin
            
            back_rect = pygame.Rect(start_kx + 10 * (key_size + margin), start_ky, key_size*2, key_size); self.dialog_widgets['backspace'] = {'rect':back_rect}; pygame.draw.rect(self.screen, (150,50,50), back_rect, border_radius=8); self.screen.blit(self.font_medium.render("BS", True, COLOR_TEXT), self.font_medium.render("BS", True, COLOR_TEXT).get_rect(center=back_rect.center))
            ok_btn = pygame.Rect(box_x + 50, box_y + box_h - 120, 250, 80); self.dialog_widgets['ok'] = {'rect':ok_btn}; pygame.draw.rect(self.screen, (0,150,0), ok_btn, border_radius=8); self.screen.blit(self.font_medium.render("OK", True, COLOR_TEXT), self.font_medium.render("OK", True, COLOR_TEXT).get_rect(center=ok_btn.center))
            self.dialog_widgets['cancel'] = {'rect':cancel_btn_rect}; pygame.draw.rect(self.screen, (150,0,0), cancel_btn_rect, border_radius=8); self.screen.blit(self.font_medium.render("Anuluj", True, COLOR_TEXT), self.font_medium.render("Anuluj", True, COLOR_TEXT).get_rect(center=cancel_btn_rect.center))
    
    def save_map_to_csv(self, filename):
        if not filename: return
        if not filename.endswith(".csv"): filename += ".csv"
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for row in self.current_map_data:
                    writer.writerow([cell_to_string(cell) for cell in row])
            self.current_map_name = filename
            print(f"Pomyślnie zapisano: {filename}")
        except Exception as e:
            print(f"Błąd zapisu: {e}")

    def load_map_from_csv(self, filename):
        if not filename.endswith(".csv"): filename += ".csv"
        if not os.path.exists(filename):
            print(f"Błąd: Plik '{filename}' nie istnieje."); return
        try:
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                processed_map = [[process_map_cell(cell) for cell in row] for row in csv.reader(f)]
            self.current_map_data = processed_map
            self.current_map_name = filename
            print(f"Pomyślnie wczytano: {filename}")
        except Exception as e:
            print(f"Błąd wczytywania {filename}: {e}")

if __name__ == '__main__':
    editor = MapEditorTouch()
    editor.run()