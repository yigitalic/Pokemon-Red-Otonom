#    .\.venv\Scripts\python.exe pokemon_ajanı.py

import time
import random
import cv2
import numpy as np
import os
import json
from enum import Enum
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
    0xF6: '0', 0xF7: '1', 0xF8: '2', 0xF9: '3', 0xFA: '4', 0xFB: '5', 0xFC: '6', 0xFD: '7', 0xFE: '8', 0xFF: '9',
    0xE1: 'PK', 0xE2: 'MN', 0xF0: '$', 0xEE: '↓', 0xEF: '♂', 0xF5: '♀', 0xF3: '/', 0xE3: '-'
}

def decode_pokemon_text(byte_array):
    result = ""
    for b in byte_array:
        if b in CHAR_MAP:
            result += CHAR_MAP[b]
        elif b not in [0x00, 0x7F, 0xFF]:
            result += " " 
    return " ".join(result.split())

class GameState(Enum):
    STATE_HARITA = 1
    STATE_SAVAS = 2

class PokemonAgentPyBoy:
    def __init__(self, rom_path="Pokemon - Red Version (USA, Europe) (SGB Enhanced).gb"):
        self.rom_path = rom_path

        kayit_dosyalari = [self.rom_path + ext for ext in [".ram", ".rtc", ".state"]]
        for kayit in kayit_dosyalari:
            if os.path.exists(kayit):
                os.remove(kayit)
                print(f"[Temizlik] Eski kayıt (Save) silindi -> {kayit}")
        
        self.pyboy = PyBoy(self.rom_path, window="SDL2")
        self.pyboy.set_emulation_speed(1)
        try:
            import ctypes
            import time
            time.sleep(0.5) 
            hwnd = ctypes.windll.user32.FindWindowW("SDL_app", None)
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9) 
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except:
            pass
            
        self.dataset_dir = "dataset"
        os.makedirs(f"{self.dataset_dir}/images", exist_ok=True)
        self.data_log = []

        self.waypoints = {
            
            0x26: {"x": 7, "y": 1, "desc": "Odadaki Merdivenden Alt Kata İnmek", "read_sign": False}, 
            0x25: {"x": 3, "y": 8, "desc": "Evden Dışarı Çık (Kapı)", "read_sign": False},           
            0x00: {"x": 10, "y": 0, "desc": "Prof. Oak Çimlerinden Ulaş (Route 1'e Git)", "read_sign": False}, 
            0x01: {"x": 29, "y": 19, "desc": "Viridian City Poke Mart'a Gir", "read_sign": False},   
        }
        
        self.route_1_state = 0 
        self.checkpoint_timer = 0 
        
        self.known_walls = {} 
        
        self.last_x = -1
        self.last_y = -1
        self.last_direction = None
        self.stuck_frames = 0
        self.step_counter = 0

        self.last_map_id = -1
        self.starter_picked = False
        self.starter_x_hedefi = random.choice([6, 7, 8])
        self.story_state = "GET_PARCEL"

    def run(self):
        print("[Zihin] BFS-SLAM Navigasyon ve Tabela Okuma Motoru Aktif!")
        self.skip_intro()
            
        print("\n[Oyun] Oyuna Başlandı! RAM Hafızalı Koordinat Ajanı Aktif...")
        tick_count = 0
        try:
            while self.pyboy.tick():
                tick_count += 1
                if tick_count % 10 == 0:
                    dialog_bytes = [self.pyboy.memory[addr] for addr in range(0x9800, 0x9BFF)]
                    text = decode_pokemon_text(dialog_bytes).lower()
                    
                    if "blacked out" in text or "scurried" in text:
                        print("\n[Acil Durum] TÜM POKEMONLAR BAYILDI! Pokemon Center'a geri dönüldü.")
                        
                    if "nickname" in text:
                        print("[Engel] Nickname ekranı algılandı! 'B' ve 'START' ile atlanıyor...")
                        self.pyboy.button("b")
                        self.pyboy.tick(2)
                        self.pyboy.button("start")
                        self.pyboy.tick(2)
                        continue

                battle_flag = self.pyboy.memory[0xD057]
                if battle_flag == 0:
                    self.explore_smart()
                else:
                    self.battle_routine(battle_flag)
        except KeyboardInterrupt:
            print("Kullanıcı Tarafından Kapatıldı. Loglar Kaydedildi.")
        finally:
            with open(f"{self.dataset_dir}/labels.json", "w") as f:
                json.dump(self.data_log, f, indent=4)
            self.pyboy.stop()

    def skip_intro(self):
        print("[Sistem] Intro Kilitleri Kırılıyor ve İsimler Otomatik Seçiliyor...")
        intro_tick = 0
        while True:
            map_id = self.pyboy.memory[0xD35E]
            mem_x = self.pyboy.memory[0xD362]
            mem_y = self.pyboy.memory[0xD361]

            if map_id == 0x26 and mem_x == 3 and mem_y == 6:
                break
                
            intro_tick += 1
            
            if intro_tick % 10 == 0:
                dialog_bytes = [self.pyboy.memory[addr] for addr in range(0x9800, 0x9BFF)]
                text = decode_pokemon_text(dialog_bytes).lower()
                
                if "new name" in text:
                    print("[Sistem] İsim seçme menüsü algılandı! Varsayılan (RED/BLUE) seçiliyor...")
                    self.pyboy.button("down")
                    self.pyboy.tick(15)
                    self.pyboy.button("a")
                    self.pyboy.tick(15)
                    continue

            if intro_tick < 1000:
                if intro_tick % 10 == 0: self.pyboy.button("a")
                if intro_tick % 30 == 0: self.pyboy.button("start")
            else:
                if intro_tick % 10 == 0: self.pyboy.button("a")
                if intro_tick % 20 == 0: self.pyboy.button("b")
                if intro_tick % 100 == 0: self.pyboy.button("start")
                
            self.pyboy.tick()
        print("[Sistem] Haritaya Başarıyla İndi!")

    def read_screen_text(self):
        dialog_bytes = [self.pyboy.memory[addr] for addr in range(0x9800, 0x9BFF)]
        text = decode_pokemon_text(dialog_bytes)
        if len(text) > 4 and "qrst" not in text:
            print(f"===================================")
            print(f"[Görsel] GÖRÜNTÜ - TABELA OKUNDU: '{text}'")
            print(f"===================================")
            return True
        return False

    def bfs_pathfind(self, start_x, start_y, target_x, target_y, map_id):
        if start_x == target_x and start_y == target_y:
            return []
            
        walls = self.known_walls.get(map_id, set())
        queue = [((start_x, start_y), [])]
        visited = {(start_x, start_y)}
        
        max_search = 2000 
        while queue and max_search > 0:
            (cx, cy), path = queue.pop(0)
            max_search -= 1
            
            for dx, dy, d_name in [(0, -1, 'up'), (0, 1, 'down'), (-1, 0, 'left'), (1, 0, 'right')]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx <= 64 and 0 <= ny <= 64:
                    if (nx, ny) not in walls and (nx, ny) not in visited:
                        if nx == target_x and ny == target_y:
                            return path + [d_name]
                        visited.add((nx, ny))
                        queue.append(((nx, ny), path + [d_name]))
        return []

    def get_visual_target(self, mem_x, mem_y, direction="UP"):
        frame = self.pyboy.screen.ndarray
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        roi = gray[16:128, :]
        
        path_mask = cv2.inRange(roi, 200, 255)
        grass_mask = cv2.inRange(roi, 100, 200)
        
        path_pixels = np.sum(path_mask > 0)
        grass_pixels = np.sum(grass_mask > 0)
        
        def get_centroid(mask):
            M = cv2.moments(mask)
            if M['m00'] > 0:
                return int(M['m10'] / M['m00']) 
            return -1

        target_cx = -1
        if path_pixels > 100:
            target_cx = get_centroid(path_mask)
        elif grass_pixels > 200:
            target_cx = get_centroid(grass_mask)
            
        hedef_x = mem_x
        if direction == "UP":
            hedef_y = max(0, mem_y - 10)
        else:
            hedef_y = min(64, mem_y + 10)

        if target_cx != -1:
            if target_cx < 60:
                hedef_x = mem_x - 3
            elif target_cx > 100:
                hedef_x = mem_x + 3

        if direction == "UP" and mem_y <= 2:
            hedef_x = 11
            hedef_y = 0
        elif direction == "DOWN" and mem_y >= 34:
            hedef_x = 10
            hedef_y = 35
            
        return hedef_x, hedef_y

    def handle_story_get_parcel(self, map_id, mem_x, mem_y, hedef_x, hedef_y):
        if map_id == 0x00: hedef_x, hedef_y = 10, 0
        elif map_id == 0x24: hedef_x, hedef_y = 7, 1
        elif map_id == 0x25: hedef_x, hedef_y = 3, 8
        elif map_id == 0x0C: 
            if getattr(self, 'global_override', 0) > 0:
                hedef_x, hedef_y = 10, 0
            else:
                hedef_x, hedef_y = self.get_visual_target(mem_x, mem_y, "UP")
                if mem_y > 3 and hedef_x < 11: hedef_x = 11
        elif map_id == 0x01:
            if 22 <= mem_x <= 24 and 24 <= mem_y <= 26:
                hedef_x, hedef_y = 25, 26
            elif mem_y >= 27:
                hedef_x, hedef_y = 21, 25
            elif mem_x == 29 and mem_y == 20:
                hedef_x, hedef_y = 29, 19
            else:
                hedef_x, hedef_y = 29, 20
        elif map_id == 0x2A:
            hedef_x, hedef_y = 3, 5
            if self.step_counter % 2 == 0: self.pyboy.button("a")
            
            dialog_bytes = [self.pyboy.memory[addr] for addr in range(0x9800, 0x9BFF)]
            text = decode_pokemon_text(dialog_bytes).lower()
            if mem_y <= 6:
                self.checkpoint_timer += 1
                
            if "oak" in text or "parcel" in text or self.checkpoint_timer > 100:
                print("[Paket] OAK'S PARCEL ALINDI! Dükkandan Ayrılınıyor...")
                self.story_state = "RETURN_TO_OAK"
                self.known_walls.clear()
                self.checkpoint_timer = 0
        
            if self.story_state == "RETURN_TO_OAK":
                hedef_x, hedef_y = 3, 8
                if self.step_counter % 5 == 0: self.pyboy.button("b")
        return hedef_x, hedef_y

    def handle_story_return_to_oak(self, map_id, mem_x, mem_y, hedef_x, hedef_y):
        if map_id == 0x2A: 
            hedef_x, hedef_y = 3, 8
            if self.step_counter % 5 == 0: self.pyboy.button("b")
        elif map_id == 0x24: hedef_x, hedef_y = 7, 1
        elif map_id == 0x25: hedef_x, hedef_y = 3, 8
        elif map_id == 0x01: 
            if mem_y < 25: 
                hedef_x, hedef_y = 21, 25
            elif mem_y >= 35:
                print("[Geçiş] Viridian sınırı! Harita değişimi için 3 adım aşağı zorlanıyor...")
                for _ in range(3):
                    self.pyboy.button_press("down")
                    self.pyboy.tick(30)
                    self.pyboy.button_release("down")
                return None, None
            else:
                hedef_x, hedef_y = 21, 35
            
            if 0x01 in self.known_walls: self.known_walls[0x01].add((29, 19))
        elif map_id == 0x0C: 
            if mem_y >= 35:
                print("[Geçiş] Rota 1 sınırı! Pallet geçişi için 3 adım aşağı zorlanıyor...")
                for _ in range(3):
                    self.pyboy.button_press("down")
                    self.pyboy.tick(30)
                    self.pyboy.button_release("down")
                return None, None
            hedef_x, hedef_y = 10, 35
        elif map_id == 0x00: 
            if mem_y < 8:
                hedef_x, hedef_y = 10, 8
            else:
                hedef_x, hedef_y = 12, 11
        elif map_id == 0x28:
            hedef_x, hedef_y = 5, 3
                
            if mem_x == 5 and mem_y == 3:
                self.pyboy.button("up")
                self.pyboy.tick(5)
                
                if self.checkpoint_timer < 5: 
                    self.pyboy.button("a")
                else:
                    self.pyboy.button("b")
                self.pyboy.tick(5)
                
                dialog_bytes = [self.pyboy.memory[addr] for addr in range(0x9800, 0x9BFF)]
                text = decode_pokemon_text(dialog_bytes).lower()
                if "pokedex" in text or self.checkpoint_timer > 300:
                    print("[Kitap] POKEDEX ALINDI! Pokemon Center'a Gidiliyor!")
                    self.story_state = "GO_TO_POKECENTER"
                    self.checkpoint_timer = 0
                self.checkpoint_timer += 1
        return hedef_x, hedef_y

    def handle_story_go_to_pokecenter(self, map_id, mem_x, mem_y, hedef_x, hedef_y):
        if map_id == 0x28: hedef_x, hedef_y = 5, 11
        elif map_id == 0x24: hedef_x, hedef_y = 7, 1
        elif map_id == 0x25: hedef_x, hedef_y = 3, 8
        elif map_id == 0x00: hedef_x, hedef_y = 10, 0
        elif map_id == 0x0C: 
            if getattr(self, 'global_override', 0) > 0:
                hedef_x, hedef_y = 10, 0
            else:
                hedef_x, hedef_y = self.get_visual_target(mem_x, mem_y, "UP")
                if mem_y > 3 and hedef_x < 11: hedef_x = 11
        elif map_id == 0x01: 
            # Viridian City'de PokeCenter'ın kapısı 23,25'tir. Hedefi direkt kapı yapıyoruz ki BFS düzgünce içeri salsın.
            hedef_x, hedef_y = 23, 25
        elif map_id == 0x2B: # Viridian City Pokecenter
            hedef_x, hedef_y = 3, 3 # Joy'un önü
            
            if mem_x == 3 and mem_y <= 4:
                if self.step_counter % 2 == 0:
                    self.pyboy.button("a")
                
                dialog_bytes = [self.pyboy.memory[addr] for addr in range(0x9800, 0x9BFF)]
                text = decode_pokemon_text(dialog_bytes).lower()
                
                # Joy'un diyaloğunun tamamen bitmesini ve "see you again" demesini bekliyoruz. Erken çıkış yok!
                if "again" in text or "see you" in text:
                    print("[Sağlık] POKEMON İYİLEŞTİRİLDİ! PokeMart'a PokeBall almaya gidiliyor...")
                    self.story_state = "BUY_POKEBALL"
        return hedef_x, hedef_y

    def handle_story_buy_pokeball(self, map_id, mem_x, mem_y, hedef_x, hedef_y):
        if map_id == 0x2B: # PokeCenter içindeysek çıkışa git
            hedef_x, hedef_y = 3, 8
        elif map_id == 0x01: # Viridian City haritası
            if 22 <= mem_x <= 24 and 24 <= mem_y <= 26:
                hedef_x, hedef_y = 25, 26 # PokeCenter'dan çıkınca takılmadan sağa geç
            elif mem_x == 29 and mem_y == 20:
                hedef_x, hedef_y = 29, 19
            else:
                hedef_x, hedef_y = 29, 20
        elif map_id == 0x2A: # PokeMart içi
            hedef_x, hedef_y = 3, 5 # Clerk'in önü
            
            if mem_x == 3 and mem_y == 5:
                print("[PokeMart] Pokeball Satın Alma Makrosu Başlıyor...")
                self.pyboy.button("up")
                self.pyboy.tick(10)
                
                # Konuşmayı başlat
                self.pyboy.button("a")
                self.pyboy.tick(120) 
                
                # BUY seç
                self.pyboy.button("a")
                self.pyboy.tick(60) 
                
                # POKE BALL seç (İlk Sırada)
                self.pyboy.button("a")
                self.pyboy.tick(60) 
                
                # Miktar 5 yap (UP tuşuna 4 kez bas)
                for _ in range(4):
                    self.pyboy.button("up")
                    self.pyboy.tick(15)
                
                # Onayla ve Satın Al
                self.pyboy.button("a")
                self.pyboy.tick(120) 
                
                # Menülerden Çık
                self.pyboy.button("b")
                self.pyboy.tick(30)
                self.pyboy.button("b")
                self.pyboy.tick(30)
                self.pyboy.button("b")
                self.pyboy.tick(30)
                
                print("[PokeMart] 5 Adet Pokeball başarıyla alındı! Viridian Forest'a geçiliyor...")
                self.story_state = "TO_VIRIDIAN_FOREST"
                
        return hedef_x, hedef_y

    def handle_story_to_viridian_forest(self, map_id, mem_x, mem_y, hedef_x, hedef_y):
        if map_id == 0x2B: # Pokecenter'dan çık
            hedef_x, hedef_y = 3, 8
        elif map_id == 0x01: # Viridian City'den yukarı çık
            hedef_x, hedef_y = 18, 0
        elif map_id == 0x0D: # Route 2
            if mem_y > 20: 
                hedef_x, hedef_y = 3, 43 # Gate'e giris
            else: 
                hedef_x, hedef_y = 9, 0 
        elif map_id == 0x2F: # Viridian Forest Gate
            hedef_x, hedef_y = 5, 0 
        elif map_id == 0x33: # Viridian Forest
            hedef_x, hedef_y = 2, 0 
        return hedef_x, hedef_y

    def explore_smart(self):
        mem_x = self.pyboy.memory[0xD362]
        mem_y = self.pyboy.memory[0xD361]
        map_id = self.pyboy.memory[0xD35E]

        hedef_x, hedef_y = -1, -1

        if self.last_map_id != -1 and self.last_map_id != map_id:
            print(f"[KAPI MÜHÜRÜ] Harita Değişti ({hex(self.last_map_id)} -> {hex(map_id)}). Warp Animasyonu Bekleniyor...")

            for _ in range(120):
                self.pyboy.tick()

            mem_x = self.pyboy.memory[0xD362]
            mem_y = self.pyboy.memory[0xD361]

            self.known_walls[map_id] = set() 

            self.known_walls[map_id].add((mem_x, mem_y))
            seal_x, seal_y = mem_x, mem_y
            
            if self.last_direction == "up": seal_y += 1
            elif self.last_direction == "down": seal_y -= 1
            elif self.last_direction == "left": seal_x += 1
            elif self.last_direction == "right": seal_x -= 1
            else: seal_y += 1
            
            self.known_walls[map_id].add((seal_x, seal_y))
            print(f"[KAPI MÜHÜRÜ] Asla Geri Dönme! Kapı Kilitlendi -> X:{mem_x}, Y:{mem_y} ve X:{seal_x}, Y:{seal_y}")
            
        self.last_map_id = map_id
        
        if not hasattr(self, 'global_override'):
            self.global_override = 0
            
        if self.global_override > 0:
            self.global_override -= 1
            
        if self.story_state == "RETURN_TO_OAK":
            if 0x01 not in self.known_walls: self.known_walls[0x01] = set()
            self.known_walls[0x01].add((29, 19))
            
            if 0x00 not in self.known_walls: self.known_walls[0x00] = set()
            self.known_walls[0x00].add((27, 23))
            
        is_target_building = False
        if self.story_state == "GET_PARCEL" and map_id == 0x2A: is_target_building = True
        if self.story_state in ["RETURN_TO_OAK", "GO_TO_POKECENTER", "TO_VIRIDIAN_FOREST", "BUY_POKEBALL"] and map_id == 0x28: is_target_building = True
        if self.story_state == "GO_TO_POKECENTER" and map_id == 0x2B: is_target_building = True
        if self.story_state == "BUY_POKEBALL" and map_id == 0x2A: is_target_building = True
        
        buildings = {0x24: (7, 1), 0x25: (3, 8), 0x26: (7, 1), 0x27: (3, 8), 0x2D: (3, 8)}
        if not is_target_building:
            buildings[0x2a] = (3, 8)
            buildings[0x2b] = (3, 8)
            
        if not is_target_building and map_id in buildings:
            hedef_x, hedef_y = buildings[map_id]
            print(f"[Otonom Çıkış] Yanlış bina ({hex(map_id)}), çıkışa gidiliyor: {hedef_x},{hedef_y}")
        
        if self.story_state != "GET_PARCEL" and map_id == 0x2A:
            hedef_x, hedef_y = 3, 8

        if self.pyboy.memory[0xD163] > 0 and not self.starter_picked:
            print("[Başarı] POKEMON BAŞARIYLA KADROYA KATILDI! Hafıza temizleniyor ve Çıkış hedefleniyor...")
            self.starter_picked = True
            if map_id in self.known_walls:
                self.known_walls[map_id] = set() # Hatalı duvar hafızasını (masayı duvar sanmayı) sıfırla.

        if map_id == 0x28:
            if not self.starter_picked:
                hedef_x, hedef_y = self.starter_x_hedefi, 4 # Poketop masası (Y=3)'ün önünde dur (Y=4).
            else:
                hedef_x, hedef_y = 5, 11 

        if self.starter_picked:
            if self.story_state == "GET_PARCEL":
                hedef_x, hedef_y = self.handle_story_get_parcel(map_id, mem_x, mem_y, hedef_x, hedef_y)
            elif self.story_state == "RETURN_TO_OAK":
                hedef_x, hedef_y = self.handle_story_return_to_oak(map_id, mem_x, mem_y, hedef_x, hedef_y)
                if hedef_x is None: return
            elif self.story_state == "GO_TO_POKECENTER":
                hedef_x, hedef_y = self.handle_story_go_to_pokecenter(map_id, mem_x, mem_y, hedef_x, hedef_y)
            elif self.story_state == "BUY_POKEBALL":
                hedef_x, hedef_y = self.handle_story_buy_pokeball(map_id, mem_x, mem_y, hedef_x, hedef_y)
            elif self.story_state == "TO_VIRIDIAN_FOREST":
                hedef_x, hedef_y = self.handle_story_to_viridian_forest(map_id, mem_x, mem_y, hedef_x, hedef_y)


        elif map_id in self.waypoints:
            target = self.waypoints[map_id]
            hedef_x, hedef_y = target["x"], target["y"]
            if target.get("read_sign", False):
                self.pyboy.button("a")
                self.pyboy.tick()
                if self.read_screen_text():
                    target["read_sign"] = False 

        if self.last_x == mem_x and self.last_y == mem_y and self.last_direction:
            wall_x, wall_y = mem_x, mem_y
            if self.last_direction == "up": wall_y -= 1
            elif self.last_direction == "down": wall_y += 1
            elif self.last_direction == "left": wall_x -= 1
            elif self.last_direction == "right": wall_x += 1
            
            if map_id not in self.known_walls:
                self.known_walls[map_id] = set()
                
            if wall_x == hedef_x and wall_y == hedef_y:
                pass 
            elif (wall_x, wall_y) not in self.known_walls[map_id]:
                print(f"[HARİTA BİLGİSİ] Yeni Engel ({self.last_direction}): Harita {hex(map_id)} -> X:{wall_x}, Y:{wall_y}")
                self.known_walls[map_id].add((wall_x, wall_y))
                
            self.stuck_frames += 1

            if self.stuck_frames > 25:
                print("[SİSTEM] Çok uzun süre takılındı veya sarkaç döngüsü! Hafıza temizleniyor...")
                self.known_walls[map_id] = set() 
                self.stuck_frames = 0
                
        else:
            if not hasattr(self, 'position_history'):
                self.position_history = []
            self.position_history.append((mem_x, mem_y))
            if len(self.position_history) > 6:
                self.position_history.pop(0)

            if len(self.position_history) == 6 and len(set(self.position_history)) <= 2:
                self.stuck_frames += 1
            else:
                self.stuck_frames = 0

        secilen_yon = "down"

        if hedef_x != -1 and hedef_y != -1:
            if mem_x == hedef_x and mem_y == hedef_y:
                if hedef_y >= 7 and map_id in [0x2E, 0x28, 0x25, 0x02, 0x24, 0x26, 0x27, 0x2A, 0x2B, 0x2D]: 
                    secilen_yon = "down"
                else:
                    secilen_yon = "up"
            else:
                path = self.bfs_pathfind(mem_x, mem_y, hedef_x, hedef_y, map_id)
                if path:
                    secilen_yon = path[0] 
                else:
                    global_x, global_y = 10, 0
                    if hasattr(self, 'story_state') and self.story_state == "RETURN_TO_OAK":
                        global_x, global_y = 10, 35
                        
                    path_global = self.bfs_pathfind(mem_x, mem_y, global_x, global_y, map_id)
                    
                    if path_global:
                        secilen_yon = path_global[0]
                        self.global_override = 20
                    else:
                        self.stuck_frames += 5
                        if self.stuck_frames > 25:
                            print("[SİSTEM] Global Plan İflas Etti! Harita bariyerleri sıfırlanıyor...")
                            self.known_walls[map_id] = set() 
                            self.stuck_frames = 0
                            
                        if not hasattr(self, 'escape_dir') or (self.last_x == mem_x and self.last_y == mem_y):
                            kacis = ["down", "left", "right"]
                            if hedef_y <= mem_y: kacis.append("up")
                            self.escape_dir = random.choice(kacis)
                        secilen_yon = self.escape_dir
        else:
            if not hasattr(self, 'escape_dir') or (self.last_x == mem_x and self.last_y == mem_y):
                kacis = ["up", "down", "left", "right"]
                if hasattr(self, 'story_state') and self.story_state == "RETURN_TO_OAK":
                    kacis = ["down", "down", "left", "right", "up"]
                self.escape_dir = random.choice(kacis)
            secilen_yon = self.escape_dir

        if hasattr(self, 'story_state') and self.story_state == "RETURN_TO_OAK":
            if map_id in [0x01, 0x0C] and secilen_yon == "up":
                print(f"[Kısıtlama] Dönüş yolunda 'UP' hareketi engellendi, 'DOWN' zorlanıyor...")
                secilen_yon = "down"
        if self.step_counter % 10 == 0:
            frame = self.pyboy.screen.ndarray 
            img_name = f"step_{self.step_counter}.png"
            cv2.imwrite(f"{self.dataset_dir}/images/{img_name}", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            self.data_log.append({
                "step": self.step_counter, "action": secilen_yon,
                "map": map_id, "x": mem_x, "y": mem_y, "image": img_name
            })
            print(f"[{mem_x},{mem_y}] Harita: {hex(map_id)} | Hedef: {hedef_x},{hedef_y} -> HAREKET: {secilen_yon.upper()}")

        self.last_x = mem_x
        self.last_y = mem_y
        self.last_direction = secilen_yon
        self.step_counter += 1
        
        self.pyboy.button_press(secilen_yon)
        for _ in range(20): 
            self.pyboy.tick()
        self.pyboy.button_release(secilen_yon)

        if map_id == 0x28 and not self.starter_picked and mem_y <= 5:
            self.pyboy.button("a")
            self.pyboy.tick(2)
        else:
            self.pyboy.button("b")
            self.pyboy.tick(2)

    def battle_routine(self, battle_type):
        hp = self.pyboy.memory[0xD16D]
        
        kac = False
        if battle_type == 1 and hp < 10 and self.story_state in ["TO_VIRIDIAN", "RETURN_TO_OAK"]:
            kac = True

        top_at = False
        # Vahşi pokemon savaşıysa ve hikayede Pokedex/Pokeball alındıktan sonraysa top atmayı dene!
        if battle_type == 1 and self.story_state in ["TO_VIRIDIAN_FOREST"] and hp > 0:
            if self.step_counter % 120 == 60: # Belirli aralıklarla top atma denemesi (ITEM menüsünden)
                top_at = True

        if self.step_counter % 30 == 0:
            durum = "[Kaçış] KAÇIYOR! (Can Kritik)" if kac else ("[Top] POKEBALL ATILIYOR!" if top_at else "Dövüşüyor...")
            print(f"[Savaş] SAVAŞ MOTORU DEVREDE! (Can: {hp}) -> {durum}")

        if kac:
            if self.step_counter % 20 == 0: self.pyboy.button("right")
            elif self.step_counter % 20 == 5: self.pyboy.button("down")
            elif self.step_counter % 20 == 10: self.pyboy.button("a")
            else: self.pyboy.button("b") 
        elif top_at:
            # Savaş sırasında Pokeball kullanma dizilimi: ITEM(Aşağı+A) -> İlk Eşya(A) -> Use(A)
            self.pyboy.button("down")
            self.pyboy.tick(10)
            self.pyboy.button("a") # ITEM
            self.pyboy.tick(20)
            self.pyboy.button("a") # Çantadaki ilk eşya (Poke Ball varsayımı)
            self.pyboy.tick(20)
            self.pyboy.button("a") # Kullan
            self.pyboy.tick(20)
        else:
            self.pyboy.button("a")
            
        self.pyboy.tick(5)
        self.step_counter += 1

if __name__ == "__main__":
    agent = PokemonAgentPyBoy()
    agent.run()

#   .\.venv\Scripts\python.exe pokemon_ajanı.py