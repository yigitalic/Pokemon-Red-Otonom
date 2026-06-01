import time
import random
from pyboy import PyBoy

CHAR_MAP = {
    0x80: 'A', 0x81: 'B', 0x82: 'C', 0x83: 'D', 0x84: 'E', 0x85: 'F', 0x86: 'G', 0x87: 'H',
    0x88: 'I', 0x89: 'J', 0x8A: 'K', 0x8B: 'L', 0x8C: 'M', 0x8D: 'N', 0x8E: 'O', 0x8F: 'P',
    0x90: 'Q', 0x91: 'R', 0x92: 'S', 0x93: 'T', 0x94: 'U', 0x95: 'V', 0x96: 'W', 0x97: 'X',
    0x98: 'Y', 0x99: 'Z',
    0xA0: 'a', 0xA1: 'b', 0xA2: 'c', 0xA3: 'd', 0xA4: 'e', 0xA5: 'f', 0xA6: 'g', 0xA7: 'h',
    0xA8: 'i', 0xA9: 'j', 0xAA: 'k', 0xAB: 'l', 0xAC: 'm', 0xAD: 'n', 0xAE: 'o', 0xAF: 'p',
    0xB0: 'q', 0xB1: 'r', 0xB2: 's', 0xB3: 't', 0xB4: 'u', 0xB5: 'v', 0xB6: 'w', 0xB7: 'x',
    0xB8: 'y', 0xB9: 'z',
    0xE8: '!', 0xE6: '?', 0xF2: '.', 0xF4: ',', 0x7F: ' ', 0x50: '[EOF]',
    0xF6: '0', 0xF7: '1', 0xF8: '2', 0xF9: '3', 0xFA: '4', 0xFB: '5', 0xFC: '6', 0xFD: '7', 0xFE: '8', 0xFF: '9'
}

def decode_pokemon_text(byte_array):
    result = ""
    for b in byte_array:
        if b in CHAR_MAP:
            result += CHAR_MAP[b]
        elif b not in [0x00, 0x7F, 0xFF]:
            result += " " 
    return " ".join(result.split())

class PokemonBrockBot:
    def __init__(self, rom_path):
        self.pyboy = PyBoy(rom_path, window="SDL2")
        self.pyboy.set_emulation_speed(3)
        
        # Kritik RAM Adresleri
        self.ADDR_BATTLE_STATE = 0xD057
        self.ADDR_MAP_ID = 0xD35E
        self.ADDR_X_COORD = 0xD362
        self.ADDR_Y_COORD = 0xD361
        self.ADDR_BADGES = 0xD356
        self.ADDR_TEXT_OPEN = 0xCFD8
        self.ADDR_HP = 0xD16D
        self.ADDR_PARTY_COUNT = 0xD163

        # Harita ID Tanımlamaları
        self.MAP_PALLET_TOWN = 0x00
        self.MAP_ROUTE_1 = 0x01
        self.MAP_VIRIDIAN_CITY = 0x02
        self.MAP_PEWTER_CITY = 0x03
        self.MAP_ROUTE_2 = 0x0D
        self.MAP_REDS_HOUSE_1F = 0x25
        self.MAP_REDS_HOUSE_2F = 0x26
        self.MAP_OAKS_LAB = 0x28
        self.MAP_VIRIDIAN_MART = 0x2A
        self.MAP_POKECENTER = 0x2B
        self.MAP_GATE_S = 0x2F
        self.MAP_GATE_N = 0x30
        self.MAP_VIRIDIAN_FOREST = 0x33
        self.MAP_PEWTER_GYM = 0x36

        # Hikaye Aşaması (Story State)
        self.story_state = "GET_PARCEL"

        # Story State tabanlı Rota Sistemi
        self.routes = {
            "GET_PARCEL": {
                self.MAP_REDS_HOUSE_2F: [(7, 1)],
                self.MAP_REDS_HOUSE_1F: [(3, 8)],
                self.MAP_PALLET_TOWN: [(10, 0)],
                self.MAP_OAKS_LAB: [(6, 4, 'A'), (5, 11)], # Oak laboratuvarına getirdiğinde Pokemon seç ve çık
                self.MAP_ROUTE_1: [(10, 25), (10, 18), (11, 4), (10, 0)],
                self.MAP_VIRIDIAN_CITY: [(29, 20), (29, 19)],
                self.MAP_VIRIDIAN_MART: [(3, 5)]
            },
            "RETURN_TO_OAK": {
                self.MAP_VIRIDIAN_MART: [(3, 8)],
                self.MAP_VIRIDIAN_CITY: [(29, 21), (21, 25), (21, 35)],
                self.MAP_ROUTE_1: [(14, 0), (14, 4), (10, 18), (10, 25), (10, 35)],
                self.MAP_PALLET_TOWN: [(10, 8), (12, 11)],
                self.MAP_OAKS_LAB: [(5, 3)]
            },
            "GO_TO_POKECENTER": {
                self.MAP_OAKS_LAB: [(5, 11)],
                self.MAP_PALLET_TOWN: [(10, 0)],
                self.MAP_ROUTE_1: [(10, 25), (10, 18), (11, 4), (10, 0)],
                self.MAP_VIRIDIAN_CITY: [(21, 35), (21, 25), (23, 25)],
                self.MAP_POKECENTER: [(3, 3)]
            },
            "BUY_POKEBALL": {
                self.MAP_POKECENTER: [(3, 8)],
                self.MAP_VIRIDIAN_CITY: [(23, 26), (29, 26), (29, 19)],
                self.MAP_VIRIDIAN_MART: [(3, 5)]
            },
            "TO_VIRIDIAN_FOREST": {
                self.MAP_VIRIDIAN_MART: [(3, 8)],
                self.MAP_VIRIDIAN_CITY: [(29, 21), (18, 0)],
                self.MAP_ROUTE_2: [(9, 0), (3, 43)], # Yukarı çıkıp kapıya gir
                self.MAP_GATE_S: [(5, 0)],
                self.MAP_VIRIDIAN_FOREST: [(17, 43), (25, 43), (25, 20), (16, 20), (16, 12), (2, 12), (2, 0)],
                self.MAP_GATE_N: [(5, 0)],
                self.MAP_PEWTER_CITY: [(14, 17), (14, 7), (16, 7)],
                self.MAP_PEWTER_GYM: [(4, 3)]
            }
        }
        
        self.current_route_index = 0
        self.last_map = -1
        
        # Takılma Sistemi ve Harita Hafızası
        self.known_walls = {}
        self.last_direction = None
        self.last_x = -1
        self.last_y = -1
        self.stuck_frames = 0
        self.escape_dir = 'UP'
        self.step_counter = 0
        self.intro_done = False

    def read_ram(self, address):
        return self.pyboy.memory[address]

    def read_screen_text(self):
        dialog_bytes = [self.read_ram(addr) for addr in range(0x9800, 0x9BFF)]
        return decode_pokemon_text(dialog_bytes).lower()

    def press(self, button, frames=20):
        self.pyboy.button_press(button)
        for _ in range(frames): self.pyboy.tick()
        self.pyboy.button_release(button)
        for _ in range(2): self.pyboy.tick()

    def handle_battle(self):
        hp = self.read_ram(self.ADDR_HP)
        battle_state = self.read_ram(self.ADDR_BATTLE_STATE)

        # Eğer Vahşi Savaş ise ve Can az ise Kaçmayı Dene
        if battle_state == 1 and hp < 10 and self.story_state != "GET_PARCEL":
            if self.step_counter % 20 == 0: self.press('RIGHT')
            elif self.step_counter % 20 == 5: self.press('DOWN')
            elif self.step_counter % 20 == 10: self.press('A')
            else: self.press('B')
        else:
            self.press('A')

    def bfs_pathfind(self, start_x, start_y, target_x, target_y, map_id):
        if start_x == target_x and start_y == target_y:
            return []
            
        walls = self.known_walls.get(map_id, set())
        queue = [((start_x, start_y), [])]
        visited = {(start_x, start_y)}
        
        max_search = 1000 
        while queue and max_search > 0:
            (cx, cy), path = queue.pop(0)
            max_search -= 1
            
            for dx, dy, d_name in [(0, -1, 'UP'), (0, 1, 'DOWN'), (-1, 0, 'LEFT'), (1, 0, 'RIGHT')]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx <= 64 and 0 <= ny <= 64:
                    if (nx, ny) not in walls and (nx, ny) not in visited:
                        if nx == target_x and ny == target_y:
                            return path + [d_name]
                        visited.add((nx, ny))
                        queue.append(((nx, ny), path + [d_name]))
        return []

    def move_towards(self, target_x, target_y, map_id):
        curr_x = self.read_ram(self.ADDR_X_COORD)
        curr_y = self.read_ram(self.ADDR_Y_COORD)

        if curr_x == target_x and curr_y == target_y:
            self.stuck_frames = 0
            return True

        # Duvar Algılama
        if self.last_x == curr_x and self.last_y == curr_y and self.last_direction:
            wall_x, wall_y = curr_x, curr_y
            if self.last_direction == 'UP': wall_y -= 1
            elif self.last_direction == 'DOWN': wall_y += 1
            elif self.last_direction == 'LEFT': wall_x -= 1
            elif self.last_direction == 'RIGHT': wall_x += 1
            
            if map_id not in self.known_walls:
                self.known_walls[map_id] = set()
                
            if (wall_x, wall_y) not in self.known_walls[map_id]:
                print(f"[DUVAR] Yeni Engel: {wall_x},{wall_y} (Harita: {hex(map_id)})")
                self.known_walls[map_id].add((wall_x, wall_y))
            
            self.stuck_frames += 1
        else:
            self.stuck_frames = 0
            self.last_x = curr_x
            self.last_y = curr_y

        if self.stuck_frames > 20:
            print("[STUCK] Takıldık, hafıza temizleniyor ve rastgele adım atılıyor...")
            if map_id in self.known_walls:
                self.known_walls[map_id].clear()
            self.stuck_frames = 0
            self.escape_dir = random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT'])
            self.last_direction = self.escape_dir
            self.press(self.escape_dir, 20)
            return False

        # BFS ile Rotayı Bul
        path = self.bfs_pathfind(curr_x, curr_y, target_x, target_y, map_id)
        if path:
            self.last_direction = path[0]
        else:
            # Hedefe yol bulunamazsa (duvarlarla kaplıysa) düz mantıkla ilerlemeye çalış
            if curr_x < target_x: self.last_direction = 'RIGHT'
            elif curr_x > target_x: self.last_direction = 'LEFT'
            elif curr_y < target_y: self.last_direction = 'DOWN'
            else: self.last_direction = 'UP'

        self.press(self.last_direction, 20)
        return False

    def handle_story_triggers(self, map_id, text):
        if self.story_state == "GET_PARCEL" and map_id == self.MAP_VIRIDIAN_MART:
            if "oak" in text or "parcel" in text:
                print("\n[HİKAYE] OAK'S PARCEL ALINDI! Laboratuvara Dönülüyor...")
                self.story_state = "RETURN_TO_OAK"
                self.current_route_index = 0

        elif self.story_state == "RETURN_TO_OAK" and map_id == self.MAP_OAKS_LAB:
            if "pokedex" in text:
                print("\n[HİKAYE] POKEDEX ALINDI! Pokemon Center'a Gidiliyor...")
                self.story_state = "GO_TO_POKECENTER"
                self.current_route_index = 0

        elif self.story_state == "GO_TO_POKECENTER" and map_id == self.MAP_POKECENTER:
            if "again" in text or "see you" in text:
                print("\n[HİKAYE] POKEMON İYİLEŞTİRİLDİ! PokeBall Almaya Gidiliyor...")
                self.story_state = "BUY_POKEBALL"
                self.current_route_index = 0

        elif self.story_state == "BUY_POKEBALL" and map_id == self.MAP_VIRIDIAN_MART:
            # Pokeball Makrosu
            if "buy" in text or "sold out" in text or self.current_route_index >= 1:
                # Satın Alma işlemini basitçe simüle edelim veya skip edelim (Orijinal bot A spamliyor)
                print("\n[HİKAYE] POKEBALL ALIMI TAMAM! Viridian Forest'a Geçiliyor...")
                self.story_state = "TO_VIRIDIAN_FOREST"
                self.current_route_index = 0
                for _ in range(5): self.press('B', 10) # Menüden Çık

    def play(self):
        print("[Bot] Başlatıldı. Mimari: Checkpoint + Story State + BFS SLAM")
        
        while self.pyboy.tick():
            self.step_counter += 1

            # 1. ZAFER KONTROLÜ
            if (self.read_ram(self.ADDR_BADGES) & 0x01) == 1:
                print("\n[Bot] TEBRİKLER! Brock yenildi ve Boulder Badge alındı!")
                break

            # 2. SAVAŞ KONTROLÜ
            if self.read_ram(self.ADDR_BATTLE_STATE) != 0:
                self.handle_battle()
                continue

            map_id = self.read_ram(self.ADDR_MAP_ID)

            # 3. DİYALOG/TEXTBOX KONTROLÜ
            if self.read_ram(self.ADDR_TEXT_OPEN) != 0:
                text = self.read_screen_text()
                if len(text) > 5 and self.step_counter % 30 == 0:
                    print(f"[Diyalog] {text}")
                
                self.handle_story_triggers(map_id, text)
                
                self.press('A')
                self.press('B')
                continue

            # 4. HARİTA VE ROTA YÖNETİMİ
            if map_id != self.last_map:
                self.current_route_index = 0
                self.last_map = map_id
                print(f"[Bot] Harita Değişti! ID: {hex(map_id)} | Aşama: {self.story_state}")

            # Başlangıç menüleri ve Intro atlama
            if not self.intro_done:
                curr_x = self.read_ram(self.ADDR_X_COORD)
                curr_y = self.read_ram(self.ADDR_Y_COORD)
                if map_id == self.MAP_REDS_HOUSE_2F and curr_x == 3 and curr_y == 6:
                    print("\n[HİKAYE] Intro Atlandı! Odada uyandık.")
                    self.intro_done = True
                else:
                    if self.step_counter % 20 == 0: self.press('A')
                    if self.step_counter % 50 == 0: self.press('START')
                    continue

            # Story State ve Map tabanlı Rota Çekimi
            current_map_routes = self.routes.get(self.story_state, {}).get(map_id, [])
            
            if self.current_route_index < len(current_map_routes):
                target = current_map_routes[self.current_route_index]
                if self.step_counter % 60 == 0:
                    print(f"[{hex(map_id)}] Hedef Nokta: {target} (Aşama: {self.story_state})")
                
                reached = self.move_towards(target[0], target[1], map_id)
                if reached:
                    print(f"-> Checkpoint Ulaşıldı: {target}")
                    if len(target) > 2 and target[2] == 'A':
                        self.press('A', 20)
                    self.current_route_index += 1
            else:
                # Tüm rotalar bittiyse A basarak etkileşime gir (Örn: NPC ile konuş, Kapıdan çık)
                if self.step_counter % 30 == 0:
                    self.press('A')
                # Eğer bina kapısı/çıkışıysa bir miktar aşağı ittir
                if map_id in [self.MAP_REDS_HOUSE_1F, self.MAP_OAKS_LAB, self.MAP_VIRIDIAN_MART, self.MAP_POKECENTER]:
                    if self.step_counter % 15 == 0: self.press('DOWN')

        self.pyboy.stop()

if __name__ == "__main__":
    # "Pokemon_Red.gb" dosyasının script ile aynı klasörde olduğundan emin ol.
    bot = PokemonBrockBot("Pokemon Red Ana Dosya ve Kod/Pokemon - Red Version (USA, Europe) (SGB Enhanced).gb")
    bot.play()
