import pygame
import math
import sys
import os
import random
import asyncio

# --- Ustawienia Główne ---
SCREEN_WIDTH = 2300
SCREEN_HEIGHT = 1000
HALF_HEIGHT = SCREEN_HEIGHT // 2

# --- Ustawienia Raycastingu ---
FOV = math.pi / 2.5
HALF_FOV = FOV / 2
NUM_RAYS = 400
MAX_DEPTH = 50
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * math.tan(HALF_FOV))
PROJ_COEFF = 3 * DIST * 60
TILE = 60
PLAYER_HEIGHT_IN_LEVEL = TILE / 2

### NOWOŚĆ: Klasa do przechowywania danych o zadaniach ###
class Quest:
    def __init__(self, name, description, objective, reward):
        self.name = name
        self.description = description
        self.objective = objective # np. {'type': 'kill', 'target': 'Szczur', 'needed': 5}
        self.reward = reward       # np. {'xp': 100, 'money': 50}
        self.progress = 0
        self.is_complete = False
        self.is_turned_in = False # Flaga zapobiegająca ponownemu wzięciu questa

    def update_progress(self, target_name):
        if not self.is_complete and self.objective['type'] == 'kill' and self.objective['target'] == target_name:
            self.progress += 1
            if self.progress >= self.objective['needed']:
                self.is_complete = True

SPRITE_PROPERTIES = {
        
    40: {"texture": "stairs_up.png", "scale_x": 1.0, "scale_y": 1.0, "blocking": True, "z": 0,
         "type": "portal", "is_portal": True, "target_floor": 1},
    41: {"texture": "stairs_down.png", "scale_x": 1.0, "scale_y": 1.0, "blocking": True, "z": 0,
         "type": "portal", "is_portal": True, "target_floor": -1},
     42: {"texture": "stairs_up.png", "scale_x": 1.0, "scale_y": 1.0, "blocking": True, "z": 0,
         "type": "portal", "is_portal": True, "target_floor": 0},

    3: {"texture": "rat.png", "scale_x": 0.5, "scale_y": 0.5, "blocking": True, "z": 0,
        "type": "monster", "name": "Szczur", "hp": 15, "attack": 3, "defense": 0, "xp_yield": 10,
        "loot_table": {
            frozenset({"name": "Szczurzy ogon", "value": 2, "type": "loot"}.items()): 0.8,
            frozenset({"name": "Mięso", "value": 5, "type": "consumable", "heals": 10}.items()): 0.2
        }},
    14: {"texture": "jelen02.png", "scale_x": 1.2, "scale_y": 0.8, "blocking": True, "z": 0,
         "type": "monster", "name": "Jeleń", "hp": 30, "attack": 6, "defense": 2, "xp_yield": 25, "loot_table": {}},
    22: {"texture": "rat_king.png", "scale_x": 0.5, "scale_y": 0.5, "blocking": True, "z": -15, "aggressive": True,
        "type": "monster", "name": "Król Szczurów", "hp": 150, "attack": 12, "defense": 5, "xp_yield": 200,
        "loot_table": {
            frozenset({"name": "Korona Króla Szczurów", "value": 250, "type": "loot"}.items()): 1.0
        }},

    # NPC
    20: {"texture": "merchant.png", "scale_x": 1.0, "scale_y": 1.0, "blocking": True, "z": 0,
         "type": "npc_merchant", "name": "Handlarz",
         "sells": [
             {"name": "Solidny miecz", "value": 50, "type": "weapon", "attack": 5},
             {"name": "Skórzana zbroja", "value": 70, "type": "armor", "defense": 3},
             {"name": "Żelazny hełm", "value": 40, "type": "helmet", "defense": 2},
             {"name": "Drewniana tarcza", "value": 30, "type": "shield", "defense": 1},
             {"name": "Mikstura leczenia", "value": 25, "type": "consumable", "heals": 50}
         ]},
    ### ZMIANA: Dodanie questa do Uzdrowicielki ###
    21: {"texture": "healer.png", "scale_x": 1.0, "scale_y": 1.0, "blocking": True, "z": 0,
         "type": "npc_healer", "name": "Uzdrowicielka Elara", "heal_cost": 10,
         "quest": Quest(
             name="Szczury w piwnicy",
             description="Oh, okropne szczury zalęgły się w mojej piwnicy! Czy mógłbyś się ich pozbyć?",
             objective={'type': 'kill', 'target': 'Szczur', 'needed': 5},
             reward={'xp': 100, 'money': 50}
         )},

    # Dekoracje
    13: {"texture": "bush2.png", "scale_x": 1.2, "scale_y": 0.8, "blocking": False, "z": 0, "type": "decoration"},
    5: {"texture": "tree2.png", "scale_x": 1.3, "scale_y": 1.2, "blocking": True, "z": 0, "type": "decoration"},
    4: {"texture": "item.png", "scale_x": 0.2, "scale_y": 0.2, "blocking": False, "z": TILE * 0.2, "type": "item"},
}


w = {"id": 1, "z": 0} # Zwykła ściana
s1 = {"id": 5, "z": 0} # Drzewo
rat = {"id": 3, "z": 0} # Szczur
merchant = {"id": 20, "z": 0}
healer = {"id": 21, "z": 0}
deer = {"id": 14, "z": 0}
rat_king = {"id": 22, "z": 0}
w2 = {"id": 2, "z": 0} # Ściana piwnicy

st_up_1 = {"id": 10, "z": 0, "target": 1} # Schody w górę na piętro 1
st_up_2 = {"id": 40, "z": 0, "target": 2} # Schody w górę na piętro 1
st_down_0 = {"id": 11, "z": 0, "target": 0} # Schody w dół na piętro 0
st_down_m1 = {"id": 11, "z": 0, "target": -1} # Schody w dół do piwnicy (-1)
st_up_0 = {"id": 42, "z": 0, "target": 0} # Schody w górę na piętro 0

# --- Szablony Kafelków ---
w = {"id": 1, "z": 0}
s1 = {"id": 5, "z": 0}
rat = {"id": 3, "z": 0}
merchant = {"id": 20, "z": 0}
healer = {"id": 21, "z": 0}
w2 = {"id": 2, "z": 0}

# NOWOŚĆ: Szablony dla schodów-sprajtów
st_up = {"id": 40, "z": 0} 
st_up_1 = {"id": 40, "z": 1}      
st_down = {"id": 41, "z": 0}    # Sprajt schodów w dół




# --- Mapy Świata ---
# Piętro 0: Miasto
WORLD_MAP_0 = [
    [[w],[w],[w],[w],[w],[w],[w],[w],[w],[w]],
    [[w],[],[],[],[],[],[],[],[],[w]],
    [[w],[st_up],[],[merchant],[],[],[healer],[],[],[st_down_m1]],
    [[w],[],[],[],[],[],[],[],[],[w]],
    [[w],[],[],[],[],[],[],[],[],[w]],
    [[w],[],[],[s1],[],[],[],[],[],[w]],
    [[w],[],[],[],[s1],[],[],[],[],[w]],
    [[w],[],[],[],[],[s1],[],[],[],[w]],
    [[w],[],[],[s1],[],[],[],[],[],[w]],
    [[w],[w],[w],[w],[w],[w],[w],[w],[w],[w]],
]
# Piętro 1: Dzicz / Lochy
WORLD_MAP_1 = [
    [[w],[w],[w],[w],[w],[w],[w],[w],[w],[w]],
    [[w],[w],[],[],[],[],[],[],[],[w]],
    [[],[st_down_0],[],[],[],[],[],[],[],[w]],
    [[w],[w],[],[],[],[],[],[],[],[w]],
    [[w],[],[],[],[{"id":1,"z":0},{"id":2,"z":1},{"id":1,"z":2}],[deer],[],[],[],[w]],
    [[w],[],[],[],[],[],[],[],[],[w]],
    [[w],[],[],[],[],[],[rat],[],[],[w]],
    [[w],[],[],[],[],[],[],[rat_king],[],[w]],
    [[w],[],[],[],[],[],[],[],[],[w]],
    [[w],[w],[w],[w],[w],[w],[w],[w],[w],[w]],
]
# Piętro -1: Piwnica
WORLD_MAP_MINUS_1 = [
    [[],[],[],[],[],[],[],[],[],[]],
    [[],[],[],[],[],[],[],[],[],[]],
    [[],[],[],[w2],[w2],[w2],[w2],[w2],[],[]],
    [[],[],[],[w2],[rat],[],[],[w2],[],[]],
    [[],[],[],[w2],[rat],[],[],[],[],[]],
    [[],[],[],[w2],[rat],[rat],[rat],[w2],[],[]],
    [[],[],[],[w2],[w2],[w2],[w2],[w2],[],[w2]],
    [[],[],[],[],[],[],[],[rat_king],[],[w2]],
    [[],[],[],[],[],[st_up_0],[],[],[],[w2]],
    [[],[],[],[],[],[],[],[],[],[w2]],
]

MAPS = {0: WORLD_MAP_0, 1: WORLD_MAP_1, -1: WORLD_MAP_MINUS_1}


DIR_VECTORS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
TEXTURE_PATH = "assets/textures"
FONT_PATH = os.path.join("assets", "fonts", "DejaVuSans.ttf")



# --- Przyciski UI ---
BUTTON_SIZE = 140; BUTTON_MARGIN = 20; BUTTON_OFFSET_Y = 400; BUTTON_OFFSET_X = 180
bx = SCREEN_WIDTH - BUTTON_SIZE * 2 - BUTTON_MARGIN * 2.5 - BUTTON_OFFSET_X
by = SCREEN_HEIGHT - BUTTON_SIZE * 2 - BUTTON_MARGIN * 2.5 - BUTTON_OFFSET_Y
up_rect = pygame.Rect(bx, by, BUTTON_SIZE, BUTTON_SIZE)
right_rect = pygame.Rect(bx + BUTTON_SIZE + BUTTON_MARGIN, by + BUTTON_SIZE / 2, BUTTON_SIZE, BUTTON_SIZE)
down_rect = pygame.Rect(bx, by + BUTTON_SIZE + BUTTON_MARGIN, BUTTON_SIZE, BUTTON_SIZE)
left_rect = pygame.Rect(bx - BUTTON_SIZE - BUTTON_MARGIN, by + BUTTON_SIZE / 2, BUTTON_SIZE, BUTTON_SIZE)
interact_rect = pygame.Rect(SCREEN_WIDTH - 200, 200, 150, 150)
character_rect = pygame.Rect(SCREEN_WIDTH - 200, 50, 150, 150)
# --- Klasa do zarządzania stanem gry ---
# KROK 1: Zastąp swoją starą klasę GameState tą wersją
class GameState:
    def __init__(self):
        self.current_state = 'playing'
        self.active_monster = None
        self.active_npc = None
        self.combat_log = []
        self.player_turn = True
        self.info_message = ""
        self.info_message_timer = 0
        # Przeniesione tutaj dla lepszego zarządzania stanem
        self.monster_attack_timer = 0
        self.MONSTER_ATTACK_DELAY = 500

    def set_info_message(self, text, duration=2000):
        self.info_message = text
        self.info_message_timer = pygame.time.get_ticks() + duration

    def start_combat(self, monster):
        self.current_state = 'combat'
        self.active_monster = monster
        self.combat_log = [f"Spotykasz na drodze: {monster.name}!"]
        self.player_turn = True
        self.monster_attack_timer = 0 # Resetuj timer przy starcie walki

    def end_combat(self):
        self.current_state = 'playing'
        self.active_monster = None

    def start_dialogue(self, npc):
        self.current_state = 'dialogue'
        self.active_npc = npc

    def end_dialogue(self):
        self.current_state = 'playing'
        self.active_npc = None


def game_loop_step(player, game_state, renderer, sprites, screen, clock, font, ui_font, info_font):
    dt = clock.tick(30)
    mx, my = pygame.mouse.get_pos()

    # --- SEKCJA OBSŁUGI ZDARZEŃ ---
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            return False # Zwróć False, aby zakończyć pętlę

        # Stan: Normalna gra
        if game_state.current_state == 'playing':
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_w: player.grid_move(True, sprites, game_state)
                if e.key == pygame.K_s: player.grid_move(False, sprites, game_state)
                if e.key == pygame.K_a: player.turn(True)
                if e.key == pygame.K_d: player.turn(False)
                if e.key == pygame.K_e: player.interact(sprites, game_state)
                if e.key == pygame.K_i: game_state.current_state = 'inventory'
                if e.key == pygame.K_c: game_state.current_state = 'character_screen'
            if e.type == pygame.MOUSEBUTTONDOWN:
                if up_rect.collidepoint(mx, my): player.grid_move(True, sprites, game_state)
                elif right_rect.collidepoint(mx, my): player.turn(False)
                elif down_rect.collidepoint(mx, my): player.grid_move(False, sprites, game_state)
                elif left_rect.collidepoint(mx, my): player.turn(True)
                elif interact_rect.collidepoint(mx, my): player.interact(sprites, game_state)
                elif character_rect.collidepoint(mx, my): game_state.current_state = 'character_screen'

        # Stan: Walka
        elif game_state.current_state == 'combat':
            if e.type == pygame.MOUSEBUTTONDOWN and game_state.player_turn:
                attack_rect, flee_rect = draw_combat_ui(screen, player, game_state.active_monster, game_state, font, ui_font)
                if attack_rect.collidepoint(mx, my):
                    process_player_attack(player, game_state.active_monster, game_state)
                    game_state.monster_attack_timer = pygame.time.get_ticks()
                elif flee_rect.collidepoint(mx, my):
                    if random.random() < 0.5:
                        game_state.end_combat()
                        game_state.set_info_message("Ucieczka udana!")
                    else:
                        game_state.player_turn = False
                        game_state.monster_attack_timer = pygame.time.get_ticks()
                        game_state.combat_log.append("Nie udało się uciec!")

        # Stan: Dialog
        elif game_state.current_state == 'dialogue':
            if e.type == pygame.MOUSEBUTTONDOWN:
                action_rects, leave_rect = draw_dialogue_ui(screen, player, game_state.active_npc, font, ui_font)
                if leave_rect.collidepoint(mx, my): game_state.end_dialogue()
                elif game_state.active_npc:
                    quest = game_state.active_npc.quest
                    if 'accept_quest' in action_rects and action_rects['accept_quest'].collidepoint(mx, my):
                        player.active_quests[quest.name] = quest; game_state.set_info_message(f"Przyjęto: {quest.name}"); game_state.end_dialogue()
                    elif 'complete_quest' in action_rects and action_rects['complete_quest'].collidepoint(mx, my):
                        player.xp += quest.reward['xp']; player.money += quest.reward['money']; quest.is_turned_in = True; del player.active_quests[quest.name]
                        game_state.set_info_message(f"Ukończono! Nagroda: {quest.reward['xp']} XP, {quest.reward['money']} zł.", 3000); game_state.end_dialogue()
                    elif 'heal' in action_rects and action_rects['heal'].collidepoint(mx,my):
                        if player.money >= game_state.active_npc.heal_cost:
                            player.money -= game_state.active_npc.heal_cost; player.hp = player.max_hp; game_state.set_info_message("Rany wyleczone.")
                        else: game_state.set_info_message("Brak złota.")
                    elif 'buy_screen' in action_rects and action_rects['buy_screen'].collidepoint(mx, my):
                        game_state.current_state = 'trade_buy'
                    elif 'sell_screen' in action_rects and action_rects['sell_screen'].collidepoint(mx, my):
                        game_state.current_state = 'trade_sell'

        # Stany: Ekrany UI
        elif game_state.current_state == 'inventory':
             if e.type == pygame.KEYDOWN and (e.key == pygame.K_i or e.key == pygame.K_c): game_state.current_state = 'playing'
             if e.type == pygame.MOUSEBUTTONDOWN:
                item_rects = draw_inventory_ui(screen, player, font, ui_font)
                for i, rect in enumerate(item_rects):
                    if rect.collidepoint(mx, my) and i < len(player.inventory): player.manage_item(player.inventory[i], game_state); break
        
        elif game_state.current_state == 'character_screen':
             if e.type == pygame.KEYDOWN and (e.key == pygame.K_c or e.key == pygame.K_i): game_state.current_state = 'playing'
             if e.type == pygame.MOUSEBUTTONDOWN:
                equip_rects, inventory_rects, leave_button_rect = draw_character_screen_ui(screen, player, font, ui_font)
                if leave_button_rect.collidepoint(mx, my): game_state.current_state = 'playing'
                else:
                    for i, rect in enumerate(inventory_rects):
                        if rect.collidepoint(mx, my) and i < len(player.inventory): player.manage_item(player.inventory[i], game_state); break
                    for slot, rect in equip_rects.items():
                        if rect.collidepoint(mx, my): player.unequip_item(slot, game_state); break

        elif game_state.current_state == 'trade_buy':
            if e.type == pygame.MOUSEBUTTONDOWN:
                buy_rects, back_button_rect = draw_buy_screen_ui(screen, player, game_state.active_npc, font, ui_font)
                if back_button_rect.collidepoint(mx, my): game_state.current_state = 'dialogue'
                else:
                    for i, rect in enumerate(buy_rects):
                        if rect.collidepoint(mx, my):
                            item_to_buy = game_state.active_npc.sells[i]
                            if player.money >= item_to_buy['value']:
                                if len(player.inventory) < player.inventory_limit:
                                    player.money -= item_to_buy['value']; player.inventory.append(item_to_buy.copy()); game_state.set_info_message(f"Kupiono: {item_to_buy['name']}")
                                else: game_state.set_info_message("Ekwipunek pełny!")
                            else: game_state.set_info_message("Za mało złota!")
                            break
        
        elif game_state.current_state == 'trade_sell':
             if e.type == pygame.MOUSEBUTTONDOWN:
                sell_rects, back_button_rect = draw_sell_screen_ui(screen, player, game_state.active_npc, font, ui_font)
                if back_button_rect.collidepoint(mx, my): game_state.current_state = 'dialogue'
                else:
                    for i, rect in enumerate(sell_rects):
                         if rect.collidepoint(mx, my) and i < len(player.inventory):
                            item_to_sell = player.inventory.pop(i); player.money += item_to_sell['value']; game_state.set_info_message(f"Sprzedano: {item_to_sell['name']}"); break

    # --- SEKCJA AKTUALIZACJI LOGIKI ---
    ### ZMIANA: player.update() jest teraz wywoływane w każdej klatce ###
    player.update() 

    if game_state.current_state == 'combat' and not game_state.player_turn:
        if pygame.time.get_ticks() - game_state.monster_attack_timer > game_state.MONSTER_ATTACK_DELAY:
            process_monster_attack(player, game_state.active_monster, game_state)

    # --- SEKCJA RYSOOWANIA GRAFIKI ---
    renderer.draw_floor_and_ceiling()
    renderer.draw_walls()
    renderer.draw_sprites()
    
    # --- SEKCJA RYSOOWANIA UI NA WIERZCHU ---
    if game_state.current_state == 'playing':
        draw_minimap(screen, player, MAPS)
        draw_buttons(screen, font)
        draw_text(screen, f'Piętro: {player.floor} | Poz: ({int(player.x/TILE)}, {int(player.y/TILE)})', (10, 10 + len(MAPS.get(player.floor, []))*8 + 10), info_font)
        pygame.draw.rect(screen, pygame.Color('darkgoldenrod'), interact_rect, border_radius=20); draw_text(screen, "E", interact_rect.center, font, center=True)
    elif game_state.current_state == 'combat': draw_combat_ui(screen, player, game_state.active_monster, game_state, font, ui_font)
    elif game_state.current_state == 'dialogue': draw_dialogue_ui(screen, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == 'inventory': draw_inventory_ui(screen, player, font, ui_font)
    elif game_state.current_state == 'character_screen': draw_character_screen_ui(screen, player, font, ui_font)
    elif game_state.current_state == 'trade_buy': draw_buy_screen_ui(screen, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == 'trade_sell': draw_sell_screen_ui(screen, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == 'game_over': draw_game_over_ui(screen, font)
    
    if game_state.info_message and pygame.time.get_ticks() < game_state.info_message_timer:
        draw_text(screen, game_state.info_message, (SCREEN_WIDTH/2, 50), ui_font, color=pygame.Color('yellow'), center=True)
    if game_state.current_state != 'game_over':
        draw_player_stats(screen, player, ui_font)

    pygame.display.flip()
    return True




async def main():
    pygame.init()
    try:
        pygame.mixer.init()
        music_path = os.path.join('assets/music', 'ThemeMy.ogg')
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(-1)
    except Exception as e:
        pass
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Prototyp RPG")
    clock = pygame.time.Clock()

    WALLS = {k: pygame.image.load(os.path.join(TEXTURE_PATH, f)).convert() for k, f in {1:'wall1.png', 2:'wall2.png', 10:'stairs_up.png', 11:'stairs_down.png'}.items()}
    sprite_files = {k: props["texture"] for k, props in SPRITE_PROPERTIES.items()}
    SPRITE_TX = {}
    for k, filename in sprite_files.items():
        try:
            SPRITE_TX[k] = pygame.image.load(os.path.join(TEXTURE_PATH, filename)).convert_alpha()
        except pygame.error:
            print(f"Nie można załadować tekstury: {filename}. Używam zastępczej.")
            placeholder = pygame.Surface((TILE, TILE))
            placeholder.fill(pygame.Color('magenta'))
            SPRITE_TX[k] = placeholder

    sprites = []
    for fl, wm in MAPS.items():
        for ry, row in enumerate(wm):
            for rx, vals in enumerate(row):
                if vals and vals[0]['id'] in SPRITE_PROPERTIES:
                    p = SPRITE_PROPERTIES[vals[0]['id']]
                    sprites.append(Sprite((rx + 0.5) * TILE, (ry + 0.5) * TILE, fl, p, SPRITE_TX[vals[0]['id']]))
                    wm[ry][rx] = []

    player = Player(MAPS)
    #font = pygame.font.SysFont(None, 60)
    #ui_font = pygame.font.SysFont(None, 48)
    #info_font = pygame.font.SysFont(None, 36)
    # Wewnątrz funkcji async def main()

    # ...
    renderer = Renderer(screen, player, MAPS, WALLS, sprites)
    game_state = GameState()
    
    try:
        font = pygame.font.Font(FONT_PATH, 50)
        ui_font = pygame.font.Font(FONT_PATH, 38)
        info_font = pygame.font.Font(FONT_PATH, 25)
    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku czcionki w '{FONT_PATH}'. Używam czcionki domyślnej.")
        font = pygame.font.Font(None, 60)
        ui_font = pygame.font.Font(None, 48)
        info_font = pygame.font.Font(None, 36)


    running = True
    #print("--- Rozpoczynam główną pętlę gry")
    while running:
        running = game_loop_step(player, game_state, renderer, sprites, screen, clock, font, ui_font, info_font)
        await asyncio.sleep(0)

    pygame.quit()
    print("Gra zakończona.")

class Player:
    def __init__(self, maps):
        self.x, self.y = TILE * 1.5, TILE * 1.5
        self.maps = maps
        self.floor = 0
        self.height_in_level = PLAYER_HEIGHT_IN_LEVEL
        self.pitch = 0
        self.dir_idx = 0
        self.angle = 0.0
        self.target_angle = 0.0
        self.rotating = False
        self.ROT_STEP = 0.3
        self.PITCH_SPEED = 200
        self.move_speed = TILE

        self.level = 1
        self.xp = 0
        self.xp_to_next_level = 100
        self.max_hp = 50
        self.hp = self.max_hp
        self.base_attack = 2
        self.base_defense = 1
        self.money = 10
        self.inventory = [
            {"name": "Stary kij", "value": 1, "type": "weapon", "attack": 1},
            {"name": "Chleb", "value": 3, "type": "consumable", "heals": 15}
        ]
        self.equipment = {"weapon": None, "armor": None, "helmet": None, "shield": None}
        self.active_quests = {} 
        self.inventory_limit = 10
    
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

    def update(self):
        if self.rotating:
            diff = (self.target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            if abs(diff) < self.ROT_STEP:
                self.angle = self.target_angle; self.rotating = False
            else:
                self.angle = (self.angle + (self.ROT_STEP if diff > 0 else -self.ROT_STEP)) % (2 * math.pi)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]: self.pitch += self.PITCH_SPEED
        if keys[pygame.K_DOWN]: self.pitch -= self.PITCH_SPEED
        self.pitch = max(-HALF_HEIGHT * 4, min(HALF_HEIGHT * 4, self.pitch))

    def change_floor(self, destination_floor):
        if destination_floor in self.maps:
            self.floor = destination_floor

    
    def check_for_aggression(self, sprites, game_state):
        player_grid_x, player_grid_y = int(self.x // TILE), int(self.y // TILE)

        # Mapa relatywnej pozycji potwora do kierunku, w który gracz musi patrzeć
        # (dx, dy): dir_idx
        adjacency_map = {
            (1, 0): 0,   # Potwór na wschodzie -> Gracz patrzy na wschód (0)
            (0, 1): 1,   # Potwór na południu -> Gracz patrzy na południe (1)
            (-1, 0): 2,  # Potwór na zachodzie -> Gracz patrzy na zachód (2)
            (0, -1): 3,  # Potwór na północy -> Gracz patrzy na północ (3)
        }

        for spr in sprites:
            # Pomiń, jeśli to nie jest żywy, agresywny potwór na tym samym piętrze
            if not (spr.floor == self.floor and spr.type == 'monster' and spr.aggressive and not spr.is_dead):
                continue

            monster_grid_x, monster_grid_y = int(spr.x // TILE), int(spr.y // TILE)
            dx = monster_grid_x - player_grid_x
            dy = monster_grid_y - player_grid_y

            # Sprawdź, czy potwór jest na sąsiednim polu (bez skosów)
            if (dx, dy) in adjacency_map:
                ### ZMIANA: Rozpocznij powolny obrót zamiast natychmiastowego ###
                target_dir_idx = adjacency_map[(dx, dy)]
                self.dir_idx = target_dir_idx
                self.target_angle = self.dir_idx * math.pi / 2
                self.rotating = True # Uruchom mechanizm płynnego obrotu

                # Rozpocznij walkę
                game_state.start_combat(spr)
                game_state.combat_log = [f"{spr.name} zauważył Cię i atakuje!"]
                
                return True # Agresja wystąpiła, przerwij dalsze sprawdzanie
        
        return False # Nie znaleziono agresywnych potworów

    ### ZMODYFIKOWANA METODA: grid_move ###
    def grid_move(self, forward, sprites, game_state):
        if self.rotating: return
        current_map = self.maps[self.floor]
        dx, dy = DIR_VECTORS[self.dir_idx]
        m = 1 if forward else -1
        nx, ny = self.x + dx * self.move_speed * m, self.y + dy * self.move_speed * m
        i, j = int(ny // TILE), int(nx // TILE)
        if not (0 <= i < len(current_map) and 0 <= j < len(current_map[0])): return
        
        for spr in sprites:
            if spr.floor == self.floor and spr.blocking and not spr.is_dead:
                si, sj = int(spr.y // TILE), int(spr.x // TILE)
                if (si, sj) == (i, j):
                    if spr.is_portal and spr.target_floor is not None:
                        self.change_floor(spr.target_floor)
                        return
                    if spr.type == 'monster':
                        game_state.start_combat(spr)
                        return
                    return
        
        tile_content = current_map[i][j]
        if tile_content and any(block['id'] not in [10, 11] for block in tile_content): return

        # Aktualizacja pozycji gracza
        self.x, self.y = nx, ny
        
        # NOWOŚĆ: Sprawdź agresję po ruchu. Jeśli walka się rozpocznie, przerwij dalsze akcje.
        if self.check_for_aggression(sprites, game_state):
            return

        # Logika dla starych schodów
        if tile_content and 'target' in tile_content[0]:
            self.change_floor(tile_content[0]['target'])

    def interact(self, sprites, game_state):
        dx, dy = DIR_VECTORS[self.dir_idx]
        nx, ny = self.x + dx * TILE, self.y + dy * TILE
        i, j = int(ny // TILE), int(nx // TILE)
        for spr in sprites:
            if spr.floor == self.floor and spr.type.startswith('npc'):
                si, sj = int(spr.y // TILE), int(spr.x // TILE)
                if (si, sj) == (i, j):
                    game_state.start_dialogue(spr); return

    def turn(self, left):
        if self.rotating: return
        self.dir_idx = (self.dir_idx + (-1 if left else 1)) % 4
        self.target_angle = self.dir_idx * math.pi / 2
        self.rotating = True

    def manage_item(self, item, game_state):
        item_type = item.get("type")

        if item_type == "consumable":
            self.hp = min(self.max_hp, self.hp + item.get("heals", 0))
            game_state.set_info_message(f"Użyto: {item['name']}, +{item['heals']} HP")
            self.inventory.remove(item)
            return

        if item_type in self.equipment:
            if self.equipment.get(item_type):
                self.inventory.append(self.equipment[item_type])
            
            self.equipment[item_type] = item
            self.inventory.remove(item)
            game_state.set_info_message(f"Założono: {item['name']}")

    def unequip_item(self, slot, game_state):
        if self.equipment.get(slot) and len(self.inventory) < self.inventory_limit:
            item = self.equipment[slot]
            self.inventory.append(item)
            self.equipment[slot] = None
            game_state.set_info_message(f"Zdjęto: {item['name']}")
            

class Sprite:
    def __init__(self, x, y, floor, properties, texture):
        self.x, self.y, self.floor = x, y, floor
        self.texture = texture
        self.scale_x = properties.get("scale_x", 1.0)
        self.scale_y = properties.get("scale_y", 1.0)
        self.blocking = properties.get("blocking", False)
        self.z = properties.get("z", 0)
        self.type = properties.get("type", "decoration")
        self.name = properties.get("name", "Obiekt")
        
        # Atrybuty potworów/NPC
        self.hp = properties.get("hp")
        self.max_hp = properties.get("hp")
        self.attack = properties.get("attack")
        self.defense = properties.get("defense")
        self.xp_yield = properties.get("xp_yield")
        self.loot_table = properties.get("loot_table")
        
        ### NOWOŚĆ: Atrybut agresji ###
        self.aggressive = properties.get("aggressive", False)

        # Atrybuty NPC
        self.sells = properties.get("sells")
        self.heal_cost = properties.get("heal_cost")
        self.quest = properties.get("quest")
        
        self.is_portal = properties.get("is_portal", False)
        self.target_floor = properties.get("target_floor", None)

        self.is_dead = False
        self.dist = 0


# main.py, wewnątrz klasy Renderer
class Renderer:
    def __init__(self, screen, player, maps, walls, sprites):
        self.screen, self.player, self.maps, self.walls, self.sprites = screen, player, maps, walls, sprites
        self.z_buffer = [float('inf')] * NUM_RAYS
        # NOWY SPOSÓB: Ładowanie tekstury trawy z pliku
        try:
            grass_texture_path = os.path.join(TEXTURE_PATH, "grass.png")
            self.GRASS_TILE = pygame.image.load(grass_texture_path).convert()
        except pygame.error:
            print("Nie można załadować tekstury trawy, używam zastępczego koloru.")
            self.GRASS_TILE = pygame.Surface((TILE, TILE))
            self.GRASS_TILE.fill(pygame.Color('darkgreen'))
            
    def draw_floor_and_ceiling(self):
        # Piwnica (piętro -1)
        if self.player.floor == -1:
            self.screen.fill(pygame.Color('gray20'), (0, 0, SCREEN_WIDTH, HALF_HEIGHT + self.player.pitch)) # Ciemny sufit
            self.screen.fill(pygame.Color('gray40'), (0, HALF_HEIGHT + self.player.pitch, SCREEN_WIDTH, SCREEN_HEIGHT)) # Ciemna podłoga
        # Inne piętra
        else:
            self.screen.fill(pygame.Color('skyblue'), (0, 0, SCREEN_WIDTH, HALF_HEIGHT + self.player.pitch)) # Niebo
            # Trawiasta podłoga
            tile_w, tile_h = self.GRASS_TILE.get_size()
            for x in range(0, SCREEN_WIDTH, tile_w):
                for y in range(HALF_HEIGHT + self.player.pitch, SCREEN_HEIGHT, tile_h):
                    self.screen.blit(self.GRASS_TILE, (x, y))
    
    ### POPRAWKA: Renderer czyta dane ze słowników ###
    def draw_walls(self):
        self.z_buffer = [float('inf')] * NUM_RAYS; current_map = self.maps[self.player.floor]; cur_angle = self.player.angle - HALF_FOV; column_width = SCREEN_WIDTH / NUM_RAYS
        for ray in range(NUM_RAYS):
            sin_a, cos_a = math.sin(cur_angle), math.cos(cur_angle); ox, oy = self.player.x, self.player.y; x_map, y_map = int(ox // TILE), int(oy // TILE)
            delta_x, delta_y = abs(TILE / (cos_a or 1e-6)), abs(TILE / (sin_a or 1e-6)); step_x, step_y = (1 if cos_a > 0 else -1), (1 if sin_a > 0 else -1)
            side_dx, side_dy = ((x_map + (1 if cos_a > 0 else 0)) * TILE - ox) / (cos_a or 1e-6), ((y_map + (1 if sin_a > 0 else 0)) * TILE - oy) / (sin_a or 1e-6)
            for _ in range(MAX_DEPTH):
                if side_dx < side_dy: side_dx += delta_x; x_map += step_x; side = 0
                else: side_dy += delta_y; y_map += step_y; side = 1
                if not (0 <= y_map < len(current_map) and 0 <= x_map < len(current_map[0])): break
                
                blocks = current_map[y_map][x_map]
                if not blocks: continue
                
                wall_blocks = [b for b in blocks if b['id'] in self.walls]
                if not wall_blocks: continue
                
                depth = (side_dx - delta_x) if side == 0 else (side_dy - delta_y); depth_corr = depth * math.cos(self.player.angle - cur_angle); self.z_buffer[ray] = depth_corr
                wx = (oy + depth * sin_a) if side == 0 else (ox + depth * cos_a); x1 = int(ray * column_width); w = max(1, int((ray + 1) * column_width) - x1)
                
                for block in sorted(wall_blocks, key=lambda b: b['z']):
                    tex_id, z_off = block['id'], block['z']
                    tex = self.walls[tex_id]; proj_h = PROJ_COEFF / (depth_corr + 1e-6); h_wall_bottom_rel = z_off * TILE; h_wall_top_rel = h_wall_bottom_rel + TILE
                    h_player_rel = self.player.height_in_level; horizon = HALF_HEIGHT + self.player.pitch; y_top = horizon - proj_h * (h_wall_top_rel - h_player_rel) / TILE
                    y_bottom = horizon - proj_h * (h_wall_bottom_rel - h_player_rel) / TILE; seg_h = y_bottom - y_top
                    if seg_h <= 0: continue
                    off = int((wx % TILE) / TILE * tex.get_width()); raw_col = tex.subsurface(off, 0, 1, tex.get_height()); col = pygame.transform.scale(raw_col, (w, int(seg_h))); self.screen.blit(col, (x1, y_top))
                break
            cur_angle += DELTA_ANGLE
            
            
    def draw_sprites(self):
        sprites_with_depth = []
        for spr in self.sprites:
            if spr.is_dead or spr.floor != self.player.floor: continue
            dx, dy = spr.x - self.player.x, spr.y - self.player.y; dist = math.hypot(dx, dy); theta = math.atan2(dy, dx); gamma = (theta - self.player.angle) % (2 * math.pi)
            if gamma > math.pi: gamma -= 2 * math.pi
            if abs(gamma) > HALF_FOV + 0.1: continue
            dist_corr = dist * math.cos(gamma); sprites_with_depth.append((spr, dist_corr, gamma))
        sprites_with_depth.sort(key=lambda t: t[1], reverse=True)
        for spr, dist_corr, gamma in sprites_with_depth:
            if dist_corr <= 0.5: continue
            proj_h = (PROJ_COEFF / (dist_corr + 1e-6)) * spr.scale_y; proj_w = (PROJ_COEFF / (dist_corr + 1e-6)) * spr.scale_x
            height_diff = (spr.floor * TILE + spr.z) - self.player.absolute_height; y_offset_from_horizon = (PROJ_COEFF * height_diff) / (dist_corr * TILE + 1e-6)
            y_base_on_screen = (HALF_HEIGHT + self.player.pitch) - y_offset_from_horizon; vert_pos = y_base_on_screen - proj_h
            screen_x = (gamma / HALF_FOV + 1) * (SCREEN_WIDTH / 2) - proj_w / 2
            if proj_w > 0 and proj_h > 0:
                try: scaled_texture = pygame.transform.scale(spr.texture, (int(proj_w), int(proj_h)))
                except ValueError: continue
                start_x = int(screen_x)
                for x in range(scaled_texture.get_width()):
                    pixel_x = start_x + x
                    if 0 <= pixel_x < SCREEN_WIDTH:
                        ray_idx = int(pixel_x / (SCREEN_WIDTH / NUM_RAYS))
                        if 0 <= ray_idx < NUM_RAYS and self.z_buffer[ray_idx] > dist_corr:
                            column = scaled_texture.subsurface(x, 0, 1, scaled_texture.get_height()); self.screen.blit(column, (pixel_x, vert_pos))

# --- Funkcje pomocnicze i UI ---
def draw_text(surface, text, pos, font, color=pygame.Color('white'), shadow_color=pygame.Color('black'), center=False):
    text_surface = font.render(text, True, color)
    shadow_surface = font.render(text, True, shadow_color)
    text_rect = text_surface.get_rect()
    if center: text_rect.center = pos
    else: text_rect.topleft = pos
    surface.blit(shadow_surface, (text_rect.x + 2, text_rect.y + 2))
    surface.blit(text_surface, text_rect)

# --- Logika gry ---
def process_player_attack(player, monster, game_state):
    if not game_state.player_turn: return
    dmg = max(0, player.attack - monster.defense)
    monster.hp -= dmg
    game_state.combat_log.append(f"Zadałeś {dmg} obrażeń potworowi!")
    if monster.hp <= 0:
        monster.is_dead = True
        player.xp += monster.xp_yield
        game_state.combat_log.append(f"Pokonałeś {monster.name}! +{monster.xp_yield} XP.")
        # NOWOŚĆ: Aktualizacja postępów w questach
        for quest in player.active_quests.values():
            quest.update_progress(monster.name)
        process_loot(player, monster, game_state)
        check_for_level_up(player, game_state)
        game_state.end_combat()
    else:
        game_state.player_turn = False

def process_monster_attack(player, monster, game_state):
    if game_state.player_turn: return
    dmg = max(0, monster.attack - player.defense)
    player.hp -= dmg
    game_state.combat_log.append(f"{monster.name} zadał Ci {dmg} obrażeń!")
    if player.hp <= 0:
        handle_player_death(player, game_state)
    else:
        game_state.player_turn = True

def process_loot(player, monster, game_state):
    for item_frozenset, chance in monster.loot_table.items():
        if random.random() < chance:
            if len(player.inventory) < player.inventory_limit:
                item_dict = dict(item_frozenset)
                player.inventory.append(item_dict)
                game_state.combat_log.append(f"Znalazłeś: {item_dict['name']}!")
            else:
                game_state.combat_log.append("Twój ekwipunek jest pełny!")

def check_for_level_up(player, game_state):
    if player.xp >= player.xp_to_next_level:
        player.level += 1
        player.xp -= player.xp_to_next_level
        player.xp_to_next_level = int(player.xp_to_next_level * 1.5)
        player.max_hp += 10
        player.hp = player.max_hp
        player.base_attack += 2
        player.base_defense += 1
        game_state.combat_log.append("AWANS NA WYŻSZY POZIOM!")
        game_state.set_info_message("AWANS!", 3000)

def handle_player_death(player, game_state):
    lost_money = int(player.money * 0.1)
    player.money -= lost_money
    player.hp = player.max_hp // 2
    player.x, player.y = TILE * 1.5, TILE * 1.5
    player.floor = 0
    game_state.end_combat()
    game_state.current_state = 'playing'
    game_state.set_info_message(f"Ocknąłeś się w mieście, tracąc {lost_money} złota.", 4000)

# --- Rysowanie interfejsów ---
def draw_combat_ui(screen, player, monster, game_state, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, 400)); s.set_alpha(200); s.fill((30, 30, 30)); screen.blit(s, (0, SCREEN_HEIGHT - 400))
    draw_text(screen, f"{monster.name}", (50, SCREEN_HEIGHT - 380), font)
    draw_text(screen, f"HP: {monster.hp}/{monster.max_hp}", (50, SCREEN_HEIGHT - 330), ui_font, color=pygame.Color("red"))
    for i, msg in enumerate(game_state.combat_log[-4:]): draw_text(screen, msg, (50, SCREEN_HEIGHT - 250 + i * 40), ui_font)
    attack_rect = pygame.Rect(SCREEN_WIDTH - 400, SCREEN_HEIGHT - 350, 300, 100)
    flee_rect = pygame.Rect(SCREEN_WIDTH - 400, SCREEN_HEIGHT - 200, 300, 100)
    pygame.draw.rect(screen, pygame.Color('darkred'), attack_rect, border_radius=12); pygame.draw.rect(screen, pygame.Color('darkblue'), flee_rect, border_radius=12)
    draw_text(screen, "Atakuj", attack_rect.center, font, center=True); draw_text(screen, "Uciekaj", flee_rect.center, font, center=True)
    return attack_rect, flee_rect

### ZMIANA: UI Dialogów z pełną obsługą questów ###
def draw_dialogue_ui(screen, player, npc, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); s.set_alpha(220); s.fill((20, 20, 40)); screen.blit(s, (0, 0))
    draw_text(screen, f"Rozmawiasz z: {npc.name}", (50, 50), font)
    
    action_rects = {}
    y_offset = 200 # Startowa pozycja Y dla przycisków
    
    # Logika Questów
    quest = npc.quest
    if quest:
        player_has_quest = quest.name in player.active_quests
        
        if player_has_quest:
            active_quest = player.active_quests[quest.name]
            if active_quest.is_complete:
                draw_text(screen, f"'Dziękuję! Moja piwnica jest bezpieczna!'", (50, 120), ui_font)
                rect = pygame.Rect(50, y_offset, 600, 80)
                pygame.draw.rect(screen, pygame.Color('gold'), rect, border_radius=12)
                draw_text(screen, f"[UKOŃCZ] {quest.name}", rect.center, ui_font, center=True, color=pygame.Color('black'))
                action_rects['complete_quest'] = rect
                y_offset += 100
            else:
                draw_text(screen, f"'Jak idzie polowanie? Zabiłeś {active_quest.progress}/{active_quest.objective['needed']}'", (50, 120), ui_font)
        elif not quest.is_turned_in:
            draw_text(screen, quest.description, (50, 120), ui_font)
            rect = pygame.Rect(50, y_offset, 600, 80)
            pygame.draw.rect(screen, pygame.Color('cyan'), rect, border_radius=12)
            draw_text(screen, f"[PRZYJMIJ] {quest.name}", rect.center, ui_font, center=True, color=pygame.Color('black'))
            action_rects['accept_quest'] = rect
            y_offset += 100

    # Inne opcje NPC
    if npc.type == "npc_healer":
        rect = pygame.Rect(50, y_offset, 600, 80)
        pygame.draw.rect(screen, pygame.Color('darkgreen'), rect, border_radius=12)
        draw_text(screen, f"Wylecz rany ({npc.heal_cost} zł)", rect.center, ui_font, center=True)
        action_rects['heal'] = rect
    elif npc.type == "npc_merchant":
        draw_text(screen, "'Co chcesz zrobić?'", (50, 120), ui_font)
        rect_buy = pygame.Rect(50, y_offset, 300, 80)
        rect_sell = pygame.Rect(370, y_offset, 300, 80)
        pygame.draw.rect(screen, pygame.Color('darkblue'), rect_buy, border_radius=12)
        pygame.draw.rect(screen, pygame.Color('darkgoldenrod'), rect_sell, border_radius=12)
        draw_text(screen, "Kup", rect_buy.center, ui_font, center=True)
        draw_text(screen, "Sprzedaj", rect_sell.center, ui_font, center=True)
        action_rects['buy_screen'] = rect_buy
        action_rects['sell_screen'] = rect_sell

    # Przycisk wyjścia
    leave_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(screen, pygame.Color('darkgray'), leave_rect, border_radius=12)
    draw_text(screen, "Wyjdź", leave_rect.center, font, center=True)
    
    return action_rects, leave_rect


### NOWOŚĆ: Interfejs do kupowania przedmiotów ###
def draw_buy_screen_ui(screen, player, npc, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); s.set_alpha(240); s.fill((20, 20, 30)); screen.blit(s, (0, 0))
    draw_text(screen, f"Towary Handlarza: {npc.name}", (50, 50), font)
    draw_text(screen, f"Twoje złoto: {player.money}", (SCREEN_WIDTH - 400, 60), ui_font, color=pygame.Color('gold'))

    buy_rects = []
    for i, item in enumerate(npc.sells):
        item_text = f"- {item['name']} (Cena: {item['value']} zł)"
        item_rect = pygame.Rect(50, 120 + i * 40, 700, 40)
        color = pygame.Color('cyan') if player.money >= item['value'] else pygame.Color('gray50')
        draw_text(screen, item_text, (item_rect.x, item_rect.y), ui_font, color=color)
        buy_rects.append(item_rect)

    back_button_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(screen, pygame.Color('darkgray'), back_button_rect, border_radius=12)
    draw_text(screen, "Wróć", back_button_rect.center, font, center=True)
    
    return buy_rects, back_button_rect


def draw_sell_screen_ui(screen, player, npc, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); s.set_alpha(240); s.fill((30, 20, 20)); screen.blit(s, (0, 0))
    draw_text(screen, f"Sprzedaj przedmioty", (50, 50), font)
    draw_text(screen, f"Twoje złoto: {player.money}", (SCREEN_WIDTH - 400, 60), ui_font, color=pygame.Color('gold'))

    sell_rects = []
    for i, item in enumerate(player.inventory):
        item_text = f"- {item['name']} (Wartość: {item['value']} zł)"
        item_rect = pygame.Rect(50, 120 + i * 40, 700, 40)
        draw_text(screen, item_text, (item_rect.x, item_rect.y), ui_font, color=pygame.Color('yellow'))
        sell_rects.append(item_rect)

    back_button_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(screen, pygame.Color('darkgray'), back_button_rect, border_radius=12)
    draw_text(screen, "Wróć", back_button_rect.center, font, center=True)

    return sell_rects, back_button_rect

def draw_inventory_ui(screen, player, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); s.set_alpha(220); s.fill((20, 40, 20)); screen.blit(s, (0, 0))
    draw_text(screen, "Ekwipunek", (50, 50), font)
    item_rects = []
    for i, item in enumerate(player.inventory):
        item_text = f"- {item['name']}"
        item_rect = pygame.Rect(50, 120 + i * 40, 800, 40)
        draw_text(screen, item_text, (item_rect.x, item_rect.y), ui_font, color=pygame.Color('white'))
        item_rects.append(item_rect)
    draw_text(screen, "Naciśnij 'I' lub 'C', aby zamknąć. Kliknij, by użyć.", (50, SCREEN_HEIGHT - 100), ui_font)
    return item_rects

### POPRAWKA: Dodanie przycisku "Zamknij" do Ekranu Postaci ###
def draw_character_screen_ui(screen, player, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); s.set_alpha(240); s.fill((40, 20, 30)); screen.blit(s, (0, 0))
    draw_text(screen, "Karta Postaci", (50, 50), font)
    
    # 1. Statystyki (lewa strona)
    draw_text(screen, "Statystyki:", (50, 150), ui_font)
    stats = {
        "Poziom": player.level, "Doświadczenie": f"{player.xp} / {player.xp_to_next_level}",
        "Życie": f"{player.hp} / {player.max_hp}", "Atak": player.attack, "Obrona": player.defense,
        "Złoto": player.money
    }
    for i, (name, value) in enumerate(stats.items()):
        draw_text(screen, f"{name}: {value}", (50, 200 + i * 40), ui_font)

    # 2. Założony ekwipunek (środek)
    draw_text(screen, "Założony ekwipunek:", (SCREEN_WIDTH / 2 - 200, 150), ui_font)
    slot_positions = {
        "helmet": (SCREEN_WIDTH / 2 - 100, 200), "armor": (SCREEN_WIDTH / 2 - 100, 300),
        "weapon": (SCREEN_WIDTH / 2 - 270, 300), "shield": (SCREEN_WIDTH / 2 + 70, 300)
    }
    equip_rects = {}
    for slot, pos in slot_positions.items():
        rect = pygame.Rect(pos[0], pos[1], 180, 80)
        pygame.draw.rect(screen, (80, 80, 80), rect, 2, border_radius=8)
        item = player.equipment.get(slot)
        if item:
            draw_text(screen, item['name'], rect.center, ui_font, color=pygame.Color('cyan'), center=True)
            equip_rects[slot] = rect
        else:
            draw_text(screen, f"[{slot.capitalize()}]", rect.center, ui_font, color=(120, 120, 120), center=True)

    # 3. Plecak (prawa strona)
    draw_text(screen, "Plecak:", (SCREEN_WIDTH - 600, 150), ui_font)
    inventory_rects = []
    for i, item in enumerate(player.inventory):
        rect = pygame.Rect(SCREEN_WIDTH - 600, 200 + i * 40, 550, 40)
        color = 'yellow' if item.get("type") in ["weapon", "armor", "helmet", "shield"] else 'lightgreen' if item.get("type") == "consumable" else 'white'
        draw_text(screen, f"- {item['name']}", (rect.x + 10, rect.y + 5), ui_font, color=pygame.Color(color))
        inventory_rects.append(rect)

    # NOWOŚĆ: Przycisk "Zamknij"
    leave_button_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(screen, pygame.Color('darkgray'), leave_button_rect, border_radius=12)
    draw_text(screen, "Zamknij", leave_button_rect.center, font, center=True)
    
    # Zmiana tekstu pomocy
    draw_text(screen, "Kliknij przedmiot, by go założyć/zdjąć.", (50, SCREEN_HEIGHT - 100), ui_font)
    
    # Zmiana zwracanych wartości
    return equip_rects, inventory_rects, leave_button_rect

def draw_game_over_ui(screen, font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); s.set_alpha(230); s.fill((0, 0, 0)); screen.blit(s, (0, 0))
    draw_text(screen, "KONIEC GRY", (SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50), font, color=pygame.Color('red'), center=True)


def draw_buttons(scr, font):
    #font = pygame.font.SysFont(None, 60)
    # Przyciski ruchu
    for rect, label in [(up_rect, 'W'), (right_rect, 'D'), (down_rect, 'S'), (left_rect, 'A')]:
        pygame.draw.rect(scr, pygame.Color('darkgray'), rect, border_radius=12)
        pygame.draw.rect(scr, pygame.Color('black'), rect, 3, border_radius=12)
        txt = font.render(label, True, pygame.Color('white'))
        scr.blit(txt, txt.get_rect(center=rect.center))
    
    # Przycisk postaci (ikona "ludzika")
    pygame.draw.rect(scr, pygame.Color('darkcyan'), character_rect, border_radius=20)
    pygame.draw.circle(scr, pygame.Color('white'), (character_rect.centerx, character_rect.centery - 20), 25)
    pygame.draw.ellipse(scr, pygame.Color('white'), (character_rect.x + 35, character_rect.y + 70, 80, 70))

def draw_player_stats(scr, player, font):
    stats_y, stats_bg_rect = SCREEN_HEIGHT - 60, pygame.Rect(0, SCREEN_HEIGHT +10, SCREEN_WIDTH, 70); pygame.draw.rect(scr, (0, 0, 0, 150), stats_bg_rect)
    hp_text = f"HP: {player.hp}/{player.max_hp}"; lvl_text = f"LVL: {player.level}"; xp_text = f"XP: {player.xp}/{player.xp_to_next_level}"; money_text = f"Złoto: {player.money}"
    atk_text = f"ATK: {player.attack}"; def_text = f"DEF: {player.defense}"
    hp_surf = font.render(hp_text,True,pygame.Color('red')); scr.blit(hp_surf, (20, stats_y))
    lvl_surf = font.render(lvl_text,True,pygame.Color('yellow')); scr.blit(lvl_surf, (250, stats_y))
    xp_surf = font.render(xp_text,True,pygame.Color('cyan')); scr.blit(xp_surf, (400, stats_y))
    money_surf = font.render(money_text,True,pygame.Color('gold')); scr.blit(money_surf, (650, stats_y))
    atk_surf = font.render(atk_text, True, pygame.Color('orange')); scr.blit(atk_surf, (850, stats_y))
    def_surf = font.render(def_text, True, pygame.Color('lightblue')); scr.blit(def_surf, (1000, stats_y))


def draw_minimap(scr, pl, maps):
    cell = 8
    current_map = maps.get(pl.floor, []) # Użyj .get() dla bezpieczeństwa
    if not current_map: return

    w, h = len(current_map[0]) * cell, len(current_map) * cell
    mini = pygame.Surface((w, h))
    mini.fill(pygame.Color('grey'))

    for ry, row in enumerate(current_map):
        for rx, cell_data in enumerate(row):
            if cell_data:
                # Ta linia została poprawiona, aby czytać słowniki
                is_stair = any(block['id'] in [10, 11] for block in cell_data)
                color = pygame.Color('yellow') if is_stair else pygame.Color('black')
                pygame.draw.rect(mini, color, (rx * cell, ry * cell, cell, cell))

    # Rysowanie gracza na niebiesko dla lepszego kontrastu
    pygame.draw.circle(mini, pygame.Color('blue'), (pl.x / TILE * cell, pl.y / TILE * cell), cell // 2)
    scr.blit(mini, (10, 10))



if __name__ == '__main__':
    if not os.path.exists(TEXTURE_PATH):
        print(f"Błąd: Nie znaleziono folderu z teksturami: '{TEXTURE_PATH}'")
        sys.exit()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Gra została zamknięta przez użytkownika.")
