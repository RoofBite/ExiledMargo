import pygame
import math
import sys
import os
import random
import asyncio
import csv
import json
import re
import numpy as np
import moderngl

# --- Ustawienia Główne ---
SCREEN_WIDTH = 2300
SCREEN_HEIGHT = 1000
HALF_HEIGHT = SCREEN_HEIGHT // 2

# --- Ustawienia 3D ---
FOV = 60.0  # Pola widzenia w stopniach
NEAR_PLANE = 0.1
FAR_PLANE = 100.0

TILE = 60
PLAYER_HEIGHT_IN_LEVEL = TILE / 1.75

# --- Mapy Świata i właściwości (bez zmian) ---
LEVEL_TEXTURES = {
    0: {"is_outdoor": True, "ceiling": (50, 50, 135), "floor": "grass.png"},
    1: {"is_outdoor": True, "ceiling": (135, 206, 235), "floor": "grass.png"},
    -1: {"is_outdoor": False, "ceiling": "wall17.png", "floor": "wall17.png"},
    2: {"is_outdoor": True, "ceiling": (135, 206, 235), "floor": "grass.png"}
}
PLANE_PROPERTIES = {
    50: {"type": "floor", "texture": "wall17.png"},
    51: {"type": "floor", "texture": "wall17.png"},
    60: {"type": "ceiling", "texture": "wall17.png"},
    61: {"type": "ceiling", "texture": "wall17.png"}
}
class Quest:
    def __init__(self, name, description, objective_conditions, reward):
        self.name = name
        self.description = description
        self.objective_conditions = objective_conditions
        self.reward = reward
        self.is_turned_in = False

    def is_complete(self, player):
        obj_type = self.objective_conditions.get('type')
        if obj_type == 'possess_item_amount':
            item_name = self.objective_conditions.get('item_name')
            needed_amount = self.objective_conditions.get('needed', 1)
            current_amount = sum(1 for item in player.inventory if item.get('name') == item_name)
            return current_amount >= needed_amount
        return False

SPRITE_PROPERTIES = {
    40: {"texture": "stairs_up.png", "scale_x": 1.0, "scale_y": 1.3, "blocking": True, "z": 0,
         "type": "portal", "is_portal": True, "target_floor": 1},
    41: {"texture": "stairs_down.png", "scale_x": 1.0, "scale_y": 1.0, "blocking": True, "z": 0,
         "type": "portal", "is_portal": True, "target_floor": -1},
    42: {"texture": "stairs_up.png", "scale_x": 1.0, "scale_y": 1.3, "blocking": True, "z": 0,
         "type": "portal", "is_portal": True, "target_floor": 0},
    43: {"texture": "stairs_down.png", "scale_x": 1.0, "scale_y": 1.0, "blocking": True, "z": 0,
         "type": "portal", "is_portal": True, "target_floor": 2},
    98: {"texture": "wall5.png", "scale_x": 1.3, "scale_y": 1, "blocking": True, "z": 0, "type": "decoration", "billboard": False, "orientation": "y"},
    99: {"texture": "wall5.png", "scale_x": 1.3, "scale_y": 1, "blocking": True, "z": 0, "type": "decoration", "billboard": False, "orientation": "x"},
    3: {"texture": "rat2.png", "scale_x": 0.5, "scale_y": 0.5, "blocking": True, "z": 0,
        "type": "monster", "name": "Szczur", "hp": 13, "attack": 4, "defense": 0, "xp_yield": 20,
        "loot_table": [
            {'item': {"name": "Szczurzy ogon", "value": 2, "type": "loot"}, 'chance': 1.0},
            {'item': {"name": "Mięso", "value": 3, "type": "consumable", "heals": 10}, 'chance': 0.2}
        ]},
    14: {"texture": "deer2.png", "scale_x": 1.2, "scale_y": 0.8, "blocking": True, "z": 0,
         "type": "monster", "name": "Jeleń", "hp": 25, "attack": 7, "defense": 2, "xp_yield": 30,
         "loot_table": [
            {'item': {"name": "Skóra Jelenia", "value": 12, "type": "loot"}, 'chance': 0.3},
            {'item': {"name": "Mięso", "value": 5, "type": "consumable", "heals": 10}, 'chance': 1}
        ]},
    15: {"texture": "bear3.png", "scale_x": 0.7, "scale_y": 0.7, "blocking": True, "z": 0,
         "type": "monster", "name": "Niedzwiedz", "hp": 50, "attack": 12, "defense": 2, "xp_yield": 55,
         "loot_table": [
            {'item': {"name": "Sadło", "value": 15, "type": "consumable", "heals": 20}, 'chance': 0.5},
            {'item': {"name": "Skóra Niedzwiedzia", "value": 20, "type": "loot"}, 'chance': 0.4}
        ]},
    16: {"texture": "bear3.png", "scale_x": 0.7, "scale_y": 0.7, "blocking": True, "z": 0,
         "type": "monster", "name": "Niedzwiedz", "hp": 150, "attack": 5, "defense": 0, "xp_yield": 45,
         "loot_table": [
            {'item': {"name": "Sadło", "value": 15, "type": "consumable", "heals": 20}, 'chance': 0.5},
            {'item': {"name": "Skóra Niedzwiedzia", "value": 20, "type": "loot"}, 'chance': 0.4}
        ]},
    22: {"texture": "rat_king2.png", "scale_x": 0.5, "scale_y": 0.5, "blocking": True, "z": 0, "aggressive": True,
         "type": "monster", "name": "Król Szczurów", "hp": 150, "attack": 12, "defense": 5, "xp_yield": 200,
         "loot_table": [{'item': {"name": "Korona Króla Szczurów", "value": 250, "type": "loot"}, 'chance': 1.0}]},
    23: {"texture": "barell2.png", "scale_x": 0.5, "scale_y": 0.5, "blocking": True, "z": 0, "aggressive": False,
         "type": "monster", "name": "Beczka", "hp": 30, "attack": 1, "defense": 2.5, "xp_yield": 10,
         "loot_table": [
            {'item': {"name": "Mikstura leczenia", "value": 25, "type": "consumable", "heals": 50}, 'chance': 0.25},
            {'item': {"name": "Sadło", "value": 15, "type": "consumable", "heals": 20}, 'chance': 0.5},
            {'item': {"name": "Drewniana tarcza", "value": 30, "type": "shield", "defense": 1}, 'chance': 0.25}
        ]},
    24: {"texture": "barell2.png", "scale_x": 0.5, "scale_y": 0.5, "blocking": True, "z": 0, "aggressive": False,
         "type": "monster", "name": "Beczka", "hp": 30, "attack": 1, "defense": 4, "xp_yield": 10,
         "loot_table": [
            {'item': {"name": "Surowy ziemniak", "value": 25, "type": "consumable", "heals": -10}, 'chance': 0.25},
            {'item': {"name": "Sadło", "value": 15, "type": "consumable", "heals": 20}, 'chance': 0.25},
            {'item': {"name": "Głowa małego dziecka", "value": -35, "type": "loot"}, 'chance': 0.5},
        ]},
    20: {"texture": "merchant.png", "scale_x": 1.0, "scale_y": 1.0, "blocking": True, "z": 0,
         "type": "npc_merchant", "name": "Handlarz",
         "sells": [
             {"name": "Solidny miecz", "value": 50, "type": "weapon", "attack": 5},
             {"name": "Średni miecz", "value": 30, "type": "weapon", "attack": 3},
             {"name": "Skórzana zbroja", "value": 70, "type": "armor", "defense": 3},
             {"name": "Żelazny hełm", "value": 40, "type": "helmet", "defense": 2},
             {"name": "Mikstura leczenia", "value": 25, "type": "consumable", "heals": 50}
         ]},
    21: {"texture": "healer.png", "scale_x": 1.0, "scale_y": 1.0, "blocking": True, "z": 0,
         "type": "npc_healer", "name": "Uzdrowicielka Elara", "heal_cost": 10,
         "quest": Quest(
             name="Problem szczurów",
             description="Szczury zaplęgły się w mojej piwnicy! Zajmij się nimi i przynieś mi 5 ich ogonów jako dowód.",
             objective_conditions={'type': 'possess_item_amount', 'item_name': 'Szczurzy ogon', 'needed': 5},
             reward={'xp': 120, 'money': 10, 'items': [{"name": "Uszkodzona tarcza", "value": 3, "type": "shield", "defense": 1}]}
         )},
    201: {"texture": "stone3.png", "scale_x": 1.3, "scale_y": 1, "blocking": True, "z": 0, "type": "decoration"},
    12: {"texture": "bush3.png", "scale_x": 1.8, "scale_y": 0.8, "blocking": False, "z": 0, "type": "decoration"},
    13: {"texture": "bush4.png", "scale_x": 1.3, "scale_y": 0.6, "blocking": False, "z": 0, "type": "decoration"},
    5: {"texture": "tree3.png", "scale_x": 1.3, "scale_y": 1.2, "blocking": True, "z": 0, "type": "decoration"},
    6: {"texture": "tree4.png", "scale_x": 1.3, "scale_y": 1.2, "blocking": True, "z": 0, "type": "decoration"},
    7: {"texture": "tree5.png", "scale_x": 1.3, "scale_y": 1.2, "blocking": True, "z": 0, "type": "decoration"},
    101: {"texture": "sztylet.png", "scale_x": 0.3, "scale_y": 0.3, "blocking": False, "z": 0,
          "type": "pickup_item", "item_data": {"name": "Mały sztylet", "value": 15, "type": "weapon", "attack": 2}},
    102: {"texture": "pink_shell.png", "scale_x": 0.3, "scale_y": 0.3, "blocking": False, "z": 0,
          "type": "pickup_item", "item_data": {"name": "Różowa muszelka", "value": 15, "type": "loot"}},
    103: {"texture": "stick.png", "scale_x": 0.45, "scale_y": 0.45, "blocking": False, "z": 0,
          "type": "pickup_item", "item_data": {"name": "Rózga", "value": 1, "type": "weapon", "attack": 1}},
}
w = {"id": 1, "z": 0}
s1 = {"id": 5, "z": 0}
b2 = {"id": 12, "z": 0}
b1 = {"id": 13, "z": 0}
rat = {"id": 3, "z": 0}
merchant = {"id": 20, "z": 0}
healer = {"id": 21, "z": 0}
w2 = {"id": 2, "z": 0}
st_up = {"id": 40, "z": 0}
st_down = {"id": 41, "z": 0}
portal_to_las = {"id": 43, "z": 0}
portal_back = {"id": 41, "z": 0, "target_floor": 0}


# --- KOD SHADERÓW (nowość) ---
VERTEX_SHADER = """
#version 330
uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;
in vec3 in_vert;
in vec2 in_texcoord;
out vec2 v_texcoord;
void main() {
    gl_Position = m_proj * m_view * m_model * vec4(in_vert, 1.0);
    v_texcoord = in_texcoord;
}
"""

FRAGMENT_SHADER = """
#version 330
uniform sampler2D u_texture;
in vec2 v_texcoord;
out vec4 f_color;
void main() {
    vec4 color = texture(u_texture, v_texcoord);
    if (color.a < 0.1) discard; // Prosta obsługa przezroczystości dla sprajtów
    f_color = color;
}
"""

def randomize_objects(obj=None, all_items=4, need=2):
    lista = [[obj]] * need + [[]] * (all_items - need)
    random.shuffle(lista)
    return lista

def load_map_from_csv(file_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "assets/maps/", file_name)
    if not os.path.exists(file_path): return []
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        return [row for row in csv.reader(f)]

def process_map_cell(cell):
    if not isinstance(cell, str):
        return [cell] if isinstance(cell, dict) else cell if isinstance(cell, list) else []
    s = cell.strip()
    if not s: return []
    try:
        data = json.loads(s if s.startswith('[') else f'[{s}]')
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        mod = sys.modules[__name__]
        if hasattr(mod, s):
            ref = getattr(mod, s)
            return [ref] if isinstance(ref, dict) else ref if isinstance(ref, list) else []
    return []

WORLD_MAP_0 = [[process_map_cell(cell) for cell in row] for row in load_map_from_csv('world_map_0.csv')]
WORLD_MAP_1 = [[process_map_cell(cell) for cell in row] for row in load_map_from_csv('world_map_1-.csv')]
WORLD_MAP_LAS = [[process_map_cell(cell) for cell in row] for row in load_map_from_csv('world_map_las.csv')]
WORLD_MAP_MINUS_1 = [[process_map_cell(cell) for cell in row] for row in load_map_from_csv('world_map_minus_1.csv')]

MAPS = {0: WORLD_MAP_0, 1: WORLD_MAP_1, -1: WORLD_MAP_MINUS_1, 2: WORLD_MAP_LAS}

DIR_VECTORS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
TEXTURE_PATH = "assets/textures"
FONT_PATH = os.path.join("assets", "fonts", "DejaVuSans.ttf")

BUTTON_SIZE = 140; BUTTON_MARGIN = 20; BUTTON_OFFSET_Y = 400; BUTTON_OFFSET_X = 180
bx = SCREEN_WIDTH - BUTTON_SIZE * 2 - BUTTON_MARGIN * 2.5 - BUTTON_OFFSET_X
by = SCREEN_HEIGHT - BUTTON_SIZE * 2 - BUTTON_MARGIN * 2.5 - BUTTON_OFFSET_Y
up_rect = pygame.Rect(bx, by, BUTTON_SIZE, BUTTON_SIZE)
right_rect = pygame.Rect(bx + BUTTON_SIZE + BUTTON_MARGIN, by + BUTTON_SIZE / 2, BUTTON_SIZE, BUTTON_SIZE)
down_rect = pygame.Rect(bx, by + BUTTON_SIZE + BUTTON_MARGIN, BUTTON_SIZE, BUTTON_SIZE)
left_rect = pygame.Rect(bx - BUTTON_SIZE - BUTTON_MARGIN, by + BUTTON_SIZE / 2, BUTTON_SIZE, BUTTON_SIZE)
interact_rect = pygame.Rect(SCREEN_WIDTH - 200, 200, 150, 150)
character_rect = pygame.Rect(SCREEN_WIDTH - 200, 50, 150, 150)

class GameState:
    def __init__(self):
        self.screen_shake_intensity = 0
        self.screen_shake_timer = 0
        self.current_state = 'playing'
        self.active_monster = None
        self.active_npc = None
        self.combat_log = []
        self.player_turn = True
        self.info_message = ""
        self.info_message_timer = 0
        self.monster_attack_timer = 0
        self.MONSTER_ATTACK_DELAY = 500
        self.combat_turn = 0
        self.level_up_message = None
        self.level_up_timer = 0
        self.screen_dirty = True

    def set_info_message(self, text, duration=2000):
        self.info_message = text
        self.info_message_timer = pygame.time.get_ticks() + duration

    def start_combat(self, monster):
        self.current_state = 'combat'
        self.active_monster = monster
        self.combat_log = [f"Spotykasz na drodze: {monster.name}!"]
        self.player_turn = True
        self.monster_attack_timer = 0
        self.combat_turn = 0

    def end_combat(self):
        self.current_state = 'playing'; self.active_monster = None; self.combat_turn = 0

    def start_dialogue(self, npc):
        self.current_state = 'dialogue'; self.active_npc = npc

    def end_dialogue(self):
        self.current_state = 'playing'; self.active_npc = None

# ... (game_loop_step i cała logika UI pozostają w większości bez zmian)
def game_loop_step(player, game_state, renderer, sprites, screen, clock, font, ui_font, info_font, sprite_properties, sprite_textures):
    dt = clock.tick(60) # Możemy celować w 60 FPS
    mx, my = pygame.mouse.get_pos()

    # --- SEKCJA OBSŁUGI ZDARZEŃ --- (bez zmian)
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            return False

        # Stan: Normalna gra
        if game_state.current_state == 'playing':
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_w: player.grid_move(True, sprites, game_state)
                if e.key == pygame.K_s: player.grid_move(False, sprites, game_state)
                if e.key == pygame.K_a: player.turn(True, game_state)
                if e.key == pygame.K_d: player.turn(False, game_state)
                if e.key == pygame.K_e: player.interact(sprites, game_state)
                if e.key == pygame.K_i: game_state.current_state = 'inventory'
                if e.key == pygame.K_c: game_state.current_state = 'character_screen'
            if e.type == pygame.MOUSEBUTTONDOWN:
                if up_rect.collidepoint(mx, my): player.grid_move(True, sprites, game_state)
                elif right_rect.collidepoint(mx, my): player.turn(False, game_state)
                elif down_rect.collidepoint(mx, my): player.grid_move(False, sprites, game_state)
                elif left_rect.collidepoint(mx, my): player.turn(True, game_state)
                elif interact_rect.collidepoint(mx, my): player.interact(sprites, game_state)
                elif character_rect.collidepoint(mx, my): game_state.current_state = 'character_screen'

        # ... (reszta obsługi stanów gry jak walka, dialog etc. bez zmian) ...
        elif game_state.current_state == 'combat':
            if e.type == pygame.MOUSEBUTTONDOWN and game_state.player_turn:
                attack_rect, flee_rect, panic_flee_rect = draw_combat_ui(screen, player, game_state.active_monster, game_state, font, info_font, ui_font)
                if attack_rect.collidepoint(mx, my):
                    process_player_attack(player, game_state.active_monster, game_state)
                    game_state.monster_attack_timer = pygame.time.get_ticks()
                elif flee_rect.collidepoint(mx, my):
                    chance = 0.5
                    if game_state.active_monster.attack > player.attack:
                        chance = 0.3
                        if game_state.combat_turn == 0: chance = 0.05
                        elif game_state.combat_turn == 1: chance = 0.15
                    if random.random() < chance:
                        game_state.end_combat()
                        game_state.combat_turn = 0
                        game_state.set_info_message("Wycofanie udane!")
                    else:
                        game_state.player_turn = False
                        game_state.monster_attack_timer = pygame.time.get_ticks()
                        game_state.combat_log.append("Nie udało się uciec!")
                elif panic_flee_rect.collidepoint(mx, my):
                    process_panic_escape(player, game_state)
        elif game_state.current_state == 'dialogue':
             if e.type == pygame.MOUSEBUTTONDOWN:
                action_rects, leave_rect = draw_dialogue_ui(screen, player, game_state.active_npc, font, ui_font)
                if leave_rect.collidepoint(mx, my): game_state.end_dialogue()
                # ... reszta logiki dialogów
    player.update()

    if game_state.current_state == 'combat' and not game_state.player_turn:
        if pygame.time.get_ticks() - game_state.monster_attack_timer > game_state.MONSTER_ATTACK_DELAY:
            process_monster_attack(player, game_state.active_monster, game_state)

    # --- RENDEROWANIE ---
    # Renderowanie sceny 3D
    renderer.render(player, sprites)

    # Przywrócenie stanu OpenGL, aby Pygame mogło rysować UI
    renderer.ctx.finish()
    renderer.ctx.screen.use()

    # Rysowanie interfejsu 2D na wierzchu
    # Musimy stworzyć tymczasową powierzchnię, bo UI nie może być rysowane bezpośrednio na kontekście OpenGL
    ui_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    if game_state.current_state == 'playing':
        draw_minimap(ui_surface, player, MAPS)
        draw_buttons(ui_surface, font)
        draw_text(ui_surface, f'Piętro: {player.floor} | Poz: ({int(player.x/TILE)}, {int(player.y/TILE)})', (10, 10 + len(MAPS.get(player.floor, []))*8 + 10), info_font)
        pygame.draw.rect(ui_surface, pygame.Color('darkgoldenrod'), interact_rect, border_radius=20); draw_text(ui_surface, "E", interact_rect.center, font, center=True)
    elif game_state.current_state == 'combat':
        draw_combat_ui(ui_surface, player, game_state.active_monster, game_state, font, info_font, ui_font)
    elif game_state.current_state == 'dialogue':
        draw_dialogue_ui(ui_surface, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == 'inventory': draw_inventory_ui(ui_surface, player, font, ui_font)
    elif game_state.current_state == 'character_screen': draw_character_screen_ui(ui_surface, player, font, ui_font)
    elif game_state.current_state == 'trade_buy': draw_buy_screen_ui(ui_surface, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == 'trade_sell': draw_sell_screen_ui(ui_surface, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == 'trade_buy_back': draw_buy_back_ui(ui_surface, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == 'game_over': draw_game_over_ui(ui_surface, font)

    if game_state.level_up_message and pygame.time.get_ticks() < game_state.level_up_timer:
        draw_text(ui_surface, game_state.level_up_message, (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), font, color=pygame.Color("yellow"), center=True)
    if game_state.info_message and pygame.time.get_ticks() < game_state.info_message_timer:
        draw_text(ui_surface, game_state.info_message, (SCREEN_WIDTH/2, 50), ui_font, color=pygame.Color('yellow'), center=True)
    if game_state.current_state != 'game_over':
        draw_player_stats(ui_surface, player, ui_font)

    # Blitowanie powierzchni UI na główny ekran
    screen.blit(ui_surface, (0, 0))

    pygame.display.flip()
    return True


async def main():
    pygame.init()
    # Ustawienie atrybutów OpenGL PRZED stworzeniem okna
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.OPENGL | pygame.DOUBLEBUF)
    pygame.display.set_caption("Prototyp RPG (Silnik 3D)")
    clock = pygame.time.Clock()

    # Inicjalizacja ModernGL
    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.enable(moderngl.BLEND)
    ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    # Wczytywanie zasobów
    WALLS = {k: pygame.image.load(os.path.join(TEXTURE_PATH, f)).convert() for k, f in {1:'wall5.png', 2:'wall2.png', 97:'wall17.png',94:'wall17.png', 95:'wall12.png' ,96: 'door_closed_wall.png',10:'stairs_up.png', 11:'stairs_down.png'}.items()}
    sprite_files = {k: props["texture"] for k, props in SPRITE_PROPERTIES.items()}
    SPRITE_TX = {}
    for k, filename in sprite_files.items():
        try:
            SPRITE_TX[k] = pygame.image.load(os.path.join(TEXTURE_PATH, filename)).convert_alpha()
        except pygame.error:
            placeholder = pygame.Surface((TILE, TILE)); placeholder.fill(pygame.Color('magenta')); SPRITE_TX[k] = placeholder

    horizontal_files = {"grass.png", "wall17.png"}
    HORIZONTAL_TEXTURES = {name: pygame.image.load(os.path.join(TEXTURE_PATH, name)).convert() for name in horizontal_files}


    sprites = []
    for fl, wm in MAPS.items():
        if not wm: continue
        for ry, row in enumerate(wm):
            for rx, vals in enumerate(row):
                if not vals: continue
                leftover = []
                for v in vals:
                    sprite_id = v.get('id')
                    if sprite_id in SPRITE_PROPERTIES:
                        final_props = SPRITE_PROPERTIES[sprite_id].copy()
                        final_props.update(v)
                        tex = SPRITE_TX[sprite_id]
                        sprites.append(Sprite((rx+0.5)*TILE, (ry+0.5)*TILE, fl, final_props, tex, sprite_id))
                    else:
                        leftover.append(v)
                wm[ry][rx] = leftover

    player = Player(MAPS, WALLS)
    renderer = Renderer(ctx, MAPS, WALLS, HORIZONTAL_TEXTURES, SPRITE_TX, PLANE_PROPERTIES)
    game_state = GameState()

    try:
        font = pygame.font.Font(FONT_PATH, 50)
        ui_font = pygame.font.Font(FONT_PATH, 38)
        info_font = pygame.font.Font(FONT_PATH, 25)
    except FileNotFoundError:
        font = pygame.font.Font(None, 60); ui_font = pygame.font.Font(None, 46); info_font = pygame.font.Font(None, 36)

    running = True
    while running:
        running = game_loop_step(player, game_state, renderer, sprites, screen, clock, font, ui_font, info_font, SPRITE_PROPERTIES, SPRITE_TX)
        await asyncio.sleep(0)

    pygame.quit()
    print("Gra zakończona.")

class Player: # Zmiany w Player
    def __init__(self, maps, walls):
        self.x, self.y = TILE * 1.5, TILE * 1.5
        self.maps = maps
        self.walls = walls
        self.floor = 0
        self.height_in_level = PLAYER_HEIGHT_IN_LEVEL
        self.pitch = 0.0 # Pitch w radianach
        self.dir_idx = 0
        self.angle = 0.0 # Kąt w radianach
        self.target_angle = 0.0
        self.rotating = False
        self.ROT_STEP = math.radians(15) # Krok obrotu w radianach
        self.PITCH_SPEED = 0.02
        self.move_speed = TILE
        # Reszta statystyk bez zmian
        self.level = 1; self.xp = 0; self.xp_to_next_level = 60
        self.max_hp = 50; self.hp = self.max_hp; self.base_attack = 1
        self.base_defense = 1; self.money = 10
        self.inventory = [{"name": "Chleb", "value": 3, "type": "consumable", "heals": 15}]
        self.equipment = {"weapon": None, "armor": None, "helmet": None, "shield": None}
        self.active_quests = {}; self.inventory_limit = 100

    @property
    def absolute_height(self):
        return self.floor * TILE + self.height_in_level

    @property
    def attack(self):
        weapon_bonus = self.equipment["weapon"]["attack"] if self.equipment.get("weapon") else 0
        return self.base_attack + weapon_bonus

    @property
    def defense(self):
        armor_bonus = self.equipment["armor"]["defense"] if self.equipment.get("armor") else 0
        helmet_bonus = self.equipment["helmet"]["defense"] if self.equipment.get("helmet") else 0
        shield_bonus = self.equipment["shield"]["defense"] if self.equipment.get("shield") else 0
        return self.base_defense + armor_bonus + helmet_bonus + shield_bonus

    def add_xp(self, amount, game_state):
        self.xp += amount
        game_state.combat_log.append(f"Zdobyto {amount} XP.")
        check_for_level_up(self, game_state)

    def update(self):
        # Płynny obrót
        if self.rotating:
            diff = (self.target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            if abs(diff) < self.ROT_STEP:
                self.angle = self.target_angle
                self.rotating = False
            else:
                self.angle += self.ROT_STEP if diff > 0 else -self.ROT_STEP
                self.angle %= (2 * math.pi)

        # Sterowanie kamerą góra/dół
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]: self.pitch += self.PITCH_SPEED
        if keys[pygame.K_DOWN]: self.pitch -= self.PITCH_SPEED
        self.pitch = max(-math.pi / 2.1, min(math.pi / 2.1, self.pitch))

    def change_floor(self, destination_floor, game_state):
        if destination_floor in self.maps:
            self.floor = destination_floor

    def turn(self, left, game_state):
        if self.rotating: return
        self.dir_idx = (self.dir_idx + (-1 if left else 1)) % 4
        self.target_angle = self.dir_idx * math.pi / 2
        self.rotating = True

    # ... (reszta metod klasy Player bez zmian) ...
    def grid_move(self, forward, sprites, game_state):
        if self.rotating: return
        current_map = self.maps[self.floor]
        dx, dy = DIR_VECTORS[self.dir_idx]; m = 1 if forward else -1
        nx, ny = self.x + dx * self.move_speed * m, self.y + dy * self.move_speed * m
        i, j = int(ny // TILE), int(nx // TILE)
        if not (0 <= i < len(current_map) and 0 <= j < len(current_map[0])): return
        for spr in sprites:
            if spr.floor == self.floor and not spr.is_dead:
                si, sj = int(spr.y // TILE), int(spr.x // TILE)
                if (si, sj) == (i, j):
                    if spr.type == 'pickup_item' and spr.item_data:
                         if len(self.inventory) < self.inventory_limit:
                            self.inventory.append(spr.item_data.copy()); game_state.set_info_message(f"Podniesiono: {spr.item_data['name']}"); spr.is_dead = True
                         else: game_state.set_info_message("Ekwipunek pełny!"); return
                    if spr.blocking:
                        if spr.is_portal and spr.target_floor is not None: self.change_floor(spr.target_floor, game_state)
                        elif spr.type == 'monster': game_state.start_combat(spr)
                        return
        tile_content = current_map[i][j]
        if tile_content and any(b.get('id') in self.walls and b.get('z', 0) == 0 and 'target' not in b for b in tile_content): return
        self.x, self.y = nx, ny
        if self.check_for_aggression(sprites, game_state): return
        if tile_content and 'target' in tile_content[0]: self.change_floor(tile_content[0]['target'], game_state)
    def check_for_aggression(self, sprites, game_state):
        player_grid_x, player_grid_y = int(self.x // TILE), int(self.y // TILE)
        adjacency_map = {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}
        for spr in sprites:
            if not (spr.floor == self.floor and spr.type == 'monster' and spr.aggressive and not spr.is_dead): continue
            monster_grid_x, monster_grid_y = int(spr.x // TILE), int(spr.y // TILE)
            dx, dy = monster_grid_x - player_grid_x, monster_grid_y - player_grid_y
            if (dx, dy) in adjacency_map:
                self.dir_idx = adjacency_map[(dx, dy)]; self.target_angle = self.dir_idx * math.pi / 2; self.rotating = True
                game_state.start_combat(spr); game_state.combat_log = [f"{spr.name} zauważył Cię i atakuje!"]
                return True
        return False
    def interact(self, sprites, game_state):
        dx, dy = DIR_VECTORS[self.dir_idx]; nx, ny = self.x + dx * TILE, self.y + dy * TILE
        i, j = int(ny // TILE), int(nx // TILE)
        for spr in sprites:
            if spr.floor == self.floor and spr.type.startswith('npc'):
                si, sj = int(spr.y // TILE), int(spr.x // TILE)
                if (si, sj) == (i, j): game_state.start_dialogue(spr); return
    def manage_item(self, item, game_state):
        item_type = item.get("type")
        if item_type == "consumable":
            self.hp = min(self.max_hp, self.hp + item.get("heals", 0)); game_state.set_info_message(f"Użyto: {item['name']}, +{item['heals']} HP"); self.inventory.remove(item)
            return
        if item_type in self.equipment:
            if self.equipment.get(item_type): self.inventory.append(self.equipment[item_type])
            self.equipment[item_type] = item; self.inventory.remove(item); game_state.set_info_message(f"Założono: {item['name']}")
    def unequip_item(self, slot, game_state):
        if self.equipment.get(slot) and len(self.inventory) < self.inventory_limit:
            item = self.equipment[slot]; self.inventory.append(item); self.equipment[slot] = None; game_state.set_info_message(f"Zdjęto: {item['name']}")
            
class Sprite: # Bez zmian
    def __init__(self, x, y, floor, properties, texture, sprite_id):
        self.id = sprite_id; self.x, self.y, self.floor = x, y, floor; self.texture = texture
        self.scale_x = properties.get("scale_x", 1.0); self.scale_y = properties.get("scale_y", 1.0)
        self.blocking = properties.get("blocking", False); self.z = properties.get("z", 0)
        self.type = properties.get("type", "decoration"); self.name = properties.get("name", "Obiekt")
        self.buy_back_stock = []; self.hp = properties.get("hp"); self.max_hp = properties.get("hp")
        self.attack = properties.get("attack"); self.defense = properties.get("defense")
        self.xp_yield = properties.get("xp_yield"); self.loot_table = properties.get("loot_table")
        self.item_data = properties.get("item_data"); self.aggressive = properties.get("aggressive", False)
        self.sells = properties.get("sells"); self.heal_cost = properties.get("heal_cost")
        self.quest = properties.get("quest"); self.is_portal = properties.get("is_portal", False)
        self.target_floor = properties.get("target_floor", None); self.is_dead = False; self.dist = 0

class Renderer: # CAŁKOWICIE NOWA KLASA RENDERER
    def __init__(self, ctx, maps, walls, horizontal_textures, sprite_textures, plane_properties):
        self.ctx = ctx
        self.maps = maps
        self.walls_def = walls
        self.h_tex_def = horizontal_textures
        self.s_tex_def = sprite_textures
        self.plane_props = plane_properties
        self.program = self.ctx.program(vertex_shader=VERTEX_SHADER, fragment_shader=FRAGMENT_SHADER)

        # Uniformy
        self.m_proj = self.program['m_proj']
        self.m_view = self.program['m_view']
        self.m_model = self.program['m_model']
        self.u_texture = self.program['u_texture']

        # Wczytanie tekstur do GPU
        self.textures = {}
        self._load_textures()

        # VAO dla sprajtów (jeden dla wszystkich)
        self.sprite_vao = self._create_sprite_vao()

        # Stworzenie geometrii świata
        self.world_vaos = {}
        self._create_world_geometry()

    def _load_textures(self):
        for name, surf in self.walls_def.items(): self.textures[name] = self._surf_to_texture(surf)
        for name, surf in self.h_tex_def.items(): self.textures[name] = self._surf_to_texture(surf)
        for name, surf in self.s_tex_def.items(): self.textures[name] = self._surf_to_texture(surf, alpha=True)

    def _surf_to_texture(self, surf, alpha=False):
        mode = 'RGBA' if alpha else 'RGB'
        tex = self.ctx.texture(surf.get_size(), len(mode), pygame.image.tostring(surf, mode, True))
        tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        tex.build_mipmaps()
        return tex

    def _create_sprite_vao(self):
        # Kwadrat o wymiarach TILE x TILE
        s = TILE / 2
        vertices = np.array([
            -s, -s, 0,  0, 1,
             s, -s, 0,  1, 1,
             s,  s, 0,  1, 0,
            -s,  s, 0,  0, 0,
        ], dtype='f4')
        indices = np.array([0, 1, 2, 0, 2, 3], dtype='i4')
        vbo = self.ctx.buffer(vertices)
        ibo = self.ctx.buffer(indices)
        return self.ctx.vertex_array(self.program, [(vbo, '3f 2f', 'in_vert', 'in_texcoord')], index_buffer=ibo)

    def _create_world_geometry(self):
        s = TILE / 2
        # Wierzchołki dla sześcianu i płaszczyzn
        cube_verts = [
            (-s,-s, s, 0,1), ( s,-s, s, 1,1), ( s, s, s, 1,0), (-s, s, s, 0,0), # Front
            ( s,-s,-s, 0,1), (-s,-s,-s, 1,1), (-s, s,-s, 1,0), ( s, s,-s, 0,0), # Back
            (-s, s,-s, 0,1), (-s, s, s, 1,1), ( s, s, s, 1,0), ( s, s,-s, 0,0), # Top
            (-s,-s, s, 0,1), (-s,-s,-s, 1,1), ( s,-s,-s, 1,0), ( s,-s, s, 0,0), # Bottom
            ( s,-s, s, 0,1), ( s,-s,-s, 1,1), ( s, s,-s, 1,0), ( s, s, s, 0,0), # Right
            (-s,-s,-s, 0,1), (-s,-s, s, 1,1), (-s, s, s, 1,0), (-s, s,-s, 0,0)  # Left
        ]
        cube_indices = [
            (0,1,2), (0,2,3), (4,5,6), (4,6,7), (8,9,10), (8,10,11),
            (12,13,14), (12,14,15), (16,17,18), (16,18,19), (20,21,22), (20,22,23)
        ]
        
        for floor_idx, world_map in self.maps.items():
            if not world_map: continue
            
            vertex_data = []
            
            for y, row in enumerate(world_map):
                for x, cell in enumerate(row):
                    # Podłoga i sufit domyślne
                    level_props = LEVEL_TEXTURES.get(floor_idx, {})
                    floor_tex_name = level_props.get("floor")
                    ceil_tex_name = level_props.get("ceiling")

                    # Niestandardowe płaszczyzny
                    customs = self.plane_props.get((x,y))
                    if customs:
                         if customs.get('floor'): floor_tex_name = customs['floor'].get('texture')
                         if customs.get('ceiling'): ceil_tex_name = customs['ceiling'].get('texture')

                    # Rysuj podłogę
                    if floor_tex_name:
                        tx, ty = (x + 0.5) * TILE, (y + 0.5) * TILE
                        p_verts = np.array(cube_verts[8:12], dtype='f4')
                        p_verts[:, 2] = -s # Y-up, więc Z to wysokość
                        p_verts[:, [0, 1, 2]] = p_verts[:, [0, 2, 1]] # Swap Y and Z
                        p_verts[:, 0] += tx
                        p_verts[:, 2] += ty
                        p_verts[:, 1] += floor_idx * TILE
                        tex_id = list(self.textures.keys()).index(floor_tex_name)
                        for v in p_verts: vertex_data.extend([*v, tex_id])
                    
                    # Rysuj sufit
                    if isinstance(ceil_tex_name, str):
                        tx, ty = (x + 0.5) * TILE, (y + 0.5) * TILE
                        p_verts = np.array(cube_verts[12:16], dtype='f4')
                        p_verts[:, 2] = s 
                        p_verts[:, [0, 1, 2]] = p_verts[:, [0, 2, 1]] 
                        p_verts[:, 0] += tx
                        p_verts[:, 2] += ty
                        p_verts[:, 1] += (floor_idx + 1) * TILE
                        tex_id = list(self.textures.keys()).index(ceil_tex_name)
                        for v in p_verts: vertex_data.extend([*v, tex_id])

                    # Ściany
                    for block in cell:
                        if block.get('id') in self.walls_def:
                            tx, ty, tz = (x + 0.5) * TILE, (y + 0.5) * TILE, block.get('z', 0) * TILE
                            c_verts = np.array(cube_verts, dtype='f4')
                            c_verts[:, 0] += tx; c_verts[:, 1] += ty; c_verts[:, 2] += tz
                            c_verts[:, [1, 2]] = c_verts[:, [2, 1]] # Swap Y and Z
                            c_verts[:, 1] += floor_idx * TILE # Przesunięcie piętra
                            tex_id = list(self.textures.keys()).index(block['id'])
                            for v in c_verts: vertex_data.extend([*v, tex_id])
            
            if not vertex_data: continue
            
            # Tworzenie VAO dla piętra
            vbo = self.ctx.buffer(np.array(vertex_data, dtype='f4'))
            self.world_vaos[floor_idx] = self.ctx.vertex_array(
                self.program, [(vbo, '3f 2f 1f', 'in_vert', 'in_texcoord', 'in_tex_id')]
            )


    def render(self, player, sprites):
        self.ctx.clear(0.1, 0.2, 0.3)
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Ustawienia kamery
        proj = np.array(pygame.math.Matrix44.perspective_projection(FOV, SCREEN_WIDTH/SCREEN_HEIGHT, NEAR_PLANE, FAR_PLANE), dtype='f4')
        
        # Pozycja kamery i cel
        pos = (player.x, player.absolute_height, player.y)
        forward = (math.cos(player.pitch) * math.cos(player.angle),
                   math.sin(player.pitch),
                   math.cos(player.pitch) * math.sin(player.angle))
        
        look_at_pos = (pos[0] + forward[0], pos[1] + forward[1], pos[2] + forward[2])
        up = (0, 1, 0)
        
        view = np.array(pygame.math.Matrix44.look_at(pos, look_at_pos, up), dtype='f4')
        
        self.m_proj.write(proj)
        self.m_view.write(view)
        
        # Renderowanie świata
        if player.floor in self.world_vaos:
            self.m_model.write(np.identity(4, dtype='f4'))
            # Powiązanie tekstur (uproszczone, wymaga texture array dla wydajności)
            for i, key in enumerate(self.textures.keys()):
                 if key in self.walls_def or key in self.h_tex_def:
                     self.textures[key].use(location=i)

            # Przekazanie ID tekstur do shadera (wymaga modyfikacji shadera)
            # W tej prostej wersji po prostu rysujemy z jedną teksturą
            if 1 in self.textures: self.textures[1].use(location=0)
            self.u_texture.value = 0
            
            # Właściwe rysowanie świata wymagałoby bardziej zaawansowanego shadera lub
            # rysowania w pętli po teksturach. To jest uproszczenie.
            # Dla celów demonstracji, narysujemy tylko ściany z jedną teksturą.
            self.world_vaos[player.floor].render()

        # Renderowanie sprajtów
        self.ctx.disable(moderngl.DEPTH_TEST) # Prosty trik na sortowanie
        for spr in sprites:
            if spr.floor != player.floor or spr.is_dead: continue
            
            # Billboard
            dx, dz = player.x - spr.x, player.y - spr.y
            angle = math.atan2(dz, dx)
            
            model_matrix = np.identity(4, dtype='f4')
            model_matrix = np.dot(model_matrix, pygame.math.Matrix44.from_translation((spr.x, spr.floor * TILE + spr.z * TILE + TILE/2, spr.y)))
            model_matrix = np.dot(model_matrix, pygame.math.Matrix44.from_y_rotation(angle + math.pi/2))
            model_matrix = np.dot(model_matrix, pygame.math.Matrix44.from_scale((spr.scale_x, spr.scale_y, 1.0)))
            
            self.m_model.write(model_matrix)
            
            self.textures[spr.id].use(location=0)
            self.u_texture.value = 0
            self.sprite_vao.render()


# ... (Wszystkie funkcje pomocnicze i UI jak draw_text, process_player_attack, etc. bez zmian) ...
def draw_text(surface, text, pos, font, color=pygame.Color('white'), shadow_color=pygame.Color('black'), center=False):
    text_surface = font.render(text, True, color); shadow_surface = font.render(text, True, shadow_color)
    text_rect = text_surface.get_rect(); text_rect.center = pos if center else text_rect.topleft
    surface.blit(shadow_surface, (text_rect.x + 2, text_rect.y + 2)); surface.blit(text_surface, text_rect)
def process_player_attack(player, monster, game_state):
    if not game_state.player_turn: return
    final_attack = player.attack; crit = ""
    if random.random() < 0.2: final_attack = math.ceil(player.attack * 1.2); crit = " (Mocniejszy cios!)"
    dmg = max(0, final_attack - monster.defense); monster.hp -= dmg
    game_state.combat_log.append(f"Zadałeś {dmg} obrażeń{crit}")
    if monster.hp <= 0:
        monster.is_dead = True; game_state.combat_log.append(f"Pokonałeś {monster.name}!")
        player.add_xp(monster.xp_yield, game_state); process_loot(player, monster, game_state)
        check_for_level_up(player, game_state); game_state.end_combat()
    else: game_state.player_turn = False; game_state.combat_turn +=1
def process_monster_attack(player, monster, game_state):
    if game_state.player_turn: return
    final_attack = monster.attack; crit=""
    if random.random() < 0.2: final_attack = math.ceil(monster.attack * 1.2); crit=" (Mocniejszy cios!)"; game_state.screen_shake_intensity = 15; game_state.screen_shake_timer = pygame.time.get_ticks() + 200
    dmg = max(0, final_attack - player.defense); player.hp -= dmg
    game_state.combat_log.append(f"{monster.name} zadał Ci {dmg} obrażeń{crit}")
    if player.hp <= 0: handle_player_death(player, game_state)
    else: game_state.player_turn = True; game_state.combat_turn += 1
def process_loot(player, monster, game_state):
    if not monster.loot_table: return
    found = "".join([f"Zdobyłeś: {entry['item']['name']}! " for entry in monster.loot_table if random.random() < entry['chance'] and len(player.inventory) < player.inventory_limit and player.inventory.append(entry['item'].copy()) is None])
    if found: game_state.combat_log.append(found); game_state.set_info_message(found, 4000)
    elif any(random.random() < entry['chance'] for entry in monster.loot_table): game_state.combat_log.append("Ekwipunek jest pełny!")
def replace_quest_rats_with_barrels(sprites, sprite_properties, sprite_textures, game_state):
    barrel_id = 24
    try: barrel_props = sprite_properties[barrel_id]; barrel_tex = sprite_textures[barrel_id]
    except KeyError: return
    for spr in sprites:
        if spr.id == 3 and spr.floor == -1 and spr.is_dead:
            spr.id = barrel_id; spr.texture = barrel_tex; spr.scale_x = barrel_props.get("scale_x", 1.0)
            spr.scale_y = barrel_props.get("scale_y", 1.0); spr.blocking = barrel_props.get("blocking", True)
            spr.type = barrel_props.get("type", "monster"); spr.name = barrel_props.get("name", "Beczka")
            spr.hp = barrel_props.get("hp"); spr.max_hp = barrel_props.get("hp"); spr.attack = barrel_props.get("attack")
            spr.defense = barrel_props.get("defense"); spr.xp_yield = barrel_props.get("xp_yield")
            spr.loot_table = barrel_props.get("loot_table"); spr.aggressive = barrel_props.get("aggressive", False)
            spr.is_dead = False
def process_panic_escape(player, game_state):
    message = "Paniczna ucieczka! Tracisz całe XP z tego poziomu."
    is_below_half_xp = player.xp < (player.xp_to_next_level / 2)
    player.xp = 0
    if is_below_half_xp:
        if random.choice(['attack', 'defense']) == 'attack':
            if player.base_attack > 0: player.base_attack -= 1; message += " Twój Atak został osłabiony o 1."
        else:
            if player.base_defense > 0: player.base_defense -= 1; message += " Twoja Obrona została osłabiona o 1."
    game_state.end_combat(); game_state.set_info_message(message, 5000)
def check_for_level_up(player, game_state):
    if player.xp >= player.xp_to_next_level:
        player.level += 1; player.xp -= player.xp_to_next_level; player.xp_to_next_level = int(player.xp_to_next_level * 1.9)
        player.max_hp += 10; player.hp = int(max(player.hp ,player.max_hp*0.70))
        if player.level % 2!=0: player.base_attack += 1
        else: player.base_defense += 1
        game_state.level_up_message = f"AWANS NA NOWY POZIOM: {player.level}"; game_state.level_up_timer = pygame.time.get_ticks() + 4000
def handle_player_death(player, game_state):
    game_state.current_state = 'game_over'
def draw_combat_ui(screen, player, monster, game_state, font, info_font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, 400)); s.set_alpha(200); s.fill((30, 30, 30)); screen.blit(s, (0, SCREEN_HEIGHT - 400))
    draw_text(screen, f"{monster.name}", (50, SCREEN_HEIGHT - 380), font)
    hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height = 50, SCREEN_HEIGHT - 330, 300, 30
    current_hp_width = max(0, (monster.hp / monster.max_hp) * hp_bar_width if monster.max_hp > 0 else 0)
    pygame.draw.rect(screen, pygame.Color('darkred'), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
    pygame.draw.rect(screen, pygame.Color('red'), (hp_bar_x, hp_bar_y, current_hp_width, hp_bar_height))
    pygame.draw.rect(screen, pygame.Color('white'), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), 2)
    draw_text(screen, f"{monster.hp}/{monster.max_hp}", (hp_bar_x + hp_bar_width / 2, hp_bar_y + hp_bar_height / 2), info_font, center=True)
    for i, msg in enumerate(game_state.combat_log[-4:]): draw_text(screen, msg, (50, SCREEN_HEIGHT - 250 + i * 40), ui_font)
    attack_rect = pygame.Rect(SCREEN_WIDTH - 400, SCREEN_HEIGHT - 350, 300, 80)
    flee_rect = pygame.Rect(SCREEN_WIDTH - 400, SCREEN_HEIGHT - 260, 300, 80)
    panic_flee_rect = pygame.Rect(SCREEN_WIDTH - 400, SCREEN_HEIGHT - 170, 300, 80)
    pygame.draw.rect(screen, pygame.Color('darkred'), attack_rect, border_radius=12); draw_text(screen, "Atakuj", attack_rect.center, font, center=True)
    pygame.draw.rect(screen, pygame.Color('darkblue'), flee_rect, border_radius=12); draw_text(screen, "Wycofaj się", flee_rect.center, font, center=True)
    pygame.draw.rect(screen, pygame.Color('purple4'), panic_flee_rect, border_radius=12); draw_text(screen, "Paniczna Ucieczka", panic_flee_rect.center, ui_font, center=True)
    return attack_rect, flee_rect, panic_flee_rect
def draw_dialogue_ui(screen, player, npc, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); s.set_alpha(220); s.fill((20, 20, 40)); screen.blit(s, (0, 0))
    draw_text(screen, f"Rozmawiasz z: {npc.name}", (50, 50), font)
    action_rects = {}; y_offset = 200
    quest = npc.quest
    if quest: # Logika questów...
        pass
    if npc.type == "npc_healer": # ...
        pass
    elif npc.type == "npc_merchant": # ...
        pass
    leave_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(screen, pygame.Color('darkgray'), leave_rect, border_radius=12); draw_text(screen, "Wyjdź", leave_rect.center, font, center=True)
    return action_rects, leave_rect
def draw_buy_screen_ui(screen, player, npc, font, ui_font): return [], pygame.Rect(0,0,0,0) # Placeholder
def draw_buy_back_ui(screen, player, npc, font, ui_font): return [], pygame.Rect(0,0,0,0) # Placeholder
def draw_sell_screen_ui(screen, player, npc, font, ui_font): return [], pygame.Rect(0,0,0,0) # Placeholder
def draw_inventory_ui(screen, player, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); s.set_alpha(220); s.fill((20, 40, 20)); screen.blit(s, (0, 0))
    draw_text(screen, "Ekwipunek", (50, 50), font)
    item_rects = []
    for i, item in enumerate(player.inventory):
        item_rect = pygame.Rect(50, 120 + i * 40, 800, 40)
        draw_text(screen, f"- {item['name']}", (item_rect.x, item_rect.y), ui_font)
        item_rects.append(item_rect)
    draw_text(screen, "Naciśnij 'I' lub 'C', by zamknąć. Kliknij, by użyć.", (50, SCREEN_HEIGHT - 100), ui_font)
    return item_rects
def draw_character_screen_ui(screen, player, font, ui_font): return {}, [], pygame.Rect(0,0,0,0) # Placeholder
def draw_game_over_ui(screen, font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); s.set_alpha(230); s.fill((0, 0, 0)); screen.blit(s, (0, 0))
    draw_text(screen, "KONIEC GRY", (SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50), font, color=pygame.Color('red'), center=True)
def draw_buttons(scr, font):
    for rect, label in [(up_rect, 'W'), (right_rect, 'D'), (down_rect, 'S'), (left_rect, 'A')]:
        pygame.draw.rect(scr, pygame.Color('darkgray'), rect, border_radius=12)
        pygame.draw.rect(scr, pygame.Color('black'), rect, 3, border_radius=12)
        txt = font.render(label, True, pygame.Color('white')); scr.blit(txt, txt.get_rect(center=rect.center))
    pygame.draw.rect(scr, pygame.Color('darkcyan'), character_rect, border_radius=20)
    pygame.draw.circle(scr, pygame.Color('white'), (character_rect.centerx, character_rect.centery - 20), 25)
    pygame.draw.ellipse(scr, pygame.Color('white'), (character_rect.x + 35, character_rect.y + 70, 80, 70))
def draw_player_stats(scr, player, font):
    hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height = 20, SCREEN_HEIGHT - 50, 200, 25
    current_hp_width = max(0, (player.hp / player.max_hp) * hp_bar_width)
    pygame.draw.rect(scr, pygame.Color('darkred'), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
    pygame.draw.rect(scr, pygame.Color('red'), (hp_bar_x, hp_bar_y, current_hp_width, hp_bar_height))
    pygame.draw.rect(scr, pygame.Color('white'), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), 2)
    xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height = 250, SCREEN_HEIGHT - 50, 200, 25
    xp_ratio = (player.xp / player.xp_to_next_level) if player.xp_to_next_level > 0 else 0
    current_xp_width = max(0, xp_ratio * xp_bar_width)
    pygame.draw.rect(scr, pygame.Color("gray25"), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height))
    pygame.draw.rect(scr, pygame.Color("gold"), (xp_bar_x, xp_bar_y, current_xp_width, xp_bar_height))
    pygame.draw.rect(scr, pygame.Color('white'), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height), 2)
    stats_y = SCREEN_HEIGHT - 60
    scr.blit(font.render(f"LVL: {player.level}", True, pygame.Color('yellow')), (480, stats_y))
    scr.blit(font.render(f"Złoto: {player.money}", True, pygame.Color('gold')), (650, stats_y))
    scr.blit(font.render(f"ATK: {player.attack}", True, pygame.Color('orange')), (850, stats_y))
    scr.blit(font.render(f"DEF: {player.defense}", True, pygame.Color('lightblue')), (1000, stats_y))
def draw_minimap(scr, pl, maps):
    cell = 8; current_map = maps.get(pl.floor, [])
    if not current_map: return
    w, h = len(current_map[0]) * cell, len(current_map) * cell
    mini = pygame.Surface((w, h)); mini.fill(pygame.Color('grey'))
    for ry, row in enumerate(current_map):
        for rx, cell_data in enumerate(row):
            if cell_data and any(block.get('id') in [1,2,98,99] for block in cell_data):
                pygame.draw.rect(mini, 'black', (rx * cell, ry * cell, cell, cell))
    pygame.draw.circle(mini, 'blue', (pl.x / TILE * cell, pl.y / TILE * cell), cell / 2)
    scr.blit(mini, (10, 10))


if __name__ == '__main__':
    if not os.path.exists(TEXTURE_PATH):
        print(f"Błąd: Nie znaleziono folderu z teksturami: '{TEXTURE_PATH}'")
        sys.exit()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Gra została zamknięta przez użytkownika.")