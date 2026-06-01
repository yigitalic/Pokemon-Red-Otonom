import os
import random
from omegaconf import OmegaConf
from red_gym.rewards.baseline import BaselineRewardEnv

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

def make_env_config(gb_path, state_dir):
    return OmegaConf.create({
        "gb_path": gb_path,
        "video_dir": "videos",
        "headless": False,
        "state_dir": state_dir,
        "init_state": "has_pokedex_nballs",
        "action_freq": 24,
        "max_steps": 2048000,
        "save_video": False,
        "fast_video": True,
        "n_record": 0,
        "perfect_ivs": True,
        "reduce_res": False,
        "log_frequency": 100,
        "two_bit": False,
        "auto_flash": True,
        "required_tolerance": 1.0,
        "disable_wild_encounters": False,
        "disable_ai_actions": False,
        "auto_teach_cut": True,
        "auto_teach_surf": True,
        "auto_teach_strength": True,
        "auto_use_cut": True,
        "auto_use_strength": True,
        "auto_use_surf": True,
        "auto_solve_strength_puzzles": True,
        "auto_remove_all_nonuseful_items": True,
        "auto_pokeflute": True,
        "auto_next_elevator_floor": True,
        "skip_safari_zone": True,
        "infinite_safari_steps": True,
        "insert_saffron_guard_drinks": True,
        "infinite_money": False,
        "infinite_health": False,
        "use_global_map": False,
        "save_state": False,
        "animate_scripts": False,
        "exploration_inc": 0.1,
        "exploration_max": 1.0,
        "max_steps_scaling": 1.0,
        "map_id_scalefactor": 1.0,
    })

def make_reward_config():
    return OmegaConf.create({
        "event": 4.0,
        "bill_saved": 5.0,
        "seen_pokemon": 0.0001,
        "caught_pokemon": 0.0001,
        "obtained_move_ids": 0.0001,
        "hm_count": 1.0,
        "level": 1.0,
        "badges": 5.0,
        "exploration": 0.012,
        "cut_coords": 1.0,
        "cut_tiles": 1.0,
        "start_menu": 0.01,
        "pokemon_menu": 0.1,
        "stats_menu": 0.1,
        "bag_menu": 0.1,
        "rival3": 4.0,
    })

class Ajan3Bot:
    def __init__(self, env: BaselineRewardEnv):
        self.env = env
        
        # Kritik RAM Adresleri
        self.ADDR_BATTLE_STATE = 0xD057
        self.ADDR_MAP_ID = 0xD35E
        self.ADDR_X_COORD = 0xD362
        self.ADDR_Y_COORD = 0xD361
        self.ADDR_BADGES = 0xD356
        self.ADDR_TEXT_OPEN = 0xCFD8
        self.ADDR_HP = 0xD16D
        self.ADDR_PARTY_COUNT = 0xD163

        # Harita ID Tanimlamalari
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

        # Action Indices
        self.ACT_DOWN = 0
        self.ACT_LEFT = 1
        self.ACT_RIGHT = 2
        self.ACT_UP = 3
        self.ACT_A = 4
        self.ACT_B = 5
        self.ACT_START = 6

        # Hikaye Asamasi (Story State)
        # NOT: RedGymEnv baslangicta has_pokedex_nballs state'i kullandigi icin
        # oyun direkt Viridian City / Rota civarlarindan veya PokeCenter'dan baslayabilir.
        # Bu yuzden story_state'i dinamik olarak ele almak ya da baslangicta resetlemek gerekebilir.
        self.story_state = "TO_VIRIDIAN_FOREST"

        # Story State tabanli yeni Rota Sistemi
        self.routes = {
            "GET_PARCEL": {
                self.MAP_REDS_HOUSE_2F: [(7, 1)],
                self.MAP_REDS_HOUSE_1F: [(3, 8)],
                self.MAP_PALLET_TOWN: [(10, 0)],
                self.MAP_OAKS_LAB: [(6, 4), (5, 11)],
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
                self.MAP_ROUTE_2: [(9, 0), (3, 43)], # Yukari cikip kapiya gir
                self.MAP_GATE_S: [(5, 0)],
                self.MAP_VIRIDIAN_FOREST: [(17, 43), (25, 43), (25, 20), (16, 20), (16, 12), (2, 12), (2, 0)],
                self.MAP_GATE_N: [(5, 0)],
                self.MAP_PEWTER_CITY: [(14, 17), (14, 7), (16, 7)],
                self.MAP_PEWTER_GYM: [(4, 3)]
            }
        }
        
        self.current_route_index = 0
        self.last_map = -1
        
        # Takilma Sistemi (Stuck Detection)
        self.last_x = -1
        self.last_y = -1
        self.stuck_frames = 0
        self.escape_dir = self.ACT_UP
        self.step_counter = 0
        self.intro_done = False

    def read_ram(self, address):
        return self.env.read_m(address)

    def read_screen_text(self):
        dialog_bytes = [self.read_ram(addr) for addr in range(0x9800, 0x9BFF)]
        return decode_pokemon_text(dialog_bytes).lower()

    def decide_battle_action(self):
        hp = self.read_ram(self.ADDR_HP)
        battle_state = self.read_ram(self.ADDR_BATTLE_STATE)

        if battle_state == 1 and hp < 10 and self.story_state != "GET_PARCEL":
            if self.step_counter % 4 == 0: return self.ACT_RIGHT
            elif self.step_counter % 4 == 1: return self.ACT_DOWN
            elif self.step_counter % 4 == 2: return self.ACT_A
            else: return self.ACT_B
        else:
            return self.ACT_A

    def decide_move_action(self, target_x, target_y):
        curr_x = self.read_ram(self.ADDR_X_COORD)
        curr_y = self.read_ram(self.ADDR_Y_COORD)

        # Takilma Kontrolu
        if self.last_x == curr_x and self.last_y == curr_y:
            self.stuck_frames += 1
        else:
            self.stuck_frames = 0
            self.last_x = curr_x
            self.last_y = curr_y

        if self.stuck_frames > 3:
            if self.stuck_frames == 4:
                self.escape_dir = random.choice([self.ACT_UP, self.ACT_DOWN, self.ACT_LEFT, self.ACT_RIGHT])
                print(f"[STUCK] {curr_x},{curr_y} konumunda sikisildi. Rastgele kaciliyor!")
            
            if self.stuck_frames > 8:
                self.stuck_frames = 0 # Yeniden dene
            return self.escape_dir, False

        if curr_x < target_x:
            return self.ACT_RIGHT, False
        elif curr_x > target_x:
            return self.ACT_LEFT, False
        elif curr_y < target_y:
            return self.ACT_DOWN, False
        elif curr_y > target_y:
            return self.ACT_UP, False
        else:
            self.stuck_frames = 0
            return None, True

    def handle_story_triggers(self, map_id, text):
        if self.story_state == "GET_PARCEL" and map_id == self.MAP_VIRIDIAN_MART:
            if "oak" in text or "parcel" in text:
                print("\n[HIKAYE] OAK'S PARCEL ALINDI! Laboratuvara Donuluyor...")
                self.story_state = "RETURN_TO_OAK"
                self.current_route_index = 0

        elif self.story_state == "RETURN_TO_OAK" and map_id == self.MAP_OAKS_LAB:
            if "pokedex" in text:
                print("\n[HIKAYE] POKEDEX ALINDI! Pokemon Center'a Gidiliyor...")
                self.story_state = "GO_TO_POKECENTER"
                self.current_route_index = 0

        elif self.story_state == "GO_TO_POKECENTER" and map_id == self.MAP_POKECENTER:
            if "again" in text or "see you" in text:
                print("\n[HIKAYE] POKEMON IYILESTIRILDI! PokeBall Almaya Gidiliyor...")
                self.story_state = "BUY_POKEBALL"
                self.current_route_index = 0

        elif self.story_state == "BUY_POKEBALL" and map_id == self.MAP_VIRIDIAN_MART:
            if "buy" in text or "sold out" in text or self.current_route_index >= 1:
                print("\n[HIKAYE] POKEBALL ALIMI TAMAM! Viridian Forest'a Geciliyor...")
                self.story_state = "TO_VIRIDIAN_FOREST"
                self.current_route_index = 0

    def get_action(self):
        self.step_counter += 1

        # 1. ZAFER KONTROLU
        if (self.read_ram(self.ADDR_BADGES) & 0x01) == 1:
            print("\n[Bot] TEBRIKLER! Brock yenildi ve Boulder Badge alindi!")
            return None # Oyun bitti

        # 2. SAVAS KONTROLU
        if self.read_ram(self.ADDR_BATTLE_STATE) != 0:
            return self.decide_battle_action()

        map_id = self.read_ram(self.ADDR_MAP_ID)

        # 3. DIYALOG/TEXTBOX KONTROLU
        if self.read_ram(self.ADDR_TEXT_OPEN) != 0:
            text = self.read_screen_text()
            if len(text) > 5 and self.step_counter % 5 == 0:
                print(f"[Diyalog] {text}")
            
            self.handle_story_triggers(map_id, text)
            
            if self.story_state == "BUY_POKEBALL" and map_id == self.MAP_VIRIDIAN_MART and self.step_counter % 2 == 0:
                return self.ACT_B # Menuden cikis
            return self.ACT_A if self.step_counter % 2 == 0 else self.ACT_B

        # 4. HARITA VE ROTA YONETIMI
        if map_id != self.last_map:
            self.current_route_index = 0
            self.last_map = map_id
            print(f"[Bot] Harita Degisti! ID: {hex(map_id)} | Asama: {self.story_state}")

        if not self.intro_done:
            curr_x = self.read_ram(self.ADDR_X_COORD)
            curr_y = self.read_ram(self.ADDR_Y_COORD)
            if map_id == self.MAP_REDS_HOUSE_2F and curr_x == 3 and curr_y == 6:
                print("\n[HIKAYE] Intro Atlandi! Odada uyandik.")
                self.intro_done = True
            else:
                # Orijinal save dosyasindan basladigi icin (has_pokedex_nballs) zaten intro gecilmis olur.
                # Bu kisim safety amaciyla hizli A ve Start basar.
                self.intro_done = True 

        current_map_routes = self.routes.get(self.story_state, {}).get(map_id, [])
        
        if self.current_route_index < len(current_map_routes):
            target = current_map_routes[self.current_route_index]
            if self.step_counter % 10 == 0:
                print(f"[{hex(map_id)}] Hedef Nokta: {target} (Asama: {self.story_state})")
            
            action, reached = self.decide_move_action(target[0], target[1])
            if reached:
                print(f"-> Checkpoint Ulasildi: {target}")
                self.current_route_index += 1
                return self.ACT_A
            return action
        else:
            if self.step_counter % 5 == 0:
                return self.ACT_A
            if map_id in [self.MAP_REDS_HOUSE_1F, self.MAP_OAKS_LAB, self.MAP_VIRIDIAN_MART, self.MAP_POKECENTER]:
                return self.ACT_DOWN
                
        return self.ACT_A

    def play(self):
        print("[Ajan 3] Baslatildi. Mimari: Checkpoint + Story State (Gymnasium Env)")
        
        obs, info = self.env.reset()
        
        try:
            while True:
                action = self.get_action()
                if action is None:
                    break # Victory
                obs, info = self.env.step(action)
                
        except KeyboardInterrupt:
            print("\nKullanici tarafindan durduruldu.")
        finally:
            self.env.pyboy.stop()

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rom_path = os.path.join(script_dir, "..", "Pokemon Red Ana Dosya ve Kod", "Pokemon - Red Version (USA, Europe) (SGB Enhanced).gb")
    state_dir = os.path.join(script_dir, "pyboy_states")
    
    if not os.path.exists(rom_path):
        print(f"ROM bulunamadi: {rom_path}")
        exit(1)
        
    env_config = make_env_config(rom_path, state_dir)
    reward_config = make_reward_config()
    env = BaselineRewardEnv(env_config, reward_config)
    bot = Ajan3Bot(env)
    bot.play()
