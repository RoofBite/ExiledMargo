import pygame
import os
import csv
import json
import re
import sys
import math
import random

# --- USTAWIENIA EDYTORA ---
SCREEN_WIDTH, SCREEN_HEIGHT = 2050, 980
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
COLOR_DIALOG_SOLID_BG = (45, 45, 70)

DEFAULT_GRID_WIDTH, DEFAULT_GRID_HEIGHT = 20, 30

OBJECT_COLORS = {
    "wall": (100, 100, 100), "monster": (220, 50, 50), "npc_merchant": (50, 220, 50),
    "npc_healer": (100, 180, 255), "portal": (200, 100, 255), "decoration": (0, 150, 100),
    "pickup_item": (255, 215, 0), "default": (200, 200, 200)
}

# === SKOPIOWANE DEFINICJE OBIEKTÓW Z GRY ===
w = {"id": 1, "z": 0}; w2 = {"id": 2, "z": 0}; s1 = {"id": 5, "z": 0}; b1 = {"id": 13, "z": 0};
b2 =  {"id": 12, "z":0}; rat = {"id": 3, "z": 0}; deer = {"id": 14, "z": 0}; bear = {"id": 15, "z": 0};
rat2 = {"id": 4, "z": 0};
merchant = {"id": 20, "z": 0}; healer = {"id": 21, "z": 0}; rat_king = {"id": 22, "z": 0};
barell = {"id": 23, "z": 0}; st_up = {"id": 40, "z": 0}; st_down = {"id": 41, "z": 0};
st_up_0 = {"id": 42, "z": 0}; portal_to_las = {"id": 43, "z": 0}; portal_back = {"id": 11, "z": 0, "target": 0};
sztylet = {"id": 101, "z": 0}; pink_shell = {"id": 102, "z": 0}; stone = {"id": 201, "z": 0};
stick =  {"id": 103, "z": 0}


SPRITE_PROPERTIES = {
    1: {"type": "wall", "name": "Ściana"}, 
    2: {"type": "wall", "name": "Ściana Piwnicy"},
    95: {"type": "wall", "name": "Ściana 95"}, 
    96: {"type": "wall", "name": "Drzwi"},
    10: {"type": "portal"}, 
    11: {"type": "portal"},
    50: {"type": "floor_custom", "name": "Niest. Podłoga", "texture": "wall17.png"},
    60: {"type": "ceiling_custom", "name": "Niest. Sufit", "texture": "wall17.png"},
    3: {"texture": "rat2.png", "type": "monster", "name": "Szczur", "hp": 13, "attack": 4},
    4: {"texture": "rat3.png", "type": "monster", "name": "Groźny Szczur", "hp": 25, "attack": 7},
    5: {"texture": "tree3.png", "type": "decoration", "name": "Drzewo 1"},
    6: {"texture": "tree4.png", "type": "decoration", "name": "Drzewo 2"},
    7: {"texture": "tree5.png", "type": "decoration", "name": "Drzewo 3"},
    12: {"texture": "bush3.png", "type": "decoration", "name": "Krzak 1"},
    13: {"texture": "bush4.png", "type": "decoration", "name": "Krzak 2"},
    14: {"texture": "deer2.png", "type": "monster", "name": "Jeleń", "hp": 28, "attack": 8},
    15: {"texture": "bear3.png", "type": "monster", "name": "Niedźwiedź", "hp": 50, "attack": 12},
    16: {"texture": "bear3.png", "type": "monster", "name": "Niedźwiedź 2", "hp": 150, "attack": 5},
    20: {"texture": "merchant.png", "type": "npc_merchant", "name": "Handlarz"},
    21: {"texture": "healer.png", "type": "npc_healer", "name": "Uzdrowicielka Elara"},
    22: {"texture": "rat_king2.png", "type": "monster", "name": "Król Szczurów", "hp": 150, "attack": 12},
    23: {"texture": "barell2.png", "type": "monster", "name": "Beczka", "hp": 30, "attack": 1},
    24: {"texture": "barell2.png", "type": "monster", "name": "Beczka 2", "hp": 30, "attack": 1},
    40: {"texture": "stairs_up.png", "type": "portal", "name": "Schody góra"},
    41: {"texture": "stairs_down.png", "type": "portal", "name": "Schody dół"},
    42: {"texture": "stairs_up.png", "type": "portal", "name": "Schody góra (0)"},
    43: {"texture": "stairs_down.png", "type": "portal", "name": "Portal do Lasu"},
    46: {"texture": "stairs_up.png", "type": "portal", "name": "Schody Góra (Niest.)"},
    47: {"texture": "stairs_down.png", "type": "portal", "name": "Schody Dół (Niest.)"},
    98: {"texture": "wall5.png", "type": "decoration", "name": "Ściana Pozioma", "orientation": "y"},
    99: {"texture": "wall5.png", "type": "decoration", "name": "Ściana Pionowa", "orientation": "x"},
    101: {"texture": "sztylet.png", "type": "pickup_item", "name": "Sztylet"},
    102: {"texture": "pink_shell.png", "type": "pickup_item", "name": "Muszelka"},
    103: {"texture": "stick.png", "type": "pickup_item", "name": "Rózga"},
    201: {"texture": "stone3.png", "type": "decoration", "name": "Kamień"}
}

PALETTE_ITEMS = {
    "Gumka": "ERASER",
    "Ściana (w)": 'w', "Ściana Piwnicy (w2)": 'w2', "Ściana Pozioma": {"id": 98, "z": 0}, "Ściana Pionowa": {"id": 99, "z": 0},
    "Szczur (rat)": 'rat', "Silny szczur (rat2)": 'rat2', "Jeleń (deer)": 'deer', "Niedźwiedź (bear)": 'bear', "Król Szczurów": 'rat_king', "Beczka": 'barell',
    "Drzewo (s1)": 's1', "Krzak (b1)": 'b1', "Krzak (b2)": 'b2', "Kamień (stone)": 'stone',
    "Handlarz": 'merchant', "Uzdrowicielka": 'healer',
    "Schody Góra (do 1)": {"id": 40, "z": 0}, "Schody Dół (do -1)": {"id": 41, "z": 0}, "Schody Góra (do 0)": {"id": 42, "z": 0},
    "Portal do Lasu (2)": {"id": 43, "z": 0},
    "Schody Góra (Niest.)": {"id": 46, "z": 0},
    "Schody Dół (Niest.)": {"id": 47, "z": 0},
    "Sztylet (item)": 'sztylet', "Różdżka (item)": 'stick',
}

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
        pygame.display.set_caption("Edytor Map (v8) - Interfejs Dotykowy")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("Arial", 18)
        self.font_medium = pygame.font.SysFont("Arial", 28)
        self.font_large = pygame.font.SysFont("Arial", 36)
        self.font_tooltip = pygame.font.SysFont("Consolas", 22)
        
        self.sprite_images = {}
        self.load_sprites()

        self.camera_x, self.camera_y = 0, 0
        self.zoom = 1.0
        self.place_z_level = 0
        self.view_z_level = None 
        self.edit_modes = ["pan", "paint_tap", "paint_drag", "edit"]
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
        self.dialog_map_width = DEFAULT_GRID_WIDTH
        self.dialog_map_height = DEFAULT_GRID_HEIGHT
        self.available_files = []
        self.dialog_scroll_y = 0
        
        self.running = True

    def load_sprites(self):
        sprite_folder = "assets/textures/"
        if not os.path.isdir(sprite_folder):
            print(f"Ostrzeżenie: Nie znaleziono folderu '{sprite_folder}'.")
            return

        for obj_id, properties in SPRITE_PROPERTIES.items():
            if "texture" in properties:
                filename = properties["texture"]
                filepath = os.path.join(sprite_folder, filename)
                try:
                    if os.path.exists(filepath):
                        self.sprite_images[obj_id] = pygame.image.load(filepath).convert_alpha()
                except pygame.error as e:
                    print(f"Błąd ładowania obrazka dla ID {obj_id} ({filename}): {e}")
    
    # ZMIANA: CAŁKOWICIE NOWA FUNKCJA Z PRZYCISKAMI ZAMIAST PÓL TEKSTOWYCH
    def prompt_for_portal_target(self, existing_data=None):
        title = "Edytuj Cel Portalu" if existing_data else "Ustaw Cel Portalu"
        
        # Pobierz istniejące wartości lub ustaw domyślne na 0
        current_x = int(existing_data.get('target_x', 0)) if existing_data else 0
        current_y = int(existing_data.get('target_y', 0)) if existing_data else 0
        current_floor = int(existing_data.get('target_floor', 0)) if existing_data else 0
        
        values = [current_x, current_y, current_floor]
        labels = ["Cel X:", "Cel Y:", "Piętro:"]
        
        center_x = self.screen.get_width() // 2
        
        # Definiowanie geometrii przycisków
        button_rects = {}
        btn_size = 80
        display_width = 150
        row_height = 100
        start_y = 220
        
        for i in range(3):
            y_pos = start_y + i * row_height
            button_rects[f'minus_{i}'] = pygame.Rect(center_x - display_width/2 - btn_size - 10, y_pos, btn_size, btn_size)
            button_rects[f'plus_{i}'] = pygame.Rect(center_x + display_width/2 + 10, y_pos, btn_size, btn_size)

        ok_button_rect = pygame.Rect(center_x - 220, start_y + 3 * row_height, 180, 80)
        cancel_button_rect = pygame.Rect(center_x + 40, start_y + 3 * row_height, 180, 80)
        
        done = False
        while not done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    return None
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = event.pos
                    # Sprawdź przyciski +/-
                    for i in range(3):
                        if button_rects[f'minus_{i}'].collidepoint(pos):
                            values[i] -= 1
                        if button_rects[f'plus_{i}'].collidepoint(pos):
                            values[i] += 1
                    
                    # Sprawdź OK/Anuluj
                    if ok_button_rect.collidepoint(pos):
                        return tuple(values)
                    if cancel_button_rect.collidepoint(pos):
                        return None
            
            # Rysowanie stabilnego tła
            self.screen.fill(COLOR_DIALOG_SOLID_BG)
            
            # Tytuł
            title_surf = self.font_large.render(title, True, COLOR_TEXT)
            self.screen.blit(title_surf, (center_x - title_surf.get_width()//2, 150))
            
            # Rysowanie wierszy z przyciskami
            for i in range(3):
                y_pos = start_y + i * row_height
                # Etykieta
                label_surf = self.font_medium.render(labels[i], True, COLOR_TEXT)
                self.screen.blit(label_surf, (center_x - display_width/2 - btn_size - 150, y_pos + 25))
                # Przycisk minus
                pygame.draw.rect(self.screen, COLOR_BUTTON, button_rects[f'minus_{i}'], border_radius=10)
                minus_surf = self.font_large.render("-", True, COLOR_TEXT)
                self.screen.blit(minus_surf, minus_surf.get_rect(center=button_rects[f'minus_{i}'].center))
                # Wyświetlacz wartości
                val_surf = self.font_large.render(str(values[i]), True, COLOR_TEXT)
                display_rect = pygame.Rect(center_x - display_width/2, y_pos, display_width, btn_size)
                pygame.draw.rect(self.screen, (30,30,30), display_rect, border_radius=10)
                self.screen.blit(val_surf, val_surf.get_rect(center=display_rect.center))
                # Przycisk plus
                pygame.draw.rect(self.screen, COLOR_BUTTON, button_rects[f'plus_{i}'], border_radius=10)
                plus_surf = self.font_large.render("+", True, COLOR_TEXT)
                self.screen.blit(plus_surf, plus_surf.get_rect(center=button_rects[f'plus_{i}'].center))

            # Rysuj OK/Anuluj
            pygame.draw.rect(self.screen, (0, 180, 0), ok_button_rect, border_radius=10)
            ok_text = self.font_large.render("OK", True, COLOR_TEXT)
            self.screen.blit(ok_text, ok_text.get_rect(center=ok_button_rect.center))
            
            pygame.draw.rect(self.screen, (180, 0, 0), cancel_button_rect, border_radius=10)
            cancel_text = self.font_large.render("Anuluj", True, COLOR_TEXT)
            self.screen.blit(cancel_text, cancel_text.get_rect(center=cancel_button_rect.center))

            pygame.display.flip()
            self.clock.tick(30)
        return None

    def create_new_map(self, width, height):
        self.current_map_data = [[[] for _ in range(width)] for _ in range(height)]
        self.current_map_name = "untitled.csv"

    def resize_map(self, new_width, new_height):
        old_height = len(self.current_map_data)
        old_width = len(self.current_map_data[0]) if old_height > 0 else 0
        new_grid = [[[] for _ in range(new_width)] for _ in range(new_height)]
        for y in range(min(old_height, new_height)):
            for x in range(min(old_width, new_width)):
                new_grid[y][x] = self.current_map_data[y][x]
        self.current_map_data = new_grid

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
            if pos[0] < SCREEN_WIDTH - PALETTE_WIDTH and pos[1] > TOP_BAR_HEIGHT and pos[1] < SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT:
                grid_x, grid_y = self.screen_to_grid(pos)
                if 0 <= grid_y < len(self.current_map_data) and 0 <= grid_x < len(self.current_map_data[0]):
                    cell_data = self.current_map_data[grid_y][grid_x]
                    if cell_data:
                        visible_objects = self.get_visible_objects_in_cell(cell_data)
                        if visible_objects:
                            self.set_tooltip_from_object(visible_objects[-1])
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
                        if self.get_edit_mode() in ['paint_tap', 'edit']:
                            self.handle_tap(event.pos)
                self.is_dragging = False
            if event.type == pygame.MOUSEMOTION and self.is_dragging:
                mode = self.get_edit_mode()
                if self.drag_start_pos[0] < SCREEN_WIDTH - PALETTE_WIDTH:
                    if mode == 'pan':
                        self.camera_x -= event.rel[0]
                        self.camera_y -= event.rel[1]
                    elif mode == 'paint_drag':
                        self.handle_drag_paint(event.pos)
                else:
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
            self.tooltip_text = "Gumka: Usuwa obiekt z aktywnej/najwyższej warstwy"
            return
        obj_def = None
        if isinstance(item_data, str) and item_data in globals():
            obj_def = globals()[item_data]
        elif isinstance(item_data, dict):
            obj_def = item_data
        if obj_def:
            self.set_tooltip_from_object(obj_def, palette_name)
    
    def set_tooltip_from_object(self, obj_data, name_override=None):
        obj_id = obj_data.get('id')
        props = SPRITE_PROPERTIES.get(obj_id, {})
        name = name_override if name_override else props.get('name', 'Nieznany')
        
        tooltip_str = f"{name} (ID: {obj_id})"
        if obj_id in [46, 47]:
            tx = obj_data.get('target_x', '?')
            ty = obj_data.get('target_y', '?')
            tf = obj_data.get('target_floor', '?')
            tooltip_str += f" -> (X:{tx}, Y:{ty}, F:{tf})"
        
        self.tooltip_text = f"{tooltip_str} | Właściwości: {str(obj_data)}"

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
                elif name == "new": self.dialog_mode = 'new_map'; self.dialog_map_width = DEFAULT_GRID_WIDTH; self.dialog_map_height = DEFAULT_GRID_HEIGHT
                elif name == "resize":
                    self.dialog_mode = 'resize_map'
                    self.dialog_map_height = len(self.current_map_data)
                    self.dialog_map_width = len(self.current_map_data[0]) if self.dialog_map_height > 0 else 0
                elif name == "load":
                    self.dialog_mode = 'load_browser'
                    map_dir = "assets/maps"
                    try:
                        if not os.path.exists(map_dir):
                            os.makedirs(map_dir)
                        self.available_files = [f for f in os.listdir(map_dir) if f.endswith('.csv')]
                    except Exception as e:
                        self.available_files = []
                        print(f"Błąd odczytu folderu map: {e}")
                    self.dialog_scroll_y = 0
                elif name == "save": self.save_map_to_csv(self.current_map_name)
                elif name == "save_as": 
                    self.dialog_mode = 'save_as_keyboard'
                    self.input_text = self.current_map_name.replace(".csv","")
                return True
        return False
    
    def handle_tap(self, pos):
        if pos[0] >= SCREEN_WIDTH - PALETTE_WIDTH: return
        grid_x, grid_y = self.screen_to_grid(pos)
        
        mode = self.get_edit_mode()

        if mode == 'paint_tap':
            self.place_object_on_grid(grid_x, grid_y)
        
        elif mode == 'edit':
            if not (0 <= grid_y < len(self.current_map_data) and 0 <= grid_x < len(self.current_map_data[0])): return
            cell_data = self.current_map_data[grid_y][grid_x]
            if not cell_data: return
            
            obj_to_edit = sorted(cell_data, key=lambda i: i.get('z', 0))[-1]
            
            if obj_to_edit.get('id') in [46, 47]:
                new_targets = self.prompt_for_portal_target(existing_data=obj_to_edit)
                if new_targets:
                    obj_to_edit['target_x'] = new_targets[0]
                    obj_to_edit['target_y'] = new_targets[1]
                    obj_to_edit['target_floor'] = new_targets[2]
                    print(f"Zaktualizowano portal na ({grid_x}, {grid_y}) do -> {new_targets}")


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
        if not (0 <= y < len(self.current_map_data) and 0 <= x < len(self.current_map_data[0])): return
        
        cell = self.current_map_data[y][x]
        tool = self.current_tool
        
        if tool == "ERASER":
            if not cell: return
            if self.view_z_level is not None:
                obj_to_remove = next((obj for obj in cell if isinstance(obj, dict) and obj.get('z') == self.view_z_level), None)
                if obj_to_remove: cell.remove(obj_to_remove)
                return
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

            if obj_to_place.get('id') in [46, 47]:
                targets = self.prompt_for_portal_target()
                if targets:
                    obj_to_place['target_x'] = targets[0]
                    obj_to_place['target_y'] = targets[1]
                    obj_to_place['target_floor'] = targets[2]
                else:
                    return 

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
        start_x, end_x = math.floor(self.camera_x / effective_tile_size), math.ceil((self.camera_x + grid_surface_width) / effective_tile_size)
        start_y, end_y = math.floor(self.camera_y / effective_tile_size), math.ceil((self.camera_y + SCREEN_HEIGHT) / effective_tile_size)
        
        if not self.current_map_data: return

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if not (0 <= y < len(self.current_map_data) and 0 <= x < len(self.current_map_data[0])): continue
                
                rect = pygame.Rect(int(x * effective_tile_size - self.camera_x), int(y * effective_tile_size - self.camera_y), effective_tile_size, effective_tile_size)
                
                if effective_tile_size > 8: pygame.draw.rect(self.screen, COLOR_GRID_LINES, rect, 1)
                
                visible_objects = self.get_visible_objects_in_cell(self.current_map_data[y][x])

                for obj_to_draw in visible_objects:
                    obj_id = obj_to_draw.get('id')
                    if obj_id in self.sprite_images:
                        self.screen.blit(pygame.transform.scale(self.sprite_images[obj_id], rect.size), rect.topleft)
                    else:
                        props = SPRITE_PROPERTIES.get(obj_id, {})
                        color = OBJECT_COLORS.get(props.get("type", "default"), OBJECT_COLORS["default"])
                        pygame.draw.rect(self.screen, color, rect.inflate(-2, -2))
                    
                if visible_objects:
                    top_object = visible_objects[-1]
                    if effective_tile_size > 40:
                        id_text = f"ID:{top_object.get('id', '?')}"
                        self.screen.blit(self.font_small.render(id_text, True, COLOR_TEXT), (rect.x + 5, rect.y + 5))
                        z_text = f"Z:{top_object.get('z', '?')}"
                        self.screen.blit(self.font_small.render(z_text, True, COLOR_TEXT), (rect.x + 5, rect.y + 25))
                    
                    if len(self.current_map_data[y][x]) > 1:
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
                text_surf = self.font_medium.render(name, True, COLOR_TEXT)
                self.screen.blit(text_surf, text_surf.get_rect(center=rect.center))
            y_offset += 60

    def draw_ui(self):
        pygame.draw.rect(self.screen, (40,40,40), (0,0,SCREEN_WIDTH - PALETTE_WIDTH, TOP_BAR_HEIGHT))
        x_offset, top_y = 20, (TOP_BAR_HEIGHT - 70) // 2
        btn_w, btn_h, margin = 160, 70, 10
        buttons_spec = {"new":"Nowa", "resize":"Zmień Rozmiar", "load":"Wczytaj", "save":"Zapisz", "save_as":"Zapisz jako"}
        for i, (name, text) in enumerate(buttons_spec.items()):
            rect = pygame.Rect(x_offset + i * (btn_w + margin), top_y, btn_w, btn_h)
            self.ui_buttons[name] = rect
            color = (0, 130, 0) if name == "save" else COLOR_BUTTON
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            text_surf = self.font_medium.render(text, True, COLOR_TEXT)
            self.screen.blit(text_surf, text_surf.get_rect(center=rect.center))
        
        pygame.draw.rect(self.screen, (40,40,40), (0, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT, SCREEN_WIDTH - PALETTE_WIDTH, BOTTOM_BAR_HEIGHT))
        bottom_y = SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + (BOTTOM_BAR_HEIGHT - 70) // 2
        
        mode_rect = pygame.Rect(20, bottom_y, 360, 70)
        self.ui_buttons["toggle_mode"] = mode_rect
        mode_texts = {"pan": "🖐️ Przesuwanie", "paint_tap": "👆 Stawianie", "paint_drag": "🎨 Rysowanie", "edit": "✍️ Edycja"}
        current_mode_text = f"Tryb: {mode_texts[self.get_edit_mode()]}"
        pygame.draw.rect(self.screen, COLOR_BUTTON, mode_rect, border_radius=8)
        text_surf = self.font_medium.render(current_mode_text, True, COLOR_TEXT)
        self.screen.blit(text_surf, text_surf.get_rect(center=mode_rect.center))

        x_offset = mode_rect.right + 20
        self.ui_buttons["zoom_out"] = pygame.Rect(x_offset, bottom_y, 70, 70); x_offset += 70
        zoom_text = f"Zoom: {self.zoom:.1f}x"; z_surf = self.font_medium.render(zoom_text, True, COLOR_TEXT); z_rect = z_surf.get_rect(left=x_offset+10, centery=mode_rect.centery); x_offset = z_rect.right + 10
        self.ui_buttons["zoom_in"] = pygame.Rect(x_offset, bottom_y, 70, 70); x_offset += 70 + 20
        self.ui_buttons["place_z_minus"] = pygame.Rect(x_offset, bottom_y, 70, 70); x_offset += 70
        place_text = f"Poziom Z: {self.place_z_level}"; p_surf = self.font_medium.render(place_text, True, COLOR_TEXT); p_rect = p_surf.get_rect(left=x_offset+10, centery=mode_rect.centery); x_offset = p_rect.right + 10
        self.ui_buttons["place_z_plus"] = pygame.Rect(x_offset, bottom_y, 70, 70); x_offset += 70 + 20
        self.ui_buttons["view_z_minus"] = pygame.Rect(x_offset, bottom_y, 70, 70); x_offset += 70
        view_text = f"Widok Z: {self.view_z_level if self.view_z_level is not None else 'All'}"; v_surf = self.font_medium.render(view_text, True, COLOR_TEXT); v_rect = pygame.Rect(x_offset+10, bottom_y, v_surf.get_width()+20, 70); x_offset = v_rect.right+10
        self.ui_buttons["view_z_all"] = v_rect
        self.ui_buttons["view_z_plus"] = pygame.Rect(x_offset, bottom_y, 70, 70)
        
        for name, rect in self.ui_buttons.items():
            if name in ["zoom_out", "place_z_minus", "view_z_minus"]:
                 pygame.draw.rect(self.screen, COLOR_BUTTON, rect, border_radius=8); self.screen.blit(self.font_large.render("-", True, COLOR_TEXT), self.font_large.render("-", True, COLOR_TEXT).get_rect(center=rect.center))
            elif name in ["zoom_in", "place_z_plus", "view_z_plus"]:
                 pygame.draw.rect(self.screen, COLOR_BUTTON, rect, border_radius=8); self.screen.blit(self.font_large.render("+", True, COLOR_TEXT), self.font_large.render("+", True, COLOR_TEXT).get_rect(center=rect.center))
        self.screen.blit(z_surf, z_rect); self.screen.blit(p_surf, p_rect)
        pygame.draw.rect(self.screen, COLOR_BUTTON_ACTIVE if self.view_z_level is None else COLOR_BUTTON, v_rect, border_radius=8); self.screen.blit(v_surf, v_surf.get_rect(center=v_rect.center))
        
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
                if data['rect'].collidepoint(pos):
                    if self.dialog_mode in ['new_map', 'resize_map']:
                        if name == 'w_plus': self.dialog_map_width += 1
                        elif name == 'w_minus': self.dialog_map_width = max(1, self.dialog_map_width - 1)
                        elif name == 'h_plus': self.dialog_map_height += 1
                        elif name == 'h_minus': self.dialog_map_height = max(1, self.dialog_map_height - 1)
                        elif name == 'ok':
                            (self.create_new_map if self.dialog_mode == 'new_map' else self.resize_map)(self.dialog_map_width, self.dialog_map_height)
                            self.dialog_mode = None
                        elif name == 'cancel': self.dialog_mode = None
                    elif self.dialog_mode == 'load_browser':
                        if name == 'cancel': self.dialog_mode = None
                        elif name.startswith("file_"): self.load_map_from_csv(data['filename']); self.dialog_mode = None
                    elif self.dialog_mode == 'save_as_keyboard':
                        if name == 'ok': self.save_map_to_csv(self.input_text + ".csv"); self.dialog_mode = None
                        elif name == 'cancel': self.dialog_mode = None
                        elif name == 'backspace': self.input_text = self.input_text[:-1]
                        elif name.startswith('key_'): self.input_text += data['char']
        if event.type == pygame.MOUSEMOTION and self.is_dragging and self.dialog_mode == 'load_browser':
             self.dialog_scroll_y += event.rel[1]
             max_scroll = len(self.available_files) * 60 - 500
             self.dialog_scroll_y = max(min(self.dialog_scroll_y, 0), -max_scroll if max_scroll > 0 else 0)

    def draw_dialog(self):
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); s.fill(COLOR_DIALOG_BG); self.screen.blit(s, (0,0))
        self.dialog_widgets.clear()
        box_w, box_h = 1000, 800
        box_rect = pygame.Rect((SCREEN_WIDTH - box_w)/2, (SCREEN_HEIGHT - box_h)/2, box_w, box_h)
        pygame.draw.rect(self.screen, (30,30,40), box_rect, border_radius=15)
        pygame.draw.rect(self.screen, COLOR_BUTTON_ACTIVE, box_rect, 5, border_radius=15)
        title_text = {"new_map": "Nowa Mapa", "resize_map": "Zmień Rozmiar Mapy", "load_browser": "Wczytaj Mapę", "save_as_keyboard": "Zapisz jako..."}.get(self.dialog_mode, "")
        title = self.font_large.render(title_text, True, COLOR_TEXT); self.screen.blit(title, title.get_rect(centerx=box_rect.centerx, y=box_rect.y + 40))
        cancel_btn_rect = pygame.Rect(box_rect.right - 300, box_rect.bottom - 120, 250, 80)
        self.dialog_widgets['cancel'] = {'rect':cancel_btn_rect}; pygame.draw.rect(self.screen, (150,0,0), cancel_btn_rect, border_radius=8); self.screen.blit(self.font_medium.render("Anuluj", True, COLOR_TEXT), self.font_medium.render("Anuluj", True, COLOR_TEXT).get_rect(center=cancel_btn_rect.center))
        if self.dialog_mode in ['new_map', 'resize_map']:
            for i, (label, val) in enumerate([("Szerokość", self.dialog_map_width), ("Wysokość", self.dialog_map_height)]):
                y_pos = box_rect.y + 150 + i * 100; prefix = 'w' if i == 0 else 'h'
                text_surf = self.font_medium.render(f"{label}: {val}", True, COLOR_TEXT); self.screen.blit(text_surf, (box_rect.x + 100, y_pos))
                self.dialog_widgets[f'{prefix}_minus'] = {'rect':pygame.Rect(box_rect.x + 550, y_pos - 10, 80, 80)}; self.screen.blit(self.font_large.render("-", True, COLOR_TEXT), self.font_large.render("-", True, COLOR_TEXT).get_rect(center=self.dialog_widgets[f'{prefix}_minus']['rect'].center))
                self.dialog_widgets[f'{prefix}_plus'] = {'rect':pygame.Rect(box_rect.x + 650, y_pos - 10, 80, 80)}; self.screen.blit(self.font_large.render("+", True, COLOR_TEXT), self.font_large.render("+", True, COLOR_TEXT).get_rect(center=self.dialog_widgets[f'{prefix}_plus']['rect'].center))
                pygame.draw.rect(self.screen, COLOR_BUTTON, self.dialog_widgets[f'{prefix}_minus']['rect'], border_radius=8); pygame.draw.rect(self.screen, COLOR_BUTTON, self.dialog_widgets[f'{prefix}_plus']['rect'], border_radius=8)
            ok_text = "Stwórz" if self.dialog_mode == 'new_map' else "Zmień"
            ok_btn = pygame.Rect(box_rect.x + 50, box_rect.bottom - 120, 250, 80); self.dialog_widgets['ok'] = {'rect':ok_btn}
            pygame.draw.rect(self.screen, (0,150,0), ok_btn, border_radius=8); self.screen.blit(self.font_medium.render(ok_text, True, COLOR_TEXT), self.font_medium.render(ok_text, True, COLOR_TEXT).get_rect(center=ok_btn.center))
        elif self.dialog_mode == 'load_browser':
            y_offset = box_rect.y + 120 + self.dialog_scroll_y
            for filename in self.available_files:
                if box_rect.y + 100 < y_offset < box_rect.bottom - 140:
                    file_rect = pygame.Rect(box_rect.x + 50, y_offset, box_w - 100, 50)
                    self.dialog_widgets[f"file_{filename}"] = {'rect':file_rect, 'filename': filename}
                    pygame.draw.rect(self.screen, COLOR_BUTTON, file_rect, border_radius=8); self.screen.blit(self.font_medium.render(filename, True, COLOR_TEXT), self.font_medium.render(filename, True, COLOR_TEXT).get_rect(center=file_rect.center))
                y_offset += 60
        elif self.dialog_mode == 'save_as_keyboard':
            input_rect = pygame.Rect(box_rect.x + 50, box_rect.y + 120, box_w - 100, 80)
            pygame.draw.rect(self.screen, (20,20,20), input_rect, border_radius=8); pygame.draw.rect(self.screen, COLOR_TEXT, input_rect, 2, border_radius=8)
            cursor = "|" if int(pygame.time.get_ticks()/500) % 2 == 0 else ""; self.screen.blit(self.font_medium.render(self.input_text + cursor + ".csv", True, COLOR_TEXT), (input_rect.x + 15, input_rect.y + 20))
            keys = "qwertyuiopasdfghjklzxcvbnm_1234567890"
            key_size, margin, start_kx, start_ky = 75, 10, box_rect.x + (box_w - 10 * (75 + 10) + 10)/2, box_rect.y + 250
            kx, ky = start_kx, start_ky
            for i, char in enumerate(keys):
                if i in [10, 19]: kx, ky = start_kx, ky + key_size + margin
                key_rect = pygame.Rect(kx, ky, key_size, key_size); self.dialog_widgets[f"key_{char}"] = {'rect':key_rect, 'char':char}
                pygame.draw.rect(self.screen, COLOR_BUTTON, key_rect, border_radius=8); self.screen.blit(self.font_medium.render(char, True, COLOR_TEXT), self.font_medium.render(char, True, COLOR_TEXT).get_rect(center=key_rect.center)); kx += key_size + margin
            back_rect = pygame.Rect(start_kx + 10 * (key_size + margin), start_ky, key_size*2, key_size); self.dialog_widgets['backspace'] = {'rect':back_rect}; pygame.draw.rect(self.screen, (150,50,50), back_rect, border_radius=8); self.screen.blit(self.font_medium.render("BS", True, COLOR_TEXT), self.font_medium.render("BS", True, COLOR_TEXT).get_rect(center=back_rect.center))
            ok_btn = pygame.Rect(box_rect.x + 50, box_rect.bottom - 120, 250, 80); self.dialog_widgets['ok'] = {'rect':ok_btn}; pygame.draw.rect(self.screen, (0,150,0), ok_btn, border_radius=8); self.screen.blit(self.font_medium.render("OK", True, COLOR_TEXT), self.font_medium.render("OK", True, COLOR_TEXT).get_rect(center=ok_btn.center))
    
    def save_map_to_csv(self, filename):
        if not filename: return
        if not filename.endswith(".csv"): filename += ".csv"
        
        map_dir = "assets/maps"
        if not os.path.exists(map_dir):
            os.makedirs(map_dir)
        
        filepath = os.path.join(map_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows([[cell_to_string(cell) for cell in row] for row in self.current_map_data])
            self.current_map_name = filename
            print(f"Pomyślnie zapisano: {filepath}")
        except Exception as e:
            print(f"Błąd zapisu: {e}")

    def load_map_from_csv(self, filename):
        map_dir = "assets/maps"
        filepath = os.path.join(map_dir, filename)

        if not (filename.endswith(".csv") and os.path.exists(filepath)):
            print(f"Błąd: Plik '{filepath}' nie istnieje."); return
        try:
            with open(filepath, 'r', newline='', encoding='utf-8') as f:
                self.current_map_data = [[process_map_cell(cell) for cell in row] for row in csv.reader(f)]
            self.current_map_name = filename
            print(f"Pomyślnie wczytano: {filepath}")
        except Exception as e:
            print(f"Błąd wczytywania {filepath}: {e}")

if __name__ == '__main__':
    editor = MapEditorTouch()
    editor.run()