import pygame
import math
import sys
import os
import random
import asyncio
import os
import csv
import json
import logging
import time

random.seed(time.time())
# --- Ustawienia Główne ---
SCREEN_WIDTH = 2300
SCREEN_HEIGHT = 1000

HALF_HEIGHT = SCREEN_HEIGHT // 2

# --- Ustawienia Raycastingu ---
FOV = math.pi / 2.1
HALF_FOV = FOV / 2
NUM_RAYS = 400
MAX_DEPTH = 30
DELTA_ANGLE = FOV / NUM_RAYS
PIXEL_SKIP = 3
USE_NUMPY_RENDERER = False

TILE = 60
PLAYER_HEIGHT_IN_LEVEL = TILE / 1.75

RENDER_SCALE = 0.17
RENDER_WIDTH = int(SCREEN_WIDTH * RENDER_SCALE)
RENDER_HEIGHT = int(SCREEN_HEIGHT * RENDER_SCALE)

def update_graphics_settings(player, renderer):
    """
    Przelicza kluczowe zmienne renderowania na podstawie wartości
    render_scale gracza i aktualizuje powiązane obiekty.
    """
    global RENDER_SCALE, RENDER_WIDTH, RENDER_HEIGHT, DIST, PROJ_COEFF, render_surface

    RENDER_SCALE = player.render_scale
    RENDER_WIDTH = int(SCREEN_WIDTH * RENDER_SCALE)
    RENDER_HEIGHT = int(SCREEN_HEIGHT * RENDER_SCALE)
    DIST = RENDER_WIDTH / (2 * math.tan(HALF_FOV))
    PROJ_COEFF = DIST * TILE

    # Odśwież powierzchnię, na której rysuje renderer
    render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))
    renderer.screen = render_surface



DIST = RENDER_WIDTH / (2 * math.tan(HALF_FOV))
PROJ_COEFF = DIST * TILE


def randomize_objects(obj=None, all_items=4, need=2):
    lista = [[obj]] * need + [[]] * (all_items - need)
    random.shuffle(lista)
    return lista


LEVEL_TEXTURES = {
    0: {"is_outdoor": True, "ceiling": (50, 50, 135), "floor": "grass.png"},
    1: {"is_outdoor": True, "ceiling": (135, 206, 235), "floor": "grass.png"},
    -1: {"is_outdoor": False, "ceiling": "wall17.png", "floor": "wall17.png"},
    2: {"is_outdoor": True, "ceiling": (135, 206, 235), "floor": "grass.png"},
}


PLANE_PROPERTIES = {
    # Niestandardowe Podłogi
    50: {
        "type": "floor",
        "texture": "wall17.png",
        "padding": 0.4,
    },  # <- tutaj 20% rozszerzenia
    51: {"type": "floor", "texture": "wall17.png"},
    # Niestandardowe Sufity
    60: {"type": "ceiling", "texture": "wall17.png"},
    61: {"type": "ceiling", "texture": "wall17.png"},
}
# --- Mapy Świata ---
# ...


### NOWA, POPRAWNA KLASA QUEST - ZASTĄP STARĄ TĄ WERSJĄ ###
class Quest:
    def __init__(self, name, description, objective_conditions, reward):
        self.name = name
        self.description = description
        # objective_conditions to słownik opisujący, co trzeba sprawdzić
        # np. {'type': 'possess_item_amount', 'item_name': 'Szczurzy ogon', 'needed': 5}
        self.objective_conditions = objective_conditions
        self.reward = reward
        self.is_turned_in = False  # Flaga zapobiegająca ponownemu oddaniu zadania

    def is_complete(self, player):
        """
        Główna metoda sprawdzająca, czy warunki zadania są spełnione.
        Zwraca True, jeśli tak, w przeciwnym razie False.
        """
        obj_type = self.objective_conditions.get("type")

        # Logika dla zadań typu "przynieś przedmioty"
        if obj_type == "possess_item_amount":
            item_name = self.objective_conditions.get("item_name")
            needed_amount = self.objective_conditions.get("needed", 1)

            # Policz, ile sztuk danego przedmiotu ma gracz w ekwipunku
            current_amount = sum(
                1 for item in player.inventory if item.get("name") == item_name
            )

            # Zwróć prawdę, jeśli gracz ma wystarczającą liczbę
            return current_amount >= needed_amount

        # Tutaj w przyszłości możesz dodać inne typy zadań, np. 'kill_specific_target'
        # if obj_type == 'kill_targets':
        #     ...
        return False


class RainParticle:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x = random.randint(0, self.screen_width)
        self.y = random.randint(-self.screen_height, 0)  # Startuj nad ekranem
        self.speed = random.randint(15, 25)
        self.length = random.randint(20, 40)
        self.color = (150, 150, 200)  # Kolor deszczu

    def update_gravity(self):
        """Przesuwa kroplę w dół i resetuje jej pozycję, gdy wyleci za ekran."""
        self.y += self.speed
        if self.y > self.screen_height:
            self.y = random.randint(-100, -10)
            self.x = random.randint(0, self.screen_width)

    def update_parallax(self, dx, dy, d_angle):
        """NOWOŚĆ: Przesuwa kroplę w reakcji na ruch gracza."""
        # Symulacja głębi - wolniejsze krople (dalsze) reagują słabiej
        depth_modifier = self.speed / 25.0  # Wartość od ~0.6 do 1.0

        # Przesunięcie poziome z obrotu i ruchu
        self.x -= (d_angle * 150 * depth_modifier) + (dx * 0.2 * depth_modifier)
        # Przesunięcie pionowe z ruchu
        self.y -= dy * 0.2 * depth_modifier

        # Zawijanie ekranu, aby deszcz nie "uciekał"
        if self.x < 0:
            self.x = self.screen_width
        if self.x > self.screen_width:
            self.x = 0

    def draw(self, surface):
        """Rysuje smugę deszczu na podanej powierzchni."""
        end_pos = (self.x - 5, self.y + self.length)
        pygame.draw.line(surface, self.color, (self.x, self.y), end_pos, 2)


class RainManager:
    def __init__(self, num_particles, screen_width, screen_height):
        self.particles = [
            RainParticle(screen_width, screen_height) for _ in range(num_particles)
        ]
        self.last_player_x = 0
        self.last_player_y = 0
        self.last_player_angle = 0
        self.initialized = False

        # Stałe do łatwej regulacji czułości efektu.
        # Możesz je modyfikować, jeśli efekt będzie za słaby lub za mocny.
        self.ROTATION_SENSITIVITY = 250.0
        self.MOVEMENT_SENSITIVITY = 0.99

    def update(self, player):
        """
        Aktualizuje pozycję wszystkich kropli, uwzględniając ruch gracza.
        """
        if not self.initialized:
            self.last_player_x = player.x
            self.last_player_y = player.y
            self.last_player_angle = player.angle
            self.initialized = True

        # 1. Oblicz zmiany (delty) od ostatniej klatki
        delta_x = player.x - self.last_player_x
        delta_y = player.y - self.last_player_y
        delta_angle = player.angle - self.last_player_angle

        # 2. KLUCZOWA ZMIANA: Przekształć ruch w świecie na ruch względem kamery gracza
        # Używamy matematyki wektorowej (iloczyn skalarny), aby dowiedzieć się,
        # o ile gracz faktycznie poruszył się "do przodu" i "w bok" z jego perspektywy.
        player_dir_x, player_dir_y = math.cos(player.angle), math.sin(player.angle)

        # Ilość ruchu w kierunku, w który patrzy gracz
        forward_move = player_dir_x * delta_x + player_dir_y * delta_y
        # Ilość ruchu w kierunku prostopadłym (strafe)
        side_move = -player_dir_y * delta_x + player_dir_x * delta_y

        for particle in self.particles:
            # Podstawowy ruch kropli w dół (grawitacja)
            particle.update_gravity()

            # Symulacja głębi - wolniejsze krople (dalsze) reagują na ruch słabiej
            depth_modifier = particle.speed / 25.0

            # 3. Zastosuj EFEKTY PARALAKSY na podstawie poprawnie obliczonego ruchu

            # Efekt OBRACANIA SIĘ (poziomy ruch na ekranie)
            particle.x -= delta_angle * self.ROTATION_SENSITIVITY * depth_modifier

            # Efekt RUCHU W BOK (strafe) (również poziomy ruch na ekranie)
            particle.x -= side_move * self.MOVEMENT_SENSITIVITY * depth_modifier

            # Efekt RUCHU DO PRZODU/TYŁU (pionowy ruch na ekranie)
            particle.y += forward_move * self.MOVEMENT_SENSITIVITY * depth_modifier

            # 4. Zawijanie ekranu, aby krople nie uciekały
            if particle.x < -particle.length:
                particle.x += particle.screen_width
            if particle.x > particle.screen_width:
                particle.x -= particle.screen_width

        # Zaktualizuj pozycje na koniec klatki
        self.last_player_x = player.x
        self.last_player_y = player.y
        self.last_player_angle = player.angle

    def draw(self, surface):
        """Rysuje wszystkie krople."""
        for particle in self.particles:
            particle.draw(surface)


class SnowParticle:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x = random.randint(0, self.screen_width)
        self.y = random.randint(-self.screen_height, 0)
        self.speed_y = random.uniform(1.5, 3.5)  # Śnieg pada znacznie wolniej
        self.radius = random.randint(2, 5)  # Płatki mają różną wielkość
        self.color = (240, 240, 245)  # Kolor śniegu

        # Parametry do kołysania na boki
        self.sway_amplitude = random.uniform(0.5, 2.0) * self.radius
        self.sway_frequency = random.uniform(0.01, 0.03)
        self.sway_offset = random.uniform(0, math.pi * 2)

    def update_gravity(self):
        """Przesuwa płatek w dół i resetuje jego pozycję."""
        # Ruch pionowy (opadanie)
        self.y += self.speed_y

        # Ruch poziomy (kołysanie)
        sway = self.sway_amplitude * math.sin(
            self.y * self.sway_frequency + self.sway_offset
        )
        self.x += sway

        # Reset pozycji, gdy wyleci za ekran
        if self.y > self.screen_height:
            self.y = random.randint(-50, -10)
            self.x = random.randint(0, self.screen_width)

    def draw(self, surface):
        """Rysuje płatek śniegu jako kółko."""
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)


class SnowManager:
    def __init__(self, num_particles, screen_width, screen_height):
        self.particles = [
            SnowParticle(screen_width, screen_height) for _ in range(num_particles)
        ]

    def update(self, player):
        """Aktualizuje pozycję wszystkich płatków śniegu."""
        # Na razie uproszczona aktualizacja bez paralaksy, tylko grawitacja
        for particle in self.particles:
            particle.update_gravity()

    def draw(self, surface):
        """Rysuje wszystkie płatki śniegu."""
        for particle in self.particles:
            particle.draw(surface)


class WeatherManager:
    def __init__(self, rain_manager, snow_manager, maps, wall_ids, plane_properties):
        self.rain_manager = rain_manager
        self.snow_manager = snow_manager  # <-- NOWOŚĆ
        self.is_raining = False
        self.is_snowing = False  # <-- NOWOŚĆ

        self.maps = maps
        self.wall_ids = wall_ids
        self.plane_properties = plane_properties
        self.player_is_sheltered = False

        # Zaktualizowane stany i przejścia
        self.states = ["Słonecznie", "Pochmurno", "Deszczowo", "Śnieg"]  # <-- NOWOŚĆ
        self.transitions = {
            "Słonecznie": {"Słonecznie": 0.55, "Pochmurno": 0.40, "Deszczowo": 0.05},
            "Pochmurno": {
                "Słonecznie": 0.30,
                "Pochmurno": 0.40,
                "Deszczowo": 0.15,
                "Śnieg": 0.15,
            },
            "Deszczowo": {"Słonecznie": 0.10, "Pochmurno": 0.60, "Deszczowo": 0.30},
            "Śnieg": {"Słonecznie": 0.05, "Pochmurno": 0.75, "Śnieg": 0.20},
        }

        self.weather_duration_timer = 0
        self.WEATHER_MIN_DURATION = 150 * 1000
        self.WEATHER_MAX_DURATION = 300 * 1000

        initial_states = ["Słonecznie", "Pochmurno", "Deszczowo", "Śnieg"]
        initial_weights = [
            0.40,
            0.40,
            0.1,
            0.1,
        ]  # Zmniejszono szansę na start w deszczu/śniegu
        self.current_state = random.choices(
            initial_states, weights=initial_weights, k=1
        )[0]

        if self.current_state == "Deszczowo":
            self.is_raining = True
            self.weather_duration_timer = pygame.time.get_ticks() + random.randint(
                self.WEATHER_MIN_DURATION, self.WEATHER_MAX_DURATION
            )
        elif self.current_state == "Śnieg":  # <-- NOWOŚĆ
            self.is_snowing = True
            self.weather_duration_timer = pygame.time.get_ticks() + random.randint(
                self.WEATHER_MIN_DURATION, self.WEATHER_MAX_DURATION
            )

        print(f"INFO: Pogoda startuje jako: {self.current_state}")

    def trigger_new_weather_period(self):
        previous_state = self.current_state

        possible_next_states = self.transitions[self.current_state]
        states = list(possible_next_states.keys())
        weights = list(possible_next_states.values())
        self.current_state = random.choices(states, weights=weights, k=1)[0]

        print(
            f"INFO: Stan pogody zmienił się z '{previous_state}' na: '{self.current_state}'"
        )

        # Uruchom deszcz, jeśli wylosowano i jeszcze nie pada
        if self.current_state == "Deszczowo" and not self.is_raining:
            self.is_raining = True
            self.is_snowing = False  # Wyłączamy śnieg dla pewności
            self.weather_duration_timer = pygame.time.get_ticks() + random.randint(
                self.WEATHER_MIN_DURATION, self.WEATHER_MAX_DURATION
            )
            print(f"INFO: Zaczyna padać deszcz!")

        # Uruchom śnieg, jeśli wylosowano i jeszcze nie pada
        if self.current_state == "Śnieg" and not self.is_snowing:  # <-- NOWOŚĆ
            self.is_snowing = True
            self.is_raining = False  # Wyłączamy deszcz dla pewności
            self.weather_duration_timer = pygame.time.get_ticks() + random.randint(
                self.WEATHER_MIN_DURATION, self.WEATHER_MAX_DURATION
            )
            print(f"INFO: Zaczyna padać śnieg!")

    def update(self, player):
        if (
            self.is_raining or self.is_snowing
        ) and pygame.time.get_ticks() > self.weather_duration_timer:
            print(f"INFO: {self.current_state} przestał padać (timer wygasł).")
            self.is_raining = False
            self.is_snowing = False

        is_sheltered = False
        current_map = self.maps.get(player.floor)
        if current_map:
            map_x = int(player.x // TILE)
            map_y = int(player.y // TILE)

            if 0 <= map_y < len(current_map) and 0 <= map_x < len(current_map[0]):
                for block in current_map[map_y][map_x]:
                    block_id = block.get("id")
                    if (
                        block_id in self.plane_properties
                        and self.plane_properties[block_id].get("type") == "ceiling"
                    ):
                        is_sheltered = True
                        break
                    if block_id in self.wall_ids:
                        is_sheltered = True
                        break
        self.player_is_sheltered = is_sheltered

        if self.is_raining:
            self.rain_manager.update(player)
        if self.is_snowing:  # <-- NOWOŚĆ
            self.snow_manager.update(player)

    def draw(self, surface):
        if self.player_is_sheltered:  # Jeśli gracz jest w schronieniu, nic nie rysuj
            return

        if self.is_raining:
            self.rain_manager.draw(surface)
        elif self.is_snowing:  # <-- NOWOŚĆ
            self.snow_manager.draw(surface)


class DayNightManager:
    def __init__(self, cycle_duration_seconds, max_alpha=180):
        # Jak długo w sekundach ma trwać pełny cykl dnia i nocy
        self.cycle_duration = cycle_duration_seconds * 1000  # Konwersja na milisekundy
        self.max_alpha = max_alpha  # Maksymalna "ciemność" (0-255)
        self.night_color = (0, 0, 50)  # Ciemnoniebieski odcień nocy

        # Powierzchnia, która będzie naszą warstwą ciemności
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.overlay.fill(self.night_color)

        # --- NOWE ATRYBUTY DO WYKRYWANIA PÓŁNOCY ---
        self.previous_darkness_level = 0
        self.respawn_triggered_this_cycle = False
        self.weather_manager = None
        self.last_period_triggered = -1

    def update(self, game_state):  # <-- WAŻNA ZMIANA: Dodajemy game_state
        """Aktualizuje porę dnia i oblicza poziom przezroczystości."""
        time_fraction = (
            pygame.time.get_ticks() % self.cycle_duration
        ) / self.cycle_duration
        sin_wave = (math.sin(time_fraction * 2 * math.pi) + 1) / 2
        darkness_level = 1.0 - sin_wave
        current_alpha = int(darkness_level * self.max_alpha)
        self.overlay.set_alpha(current_alpha)
        current_period = 0
        if time_fraction > 0.25 and time_fraction <= 0.75:  # Dzień (okres 2)
            current_period = 1
        else:  # Noc (okres 1)
            current_period = 0

        # Sprawdź, czy okres się zmienił
        if current_period != self.last_period_triggered and self.weather_manager:
            self.weather_manager.trigger_new_weather_period()
            self.last_period_triggered = current_period
        # --- NOWA LOGIKA WYKRYWANIA PÓŁNOCY ---
        # Sprawdź, czy właśnie minęliśmy "północ" (moment maksymalnej ciemności)
        if (
            darkness_level < self.previous_darkness_level
            and not self.respawn_triggered_this_cycle
            and darkness_level > 0.95
        ):
            # Ustaw flagę, aby główna pętla wiedziała, że ma odrodzić potwory
            game_state.should_respawn_monsters = True
            self.respawn_triggered_this_cycle = True
            print("INFO: Nastała północ. Czas na odrodzenie potworów.")

        # Zresetuj flagę, gdy cykl się rozpocznie od nowa (środek dnia)
        if darkness_level < 0.1:
            self.respawn_triggered_this_cycle = False

        self.previous_darkness_level = darkness_level

    def draw(self, surface):
        """Rysuje warstwę ciemności na ekranie."""
        surface.blit(self.overlay, (0, 0))


SPRITE_PROPERTIES = {
    40: {
        "texture": "stairs_up.png",
        "scale_x": 1.0,
        "scale_y": 1.3,
        "blocking": True,
        "z": 0,
        "type": "portal",
        "is_portal": True,
        "target_floor": 1,
    },
    41: {
        "texture": "stairs_down.png",
        "scale_x": 1.0,
        "scale_y": 1.0,
        "blocking": True,
        "z": 0,
        "type": "portal",
        "is_portal": True,
        "target_floor": -1,
    },
    42: {
        "texture": "stairs_up.png",
        "scale_x": 1.0,
        "scale_y": 1.3,
        "blocking": True,
        "z": 0,
        "type": "portal",
        "is_portal": True,
        "target_floor": 0,
    },
    43: {
        "texture": "stairs_down.png",
        "scale_x": 1.0,
        "scale_y": 1.0,
        "blocking": True,
        "z": 0,
        "type": "portal",
        "is_portal": True,
        "target_floor": 2,
    },
    46: {
        "texture": "stairs_up.png",
        "scale_x": 1.2,
        "scale_y": 1.2,
        "blocking": True,
        "z": 0,
        "type": "portal",
        "is_portal": True,
    },
    # 47: {"texture": "stairs_down.png", "scale_x": 1.3, "scale_y": 1, "blocking": True, "z": 0,
    #         "type": "portal", "is_portal": True},
    98: {
        "texture": "wall5.png",
        "scale_x": 1.3,
        "scale_y": 1,
        "blocking": True,
        "z": 0,
        "type": "decoration",
        "billboard": False,
        "orientation": "y",
    },
    99: {
        "texture": "wall5.png",
        "scale_x": 1.3,
        "scale_y": 1,
        "blocking": True,
        "z": 0,
        "type": "decoration",
        "billboard": False,
        "orientation": "x",
    },
    # --- POTWORY ZSYSTEMATYZOWANE ---
    3: {
        "texture": "rat2.png",
        "scale_x": 0.5,
        "scale_y": 0.5,
        "blocking": True,
        "z": 0,
        "type": "monster",
        "name": "Szczur",
        "level": 0.8,
        "archetype": "standard",
        "loot_table": [
            {
                "item": {"name": "Szczurzy ogon", "value": 2, "type": "loot"},
                "chance": 1.0,
            },
            {
                "item": {
                    "name": "Mięso",
                    "value": 3,
                    "type": "consumable",
                    "heals": 10 * 2,
                },
                "chance": 0.2,
            },
        ],
    },
    4: {
        "texture": "rat3.png",
        "scale_x": 0.5,
        "scale_y": 0.5,
        "blocking": True,
        "z": 0,
        "type": "monster",
        "name": "Groźny Szczur",
        "level": 3.3,
        "archetype": "standard",
        "loot_table": [
            {
                "item": {"name": "Szczurzy ogon", "value": 2, "type": "loot"},
                "chance": 1.0,
            },
            {
                "item": {
                    "name": "Mięso",
                    "value": 3,
                    "type": "consumable",
                    "heals": 10 * 2,
                },
                "chance": 0.2,
            },
            {
                "item": {
                    "name": "Gnilna Padlina Życia",
                    "value": -6,
                    "type": "consumable",
                    "heals": 1000,
                },
                "chance": 0.25,
            },
        ],
    },
    14: {
        "texture": "deer2.png",
        "scale_x": 1.2,
        "scale_y": 0.8,
        "blocking": True,
        "z": 0,
        "type": "monster",
        "name": "Jeleń",
        "level": 4.2,
        "archetype": "standard",
        "loot_table": [
            {
                "item": {"name": "Skóra Jelenia", "value": 12, "type": "loot"},
                "chance": 0.3,
            },
            {
                "item": {
                    "name": "Mięso",
                    "value": 5,
                    "type": "consumable",
                    "heals": 10 * 2,
                },
                "chance": 1,
            },
        ],
    },
    15: {
        "texture": "bear3.png",
        "scale_x": 0.7,
        "scale_y": 0.7,
        "blocking": True,
        "z": 0,
        "type": "monster",
        "name": "Niedzwiedz",
        "level": 8.0,
        "archetype": "brute",
        "loot_table": [
            {
                "item": {
                    "name": "Sadło",
                    "value": 15,
                    "type": "consumable",
                    "heals": 20 * 2,
                },
                "chance": 0.5,
            },
            {
                "item": {"name": "Skóra Niedzwiedzia", "value": 20, "type": "loot"},
                "chance": 0.4,
            },
        ],
    },
    # --- WYJĄTKI I OBIEKTY (POZOSTAWIONE BEZ ZMIAN) ---
    16: {
        "texture": "bear3.png",
        "scale_x": 0.7,
        "scale_y": 0.7,
        "blocking": True,
        "z": 0,
        "type": "monster",
        "name": "Niedzwiedz",
        "hp": 150 * 2,
        "attack": 5 * 2,
        "defense": 0,
        "xp_yield": 45 * 2,
        "loot_table": [
            {
                "item": {
                    "name": "Sadło",
                    "value": 15,
                    "type": "consumable",
                    "heals": 20 * 2,
                },
                "chance": 0.5,
            },
            {
                "item": {"name": "Skóra Niedzwiedzia", "value": 20, "type": "loot"},
                "chance": 0.4,
            },
        ],
    },
    22: {
        "texture": "rat_king2.png",
        "scale_x": 0.5,
        "scale_y": 0.5,
        "blocking": True,
        "z": 0,
        "aggressive": True,
        "type": "monster",
        "name": "Król Szczurów",
        "hp": 100 * 1.8,
        "attack": 12 * 2,
        "defense": 5 * 2,
        "xp_yield": 450 * 2,
        "loot_table": [
            {
                "item": {
                    "name": "Korona Króla Szczurów",
                    "value": 250,
                    "type": "helmet",
                    "defense": 3 * 2,
                    "attack": 3 * 2,
                },
                "chance": 1.0,
            }
        ],
    },
    23: {
        "texture": "barell2.png",
        "scale_x": 0.5,
        "scale_y": 0.5,
        "blocking": True,
        "z": 0,
        "aggressive": False,
        "type": "monster",
        "name": "Beczka",
        "level": 2,
        "archetype": "blockade",
        "loot_table": [
            {
                "item": {
                    "name": "Mikstura leczenia",
                    "value": 25,
                    "type": "consumable",
                    "heals": 50 * 2,
                },
                "chance": 0.25,
            },
            {
                "item": {
                    "name": "Sadło",
                    "value": 15,
                    "type": "consumable",
                    "heals": 20 * 2,
                },
                "chance": 0.5,
            },
            {
                "item": {
                    "name": "Drewniana tarcza",
                    "value": 30,
                    "type": "shield",
                    "defense": 1.5 * 2,
                },
                "chance": 0.25,
            },
        ],
    },
    24: {
        "texture": "barell2.png",
        "scale_x": 0.5,
        "scale_y": 0.5,
        "blocking": True,
        "z": 0,
        "aggressive": False,
        "type": "monster",
        "name": "Wzmocniona Beczka",
        "level": 3,
        "archetype": "blockade",
        "loot_table": [
            {
                "item": {
                    "name": "Surowy ziemniak",
                    "value": 25,
                    "type": "consumable",
                    "heals": -10,
                },
                "chance": 0.25,
            },
            {
                "item": {
                    "name": "Sadło",
                    "value": 15,
                    "type": "consumable",
                    "heals": 20 * 2,
                },
                "chance": 0.25,
            },
            {
                "item": {"name": "Głowa małego dziecka", "value": -35, "type": "loot"},
                "chance": 0.5,
            },
        ],
    },
    # --- NPCS ---
    20: {
        "texture": "merchant.png",
        "scale_x": 1.0,
        "scale_y": 1.0,
        "blocking": True,
        "z": 0,
        "type": "npc_merchant",
        "name": "Handlarz",
        "sells": [
            # --- NOWE NARZĘDZIA ---
            {
                "name": "Siekiera",
                "value": 200,
                "type": "tool",
                "tool_type": "axe",
                "gathering_damage": 2,
                "level_req": 1,
            },
            {
                "name": "Kilof",
                "value": 200,
                "type": "tool",
                "tool_type": "pickaxe",
                "gathering_damage": 2,
                "level_req": 1,
            },
            # --- Reszta przedmiotów ---
            {
                "name": "Solidny miecz",
                "value": 90,
                "type": "weapon",
                "attack": 5 * 2,
                "level_req": 1,
            },
            {
                "name": "Średni miecz",
                "value": 40,
                "type": "weapon",
                "attack": 3 * 2,
                "level_req": 1,
            },
            {
                "name": "Skórzana zbroja",
                "value": 130,
                "type": "armor",
                "defense": 3 * 2,
                "level_req": 4,
            },
            {
                "name": "Żelazny hełm",
                "value": 80,
                "type": "helmet",
                "defense": 2 * 2,
                "level_req": 1,
            },
            {
                "name": "Mikstura leczenia",
                "value": 25,
                "type": "consumable",
                "heals": 50 * 2,
                "level_req": 1,
            },
        ],
    },
    21: {
        "texture": "healer.png",
        "scale_x": 1.0,
        "scale_y": 1.0,
        "blocking": True,
        "z": 0,
        "type": "npc_healer",
        "name": "Uzdrowicielka Elara",
        "heal_cost": 10,
        "quest": Quest(
            name="Problem szczurów",
            description="Szczury zaplęgły się w mojej piwnicy! Zamij się nimi i przynieś mi 5 ich ogonów jako dowód",
            objective_conditions={
                "type": "possess_item_amount",
                "item_name": "Szczurzy ogon",
                "needed": 5,
            },
            reward={
                "xp": 120,
                "money": 10,
                "items": [
                    # WYMAGANIE DLA TARCZY Z QUESTA
                    {
                        "name": "Uszkodzona tarcza",
                        "value": 3,
                        "type": "shield",
                        "defense": 1 * 2,
                        "level_req": 1,
                    }
                ],
            },
        ),
    },
    # --- DEKORACJE I SUROWCE ---
    201: {
        "texture": "stone3.png",
        "scale_x": 1.3,
        "scale_y": 1,
        "blocking": True,
        "z": 0,
        "type": "monster",
        "archetype": "resource",
        "name": "Złoże Kamienia",  # <-- ZMIANA TYPU
        "hp": 60,
        "attack": 0,
        "defense": 0,
        "xp_yield": 5,  # <-- NOWE STATYSTYKI
        "required_tool": "pickaxe",
        "loot_table": [
            {"item": {"name": "Kamień", "value": 5, "type": "loot"}, "chance": 1.0}
        ],
    },
    12: {
        "texture": "bush3.png",
        "scale_x": 1.8,
        "scale_y": 0.8,
        "blocking": False,
        "z": 0,
        "type": "decoration",
    },
    13: {
        "texture": "bush4.png",
        "scale_x": 1.3,
        "scale_y": 0.6,
        "blocking": False,
        "z": 0,
        "type": "decoration",
    },
    5: {
        "texture": "tree3.png",
        "scale_x": 1.3,
        "scale_y": 1.2,
        "blocking": True,
        "z": 0,
        "type": "monster",
        "archetype": "resource",
        "name": "Drzewo",  # <-- ZMIANA TYPU
        "hp": 40,
        "attack": 0,
        "defense": 0,
        "xp_yield": 5,  # <-- NOWE STATYSTYKI
        "required_tool": "axe",
        "loot_table": [
            {"item": {"name": "Drewno", "value": 3, "type": "loot"}, "chance": 1.0}
        ],
    },
    6: {
        "texture": "tree4.png",
        "scale_x": 1.3,
        "scale_y": 1.2,
        "blocking": True,
        "z": 0,
        "type": "monster",
        "archetype": "resource",
        "name": "Drzewo",  # <-- ZMIANA TYPU
        "hp": 40,
        "attack": 0,
        "defense": 0,
        "xp_yield": 5,  # <-- NOWE STATYSTYKI
        "required_tool": "axe",
        "loot_table": [
            {"item": {"name": "Drewno", "value": 3, "type": "loot"}, "chance": 1.0}
        ],
    },
    7: {
        "texture": "tree5.png",
        "scale_x": 1.3,
        "scale_y": 1.2,
        "blocking": True,
        "z": 0,
        "type": "monster",
        "archetype": "resource",
        "name": "Drzewo",  # <-- ZMIANA TYPU
        "hp": 40,
        "attack": 0,
        "defense": 0,
        "xp_yield": 5,  # <-- NOWE STATYSTYKI
        "required_tool": "axe",
        "loot_table": [
            {"item": {"name": "Drewno", "value": 3, "type": "loot"}, "chance": 1.0}
        ],
    },
    # --- PRZEDMIOTY DO PODNIESIENIA ---
    101: {
        "texture": "sztylet.png",
        "scale_x": 0.3,
        "scale_y": 0.3,
        "blocking": False,
        "z": 0,
        "type": "pickup_item",
        "item_data": {
            "name": "Mały sztylet",
            "value": 15,
            "type": "weapon",
            "attack": 4,
            "defense": -4,
            "level_req": 1,
        },
    },
    102: {
        "texture": "pink_shell.png",
        "scale_x": 0.3,
        "scale_y": 0.3,
        "blocking": False,
        "z": 0,
        "type": "pickup_item",
        "item_data": {"name": "Różowa muszelka", "value": 15, "type": "loot"},
    },
    103: {
        "texture": "stick.png",
        "scale_x": 0.45,
        "scale_y": 0.45,
        "blocking": False,
        "z": 0,
        "type": "pickup_item",
        "item_data": {
            "name": "Rózga",
            "value": 1,
            "type": "weapon",
            "attack": 2,
            "level_req": 1,
        },
    },
}


# w = {"id": 1, "z": 0} # Zwykła ściana
wl = {"id": 98, "z": 0}
w_ = {"id": 99, "z": 0}
s1 = {"id": 5, "z": 0}  # Drzewo
s2 = {"id": 7, "z": 0}
rat = {"id": 3, "z": 0}  # Szczur
merchant = {"id": 20, "z": 0}
healer = {"id": 21, "z": 0}
deer = {"id": 14, "z": 0}
bear = {"id": 15, "z": 0}
rat_king = {"id": 22, "z": 0}
barell = {"id": 23, "z": 0}
w2 = {"id": 2, "z": 0}  # Ściana piwnicy

st_up_1 = {"id": 10, "z": 0, "target": 1}  # Schody w górę na piętro 1
st_up_2 = {"id": 40, "z": 0, "target": 2}  # Schody w górę na piętro 1
st_down_0 = {"id": 11, "z": 0, "target": 0}  # Schody w dół na piętro 0
# st_down_m1 = {"id": 11, "z": 0, "target": -1} # Schody w dół do piwnicy (-1)
st_up_0 = {"id": 42, "z": 0, "target": 0}  # Schody w górę na piętro 0


st_down_m1 = {"id": 47, "target_x": 2, "target_y": 3, "target_floor": 2}


# --- Szablony Kafelków ---
w = {"id": 1, "z": 0}
s1 = {"id": 5, "z": 0}
b2 = {"id": 12, "z": 0}
b1 = {"id": 13, "z": 0}
rat = {"id": 3, "z": 0}
merchant = {"id": 20, "z": 0}
healer = {"id": 21, "z": 0}
w2 = {"id": 2, "z": 0}

# NOWOŚĆ: Szablony dla schodów-sprajtów
st_up = {"id": 40, "z": 0}
st_up_1 = {"id": 40, "z": 1}
st_down = {"id": 41, "z": 0}  # Sprajt schodów w dół


guardian_deer = {"id": 14, "z": 0}  # Strażnik Lasu
portal_to_las = {"id": 11, "z": 0, "target": 2}
# portal_to_las = {"id": 43, "z": 0} # Portal prowadzący do lasu
portal_back = {
    "id": 11,
    "z": 0,
    "target": 0,
}  # Portal powrotny na piętro 1 (używamy sprajtu schodów w dół)
sztylet = {"id": 101, "z": 0}
pink_shell = {"id": 102, "z": 0}
stone = {"id": 201, "z": 0}
stick = {"id": 103, "z": 0}
rnd_item = random.choice([[stick], [sztylet]])


p1_rat1, p1_rat2, p1_rat3, p1_rat4, p1_rat5, p1_rat6, p1_rat7, p1_rat8 = (
    randomize_objects(rat, 8, 5)
)

p1_stick1, p1_stick2, p1_stick3, p1_stick4 = randomize_objects(stick, 4, 1)


def load_map_from_csv(file_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "assets/maps/", file_name)
    with open(file_path, "r", newline="", encoding="utf-8") as f:
        return [row for row in csv.reader(f)]


import sys, json, re


def process_map_cell(cell):
    """
    - []                              — dla pustych lub nie-rozpoznanych
    - [dict, …]                       — dla JSON-owej listy dictów
    - [data]                          — dla JSON-owego słownika
    - [zmienna modułu]                — jeżeli istnieje jako dict lub list(dict)
    """
    # 1) Jeżeli już to nie string (czyli lista/dict), zaakceptuj lub wyczyść
    if not isinstance(cell, str):
        if isinstance(cell, dict):
            return [cell]
        if isinstance(cell, list) and all(isinstance(el, dict) for el in cell):
            return cell
        return []

    s = cell.strip()
    if not s:
        return []

    # 2) Spróbuj rozpoznać ciąg wielu dictów bez listy:  {"…"} , {"…"} , …
    #    jeśli jest co najmniej 2 wystąpienia "{...}", oblejamy w [ ... ]
    dicts = re.findall(r"\{[^}]+\}", s)
    if len(dicts) >= 2 and all(d in s for d in dicts):
        wrapped = "[" + s + "]"
        try:
            data = json.loads(wrapped)
            if isinstance(data, list) and all(isinstance(el, dict) for el in data):
                return data
        except json.JSONDecodeError:
            pass

    # 3) JSON list lub dict?
    if (s.startswith("[") and s.endswith("]")) or (
        s.startswith("{") and s.endswith("}")
    ):
        try:
            data = json.loads(s)
            if isinstance(data, dict):
                return [data]
            if isinstance(data, list) and all(isinstance(el, dict) for el in data):
                return data
        except json.JSONDecodeError:
            pass

    # 4) Zmienna w module?
    mod = sys.modules[__name__]
    if hasattr(mod, s):
        ref = getattr(mod, s)
        if isinstance(ref, dict):
            return [ref]
        if isinstance(ref, list) and all(isinstance(el, dict) for el in ref):
            return ref

    # 5) W każdym innym wypadku: pusta lista
    return []


# --- Mapy Świata ---
# Piętro 0: Miasto
WORLD_MAP_0 = [
    [[w], [w], [w], [w], [w], [w], [w], [w], [w], [w]],
    [[w], [], [], [], [], [], [], [], [], [w]],
    [[w], [st_up], [], [], [], [], [healer], [], [], [st_down_m1]],
    [[w], [], [], [], [merchant], [], [], [], [], [w]],
    [[w], [], [], [], [], [], [], [], [], [w]],
    [[w], [], [], [s1], [], [], [], [], [], [w]],
    [[w], [], [], [], [s1], [], [s1], [b1], [], [w]],
    [[w], [], [], [], [], [s1], [], [rat_king], [b1], [w]],
    [[w], [], [], [s1], [deer], [], [], [s1], [sztylet], [w]],
    [[w], [w], [w], [w], [portal_to_las], [w], [w], [w], [w], [w]],
]
# Piętro 1: Dzicz / Lochy
WORLD_MAP_1 = [
    [[w], [w], [w], [w], [w], [w], [w], [w], [w], [w]],
    [[w], [w], [], [], [], [], [], [stone], [deer], [w]],
    [[], [st_down_0], [], [], [], [], [s1], [b1], [pink_shell], [w]],
    [[w], [w], [], [], [], [s1], [], [rat], [], [w]],
    [
        [w],
        [],
        [],
        [],
        [{"id": 1, "z": 0}, {"id": 2, "z": 1}, {"id": 1, "z": 2}],
        [deer],
        [],
        [],
        [],
        [w],
    ],
    [[w], [], [], [], [b1], [stone], [barell], [w], [deer], [w]],
    [[w], [], [], [], [], [], [rat], [], [w], [w]],
    [[w], [b1], [b1], [b2], [b2], [], [], [rat], [], [w]],
    [[w], [], [b1], [b2], rnd_item, [], [], [], [], [w]],
    [[w], [w], [w], [w], [w], [w], [w], [w], [w], [w]],
]
# Piętro -1: Piwnica
WORLD_MAP_MINUS_1 = [
    [p1_rat1, [], [], [], [], [], [], [], [], []],
    [[], [], [], [], [], [], [], [], [], []],
    [[], [], [], [w2], [w2], [w2], [w2], [w2], [], []],
    [[], [], [], [w2], p1_rat2, [], [], [w2], [], []],
    [[], [], [], [w2], p1_rat4, [], [], [], [], []],
    [[], [], [], [w2], p1_rat6, p1_rat5, p1_rat7, [w2], [], []],
    [p1_rat8, [], [], [w2], [w2], [w2], [w2], [w2], [], [w2]],
    [[], [], [], [], [], [], [], [rat_king], [], [w2]],
    [[], [], [], [st_up_0], p1_rat3, [], [], [], [], [w2]],
    [[], [], [], [], [], [], [], [], [], [w2]],
]


# --- Mapa Świata ---
# Piętro 2: Duży Las
WORLD_MAP_LAS = [
    [
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
    ],
    [
        [w],
        [],
        [s1],
        [],
        [],
        [rat],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [s1],
        [s1],
        [],
        [],
        [deer],
        [],
        [],
        [w],
    ],
    [
        [w],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [w],
    ],
    [
        [w],
        [],
        [],
        [rat],
        [],
        [],
        [s1],
        [],
        [],
        [deer],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [s1],
        [],
        [],
        [w],
    ],
    [
        [w],
        [w],
        [s1],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [bear],
        [],
        [w],
    ],
    [
        [w],
        [portal_back],
        [],
        [s1],
        [],
        [],
        [deer],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [deer],
        [],
        [],
        [],
        [],
        [s1],
        [w],
    ],
    [
        [w],
        [w],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [w],
    ],
    [
        [w],
        [s1],
        [],
        [rat],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [deer],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [w],
    ],
    [
        [w],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [rat],
        [],
        [w],
    ],
    [
        [w],
        [],
        [s1],
        [],
        [deer],
        [],
        [],
        [],
        [],
        [s1],
        [s1],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [w],
    ],
    [
        [w],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [rat],
        [],
        [],
        [],
        [],
        [w],
    ],
    [
        [w],
        [s1],
        [],
        [deer],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [bear],
        [],
        [s1],
        [],
        [w],
    ],
    [
        [w],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [bear],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [w],
    ],
    [
        [w],
        [],
        [s1],
        [bear],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [bear],
        [],
        [],
        [s1],
        [],
        [w],
    ],
    [
        [w],
        [],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [s1],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [bear],
        [],
        [],
        [w],
    ],
    [
        [w],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [],
        [],
        [bear],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [w],
    ],
    [
        [w],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [rat],
        [],
        [w],
    ],
    [
        [w],
        [s1],
        [],
        [deer],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [bear],
        [],
        [deer],
        [],
        [],
        [],
        [],
        [s1],
        [w],
    ],
    [
        [w],
        [],
        [bear],
        [],
        [],
        [s1],
        [],
        [rat],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [s1],
        [],
        [],
        [],
        [w],
    ],
    [
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
        [w],
    ],
]


# Wczytanie map
WORLD_MAP_0 = load_map_from_csv("world_map_0.csv")
WORLD_MAP_1 = load_map_from_csv("world_map_1-.csv")
WORLD_MAP_LAS = load_map_from_csv("world_map_las.csv")
WORLD_MAP_MINUS_1 = load_map_from_csv("world_map_minus_1.csv")

# Przetworzenie
WORLD_MAP_0 = [[process_map_cell(cell) for cell in row] for row in WORLD_MAP_0]
WORLD_MAP_1 = [[process_map_cell(cell) for cell in row] for row in WORLD_MAP_1]
WORLD_MAP_LAS = [[process_map_cell(cell) for cell in row] for row in WORLD_MAP_LAS]
WORLD_MAP_MINUS_1 = [
    [process_map_cell(cell) for cell in row] for row in WORLD_MAP_MINUS_1
]


# ZAKTUALIZOWANA definicja słownika MAPS
MAPS = {0: WORLD_MAP_0, 1: WORLD_MAP_1, -1: WORLD_MAP_MINUS_1, 2: WORLD_MAP_LAS}


DIR_VECTORS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
TEXTURE_PATH = "assets/textures"
FONT_PATH = os.path.join("assets", "fonts", "DejaVuSans.ttf")


# --- Przyciski UI ---
BUTTON_SIZE = 140
BUTTON_MARGIN = 20
BUTTON_OFFSET_Y = 400
BUTTON_OFFSET_X = 180
bx = SCREEN_WIDTH - BUTTON_SIZE * 2 - BUTTON_MARGIN * 2.5 - BUTTON_OFFSET_X
by = SCREEN_HEIGHT - BUTTON_SIZE * 2 - BUTTON_MARGIN * 2.5 - BUTTON_OFFSET_Y
up_rect = pygame.Rect(bx, by, BUTTON_SIZE, BUTTON_SIZE)
right_rect = pygame.Rect(
    bx + BUTTON_SIZE + BUTTON_MARGIN, by + BUTTON_SIZE / 2, BUTTON_SIZE, BUTTON_SIZE
)
down_rect = pygame.Rect(bx, by + BUTTON_SIZE + BUTTON_MARGIN, BUTTON_SIZE, BUTTON_SIZE)
left_rect = pygame.Rect(
    bx - BUTTON_SIZE - BUTTON_MARGIN, by + BUTTON_SIZE / 2, BUTTON_SIZE, BUTTON_SIZE
)
interact_rect = pygame.Rect(SCREEN_WIDTH - 200, 200, 150, 150)
character_rect = pygame.Rect(SCREEN_WIDTH - 200, 50, 150, 150)


# --- Generator Statystyk Potworów ---
def generate_monster_stats(level, archetype="standard"):
    """
    Oblicza statystyki potwora na podstawie jego poziomu i archetypu.
    Zwraca słownik ze statystykami do użycia w klasie Sprite.
    """
    # 1. Definicja archetypów (modyfikatory)
    archetypes = {
        "standard": {"hp_mod": 1.15, "atk_mod": 1.1, "def_mod": 1.1},
        "tank": {"hp_mod": 1.5, "atk_mod": 0.7, "def_mod": 1.3},
        "glass_cannon": {"hp_mod": 0.7, "atk_mod": 1.4, "def_mod": 0.6},
        "brute": {"hp_mod": 1.25, "atk_mod": 1, "def_mod": 0.5},
        "elite": {"hp_mod": 1.8, "atk_mod": 1.3, "def_mod": 1.2},
        "blockade": {
            "hp_mod": 2.5,
            "atk_mod": 0.1,
            "def_mod": 1.5,
        },  # <-- NOWY ARCHETYP DLA BECZEK/BLOKAD
    }
    mods = archetypes.get(archetype, archetypes["standard"])

    # 2. Formuły bazowe
    base_hp = 10 * 2
    base_attack = 3 * 2
    base_defense = 1 * 2
    base_xp = 15 * 2

    # 3. Obliczenia z uwzględnieniem poziomu i archetypu
    hp = int((base_hp + level * 5) * mods["hp_mod"])
    attack = int((base_attack + level * 1.5) * mods["atk_mod"])
    defense = int((base_defense + level * 0.5) * mods["def_mod"])
    xp_yield = int((base_xp + level * 5) * (1.2 if archetype == "elite" else 1.0))

    # <-- NOWA SEKCJA: Specjalna zasada dla blokad - redukcja XP -->
    if archetype == "blockade":
        xp_yield = int(xp_yield * 0.2)  # Daje tylko 20% normalnego XP
        if xp_yield < 5:
            xp_yield = 5  # Ale nie mniej niż 5 XP

    return {"hp": hp, "attack": attack, "defense": defense, "xp_yield": xp_yield}


### ZASTĄP CAŁĄ TĘ KLASĘ W SWOIM KODZIE ###
class GameState:
    def __init__(self):
        self.screen_shake_intensity = 0
        self.screen_shake_timer = 0

        self.current_state = "playing"
        self.active_monster = None
        self.active_npc = None
        self.combat_log = []
        self.player_turn = True
        self.info_message = ""
        self.info_message_timer = 0
        self.monster_attack_timer = 0
        self.MONSTER_ATTACK_DELAY = 500
        self.combat_turn = 0
        self.screen_dirty = True
        self.level_up_message = None
        self.level_up_timer = 0
        self.should_respawn_monsters = False

        # --- DODAJ TĘ LINIĘ ---
        self.is_dragging_quality_slider = False

    def set_info_message(self, text, duration=2000):
        self.info_message = text
        self.info_message_timer = pygame.time.get_ticks() + duration

    def start_combat(self, monster, logger, player):
        self.current_state = "combat"
        self.active_monster = monster
        self.combat_log = [f"Spotykasz na drodze: {monster.name}!"]
        self.player_turn = True
        self.monster_attack_timer = 0
        self.combat_turn = 0
        self.screen_dirty = True
        logger.info(
            f"COMBAT_START; Monster: {monster.name}; MonsterHP: {monster.hp}/{monster.max_hp}; PlayerHP: {player.hp}/{player.max_hp}"
        )

    def end_combat(self, player, logger, outcome):
        self.current_state = "playing"
        self.active_monster = None
        self.combat_turn = 0
        self.screen_dirty = True
        logger.info(
            f"COMBAT_END; Outcome: {outcome}; PlayerHP: {player.hp}/{player.max_hp}"
        )

    def start_dialogue(self, npc):
        self.current_state = "dialogue"
        self.active_npc = npc
        self.screen_dirty = True

    def end_dialogue(self):
        self.current_state = "playing"
        self.active_npc = None
        self.screen_dirty = True

def game_loop_step(
    player,
    game_state,
    renderer,
    sprites,
    screen,
    clock,
    font,
    ui_font,
    info_font,
    sprite_properties,
    sprite_textures,
    last_world_render,
    logger,
    rain_manager,
    day_night_manager,
    weather_manager,
    sprite_grid
):
    
    dt = clock.tick(50)
    mx, my = pygame.mouse.get_pos()

    # --- SEKCJA OBSŁUGI ZDARZEŃ ---
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            return False

        # Stan: Normalna gra
        if game_state.current_state == "playing":
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_w:
                    player.grid_move(True, sprites, game_state, logger, player,sprite_grid)
                if e.key == pygame.K_s:
                    player.grid_move(False, sprites, game_state, logger, player,sprite_grid)
                if e.key == pygame.K_a:
                    player.turn(True, game_state)
                if e.key == pygame.K_d:
                    player.turn(False, game_state)
                if e.key == pygame.K_e:
                    player.interact(sprites, game_state, logger)
                if e.key == pygame.K_i:
                    game_state.current_state = "inventory"
                    game_state.screen_dirty = True
                if e.key == pygame.K_c:
                    game_state.current_state = "character_screen"
                    game_state.screen_dirty = True
            if e.type == pygame.MOUSEBUTTONDOWN:
                if up_rect.collidepoint(mx, my):
                    player.grid_move(True, sprites, game_state, logger, player, sprite_grid)
                elif right_rect.collidepoint(mx, my):
                    player.turn(False, game_state)
                elif down_rect.collidepoint(mx, my):
                    player.grid_move(False, sprites, game_state, logger, player,sprite_grid)
                elif left_rect.collidepoint(mx, my):
                    player.turn(True, game_state)
                elif interact_rect.collidepoint(mx, my):
                    player.interact(sprites, game_state, logger)
                elif character_rect.collidepoint(mx, my):
                    game_state.current_state = "character_screen"
                    game_state.screen_dirty = True

        # Stan: Walka
        elif game_state.current_state == "combat":
            if e.type == pygame.MOUSEBUTTONDOWN and game_state.player_turn:

                attack_rect, power_rect, flee_rect, panic_flee_rect = draw_combat_ui(
                    screen,
                    player,
                    game_state.active_monster,
                    game_state,
                    font,
                    info_font,
                    ui_font,
                )

                if attack_rect.collidepoint(mx, my):
                    process_player_attack(
                        player, game_state.active_monster, game_state, logger
                    )
                    game_state.monster_attack_timer = pygame.time.get_ticks()

                elif power_rect.collidepoint(mx, my):
                    if player.moc > 0:
                        process_player_power_attack(
                            player, game_state.active_monster, game_state, logger
                        )
                        game_state.monster_attack_timer = pygame.time.get_ticks()
                    else:
                        game_state.set_info_message("Brak Mocy!", 1500)

                elif flee_rect.collidepoint(mx, my):
                    chance = 0.5
                    if game_state.active_monster.attack > player.attack:
                        chance = 0.3
                        if game_state.combat_turn == 0:
                            chance = 0.05
                        elif game_state.combat_turn == 1:
                            chance = 0.15

                    if random.random() < chance:
                        game_state.active_monster.hp = game_state.active_monster.max_hp
                        game_state.end_combat(player, logger, "Fled")
                        game_state.combat_turn = 0
                        game_state.set_info_message("Wycofanie udane!")
                    else:
                        game_state.player_turn = False
                        game_state.monster_attack_timer = pygame.time.get_ticks()
                        game_state.combat_log.append("Nie udało się uciec!")
                elif panic_flee_rect.collidepoint(mx, my):
                    process_panic_escape(player, game_state, logger)

        # Stan: Dialog
        elif game_state.current_state == "dialogue":
            if e.type == pygame.MOUSEBUTTONDOWN:
                action_rects, leave_rect = draw_dialogue_ui(
                    screen, player, game_state.active_npc, font, ui_font, logger
                )
                if leave_rect.collidepoint(mx, my):
                    game_state.end_dialogue()
                elif game_state.active_npc:
                    quest = game_state.active_npc.quest
                    info = ""
                    if "accept_quest" in action_rects and action_rects[
                        "accept_quest"
                    ].collidepoint(mx, my):
                        if quest.name == "Problem szczurów":
                            info = "Uleczono. "
                            player.hp = player.max_hp
                        player.active_quests[quest.name] = quest
                        game_state.set_info_message(f"{info}Przyjęto: {quest.name}")
                        logger.info(f"QUEST_ACCEPT; Quest: {quest.name}")
                        game_state.end_dialogue()

                    elif "complete_quest" in action_rects and action_rects[
                        "complete_quest"
                    ].collidepoint(mx, my):

                        logger.info(
                            f"QUEST_COMPLETE; Quest: {quest.name}; RewardXP: {quest.reward['xp']}; RewardMoney: {quest.reward['money']}"
                        )
                        player.add_xp(quest.reward["xp"], game_state, logger)
                        player.money += quest.reward["money"]

                        reward_items_text = ""

                        if "items" in quest.reward:
                            for item_reward in quest.reward["items"]:
                                if len(player.inventory) < player.inventory_limit:
                                    player.inventory.append(item_reward.copy())
                                    if reward_items_text:
                                        reward_items_text += ", "
                                    reward_items_text += item_reward["name"]
                                else:
                                    game_state.set_info_message(
                                        "Ekwipunek pełny! Nie otrzymano wszystkich przedmiotów.",
                                        4000,
                                    )
                                    break
                        quest.is_turned_in = True
                        del player.active_quests[quest.name]
                        replace_quest_rats_with_barrels(
                            sprites, sprite_properties, sprite_textures, game_state
                        )
                        final_message = f"Ukończono! Nagroda: {quest.reward['xp']} XP, {quest.reward['money']} zł."
                        if reward_items_text:
                            final_message += f" Otrzymano: {reward_items_text}."
                        game_state.set_info_message(final_message, 4000)
                        game_state.end_dialogue()

                    elif "heal_free" in action_rects and action_rects[
                        "heal_free"
                    ].collidepoint(mx, my):
                        player.hp = int(max(player.max_hp * 0.6, player.hp))
                        game_state.set_info_message("Rany podleczone.")
                        logger.info(f"HEALED NOT FULLY")
                    elif "heal" in action_rects and action_rects["heal"].collidepoint(
                        mx, my
                    ):
                        if player.money >= game_state.active_npc.heal_cost:
                            player.money -= game_state.active_npc.heal_cost
                            player.hp = player.max_hp
                            game_state.set_info_message("Rany wyleczone.")
                            logger.info(f"HEALED FULLY")
                        else:
                            game_state.set_info_message("Brak złota.")
                    elif "buy_screen" in action_rects and action_rects[
                        "buy_screen"
                    ].collidepoint(mx, my):
                        game_state.current_state = "trade_buy"
                        game_state.screen_dirty = True
                    elif "sell_screen" in action_rects and action_rects[
                        "sell_screen"
                    ].collidepoint(mx, my):
                        game_state.current_state = "trade_sell"
                        game_state.screen_dirty = True
                    elif "buy_back_screen" in action_rects and action_rects[
                        "buy_back_screen"
                    ].collidepoint(mx, my):
                        game_state.current_state = "trade_buy_back"
                        game_state.screen_dirty = True

        # Stany: Ekrany UI
        elif game_state.current_state == "inventory":
            if e.type == pygame.KEYDOWN and (
                e.key == pygame.K_i or e.key == pygame.K_c
            ):
                game_state.current_state = "playing"
                game_state.screen_dirty = True
            if e.type == pygame.MOUSEBUTTONDOWN:
                item_rects = draw_inventory_ui(screen, player, font, ui_font)
                for i, rect in enumerate(item_rects):
                    if rect.collidepoint(mx, my) and i < len(player.inventory):
                        player.manage_item(player.inventory[i], game_state, logger)
                        break

        elif game_state.current_state == "character_screen":
            if e.type == pygame.KEYDOWN and (
                e.key == pygame.K_c or e.key == pygame.K_i
            ):
                game_state.current_state = "playing"
                game_state.screen_dirty = True
            
            equip_rects, inventory_rects, leave_button_rect, slider_area = (
                draw_character_screen_ui(screen, player, font, ui_font)
            )

            if e.type == pygame.MOUSEBUTTONDOWN and slider_area.collidepoint(mx, my):
                game_state.is_dragging_quality_slider = True
            
            if e.type == pygame.MOUSEBUTTONUP:
                game_state.is_dragging_quality_slider = False
                
            if game_state.is_dragging_quality_slider and (e.type == pygame.MOUSEMOTION or e.type == pygame.MOUSEBUTTONDOWN):
                slider_x, slider_width, min_val, max_val = 50, 350, 0.14, 0.28
                relative_x = max(0, min(slider_width, mx - slider_x))
                new_scale = min_val + (relative_x / slider_width) * (max_val - min_val)
                
                if abs(player.render_scale - new_scale) > 0.001:
                    player.render_scale = new_scale
                    # --- KLUCZOWA ZMIANA: Wywołaj nową funkcję ---
                    update_graphics_settings(player, renderer)
                    game_state.screen_dirty = True
            
            
            if e.type == pygame.MOUSEBUTTONDOWN:
                equip_rects, inventory_rects, leave_button_rect, slider_area = (
                draw_character_screen_ui(screen, player, font, ui_font)
            )
                if leave_button_rect.collidepoint(mx, my):
                    game_state.current_state = "playing"
                    game_state.screen_dirty = True
                else:
                    for i, rect in enumerate(inventory_rects):
                        if rect.collidepoint(mx, my) and i < len(player.inventory):
                            player.manage_item(player.inventory[i], game_state, logger)
                            break
                    for slot, rect in equip_rects.items():
                        if rect.collidepoint(mx, my):
                            player.unequip_item(slot, game_state)
                            break

        elif game_state.current_state == "trade_buy":
            if e.type == pygame.MOUSEBUTTONDOWN:
                buy_rects, back_button_rect = draw_buy_screen_ui(
                    screen, player, game_state.active_npc, font, ui_font
                )
                if back_button_rect.collidepoint(mx, my):
                    game_state.current_state = "dialogue"
                    game_state.screen_dirty = True
                else:
                    for i, rect in enumerate(buy_rects):
                        if rect.collidepoint(mx, my):
                            item_to_buy = game_state.active_npc.sells[i]
                            if player.money >= item_to_buy["value"]:
                                if len(player.inventory) < player.inventory_limit:
                                    player.money -= item_to_buy["value"]
                                    player.inventory.append(item_to_buy.copy())
                                    game_state.set_info_message(
                                        f"Kupiono: {item_to_buy['name']}"
                                    )
                                    logger.info(
                                        f"ITEM_BUY; Item: {item_to_buy['name']}; Cost: {item_to_buy['value']}"
                                    )
                                else:
                                    game_state.set_info_message("Ekwipunek pełny!")
                            else:
                                game_state.set_info_message("Za mało złota!")
                            break

        elif game_state.current_state == "trade_sell":
            if e.type == pygame.MOUSEBUTTONDOWN:
                sell_rects, back_button_rect = draw_sell_screen_ui(
                    screen, player, game_state.active_npc, font, ui_font
                )
                if back_button_rect.collidepoint(mx, my):
                    game_state.current_state = "dialogue"
                    game_state.screen_dirty = True
                else:
                    # --- TEN FRAGMENT ZOSTAŁ PRZYWRÓCONY ---
                    for i, rect in enumerate(sell_rects):
                        if rect.collidepoint(mx, my) and i < len(player.inventory):
                            item_to_sell = player.inventory.pop(i)
                            player.money += item_to_sell["value"]
                            game_state.active_npc.buy_back_stock.append(item_to_sell)
                            game_state.set_info_message(
                                f"Sprzedano: {item_to_sell['name']}"
                            )
                            logger.info(
                                f"ITEM_SELL; Item: {item_to_sell['name']}; Value: {item_to_sell['value']}"
                            )
                            break

        elif game_state.current_state == "trade_buy_back":
            if e.type == pygame.MOUSEBUTTONDOWN:
                buy_back_rects, back_button_rect = draw_buy_back_ui(
                    screen, player, game_state.active_npc, font, ui_font
                )
                if back_button_rect.collidepoint(mx, my):
                    game_state.current_state = "dialogue"
                    game_state.screen_dirty = True
                else:
                    for i in range(len(buy_back_rects) - 1, -1, -1):
                        rect = buy_back_rects[i]
                        if rect.collidepoint(mx, my):
                            item_to_buy_back = game_state.active_npc.buy_back_stock[i]
                            buy_back_price = int(item_to_buy_back["value"] * 1.1)

                            if player.money >= buy_back_price:
                                if len(player.inventory) < player.inventory_limit:
                                    player.money -= buy_back_price
                                    player.inventory.append(
                                        game_state.active_npc.buy_back_stock.pop(i)
                                    )
                                    game_state.set_info_message(
                                        f"Odkupiono: {item_to_buy_back['name']}"
                                    )
                                else:
                                    game_state.set_info_message("Ekwipunek pełny!")
                            else:
                                game_state.set_info_message("Za mało złota!")
                            break

    player.update(game_state)
    weather_manager.update(player)
    day_night_manager.update(game_state)



    # BLOK 1: Wyzwalacz o Północy - przygotowanie grup potworów
    if game_state.should_respawn_monsters:

        # 1. Pogrupuj kwalifikujące się potwory według pięter
        eligible_by_floor = {}
        for spr in sprites:
            is_monster = spr.type == "monster"
            is_dead = spr.is_dead
            can_respawn = not spr.properties.get("no_respawn")
            is_not_blockade = spr.properties.get("archetype") != "blockade"

            if is_monster and is_dead and can_respawn and is_not_blockade:
                if spr.floor not in eligible_by_floor:
                    eligible_by_floor[spr.floor] = []
                eligible_by_floor[spr.floor].append(spr)

        # 2. Dla każdego piętra sprawdź warunki i wylosuj potwory do odrodzenia
        for floor_idx, monster_list in eligible_by_floor.items():

            # UŻYCIE NASZEJ NOWEJ FUNKCJI-STRAŻNIKA
            if are_respawns_allowed_on_floor(floor_idx, player, game_state, sprites):

                num_to_respawn = int(len(monster_list) * 0.30)
                if num_to_respawn > 0:
                    monsters_to_respawn = random.sample(monster_list, num_to_respawn)

                    print(
                        f"INFO: Północ. Na piętrze {floor_idx} wybrano {len(monsters_to_respawn)} potworów do odrodzenia."
                    )

                    current_time = pygame.time.get_ticks()
                    for monster in monsters_to_respawn:
                        monster.is_awaiting_respawn = True
                        delay_ms = random.randint(0, 120000)  # Losowe opóźnienie 0-120s
                        monster.respawn_timer = current_time + delay_ms
            else:
                print(
                    f"INFO: Północ. Odradzanie na piętrze {floor_idx} zostało zablokowane przez warunek specjalny."
                )

        game_state.should_respawn_monsters = False

    # BLOK 2: Ciągłe Sprawdzanie Timerów (pozostaje bez zmian)
    for spr in sprites:
        if spr.is_awaiting_respawn and pygame.time.get_ticks() > spr.respawn_timer:
            spr.is_dead = False
            spr.hp = spr.max_hp
            spr.is_awaiting_respawn = False
            spr.respawn_timer = 0
            game_state.screen_dirty = True
            print(f"INFO: Potwór '{spr.name}' na piętrze {spr.floor} odrodził się.")

    if game_state.current_state == "combat" and not game_state.player_turn:
        if (
            pygame.time.get_ticks() - game_state.monster_attack_timer
            > game_state.MONSTER_ATTACK_DELAY
        ):
            process_monster_attack(
                player, game_state.active_monster, game_state, logger
            )
            if game_state.screen_shake_intensity > 0:
                game_state.screen_dirty = True

    is_shaking = game_state.screen_shake_timer > pygame.time.get_ticks()
    if is_shaking:
        game_state.screen_dirty = True

    if game_state.screen_dirty:
        is_outdoor = LEVEL_TEXTURES.get(player.floor, {}).get("is_outdoor", False)
        if is_outdoor:

            renderer.draw_skybox()

        # 1. Rysujemy podłogę i sufit (zoptymalizowaną wersją)
        renderer.draw_floor_and_ceiling()
        # 2. Rysujemy ściany (teraz już bez błędów)
        renderer.draw_walls()
        # 3. Rysujemy sprajty
        # W game_loop_step:

        # --- NOWY KOD: Pobieranie tylko pobliskich sprajtów do renderowania ---
        # Definiujemy, jak duży obszar wokół gracza nas interesuje. 
        # Wartość musi być większa niż maksymalny zasięg widzenia.
        VIEW_RADIUS_TILES = 30 
        view_radius_pixels = VIEW_RADIUS_TILES * TILE

        # Tworzymy prostokąt (obszar zainteresowania) wokół gracza
        player_view_rect = pygame.Rect(
            player.x - view_radius_pixels,
            player.y - view_radius_pixels,
            view_radius_pixels * 2,
            view_radius_pixels * 2
        )

        # Pobieramy z siatki tylko te sprajty, które są w tym obszarze
        sprites_to_render = sprite_grid.get_sprites_in_rect(player_view_rect)
        # --- KONIEC NOWEGO KODU ---
        renderer.draw_sprites(sprites_to_render)

        scaled_render = pygame.transform.scale(
            render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT)
        )
        last_world_render.blit(scaled_render, (0, 0))

        game_state.screen_dirty = False

    screen.blit(last_world_render, (0, 0))

    if LEVEL_TEXTURES.get(player.floor, {}).get("is_outdoor", False):
        weather_manager.draw(screen)
        day_night_manager.draw(screen)

    if game_state.current_state == "playing":
        draw_minimap(screen, player, MAPS)
        draw_buttons(screen, font)
        draw_text(
            screen,
            f"Piętro: {player.floor} | Poz: ({int(player.x/TILE)}, {int(player.y/TILE)})",
            (10, 10 + len(MAPS.get(player.floor, [])) * 8 + 10),
            info_font,
        )
        pygame.draw.rect(
            screen, pygame.Color("darkgoldenrod"), interact_rect, border_radius=20
        )
        draw_text(screen, "E", interact_rect.center, font, center=True)
    elif game_state.current_state == "combat":
        draw_combat_ui(
            screen,
            player,
            game_state.active_monster,
            game_state,
            font,
            info_font,
            ui_font,
        )
    elif game_state.current_state == "dialogue":
        draw_dialogue_ui(screen, player, game_state.active_npc, font, ui_font, logger)
    elif game_state.current_state == "inventory":
        draw_inventory_ui(screen, player, font, ui_font)
    elif game_state.current_state == "character_screen":
        draw_character_screen_ui(screen, player, font, ui_font)
    elif game_state.current_state == "trade_buy":
        draw_buy_screen_ui(screen, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == "trade_sell":
        draw_sell_screen_ui(screen, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == "trade_buy_back":
        draw_buy_back_ui(screen, player, game_state.active_npc, font, ui_font)
    elif game_state.current_state == "game_over":
        draw_game_over_ui(screen, font)

    if (
        game_state.level_up_message
        and pygame.time.get_ticks() < game_state.level_up_timer
    ):
        draw_text(
            screen,
            game_state.level_up_message,
            (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2),
            font,
            color=pygame.Color("yellow"),
            center=True,
        )

    if (
        game_state.info_message
        and pygame.time.get_ticks() < game_state.info_message_timer
    ):
        draw_text(
            screen,
            game_state.info_message,
            (SCREEN_WIDTH / 2, 50),
            ui_font,
            color=pygame.Color("yellow"),
            center=True,
        )

    if game_state.current_state != "game_over":
        draw_player_stats(screen, player, ui_font)

    if is_shaking:
        offset_x = random.randint(
            -game_state.screen_shake_intensity, game_state.screen_shake_intensity
        )
        offset_y = random.randint(
            -game_state.screen_shake_intensity, game_state.screen_shake_intensity
        )

        temp_surface = screen.copy()
        screen.fill((0, 0, 0))
        screen.blit(temp_surface, (offset_x, offset_y))
    else:
        game_state.screen_shake_intensity = 0

    pygame.display.flip()
    return True


async def main():
    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    log_file = "game_analytics.log"

    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setFormatter(log_formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    logger.info("GAME_SESSION_START")

    pygame.init()
    try:
        pygame.mixer.init()
        music_path = os.path.join("assets/music", "ThemeMy.ogg")
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(-1)
    except Exception as e:
        pass
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))


    WALLS = {
        k: pygame.image.load(os.path.join(TEXTURE_PATH, f)).convert()
        for k, f in {
            1: "wall5.png", 2: "wall2.png", 97: "wall17.png", 94: "wall17.png",
            95: "wall12.png", 96: "door_closed_wall.png", 10: "stairs_up.png",
            11: "stairs_down.png", 47: "stairs_down.png",
        }.items()
    }
    sprite_files = {k: props["texture"] for k, props in SPRITE_PROPERTIES.items()}
    SPRITE_TX = {}
    for k, filename in sprite_files.items():
        try:
            SPRITE_TX[k] = pygame.image.load(
                os.path.join(TEXTURE_PATH, filename)
            ).convert_alpha()
        except pygame.error:
            print(f"Nie można załadować tekstury: {filename}. Używam zastępczej.")
            placeholder = pygame.Surface((TILE, TILE))
            placeholder.fill(pygame.Color("magenta"))
            SPRITE_TX[k] = placeholder
    
    rain_manager = RainManager(num_particles=300, screen_width=SCREEN_WIDTH, screen_height=SCREEN_HEIGHT)
    snow_manager = SnowManager(num_particles=250, screen_width=SCREEN_WIDTH, screen_height=SCREEN_HEIGHT)
    weather_manager = WeatherManager(rain_manager, snow_manager, MAPS, WALLS.keys(), PLANE_PROPERTIES)
    day_night_manager = DayNightManager(cycle_duration_seconds=600)
    day_night_manager.weather_manager = weather_manager

    pygame.display.set_caption("Prototyp RPG")
    clock = pygame.time.Clock()
    last_world_render = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    horizontal_files = {"grass.png", "wall17.png"}
    HORIZONTAL_SURFACES = {}

    if USE_NUMPY_RENDERER:
        import numpy as np
        print("INFO: Używam szybkiego renderera NumPy.")
        for filename in horizontal_files:
            try:
                path = os.path.join(TEXTURE_PATH, filename)
                tex_raw = pygame.image.load(path).convert()
                HORIZONTAL_SURFACES[filename] = pygame.surfarray.array3d(tex_raw).transpose(1, 0, 2)
            except (pygame.error, FileNotFoundError):
                print(f"BŁĄD: Nie można załadować tekstury poziomej: {filename}")
                placeholder = np.full((TILE, TILE, 3), (255, 0, 255), dtype=np.uint8)
                HORIZONTAL_SURFACES[filename] = placeholder
    else:
        print("INFO: Używam kompatybilnego renderera Pygame.")
        for filename in horizontal_files:
            try:
                path = os.path.join(TEXTURE_PATH, filename)
                HORIZONTAL_SURFACES[filename] = pygame.image.load(path).convert()
            except (pygame.error, FileNotFoundError):
                print(f"BŁĄD: Nie można załadować tekstury poziomej: {filename}")
                placeholder = pygame.Surface((TILE, TILE))
                placeholder.fill((255, 0, 255))
                HORIZONTAL_SURFACES[filename] = placeholder

    # --- POPRAWIONA KOLEJNOŚĆ ---

    # 1. Stwórz pustą listę sprajtów
    sprites = []
    
    # 2. Wypełnij listę sprajtów danymi z map
    for fl, wm in MAPS.items():
        print("INFO: Tworzenie siatki przestrzennej dla sprajtów...")
        sprite_grid = SpriteGrid(cell_size=TILE)
        for spr in sprites:
            sprite_grid.add(spr)
        print(f"INFO: Siatka stworzona. {len(sprites)} sprajtów w {len(sprite_grid.grid)} komórkach.")
        
        for ry, row in enumerate(wm):
            for rx, vals in enumerate(row):
                leftover = []
                for v in vals:
                    sprite_id = v.get("id")
                    if sprite_id in SPRITE_PROPERTIES:
                        final_props = SPRITE_PROPERTIES[sprite_id].copy()
                        final_props.update(v)
                        if (final_props.get("type") == "monster" and "level" in final_props):
                            monster_level = final_props["level"]
                            monster_archetype = final_props.get("archetype", "standard")
                            generated_stats = generate_monster_stats(monster_level, monster_archetype)
                            final_props.update(generated_stats)
                            final_props["level"] = monster_level
                        tex = SPRITE_TX[sprite_id]
                        sprites.append(
                            Sprite((rx + 0.5) * TILE, (ry + 0.5) * TILE, fl, final_props, tex, sprite_id)
                        )
                    else:
                        leftover.append(v)
                wm[ry][rx] = leftover

    # 3. Teraz stwórz gracza i renderer
    player = Player(MAPS, WALLS)
    renderer = Renderer(None, player, MAPS, WALLS, sprites, HORIZONTAL_SURFACES, PLANE_PROPERTIES, SPRITE_PROPERTIES)

    # 4. Na koniec wywołaj funkcję ustawiającą grafikę
    update_graphics_settings(player, renderer)
    
    game_state = GameState()

    try:
        font = pygame.font.Font(FONT_PATH, 50)
        ui_font = pygame.font.Font(FONT_PATH, 38)
        info_font = pygame.font.Font(FONT_PATH, 25)
    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku czcionki w '{FONT_PATH}'. Używam czcionki domyślnej.")
        font = pygame.font.Font(None, 60)
        ui_font = pygame.font.Font(None, 46)
        info_font = pygame.font.Font(None, 36)

    running = True
    print("--- Przed wejściem do głównej pętli ---")
    

    while running:
        try:
            
            running = game_loop_step(
                player,
                game_state,
                renderer,
                sprites,
                screen,
                clock,
                font,
                ui_font,
                info_font,
                SPRITE_PROPERTIES,
                SPRITE_TX,
                last_world_render,
                logger,
                rain_manager,
                day_night_manager,
                weather_manager, 
                sprite_grid# <-- DODAJ TĘ LINIĘ
            )
        except Exception as e:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"KRYTYCZNY BŁĄD ZATRZYMAŁ GRĘ: {e}")
            import traceback
            traceback.print_exc() 
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            running = False

        await asyncio.sleep(0)

    print("Gra zakończona z powodu błędu lub zamknięcia okna.")


class Player:
    def __init__(self, maps, walls):
        self.x, self.y = TILE * 1.5, TILE * 1.5
        self.maps = maps
        self.walls = walls
        self.floor = 0
        self.height_in_level = PLAYER_HEIGHT_IN_LEVEL
        self.pitch = 0
        self.dir_idx = 0
        self.angle = 0.0
        self.target_angle = 0.0
        self.rotating = False
        self.ROT_STEP = 2.2
        # self.ROT_STEP = 1.8
        self.PITCH_SPEED = 200
        self.move_speed = TILE
        self.rotation_timer = 0
        self.move_cooldown = 100  # Opóźnienie w milisekundach (100ms = 0.1s)
        self.last_move_time = 0
        self.render_scale = 0.18

        # self.ROTATION_COOLDOWN = 0

        self.level = 1
        self.xp = 0
        self.xp_to_next_level = 90 * 2
        self.max_hp = 50 * 2
        self.hp = self.max_hp
        self.base_attack = 2 * 2
        self.base_defense = 1 * 2
        self.money = 10
        self.moc = 0
        self.max_moc = self.max_hp * 5
        self.inventory = [
            {"name": "Chleb", "value": 3, "type": "consumable", "heals": 15 * 2}
        ]
        self.equipment = {"weapon": None, "armor": None, "helmet": None, "shield": None}
        self.active_quests = {}
        self.inventory_limit = 100

    @property
    def absolute_height(self):
        return self.floor * TILE + self.height_in_level

    @property
    def attack(self):
        total_attack_bonus = 0
        # Pętla przechodzi przez każdy przedmiot w ekwipunku (broń, zbroja, hełm, tarcza)
        for item in self.equipment.values():
            if item:
                # Używamy .get("attack", 0), aby bezpiecznie dodać bonus do ataku, jeśli istnieje
                total_attack_bonus += item.get("attack", 0)
        return self.base_attack + total_attack_bonus

    @property
    def defense(self):
        total_defense_bonus = 0
        # Ta sama pętla dla obrony
        for item in self.equipment.values():
            if item:
                # Używamy .get("defense", 0), aby bezpiecznie dodać bonus do obrony, jeśli istnieje
                total_defense_bonus += item.get("defense", 0)
        return self.base_defense + total_defense_bonus

    

    def add_xp(self, amount, game_state, logger):
        self.xp += amount
        game_state.combat_log.append(f"Zdobyto {amount} XP.")
        logger.info(
            f"XP_GAIN; Amount: {amount}; TotalXP: {self.xp}/{self.xp_to_next_level}"
        )
        check_for_level_up(self, game_state, logger)

    def update(self, game_state):
        if self.rotating:
            game_state.screen_dirty = True
            diff = (self.target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            if abs(diff) < self.ROT_STEP:
                self.angle = self.target_angle
                self.rotating = False
            else:
                self.angle = (
                    self.angle + (self.ROT_STEP if diff > 0 else -self.ROT_STEP)
                ) % (2 * math.pi)

        keys = pygame.key.get_pressed()
        pitch_changed = False
        if keys[pygame.K_UP]:
            self.pitch += self.PITCH_SPEED
            pitch_changed = True
        if keys[pygame.K_DOWN]:
            self.pitch -= self.PITCH_SPEED
            pitch_changed = True

        if pitch_changed:
            self.pitch = max(-HALF_HEIGHT * 4, min(HALF_HEIGHT * 4, self.pitch))
            game_state.screen_dirty = True

    def change_floor(self, destination_floor, game_state, logger):
        if destination_floor in self.maps:
            self.floor = destination_floor
            game_state.screen_dirty = True
            logger.info(
                f"FLOOR_CHANGE; NewFloor: {destination_floor}; Position: ({self.x/TILE:.1f}, {self.y/TILE:.1f})"
            )

    def turn(self, left, game_state):

        if self.rotating:
            return
        self.dir_idx = (self.dir_idx + (-1 if left else 1)) % 4
        self.target_angle = self.dir_idx * math.pi / 2
        self.rotating = True
        game_state.screen_dirty = True

    def grid_move(self, forward, sprites, game_state, logger, player, sprite_grid):
        if self.rotating:
            return
        old_floor = self.floor
        original_x, original_y = self.x, self.y
        current_map = self.maps[self.floor]
        dx, dy = DIR_VECTORS[self.dir_idx]
        m = 1 if forward else -1
        nx, ny = self.x + dx * self.move_speed * m, self.y + dy * self.move_speed * m
        i, j = int(ny // TILE), int(nx // TILE)

        if not (0 <= i < len(current_map) and 0 <= j < len(current_map[0])):
            return

        # Określ mały obszar do sprawdzenia kolizji (tylko tam, gdzie gracz się rusza)
        check_rect = pygame.Rect(nx - TILE // 2, ny - TILE // 2, TILE, TILE)
        nearby_sprites = sprite_grid.get_sprites_in_rect(check_rect)

        for spr in nearby_sprites:
            if spr.floor == self.floor and not spr.is_dead:
                si, sj = int(spr.y // TILE), int(spr.x // TILE)
                if (si, sj) == (i, j):
                    if spr.type == "pickup_item" and spr.item_data:
                        if len(self.inventory) < self.inventory_limit:
                            self.inventory.append(spr.item_data.copy())
                            game_state.set_info_message(
                                f"Podniesiono: {spr.item_data['name']}"
                            )
                            logger.info(f"ITEM_PICKUP; Item: {spr.item_data['name']}")
                            spr.is_dead = True
                            game_state.screen_dirty = True
                        else:
                            game_state.set_info_message("Ekwipunek pełny!")
                            return

                    if spr.blocking:
                        # --- NOWA, UPROSZCZONA LOGIKA TELEPORTACJI ---
                        if spr.is_portal:
                            # Pobieramy cel z definicji sprite'a na mapie
                            props = spr.properties  # Pobieramy właściwości sprite'a
                            target_x = props.get("target_x")
                            target_y = props.get("target_y")
                            target_floor = props.get("target_floor")

                            # Sprawdzamy, czy cel został zdefiniowany
                            if (
                                target_x is not None
                                and target_y is not None
                                and target_floor is not None
                            ):
                                # Przenosimy gracza na środek docelowego pola
                                self.x = (target_x + 0.5) * TILE
                                self.y = (target_y + 0.5) * TILE
                                self.floor = target_floor
                                logger.info(
                                    f"PORTAL_USE; FromFloor: {old_floor} -> ToFloor: {target_floor}; ToPosition: ({target_x}, {target_y})"
                                )

                                # game_state.set_info_message("Teleportacja...")
                                game_state.screen_dirty = True
                                return  # Zatrzymujemy dalszy ruch

                        elif (
                            spr.type == "monster"
                            and spr.properties.get("archetype") != "resource"
                        ):
                            game_state.start_combat(spr, logger, player)

                        return

        tile_content = current_map[i][j]
        if tile_content:
            for block in tile_content:
                is_blocking_wall = (
                    block.get("id") in self.walls
                    and block.get("z", 0) == 0
                    and not ("target" in block or "target_floor" in block)
                )
                if is_blocking_wall:
                    return

        self.x, self.y = nx, ny

        if self.x != original_x or self.y != original_y:
            game_state.screen_dirty = True
            logger.info(
                f"MOVE; Position: ({self.x/TILE:.1f}, {self.y/TILE:.1f}); Floor: {self.floor}"
            )

        if self.check_for_aggression(sprites, game_state, logger):
            return

        if tile_content:
            portal_data = tile_content[0]
            # Użyjmy "target_floor" dla spójności z formatem, który podałeś
            target_floor = portal_data.get("target_floor")

            # Sprawdzenie starego formatu "target" dla kompatybilności wstecznej (np. z id=11)
            if target_floor is None:
                target_floor = portal_data.get("target")

            if target_floor is not None:
                # Zapamiętaj stary floor przed zmianą
                old_floor = self.floor

                # Sprawdź, czy są zdefiniowane konkretne koordynaty
                target_x = portal_data.get("target_x")
                target_y = portal_data.get("target_y")

                # Zmień piętro
                self.change_floor(target_floor, game_state, logger)

                # Jeśli koordynaty są podane, przenieś gracza
                if target_x is not None and target_y is not None:
                    self.x = (target_x + 0.5) * TILE
                    self.y = (target_y + 0.5) * TILE
                    # Logujemy pełną informację o precyzyjnym portalu
                    logger.info(
                        f"PORTAL_USE (Tile); FromFloor: {old_floor} -> ToFloor: {target_floor}; ToPosition: ({target_x}, {target_y})"
                    )

                # Upewnij się, że pozycja jest logowana po teleportacji
                logger.info(
                    f"MOVE after portal; Position: ({self.x/TILE:.1f}, {self.y/TILE:.1f}); Floor: {self.floor}"
                )

    def check_for_aggression(self, sprites, game_state, logger):
        player_grid_x, player_grid_y = int(self.x // TILE), int(self.y // TILE)

        # Mapa relatywnej pozycji potwora do kierunku, w który gracz musi patrzeć
        # (dx, dy): dir_idx
        adjacency_map = {
            (1, 0): 0,  # Potwór na wschodzie -> Gracz patrzy na wschód (0)
            (0, 1): 1,  # Potwór na południu -> Gracz patrzy na południe (1)
            (-1, 0): 2,  # Potwór na zachodzie -> Gracz patrzy na zachód (2)
            (0, -1): 3,  # Potwór na północy -> Gracz patrzy na północ (3)
        }

        for spr in sprites:
            # Pomiń, jeśli to nie jest żywy, agresywny potwór na tym samym piętrze
            if not (
                spr.floor == self.floor
                and spr.type == "monster"
                and spr.aggressive
                and not spr.is_dead
            ):
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
                self.rotating = True  # Uruchom mechanizm płynnego obrotu

                # Rozpocznij walkę
                game_state.start_combat(spr, logger, self)
                game_state.combat_log = [f"{spr.name} zauważył Cię i atakuje!"]

                return True  # Agresja wystąpiła, przerwij dalsze sprawdzanie

        return False

    def interact(self, sprites, game_state, logger):
        dx, dy = DIR_VECTORS[self.dir_idx]
        nx, ny = self.x + dx * TILE, self.y + dy * TILE
        i, j = int(ny // TILE), int(nx // TILE)

        for spr in sprites:
            if spr.floor == self.floor and not spr.is_dead:
                si, sj = int(spr.y // TILE), int(spr.x // TILE)
                if (si, sj) != (i, j):
                    continue

                # --- Logika dla NPC ---
                if spr.type.startswith("npc"):
                    game_state.start_dialogue(spr)
                    return

                # --- NOWA LOGIKA ZBIERANIA SUROWCÓW (JAKO WALKA) ---
                elif (
                    spr.type == "monster"
                    and spr.properties.get("archetype") == "resource"
                ):
                    required_tool = spr.properties.get("required_tool")

                    # Sprawdź, czy gracz ma odpowiednie narzędzie w ekwipunku
                    has_tool = any(
                        item.get("tool_type") == required_tool
                        for item in self.inventory
                    )

                    if has_tool:
                        # Gracz ma narzędzie, więc może rozpocząć "walkę" z surowcem
                        game_state.start_combat(spr, logger, self)
                    else:
                        # Gracz nie ma narzędzia
                        tool_name = "siekierę" if required_tool == "axe" else "kilof"
                        game_state.set_info_message(f"Potrzebujesz {tool_name}!", 2000)
                    return

    # W klasie Player

    def manage_item(self, item, game_state, logger):
        item_type = item.get("type")

        if item_type == "consumable":
            self.hp = min(self.max_hp, self.hp + item.get("heals", 0))
            game_state.set_info_message(f"Użyto: {item['name']}, +{item['heals']} HP")
            logger.info(
                f"ITEM_USE; Item: {item['name']}; Healed for: {item.get('heals', 0)}"
            )
            self.inventory.remove(item)
            return

        if item_type in self.equipment:
            # --- POCZĄTEK NOWEGO KODU ---
            level_req = item.get("level_req", 1)
            if self.level < level_req:
                game_state.set_info_message(
                    f"Wymagany poziom {level_req}, aby założyć {item['name']}."
                )
                return  # Zakończ funkcję, nie zakładaj przedmiotu
            # --- KONIEC NOWEGO KODU ---

            if self.equipment.get(item_type):
                self.inventory.append(self.equipment[item_type])

            self.equipment[item_type] = item
            self.inventory.remove(item)
            game_state.set_info_message(f"Założono: {item['name']}")
            logger.info(f"ITEM_EQUIP; Item: {item['name']}; Slot: {item_type}")

    def unequip_item(self, slot, game_state):
        if self.equipment.get(slot) and len(self.inventory) < self.inventory_limit:
            item = self.equipment[slot]
            self.inventory.append(item)
            self.equipment[slot] = None
            game_state.set_info_message(f"Zdjęto: {item['name']}")

class SpriteGrid:
    """Zarządza sprajtami w siatce dla szybkiego dostępu przestrzennego."""
    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.grid = {}  # Słownik przechowujący sprajty: {(cx, cy): [sprite1, sprite2]}

    def _get_cell_coords(self, x, y):
        """Zwraca koordynaty komórki dla danej pozycji w świecie gry."""
        return (int(x // self.cell_size), int(y // self.cell_size))

    def add(self, sprite):
        """Dodaje sprajt do odpowiedniej komórki w siatce."""
        # Każdy sprajt dodajemy tylko raz, na podstawie jego centralnego punktu
        key = self._get_cell_coords(sprite.x, sprite.y)
        if key not in self.grid:
            self.grid[key] = []
        self.grid[key].append(sprite)

    def get_sprites_in_rect(self, rect):
        """Zwraca listę unikalnych sprajtów znajdujących się w danym prostokącie."""
        sprites_found = set()  # Używamy zbioru, aby uniknąć duplikatów
        
        # Oblicz, które komórki siatki pokrywają się z prostokątem
        start_cx, start_cy = self._get_cell_coords(rect.left, rect.top)
        end_cx, end_cy = self._get_cell_coords(rect.right, rect.bottom)

        # Przejdź przez wszystkie komórki w zasięgu
        for cx in range(start_cx, end_cx + 1):
            for cy in range(start_cy, end_cy + 1):
                key = (cx, cy)
                if key in self.grid:
                    # Dodaj wszystkie sprajty z komórki do naszego zbioru
                    sprites_found.update(self.grid[key])
        
        return list(sprites_found)

class Sprite:
    def __init__(self, x, y, floor, properties, texture, sprite_id):
        self.id = sprite_id
        self.x, self.y, self.floor = x, y, floor

        self.respawn_timer = 0
        self.is_awaiting_respawn = False
        self.texture = texture
        self.scale_x = properties.get("scale_x", 1.0)
        self.scale_y = properties.get("scale_y", 1.0)
        self.blocking = properties.get("blocking", False)
        self.z = properties.get("z", 0)
        self.type = properties.get("type", "decoration")
        self.name = properties.get("name", "Obiekt")
        self.buy_back_stock = []
        # Atrybuty potworów/NPC
        self.hp = properties.get("hp")
        self.max_hp = properties.get("hp")
        self.attack = properties.get("attack")
        self.defense = properties.get("defense")
        self.xp_yield = properties.get("xp_yield")
        self.loot_table = properties.get("loot_table")
        self.item_data = properties.get("item_data")
        self.aggressive = properties.get("aggressive", False)
        self.properties = properties

        # Atrybuty NPC
        self.sells = properties.get("sells")
        self.heal_cost = properties.get("heal_cost")
        self.quest = properties.get("quest")

        self.is_portal = properties.get("is_portal", False)
        self.target_floor = properties.get("target_floor", None)

        self.is_dead = False
        self.dist = 0


import pygame
import math
import os


class Renderer:
    def __init__(
        self,
        screen,
        player,
        maps,
        walls,
        sprites,
        HORIZONTAL_TEXTURES,
        PLANE_PROPERTIES,
        SPRITE_PROPERTIES,
    ):
        self.texture_cache = {}
        self.screen = screen
        self.player = player
        self.maps = maps
        self.walls = walls
        self.sprites = sprites
        self.HORIZONTAL_SURFACES = HORIZONTAL_TEXTURES
        self.PLANE_PROPERTIES = PLANE_PROPERTIES
        self.SPRITE_PROPERTIES = SPRITE_PROPERTIES

        self.SOLID_WALLS = {1, 2, 98, 99, 94}

        print(
            "INFO: Przetwarzanie wstępne niestandardowych płaszczyzn w siatkę przestrzenną..."
        )
        self.custom_surfaces_grid = {}

        for floor_idx, world_map in maps.items():
            map_height = len(world_map)
            if map_height == 0:
                continue
            map_width = len(world_map[0])

            grid = [[None for _ in range(map_width)] for _ in range(map_height)]

            for y, row in enumerate(world_map):
                for x, cell in enumerate(row):
                    if not cell:
                        continue
                    floor_data, ceiling_data = None, None
                    for item in cell:
                        item_id = item.get("id")
                        if item_id in self.PLANE_PROPERTIES:
                            plane_props = self.PLANE_PROPERTIES[item_id]
                            full_data = plane_props.copy()
                            full_data.update(item)
                            if plane_props["type"] == "floor":
                                floor_data = full_data
                            elif plane_props["type"] == "ceiling":
                                ceiling_data = full_data
                    if floor_data or ceiling_data:
                        grid[y][x] = {"floor": floor_data, "ceiling": ceiling_data}
            self.custom_surfaces_grid[floor_idx] = grid
        print("INFO: Przetwarzanie zakończone.")

        try:
            self.sky_texture = pygame.image.load(
                os.path.join(TEXTURE_PATH, "sky.png")
            ).convert()
            self.sky_texture = pygame.transform.scale(
                self.sky_texture, (RENDER_WIDTH, RENDER_HEIGHT)
            )
        except (pygame.error, FileNotFoundError):
            self.sky_texture = None

        if USE_NUMPY_RENDERER:
            import numpy as np # Dodatkowy import dla pewności
            self.pixel_buffer = np.zeros((RENDER_HEIGHT, RENDER_WIDTH, 3), dtype=np.uint8)
        else:
            self.pixel_buffer = None # W trybie Pygame nie jest używany

    def draw_skybox(self):
        if self.sky_texture:
            sky_offset = -int(self.player.angle * (RENDER_WIDTH / (2 * math.pi)))
            self.screen.blit(self.sky_texture, (sky_offset % RENDER_WIDTH, 0))
            self.screen.blit(
                self.sky_texture, ((sky_offset % RENDER_WIDTH) - RENDER_WIDTH, 0)
            )
        else:
            self.screen.fill((135, 206, 235))

    def draw_floor_and_ceiling(self):
        if USE_NUMPY_RENDERER:
            self.draw_floor_and_ceiling_numpy()
        else:
            self.draw_floor_and_ceiling_pygame()

    def draw_floor_and_ceiling_numpy(self):
        is_outdoor = LEVEL_TEXTURES.get(self.player.floor, {}).get("is_outdoor", False)
        if is_outdoor:
            self.pixel_buffer = pygame.surfarray.array3d(self.screen).transpose(1, 0, 2)
        else:
            self.pixel_buffer.fill(0)
        horizon_y_abs = RENDER_HEIGHT // 2 + int(self.player.pitch * RENDER_SCALE)
        self.draw_horizontal_surface_numpy(horizon_y_abs, RENDER_HEIGHT, is_floor=True)
        self.draw_horizontal_surface_numpy(
            horizon_y_abs - 1, -1, is_floor=False, step=-1
        )
        pygame.surfarray.blit_array(self.screen, self.pixel_buffer.transpose(1, 0, 2))

    def draw_floor_and_ceiling_pygame(self):
        horizon = RENDER_HEIGHT // 2 + int(self.player.pitch * RENDER_SCALE)
        pos_x, pos_y = self.player.x, self.player.y
        dir_x, dir_y = math.cos(self.player.angle), math.sin(self.player.angle)
        plane_x = math.cos(self.player.angle + math.pi / 2) * math.tan(HALF_FOV)
        plane_y = math.sin(self.player.angle + math.pi / 2) * math.tan(HALF_FOV)
        left_vec_x, left_vec_y = dir_x - plane_x, dir_y - plane_y
        right_vec_x, right_vec_y = dir_x + plane_x, dir_y + plane_y
        level_defaults = LEVEL_TEXTURES.get(self.player.floor, {})
        default_floor_texture = self.HORIZONTAL_SURFACES.get(
            level_defaults.get("floor")
        )
        default_ceil_texture, default_ceil_color = None, None
        ceil_setting = level_defaults.get("ceiling")
        if isinstance(ceil_setting, str):
            default_ceil_texture = self.HORIZONTAL_SURFACES.get(ceil_setting)
        elif isinstance(ceil_setting, tuple):
            default_ceil_color = ceil_setting
        custom_grid = self.custom_surfaces_grid.get(self.player.floor)
        if not custom_grid:
            return

        grid_h = len(custom_grid)
        grid_w = len(custom_grid[0]) if grid_h > 0 else 0
        for y in range(horizon, RENDER_HEIGHT):
            dist = (self.player.height_in_level * DIST) / (y - horizon + 1e-6)
            start_wx = pos_x + dist * left_vec_x
            start_wy = pos_y + dist * left_vec_y
            end_wx = pos_x + dist * right_vec_x
            end_wy = pos_y + dist * right_vec_y
            step_x = (end_wx - start_wx) / RENDER_WIDTH
            step_y = (end_wy - start_wy) / RENDER_WIDTH
            for x in range(0, RENDER_WIDTH, PIXEL_SKIP):
                world_x = start_wx + x * step_x
                world_y = start_wy + x * step_y
                map_mx, map_my = int(world_x // TILE), int(world_y // TILE)
                candidates = []
                for ny_offset in range(-1, 2):
                    for nx_offset in range(-1, 2):
                        nx, ny = map_mx + nx_offset, map_my + ny_offset
                        if 0 <= ny < grid_h and 0 <= nx < grid_w:
                            cell_data = custom_grid[ny][nx]
                            if cell_data and cell_data.get("floor"):
                                floor_props = cell_data["floor"]
                                pad = float(floor_props.get("padding", 0.0))
                                if (
                                    nx * TILE - pad * TILE
                                    <= world_x
                                    <= (nx + 1) * TILE + pad * TILE
                                    and ny * TILE - pad * TILE
                                    <= world_y
                                    <= (ny + 1) * TILE + pad * TILE
                                ):
                                    center_x = nx * TILE + TILE / 2
                                    center_y = ny * TILE + TILE / 2
                                    dist_sq = (world_x - center_x) ** 2 + (
                                        world_y - center_y
                                    ) ** 2
                                    candidates.append((dist_sq, floor_props))
                texture_to_use = default_floor_texture
                if candidates:
                    candidates.sort(key=lambda t: t[0])
                    closest_props = candidates[0][1]
                    tex_name = closest_props.get("texture")
                    custom_tex = self.HORIZONTAL_SURFACES.get(tex_name)
                    if custom_tex:
                        texture_to_use = custom_tex
                if texture_to_use:
                    tex_w, tex_h = texture_to_use.get_size()
                    tex_x = int(world_x / TILE * tex_w) % tex_w
                    tex_y = int(world_y / TILE * tex_h) % tex_h
                    color = texture_to_use.get_at((tex_x, tex_y))
                    pygame.draw.rect(self.screen, color, (x, y, PIXEL_SKIP, 1))
        for y in range(horizon):
            dist = ((TILE - self.player.height_in_level) * DIST) / (horizon - y + 1e-6)
            start_wx = pos_x + dist * left_vec_x
            start_wy = pos_y + dist * left_vec_y
            end_wx = pos_x + dist * right_vec_x
            end_wy = pos_y + dist * right_vec_y
            step_x = (end_wx - start_wx) / RENDER_WIDTH
            step_y = (end_wy - start_wy) / RENDER_WIDTH
            for x in range(0, RENDER_WIDTH, PIXEL_SKIP):
                world_x = start_wx + x * step_x
                world_y = start_wy + x * step_y
                map_mx, map_my = int(world_x // TILE), int(world_y // TILE)
                texture_to_use = default_ceil_texture
                color_to_use = default_ceil_color
                if custom_grid and 0 <= map_my < grid_h and 0 <= map_mx < grid_w:
                    cell_data = custom_grid[map_my][map_mx]
                    if cell_data and cell_data.get("ceiling"):
                        tex_name = cell_data["ceiling"].get("texture")
                        custom_tex = self.HORIZONTAL_SURFACES.get(tex_name)
                        if custom_tex:
                            texture_to_use = custom_tex
                            color_to_use = None

                if texture_to_use:
                    tex_w, tex_h = texture_to_use.get_size()
                    tex_x = int(world_x / TILE * tex_w) % tex_w
                    tex_y = int(world_y / TILE * tex_h) % tex_h
                    color = texture_to_use.get_at((tex_x, tex_y))
                    pygame.draw.rect(self.screen, color, (x, y, PIXEL_SKIP, 1))
                elif color_to_use:
                    pygame.draw.rect(self.screen, color_to_use, (x, y, PIXEL_SKIP, 1))

    def draw_horizontal_surface_numpy(self, y_start, y_end, is_floor, step=1):
        dir_x, dir_y = math.cos(self.player.angle), math.sin(self.player.angle)
        plane_x = math.cos(self.player.angle + math.pi / 2) * math.tan(HALF_FOV)
        plane_y = math.sin(self.player.angle + math.pi / 2) * math.tan(HALF_FOV)
        pos_x, pos_y = self.player.x / TILE, self.player.y / TILE
        horizon_y_abs = RENDER_HEIGHT // 2 + int(self.player.pitch * RENDER_SCALE)
        left_vec_x, left_vec_y = dir_x - plane_x, dir_y - plane_y
        right_vec_x, right_vec_y = dir_x + plane_x, dir_y + plane_y
        rays_dir_x = np.linspace(left_vec_x, right_vec_x, RENDER_WIDTH)
        rays_dir_y = np.linspace(left_vec_y, right_vec_y, RENDER_WIDTH)
        current_level_defaults = LEVEL_TEXTURES.get(self.player.floor, {})
        default_res_name = current_level_defaults.get(
            "floor" if is_floor else "ceiling"
        )
        default_res = (
            self.HORIZONTAL_SURFACES.get(default_res_name)
            if isinstance(default_res_name, str)
            else default_res_name
        )
        custom_grid = self.custom_surfaces_grid.get(self.player.floor)
        grid_h = len(custom_grid) if custom_grid else 0
        grid_w = len(custom_grid[0]) if grid_h > 0 else 0
        for y in range(y_start, y_end, step):
            p = (y - horizon_y_abs) if is_floor else (horizon_y_abs - y)
            if p == 0:
                continue
            cam_z = (
                (0.5 * self.player.height_in_level / TILE)
                if is_floor
                else (0.5 * (TILE - self.player.height_in_level) / TILE)
            )
            row_distance = cam_z * (PROJ_COEFF / TILE) / p
            row_wx = pos_x + row_distance * rays_dir_x
            row_wy = pos_y + row_distance * rays_dir_y
            final_color_row = np.zeros((RENDER_WIDTH, 3), dtype=np.uint8)
            if default_res is not None:
                if isinstance(default_res, np.ndarray):
                    tex_h, tex_w = default_res.shape[:2]
                    tex_x = (row_wx * tex_w).astype(int) & (tex_w - 1)
                    tex_y = (row_wy * tex_h).astype(int) & (tex_h - 1)
                    final_color_row = default_res[tex_y, tex_x]
                else:
                    final_color_row[:] = default_res
            if custom_grid:
                map_x_coords = row_wx.astype(int)
                map_y_coords = row_wy.astype(int)
                for map_x, map_y in np.unique(
                    np.stack((map_x_coords, map_y_coords), axis=-1), axis=0
                ):
                    if 0 <= map_y < grid_h and 0 <= map_x < grid_w:
                        cell_data = custom_grid[map_y][map_x]
                        if cell_data:
                            surface_data = cell_data.get(
                                "floor" if is_floor else "ceiling"
                            )
                            if surface_data:
                                mask = (map_x_coords == map_x) & (map_y_coords == map_y)
                                tex_name = surface_data.get("texture")
                                tex_array = self.HORIZONTAL_SURFACES.get(tex_name)
                                if tex_array is not None:
                                    tex_h, tex_w = tex_array.shape[:2]
                                    tex_coord_x = (row_wx[mask] * tex_w).astype(int) & (
                                        tex_w - 1
                                    )
                                    tex_coord_y = (row_wy[mask] * tex_h).astype(int) & (
                                        tex_h - 1
                                    )
                                    final_color_row[mask] = tex_array[
                                        tex_coord_y, tex_coord_x
                                    ]
            self.pixel_buffer[y, :] = final_color_row

    def draw_sprites(self, sprites_to_draw):
        sprites_with_depth = []
        for spr in sprites_to_draw:
            if spr.is_dead or spr.floor != self.player.floor:
                continue
            dx, dy = spr.x - self.player.x, spr.y - self.player.y
            dist = math.hypot(dx, dy)
            theta = math.atan2(dy, dx)
            gamma = (theta - self.player.angle) % (2 * math.pi)
            if gamma > math.pi:
                gamma -= 2 * math.pi
            if abs(gamma) > HALF_FOV + 0.1:
                continue
            dist_corr = dist * math.cos(gamma)
            sprites_with_depth.append((spr, dist_corr, gamma, theta))
        sprites_with_depth.sort(key=lambda t: t[1], reverse=True)

        for spr, dist_corr, gamma, theta in sprites_with_depth:
            if dist_corr < 0.5:
                continue
            
            props = self.SPRITE_PROPERTIES.get(spr.id, {})
            is_billboard = props.get("billboard", True)
            proj_h = PROJ_COEFF / (dist_corr + 1e-6) * spr.scale_y
            base_proj_w = PROJ_COEFF / (dist_corr + 1e-6) * spr.scale_x
            proj_w = base_proj_w

            if not is_billboard:
                orientation = props.get("orientation", "x")
                sprite_plane_angle = math.pi / 2 if orientation == "x" else 0
                angle_between_view_and_normal = self.player.angle - sprite_plane_angle
                angle_factor = abs(math.cos(angle_between_view_and_normal))
                proj_w *= angle_factor
            
            screen_x = (gamma / HALF_FOV + 1) * (RENDER_WIDTH / 2) - proj_w / 2
            sprite_base_abs_height = spr.floor * TILE + spr.z * TILE
            height_diff = sprite_base_abs_height - self.player.absolute_height
            y_offset_from_horizon = (PROJ_COEFF * height_diff) / (
                dist_corr * TILE + 1e-6
            )
            render_half_height = RENDER_HEIGHT // 2
            y_base_on_screen = (
                render_half_height + int(self.player.pitch * RENDER_SCALE)
            ) - y_offset_from_horizon
            vert_pos = y_base_on_screen - proj_h

            proj_w_int = int(proj_w)
            proj_h_int = int(proj_h)

            scaled_texture = None 
            
            if proj_w_int > 0 and proj_h_int > 0:
                cache_key = (spr.id, proj_w_int, proj_h_int)
                
                scaled_texture = self.texture_cache.get(cache_key)

                if scaled_texture is None:
                    try:
                        scaled_texture = pygame.transform.scale(
                            spr.texture, (proj_w_int, proj_h_int)
                        )
                        # ...i zapisz wynik w cache'u na przyszłość!
                        self.texture_cache[cache_key] = scaled_texture
                    except (ValueError, pygame.error):
                        continue
            
            if scaled_texture is None:
                continue

            for tex_x in range(scaled_texture.get_width()):
                current_screen_x = int(screen_x + tex_x)
                if 0 <= current_screen_x < RENDER_WIDTH:
                    # Użyj NUM_RAYS zamiast RENDER_WIDTH do indeksowania z_buffer
                    ray_idx = int(current_screen_x * NUM_RAYS / RENDER_WIDTH)
                    # Upewnij się, że indeks jest w zakresie
                    if 0 <= ray_idx < NUM_RAYS and self.z_buffer[ray_idx] > dist_corr:
                        self.screen.blit(
                            scaled_texture,
                            (current_screen_x, vert_pos),
                            (tex_x, 0, 1, scaled_texture.get_height()),
                        )

    def draw_walls(self):
        self.z_buffer = [float("inf")] * NUM_RAYS
        current_map = self.maps[self.player.floor]
        cur_angle = self.player.angle - HALF_FOV
        column_width = RENDER_WIDTH / NUM_RAYS
        horizon = RENDER_HEIGHT // 2 + int(self.player.pitch * RENDER_SCALE)
        for ray in range(NUM_RAYS):
            column_segments = []
            sin_a, cos_a = math.sin(cur_angle), math.cos(cur_angle)
            pos_x, pos_y = self.player.x, self.player.y
            x_map, y_map = int(pos_x // TILE), int(pos_y // TILE)
            delta_x, delta_y = abs(TILE / (cos_a or 1e-6)), abs(TILE / (sin_a or 1e-6))
            step_x, step_y = (1 if cos_a > 0 else -1), (1 if sin_a > 0 else -1)
            side_dx = ((x_map + (1 if cos_a > 0 else 0)) * TILE - pos_x) / (
                cos_a or 1e-6
            )
            side_dy = ((y_map + (1 if sin_a > 0 else 0)) * TILE - pos_y) / (
                sin_a or 1e-6
            )
            should_break_dda = False
            for _ in range(MAX_DEPTH):
                if side_dx < side_dy:
                    depth = side_dx
                    side_dx += delta_x
                    x_map += step_x
                    wx = pos_y + depth * sin_a
                else:
                    depth = side_dy
                    side_dy += delta_y
                    y_map += step_y
                    wx = pos_x + depth * cos_a
                if not (
                    0 <= y_map < len(current_map) and 0 <= x_map < len(current_map[0])
                ):
                    break
                blocks = current_map[y_map][x_map]
                if not blocks:
                    continue
                wall_blocks = [b for b in blocks if b.get("id") in self.walls]
                if not wall_blocks:
                    continue
                depth_corr = depth * math.cos(self.player.angle - cur_angle)
                self.z_buffer[ray] = min(depth_corr, self.z_buffer[ray])
                for block in sorted(wall_blocks, key=lambda b: b.get("z", 0)):
                    x1 = int(ray * column_width)
                    w = max(1, int((ray + 1) * column_width) - x1)
                    tex_id = block["id"]
                    proj_h = PROJ_COEFF / (depth_corr + 1e-6)
                    z_offset = block.get("z", 0)
                    wall_height = block.get("h", 1.0)
                    h_wall_bottom_rel = z_offset * TILE
                    h_wall_top_rel = h_wall_bottom_rel + (wall_height * TILE)
                    h_player_rel = self.player.height_in_level
                    y_top = horizon - proj_h * (h_wall_top_rel - h_player_rel) / TILE
                    y_bottom = (
                        horizon - proj_h * (h_wall_bottom_rel - h_player_rel) / TILE
                    )
                    if y_bottom - y_top > 0:
                        off = int((wx % TILE) / TILE * self.walls[tex_id].get_width())
                        segment_data = (depth_corr, y_top, y_bottom, tex_id, off, x1, w)
                        column_segments.append(segment_data)
                    if (
                        tex_id in self.SOLID_WALLS
                        and y_top <= 0
                        and y_bottom >= RENDER_HEIGHT
                    ):
                        should_break_dda = True
                if should_break_dda:
                    break
            column_segments.sort(key=lambda x: x[0], reverse=True)
            for _, y_top, y_bottom, tex_id, off, x1, w in column_segments:
                if y_bottom > y_top:
                    target_h = int(y_bottom - y_top)
                    cache_key = (tex_id, off, target_h, w)
                    col = self.texture_cache.get(cache_key)
                    if col is None:
                        tex = self.walls[tex_id]
                        raw_col = tex.subsurface(off, 0, 1, tex.get_height())
                        col = pygame.transform.scale(raw_col, (w, target_h))
                        self.texture_cache[cache_key] = col
                    self.screen.blit(col, (x1, y_top))
            cur_angle += DELTA_ANGLE


# --- Funkcje pomocnicze i UI ---
def draw_text(
    surface,
    text,
    pos,
    font,
    color=pygame.Color("white"),
    shadow_color=pygame.Color("black"),
    center=False,
):
    text_surface = font.render(text, True, color)
    shadow_surface = font.render(text, True, shadow_color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = pos
    else:
        text_rect.topleft = pos
    surface.blit(shadow_surface, (text_rect.x + 2, text_rect.y + 2))
    surface.blit(text_surface, text_rect)


def process_player_attack(player, monster, game_state, logger):
    if not game_state.player_turn:
        return

    # --- NOWA LOGIKA: Sprawdź, czy walczysz z surowcem ---
    if monster.properties.get("archetype") == "resource":
        # Jesteś w trakcie zbierania surowca
        required_tool = monster.properties.get("required_tool")

        # Znajdź najlepsze narzędzie danego typu w ekwipunku gracza
        best_gathering_damage = 0
        for item in player.inventory:
            if item.get("tool_type") == required_tool:
                damage = item.get("gathering_damage", 0)
                if damage > best_gathering_damage:
                    best_gathering_damage = damage

        # Jeśli z jakiegoś powodu nie znaleziono narzędzia, uderzaj za 1 (ręką)
        if best_gathering_damage == 0:
            best_gathering_damage = 1

        dmg = max(0, best_gathering_damage - monster.defense)
        monster.hp -= dmg

        # Zmień komunikat, aby pasował do akcji
        action_text = "Rąbiesz drzewo" if required_tool == "axe" else "Uderzasz w złoże"
        game_state.combat_log.append(f"{action_text}! Postęp: {dmg}")
        logger.info(
            f"RESOURCE_GATHERING; Target: {monster.name}; Damage: {dmg}; ResourceHP: {monster.hp}/{monster.max_hp}"
        )

    else:
        # --- ORYGINALNA LOGIKA: Normalna walka z potworem ---
        final_attack = player.attack
        is_crit = False
        if random.random() < 0.2:
            final_attack = math.ceil(player.attack * 1.2)
            game_state.combat_log.append("Zadajesz mocniejszy cios!")
            is_crit = True

        dmg = max(0, final_attack - monster.defense)
        monster.hp -= dmg
        game_state.combat_log.append(f"Zadałeś {dmg} obrażeń przeciwnikowi!")
        logger.info(
            f"PLAYER_ATTACK; Target: {monster.name}; Damage: {dmg}; Crit: {is_crit}; MonsterHP: {monster.hp}/{monster.max_hp}"
        )

    # --- Wspólna logika zakończenia "walki" ---
    if monster.hp <= 0:
        monster.is_dead = True
        game_state.screen_dirty = True

        if monster.properties.get("archetype") == "resource":
            game_state.combat_log.append(f"Zdobyto surowiec: {monster.name}!")
        else:
            game_state.combat_log.append(
                f"Pokonałeś {monster.name}! +{monster.xp_yield} XP."
            )

        player.add_xp(monster.xp_yield, game_state, logger)
        process_loot(player, monster, game_state)
        check_for_level_up(player, game_state, logger)
        game_state.end_combat(player, logger, "Win")
    else:
        game_state.player_turn = False
        game_state.combat_turn += 1


def are_respawns_allowed_on_floor(floor_index, player, game_state, all_sprites):
    """
    Centralna funkcja sprawdzająca, czy potwory mogą się odradzać na danym piętrze.
    Zwraca True, jeśli tak. Zwraca False, jeśli jakikolwiek warunek jest spełniony.
    """

    # --- TUTAJ DODAJESZ SWOJE PRZYSZŁE REGUŁY ---

    # PRZYKŁAD 1: Nie odradzaj potworów, jeśli na piętrze wciąż żyje boss
    for spr in all_sprites:
        if (
            spr.floor == floor_index
            and not spr.is_dead
            and spr.properties.get("no_respawn")
        ):
            # Znaleziono żywego bossa na tym piętrze
            # print(f"DEBUG: Respawn na piętrze {floor_index} zablokowany przez żywego bossa: {spr.name}")
            return False

    # PRZYKŁAD 2: Nie odradzaj potworów w piwnicy, jeśli gracz ma w ekwipunku "Święty Amulet"
    # if floor_index == -1:
    #     for item in player.inventory:
    #         if item['name'] == "Święty Amulet":
    #             # print("DEBUG: Respawn w piwnicy zablokowany przez amulet.")
    #             return False

    # PRZYKŁAD 3: Nie odradzaj potworów, jeśli aktywne jest zadanie "Eskorta"
    # if "Eskorta kupca" in player.active_quests:
    #     # print("DEBUG: Respawn zablokowany na czas eskorty.")
    #     return False

    # Jeśli żaden z powyższych warunków nie został spełniony, odradzanie jest dozwolone
    return True


def process_loot(player, monster, game_state):
    # Sprawdź, czy potwór w ogóle ma zdefiniowaną tabelę lootu
    if not monster.loot_table:
        return

    found_items_messages = []

    # Przejdź przez KAŻDY możliwy przedmiot w tabeli lootu
    for loot_entry in monster.loot_table:
        # Sprawdź szansę na wypadnięcie tego konkretnego przedmiotu
        if random.random() < loot_entry["chance"]:
            if len(player.inventory) < player.inventory_limit:

                item_dict = loot_entry["item"].copy()
                player.inventory.append(item_dict)

                found_items_messages.append(f"Zdobyłeś: {item_dict['name']}!")
            else:
                game_state.combat_log.append("Twój ekwipunek jest pełny!")
                break

    # Jeśli znaleziono jakiekolwiek przedmioty, połącz je w jedną wiadomość
    if found_items_messages:
        full_message = "".join(found_items_messages)
        game_state.combat_log.append(full_message)
        game_state.set_info_message(full_message, 4000)


def replace_quest_rats_with_barrels(
    sprites, sprite_properties, sprite_textures, game_state
):
    """
    Zamienia martwe szczury (ID 3) w piwnicy (piętro -1) na żywe beczki (ID 24).
    Funkcja jest wywoływana po ukończeniu zadania od Uzdrowicielki.
    """
    print("INFO: Uruchomiono zamianę szczurów na beczki.")
    barrel_id = 24  # Użyjemy wzmocnionej beczki jako nagrody

    try:
        # Krok 1: Pobierz bazowe właściwości beczki (które mają 'level' i 'archetype')
        barrel_props = sprite_properties[barrel_id].copy()
        barrel_tex = sprite_textures[barrel_id]

        # Krok 2: WYGENERUJ STATYSTYKI DLA BECZKI (TEGO BRAKOWAŁO)
        if "level" in barrel_props:
            barrel_level = barrel_props["level"]
            barrel_archetype = barrel_props.get("archetype", "standard")
            generated_stats = generate_monster_stats(barrel_level, barrel_archetype)
            # Zaktualizuj słownik właściwości o wygenerowane statystyki (HP, atak, etc.)
            barrel_props.update(generated_stats)
        else:
            # Zabezpieczenie, gdyby beczka miała ręcznie wpisane staty
            print(f"OSTRZEŻENIE: Beczka o ID {barrel_id} nie używa systemu poziomów.")

    except KeyError:
        print(
            f"BŁĄD: Nie można znaleźć właściwości lub tekstury dla sprajta o ID: {barrel_id}"
        )
        return

    # Przejdź przez wszystkie sprajty w grze
    for spr in sprites:
        # Sprawdź, czy sprajt to martwy szczur (ID 3) i czy znajduje się w piwnicy (piętro -1)
        if spr.id == 3 and spr.floor == -1 and spr.is_dead:
            print(f"INFO: Zamieniam szczura na pozycji ({spr.x}, {spr.y}) na beczkę.")

            # Krok 3: Zaktualizuj sprajta używając W PEŁNI PRZYGOTOWANYCH właściwości
            spr.id = barrel_id
            spr.texture = barrel_tex
            spr.properties = barrel_props  # Przypisz cały zaktualizowany słownik

            # Aktualizuj kluczowe atrybuty sprajta z gotowego słownika
            spr.scale_x = barrel_props.get("scale_x", 1.0)
            spr.scale_y = barrel_props.get("scale_y", 1.0)
            spr.blocking = barrel_props.get("blocking", True)
            spr.type = barrel_props.get("type", "monster")
            spr.name = barrel_props.get("name", "Beczka")
            spr.hp = barrel_props.get("hp")
            spr.max_hp = barrel_props.get("hp")  # Ważne, aby zresetować też max_hp
            spr.attack = barrel_props.get("attack")
            spr.defense = barrel_props.get("defense")
            spr.xp_yield = barrel_props.get("xp_yield")
            spr.loot_table = barrel_props.get("loot_table")
            spr.aggressive = barrel_props.get("aggressive", False)
            spr.is_dead = False  # Upewnij się, że beczka jest "żywa"

    game_state.screen_dirty = True


def process_panic_escape(player, game_state, logger):
    """Obsługuje logikę "Paniczej Ucieczki" z walki."""
    message = "Paniczna ucieczka! Tracisz całe XP z tego poziomu."

    # Sprawdź, czy XP gracza jest poniżej połowy progu do następnego poziomu
    is_below_half_xp = player.xp < (player.xp_to_next_level / 2)

    # Zresetuj XP do zera
    player.xp = 0

    # Jeśli warunek XP był spełniony, nałóż karę do statystyk
    if is_below_half_xp:
        # Losowo wybierz, czy osłabić Atak, czy Obronę
        if random.choice(["attack", "defense"]) == "attack":
            # Upewnij się, że statystyka nie spadnie poniżej 1
            if player.base_attack > 0:
                player.base_attack -= 1
                message += " Twój Atak został osłabiony o 1."
            else:
                message += " Twój Atak jest już na minimalnym poziomie."
        else:
            if player.base_defense > 0:
                player.base_defense -= 1
                message += " Twoja Obrona została osłabiona o 1."
            else:
                message += " Twoja Obrona jest już na minimalnym poziomie."

    # Zakończ walkę i wyświetl graczowi komunikat o konsekwencjach
    game_state.end_combat(player, logger, "PanicFled")
    game_state.set_info_message(
        message, 5000
    )  # Ustaw dłuższy czas wyświetlania ważnego komunikatu


# NOWA FUNKCJA DO OBSŁUGI ATAKU MOCĄ
def process_player_power_attack(player, monster, game_state, logger):
    """Obsługuje specjalny atak gracza, który zużywa całą moc."""
    if not game_state.player_turn or player.moc <= 0:
        return

    # Oblicz obrażenia na podstawie Mocy
    dmg = int(player.moc / 10)

    # Zresetuj moc do zera
    player.moc = 0

    # Zadaj obrażenia i dodaj wpis do logu
    monster.hp -= dmg
    logger.info(
        f"PLAYER_ATTACK (MOC); Target: {monster.name}; Damage: {dmg}; MonsterHP: {monster.hp}/{monster.max_hp}"
    )
    game_state.combat_log.append(f"Używasz Mocy! Zadajesz {dmg} obrażeń!")

    # Sprawdź, czy potwór został pokonany
    if monster.hp <= 0:
        monster.is_dead = True
        game_state.screen_dirty = True
        game_state.combat_log.append(f"Pokonałeś {monster.name} potęgą Mocy!")
        player.add_xp(monster.xp_yield, game_state, logger)

        process_loot(player, monster, game_state)
        check_for_level_up(player, game_state, logger)
        game_state.end_combat(player, logger, "Win")
    else:
        # Zakończ turę gracza
        game_state.player_turn = False
        game_state.combat_turn += 1


# ZAKTUALIZOWANA FUNKCJA ATAKU POTWORA
def process_monster_attack(player, monster, game_state, logger):
    if game_state.player_turn:
        return

    final_attack = monster.attack
    is_crit = False
    if random.random() < 0.2:
        final_attack = math.ceil(monster.attack * 1.2)
        game_state.combat_log.append("Przeciwnik zadaje mocniejszy cios!")
        is_crit = True
        game_state.screen_shake_intensity = 15
        game_state.screen_shake_timer = pygame.time.get_ticks() + 200
    dmg = max(0, final_attack - player.defense)

    player.hp -= dmg
    logger.info(
        f"MONSTER_ATTACK; Attacker: {monster.name}; Damage: {dmg}; Crit: {is_crit}; PlayerHP: {player.hp}/{player.max_hp}"
    )

    # <<< NOWOŚĆ: Ładowanie paska Mocy >>>
    # Pasek mocy ładuje się o wartość otrzymanych obrażeń.
    if dmg > 0:
        player.moc = min(player.max_moc, player.moc + dmg)

    game_state.combat_log.append(f"{monster.name} zadał Ci {dmg} obrażeń!")
    if player.hp <= 0:
        handle_player_death(player, game_state, logger)
    else:
        game_state.player_turn = True
        game_state.combat_turn += 1


def check_for_level_up(player, game_state, logger):
    if player.xp >= player.xp_to_next_level:
        # <<< NOWOŚĆ: Sprawdzenie warunku dla paska Mocy PRZED awansem >>>
        is_power_full_before_levelup = player.moc >= player.max_moc

        player.level += 1
        player.xp -= player.xp_to_next_level
        player.xp_to_next_level = int(player.xp_to_next_level * 1.9)
        player.max_hp += 10
        player.hp = int(max(player.hp, player.max_hp * 0.70))
        logger.info(f"LEVEL_UP; NewLevel: {player.level}; NewMaxHP: {player.max_hp}")

        # <<< NOWOŚĆ: Aktualizacja max_moc z wyjątkiem >>>
        if not is_power_full_before_levelup:
            player.max_moc = player.max_hp * 5

        if player.level % 2 != 0:
            player.base_attack += 1
        else:
            player.base_defense += 1
        game_state.combat_log.append("AWANS NA WYŻSZY POZIOM!")

        game_state.level_up_message = f"AWANS NA NOWY POZIOM: {player.level}"
        game_state.level_up_timer = pygame.time.get_ticks() + 4000


def handle_player_death(player, game_state, logger):
    game_state.current_state = "game_over"
    # DODAJ TĘ LINIĘ
    logger.critical(
        f"PLAYER_DEATH; FinalLevel: {player.level}; FinalMoney: {player.money}"
    )


# ZAKTUALIZOWANA FUNKCJA RYSUJĄCA STATYSTYKI GRACZA
def draw_player_stats(scr, player, font):
    # --- Pasek HP ---
    hp_bar_x = 20
    hp_bar_y = SCREEN_HEIGHT - 50
    hp_bar_width = 200
    hp_bar_height = 25
    current_hp_width = max(0, (player.hp / player.max_hp) * hp_bar_width)
    pygame.draw.rect(
        scr, pygame.Color("darkred"), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height)
    )
    pygame.draw.rect(
        scr, pygame.Color("red"), (hp_bar_x, hp_bar_y, current_hp_width, hp_bar_height)
    )
    pygame.draw.rect(
        scr, pygame.Color("white"), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), 2
    )

    # --- Pasek XP ---
    xp_bar_x = 250
    xp_bar_y = SCREEN_HEIGHT - 50
    xp_bar_width = 200
    xp_bar_height = 25
    xp_ratio = (
        (player.xp / player.xp_to_next_level) if player.xp_to_next_level > 0 else 0
    )
    current_xp_width = max(0, xp_ratio * xp_bar_width)
    pygame.draw.rect(
        scr, pygame.Color("gray25"), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height)
    )
    pygame.draw.rect(
        scr, pygame.Color("gold"), (xp_bar_x, xp_bar_y, current_xp_width, xp_bar_height)
    )
    pygame.draw.rect(
        scr, pygame.Color("white"), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height), 2
    )

    # <<< NOWOŚĆ: Pasek Mocy >>>
    power_bar_x = 480  # Po prawej od paska XP
    power_bar_y = SCREEN_HEIGHT - 50
    power_bar_width = 200
    power_bar_height = 25
    power_ratio = (player.moc / player.max_moc) if player.max_moc > 0 else 0
    current_power_width = max(0, power_ratio * power_bar_width)
    pygame.draw.rect(
        scr,
        pygame.Color("purple4"),
        (power_bar_x, power_bar_y, power_bar_width, power_bar_height),
    )
    pygame.draw.rect(
        scr,
        pygame.Color("magenta"),
        (power_bar_x, power_bar_y, current_power_width, power_bar_height),
    )
    pygame.draw.rect(
        scr,
        pygame.Color("white"),
        (power_bar_x, power_bar_y, power_bar_width, power_bar_height),
        2,
    )

    # --- Pozostałe statystyki tekstowe ---
    stats_y = SCREEN_HEIGHT - 60
    lvl_text = f"LVL: {player.level}"
    money_text = f"Złoto: {player.money}"
    atk_text = f"ATK: {player.attack}"
    def_text = f"DEF: {player.defense}"

    # Pozycje statystyk zostały zaktualizowane, aby zrobić miejsce
    lvl_surf = font.render(lvl_text, True, pygame.Color("yellow"))
    scr.blit(lvl_surf, (710, stats_y))

    money_surf = font.render(money_text, True, pygame.Color("gold"))
    scr.blit(money_surf, (880, stats_y))

    atk_surf = font.render(atk_text, True, pygame.Color("orange"))
    scr.blit(atk_surf, (1100, stats_y))

    def_surf = font.render(def_text, True, pygame.Color("lightblue"))
    scr.blit(def_surf, (1250, stats_y))


# ZAKTUALIZOWANA FUNKCJA RYSUJĄCA UI WALKI
def draw_combat_ui(screen, player, monster, game_state, font, info_font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, 400))
    s.set_alpha(200)
    s.fill((30, 30, 30))
    screen.blit(s, (0, SCREEN_HEIGHT - 400))
    draw_text(screen, f"{monster.name}", (50, SCREEN_HEIGHT - 380), font)

    # Pasek HP Potwora
    hp_bar_x = 50
    hp_bar_y = SCREEN_HEIGHT - 330
    hp_bar_width = 300
    hp_bar_height = 30
    current_hp_width = (
        (monster.hp / monster.max_hp) * hp_bar_width if monster.max_hp > 0 else 0
    )
    pygame.draw.rect(
        screen,
        pygame.Color("darkred"),
        (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height),
    )
    pygame.draw.rect(
        screen,
        pygame.Color("red"),
        (hp_bar_x, hp_bar_y, max(0, current_hp_width), hp_bar_height),
    )
    pygame.draw.rect(
        screen,
        pygame.Color("white"),
        (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height),
        2,
    )
    draw_text(
        screen,
        f"{monster.hp}/{monster.max_hp}",
        (hp_bar_x + hp_bar_width / 2, hp_bar_y + hp_bar_height / 2),
        info_font,
        center=True,
    )

    for i, msg in enumerate(game_state.combat_log[-4:]):
        draw_text(screen, msg, (50, SCREEN_HEIGHT - 250 + i * 40), ui_font)

    # Zaktualizowany układ przycisków
    attack_rect = pygame.Rect(SCREEN_WIDTH - 400, SCREEN_HEIGHT - 350, 300, 80)

    # <<< NOWOŚĆ: Przycisk Mocy >>>
    power_rect = pygame.Rect(SCREEN_WIDTH - 400, SCREEN_HEIGHT - 260, 300, 80)

    flee_rect = pygame.Rect(SCREEN_WIDTH - 400, SCREEN_HEIGHT - 170, 300, 80)
    panic_flee_rect = pygame.Rect(SCREEN_WIDTH - 400, SCREEN_HEIGHT - 80, 300, 80)

    # Rysowanie przycisków
    pygame.draw.rect(screen, pygame.Color("darkred"), attack_rect, border_radius=12)

    # <<< NOWOŚĆ: Kolor przycisku Mocy zależy od tego, czy można go użyć >>>
    power_button_color = (
        pygame.Color("darkmagenta") if player.moc > 0 else pygame.Color("gray20")
    )
    pygame.draw.rect(screen, power_button_color, power_rect, border_radius=12)

    pygame.draw.rect(screen, pygame.Color("darkblue"), flee_rect, border_radius=12)
    pygame.draw.rect(screen, pygame.Color("purple4"), panic_flee_rect, border_radius=12)

    # Teksty na przyciskach
    draw_text(screen, "Atakuj", attack_rect.center, font, center=True)
    draw_text(
        screen, "Użyj Mocy", power_rect.center, font, center=True
    )  # Tekst dla nowego przycisku
    draw_text(screen, "Wycofaj się", flee_rect.center, ui_font, center=True)
    draw_text(screen, "Paniczna Ucieczka", panic_flee_rect.center, ui_font, center=True)

    # Zwróć prostokąty wszystkich przycisków
    return attack_rect, power_rect, flee_rect, panic_flee_rect


### ZMIANA: UI Dialogów z pełną obsługą questów ###
def draw_dialogue_ui(screen, player, npc, font, ui_font, logger):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    s.set_alpha(220)
    s.fill((20, 20, 40))
    screen.blit(s, (0, 0))
    draw_text(screen, f"Rozmawiasz z: {npc.name}", (50, 50), font)

    action_rects = {}
    y_offset = 200  # Startowa pozycja Y dla przycisków

    # Logika Questów
    quest = npc.quest
    if quest:
        player_has_quest = quest.name in player.active_quests

        if player_has_quest:
            active_quest = player.active_quests[quest.name]
            if active_quest.is_complete(player):
                draw_text(
                    screen,
                    f"'Dziękuję! Moja piwnica jest bezpieczna!'",
                    (50, 120),
                    ui_font,
                )
                rect = pygame.Rect(50, y_offset, 600, 80)
                pygame.draw.rect(screen, pygame.Color("gold"), rect, border_radius=12)
                draw_text(
                    screen,
                    f"[UKOŃCZ] {quest.name}",
                    rect.center,
                    ui_font,
                    center=True,
                    color=pygame.Color("black"),
                )
                action_rects["complete_quest"] = rect
                # logger.info(f"QUEST_COMPLETE; Quest: {quest.name}; RewardXP: {quest.reward['xp']}; RewardMoney: {quest.reward['money']}")
                y_offset += 100
            else:
                item_name = active_quest.objective_conditions["item_name"]
                needed = active_quest.objective_conditions["needed"]
                current_amount = sum(
                    1 for item in player.inventory if item.get("name") == item_name
                )

                draw_text(
                    screen,
                    f"'Przynieś mi {needed} {item_name}. Masz już {current_amount}.'",
                    (50, 120),
                    ui_font,
                )
        elif not quest.is_turned_in:
            draw_text(screen, quest.description, (50, 120), ui_font)
            rect = pygame.Rect(50, y_offset, 600, 80)
            pygame.draw.rect(screen, pygame.Color("cyan"), rect, border_radius=12)
            draw_text(
                screen,
                f"[PRZYJMIJ] {quest.name}",
                rect.center,
                ui_font,
                center=True,
                color=pygame.Color("black"),
            )
            action_rects["accept_quest"] = rect
            y_offset += 100

    # Inne opcje NPC
    if npc.type == "npc_healer":
        rect2 = pygame.Rect(50, y_offset + 100, 600, 80)
        pygame.draw.rect(screen, pygame.Color("darkgreen"), rect2, border_radius=12)
        draw_text(
            screen, f"Poproś o stabilizację zdrowia", rect2.center, ui_font, center=True
        )
        rect = pygame.Rect(50, y_offset, 600, 80)
        pygame.draw.rect(screen, pygame.Color("darkgreen"), rect, border_radius=12)
        draw_text(
            screen,
            f"Zapłać za pełne leczenie ({npc.heal_cost} zł)",
            rect.center,
            ui_font,
            center=True,
        )
        action_rects["heal"] = rect
        action_rects["heal_free"] = rect2

    elif npc.type == "npc_merchant":
        draw_text(screen, "'Witaj! Czym mogę służyć?'", (50, 120), ui_font)
        rect_buy = pygame.Rect(50, y_offset, 250, 80)
        rect_sell = pygame.Rect(320, y_offset, 250, 80)
        # NOWOŚĆ: Przycisk odkupu
        rect_buy_back = pygame.Rect(590, y_offset, 250, 80)

        pygame.draw.rect(screen, pygame.Color("darkblue"), rect_buy, border_radius=12)
        pygame.draw.rect(
            screen, pygame.Color("darkgoldenrod"), rect_sell, border_radius=12
        )
        # NOWOŚĆ: Rysowanie przycisku odkupu
        pygame.draw.rect(
            screen, pygame.Color("darkgreen"), rect_buy_back, border_radius=12
        )

        draw_text(screen, "Kup", rect_buy.center, ui_font, center=True)
        draw_text(screen, "Sprzedaj", rect_sell.center, ui_font, center=True)
        # NOWOŚĆ: Tekst na przycisku
        draw_text(screen, "Odkup", rect_buy_back.center, ui_font, center=True)

        action_rects["buy_screen"] = rect_buy
        action_rects["sell_screen"] = rect_sell
        action_rects["buy_back_screen"] = rect_buy_back

    # Przycisk wyjścia
    leave_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(screen, pygame.Color("darkgray"), leave_rect, border_radius=12)
    draw_text(screen, "Wyjdź", leave_rect.center, font, center=True)

    return action_rects, leave_rect


### NOWOŚĆ: Interfejs do kupowania przedmiotów ###
def draw_buy_screen_ui(screen, player, npc, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    s.set_alpha(240)
    s.fill((20, 20, 30))
    screen.blit(s, (0, 0))
    draw_text(screen, f"Towary Handlarza: {npc.name}", (50, 50), font)
    draw_text(
        screen,
        f"Twoje złoto: {player.money}",
        (SCREEN_WIDTH - 400, 60),
        ui_font,
        color=pygame.Color("gold"),
    )

    buy_rects = []

    for i, item in enumerate(npc.sells):
        level_req = item.get("level_req", 1)
        req_text = f" (Wym. Lvl: {level_req})" if level_req > 1 else ""
        item_text = f"- {item['name']} (Cena: {item['value']} zł){req_text}"

        item_rect = pygame.Rect(50, 120 + i * 40, 800, 40)  # Zwiększono szerokość

        # Logika kolorów
        can_afford = player.money >= item["value"]
        can_equip = player.level >= level_req

        if not can_equip:
            color = pygame.Color("darkred")  # Gracz ma za niski poziom
        elif not can_afford:
            color = pygame.Color("gray50")  # Gracza nie stać
        else:
            color = pygame.Color("cyan")  # Gracz może kupić i użyć

        draw_text(screen, item_text, (item_rect.x, item_rect.y), ui_font, color=color)
        buy_rects.append(item_rect)

    back_button_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(
        screen, pygame.Color("darkgray"), back_button_rect, border_radius=12
    )
    draw_text(screen, "Wróć", back_button_rect.center, font, center=True)

    return buy_rects, back_button_rect


### NOWOŚĆ: Interfejs do odkupywania przedmiotów ###
def draw_buy_back_ui(screen, player, npc, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    s.set_alpha(240)
    s.fill((20, 30, 20))
    screen.blit(s, (0, 0))
    draw_text(screen, "Odkup swoje przedmioty", (50, 50), font)
    draw_text(
        screen,
        f"Twoje złoto: {player.money}",
        (SCREEN_WIDTH - 400, 60),
        ui_font,
        color=pygame.Color("gold"),
    )

    buy_back_rects = []
    # Wyświetl przedmioty z magazynu handlarza
    for i, item in enumerate(npc.buy_back_stock):
        # Handlarz może chcieć odsprzedać drożej!
        buy_back_price = int(item["value"] * 1.1)  # Np. za podwójną cenę

        item_text = f"- {item['name']} (Cena odkupu: {buy_back_price} zł)"
        item_rect = pygame.Rect(50, 120 + i * 40, 800, 40)

        # Kolor zależy od tego, czy gracza stać
        color = (
            pygame.Color("yellow")
            if player.money >= buy_back_price
            else pygame.Color("gray50")
        )
        draw_text(screen, item_text, (item_rect.x, item_rect.y), ui_font, color=color)
        buy_back_rects.append(item_rect)

    back_button_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(
        screen, pygame.Color("darkgray"), back_button_rect, border_radius=12
    )
    draw_text(screen, "Wróć", back_button_rect.center, font, center=True)

    return buy_back_rects, back_button_rect


def draw_sell_screen_ui(screen, player, npc, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    s.set_alpha(240)
    s.fill((30, 20, 20))
    screen.blit(s, (0, 0))
    draw_text(screen, f"Sprzedaj przedmioty", (50, 50), font)
    draw_text(
        screen,
        f"Twoje złoto: {player.money}",
        (SCREEN_WIDTH - 400, 60),
        ui_font,
        color=pygame.Color("gold"),
    )

    sell_rects = []
    for i, item in enumerate(player.inventory):
        item_text = f"- {item['name']} (Wartość: {item['value']} zł)"
        item_rect = pygame.Rect(50, 120 + i * 40, 700, 40)
        draw_text(
            screen,
            item_text,
            (item_rect.x, item_rect.y),
            ui_font,
            color=pygame.Color("yellow"),
        )
        sell_rects.append(item_rect)

    back_button_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(
        screen, pygame.Color("darkgray"), back_button_rect, border_radius=12
    )
    draw_text(screen, "Wróć", back_button_rect.center, font, center=True)

    return sell_rects, back_button_rect


def draw_inventory_ui(screen, player, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    s.set_alpha(220)
    s.fill((20, 40, 20))
    screen.blit(s, (0, 0))
    draw_text(screen, "Ekwipunek", (50, 50), font)
    item_rects = []
    for i, item in enumerate(player.inventory):
        item_text = f"- {item['name']}"
        item_rect = pygame.Rect(50, 120 + i * 40, 800, 40)
        draw_text(
            screen,
            item_text,
            (item_rect.x, item_rect.y),
            ui_font,
            color=pygame.Color("white"),
        )
        item_rects.append(item_rect)
    draw_text(
        screen,
        "Naciśnij 'I' lub 'C', aby zamknąć. Kliknij, by użyć.",
        (50, SCREEN_HEIGHT - 100),
        ui_font,
    )
    return item_rects





### POPRAWKA: Dodanie przycisku "Zamknij" do Ekranu Postaci ###
def draw_character_screen_ui(screen, player, font, ui_font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    s.set_alpha(240)
    s.fill((40, 20, 30))
    screen.blit(s, (0, 0))
    draw_text(screen, "Karta Postaci", (50, 50), font)

    # 1. Statystyki (lewa strona)
    draw_text(screen, "Statystyki:", (50, 150), ui_font)
    stats = {
        "Poziom": player.level, "Doświadczenie": f"{player.xp} / {player.xp_to_next_level}",
        "Życie": f"{player.hp} / {player.max_hp}", "Atak": player.attack,
        "Obrona": player.defense, "Złoto": player.money,
    }
    for i, (name, value) in enumerate(stats.items()):
        draw_text(screen, f"{name}: {value}", (50, 200 + i * 40), ui_font)

    # --- Slider jakości grafiki ---
    draw_text(screen, "Jakość Grafiki:", (50, 480), ui_font)
    slider_x, slider_y, slider_width, slider_height = 50, 530, 350, 20
    slider_rect = pygame.Rect(slider_x, slider_y, slider_width, slider_height)
    knob_width, knob_height = 30, 40
    
    value_range, min_value = 0.28 - 0.14, 0.14
    current_pos_ratio = (player.render_scale - min_value) / value_range
    knob_x = slider_x + current_pos_ratio * (slider_width - knob_width)
    knob_rect = pygame.Rect(knob_x, slider_y - (knob_height - slider_height) / 2, knob_width, knob_height)

    pygame.draw.rect(screen, (80, 80, 80), slider_rect, border_radius=8)
    pygame.draw.rect(screen, pygame.Color('cyan'), knob_rect, border_radius=8)
    draw_text(screen, f"{player.render_scale:.2f}", (slider_x + slider_width + 20, slider_y - 10), ui_font)
    slider_interaction_area = slider_rect.inflate(20, 40)

    # 2. Założony ekwipunek (środek)
    draw_text(screen, "Założony ekwipunek:", (SCREEN_WIDTH / 2 - 200, 150), ui_font)
    slot_positions = {
        "helmet": (SCREEN_WIDTH / 2 - 100, 200), "armor": (SCREEN_WIDTH / 2 - 100, 300),
        "weapon": (SCREEN_WIDTH / 2 - 270, 300), "shield": (SCREEN_WIDTH / 2 + 70, 300),
    }
    equip_rects = {}
    for slot, pos in slot_positions.items():
        rect = pygame.Rect(pos[0], pos[1], 180, 80)
        pygame.draw.rect(screen, (80, 80, 80), rect, 2, border_radius=8)
        item = player.equipment.get(slot)
        if item:
            draw_text(screen, item["name"], rect.center, ui_font, color=pygame.Color("cyan"), center=True)
            equip_rects[slot] = rect
        else:
            draw_text(screen, f"[{slot.capitalize()}]", rect.center, ui_font, color=(120, 120, 120), center=True)

    # 3. Plecak (prawa strona)
    draw_text(screen, "Plecak:", (SCREEN_WIDTH - 600, 150), ui_font)
    inventory_rects = []
    for i, item in enumerate(player.inventory):
        rect = pygame.Rect(SCREEN_WIDTH - 600, 200 + i * 40, 550, 40)
        level_req = item.get("level_req", 1)
        req_text = f" (Wym. Lvl: {level_req})" if item.get("type") in player.equipment and level_req > 1 else ""
        item_text = f"- {item['name']}{req_text}"
        can_equip = player.level >= level_req
        color = "darkred" if item.get("type") in player.equipment and not can_equip else "yellow" if item.get("type") in player.equipment else "lightgreen" if item.get("type") == "consumable" else "white"
        draw_text(screen, item_text, (rect.x + 10, rect.y + 5), ui_font, color=pygame.Color(color))
        inventory_rects.append(rect)

    leave_button_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT - 150, 300, 100)
    pygame.draw.rect(screen, pygame.Color("darkgray"), leave_button_rect, border_radius=12)
    draw_text(screen, "Zamknij", leave_button_rect.center, font, center=True)
    draw_text(screen, "Kliknij przedmiot, by go założyć/zdjąć.", (50, SCREEN_HEIGHT - 100), ui_font)

    # Ta linia jest kluczowa - musi zwracać 4 wartości
    return equip_rects, inventory_rects, leave_button_rect, slider_interaction_area





def draw_game_over_ui(screen, font):
    s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    s.set_alpha(230)
    s.fill((0, 0, 0))
    screen.blit(s, (0, 0))
    draw_text(
        screen,
        "KONIEC GRY",
        (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50),
        font,
        color=pygame.Color("red"),
        center=True,
    )


def draw_buttons(scr, font):
    # font = pygame.font.SysFont(None, 60)
    # Przyciski ruchu
    for rect, label in [
        (up_rect, "W"),
        (right_rect, "D"),
        (down_rect, "S"),
        (left_rect, "A"),
    ]:
        pygame.draw.rect(scr, pygame.Color("darkgray"), rect, border_radius=12)
        pygame.draw.rect(scr, pygame.Color("black"), rect, 3, border_radius=12)
        txt = font.render(label, True, pygame.Color("white"))
        scr.blit(txt, txt.get_rect(center=rect.center))

    # Przycisk postaci (ikona "ludzika")
    pygame.draw.rect(scr, pygame.Color("darkcyan"), character_rect, border_radius=20)
    pygame.draw.circle(
        scr,
        pygame.Color("white"),
        (character_rect.centerx, character_rect.centery - 20),
        25,
    )
    pygame.draw.ellipse(
        scr,
        pygame.Color("white"),
        (character_rect.x + 35, character_rect.y + 70, 80, 70),
    )


def draw_minimap(scr, pl, maps):
    cell = 15
    view_distance = 7  # 6 kratek w każdą stronę

    current_map = maps.get(pl.floor, [])
    if not current_map or not current_map[0]:
        return

    map_height = len(current_map)
    map_width = len(current_map[0])

    # Rozmiar minimapy będzie stały: (2 * 10 + 1) x (2 * 10 + 1) kratek
    minimap_size = (2 * view_distance + 1) * cell
    mini = pygame.Surface((minimap_size, minimap_size))
    mini.fill(pygame.Color("grey"))
    # Opcjonalnie: dodaj przezroczystość dla lepszego wyglądu
    mini.set_alpha(240)

    player_tile_x = int(pl.x / TILE)
    player_tile_y = int(pl.y / TILE)

    # Określ granice pętli, które będą renderowane na minimapie
    start_col = max(0, player_tile_x - view_distance)
    end_col = min(map_width, player_tile_x + view_distance + 1)

    start_row = max(0, player_tile_y - view_distance)
    end_row = min(map_height, player_tile_y + view_distance + 1)

    for ry in range(start_row, end_row):
        for rx in range(start_col, end_col):
            # Oblicz pozycję rysowania na małej powierzchni minimapy
            draw_x = (rx - player_tile_x + view_distance) * cell
            draw_y = (ry - player_tile_y + view_distance) * cell

            cell_data = current_map[ry][rx]
            if cell_data:
                # Sprawdź czy jakikolwiek element w komórce to ściana lub schody
                is_wall = any(
                    "id" in block and block["id"] in pl.walls for block in cell_data
                )
                is_stair = any(
                    "id" in block and block["id"] in [10, 11, 40, 41, 42, 43]
                    for block in cell_data
                )

                if is_stair:
                    color = pygame.Color("yellow")
                elif is_wall:
                    color = pygame.Color("black")
                else:  # Pomijamy rysowanie, jeśli komórka nie jest "ważna"
                    continue

                pygame.draw.rect(mini, color, (draw_x, draw_y, cell, cell))

    # Gracz jest zawsze na środku minimapy
    player_draw_x = view_distance * cell + cell // 2
    player_draw_y = view_distance * cell + cell // 2
    pygame.draw.circle(
        mini, pygame.Color("blue"), (player_draw_x, player_draw_y), cell // 2
    )

    # Rysowanie kierunku gracza
    dir_dx, dir_dy = DIR_VECTORS[pl.dir_idx]
    line_end_x = player_draw_x + dir_dx * cell * 1.5
    line_end_y = player_draw_y + dir_dy * cell * 1.5
    pygame.draw.line(
        mini,
        pygame.Color("cyan"),
        (player_draw_x, player_draw_y),
        (line_end_x, line_end_y),
        2,
    )

    scr.blit(mini, (10, 10))


if __name__ == "__main__":
    if not os.path.exists(TEXTURE_PATH):
        print(f"Błąd: Nie znaleziono folderu z teksturami: '{TEXTURE_PATH}'")
        sys.exit()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Gra została zamknięta przez użytkownika.")