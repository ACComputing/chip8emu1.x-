import tkinter as tk
from tkinter import filedialog, messagebox
import pygame
import random
import struct

# -------------------------------
# CHIP-8 Emulator Core
# -------------------------------
class Chip8:
    def __init__(self, draw_callback):
        self.memory = [0] * 4096
        self.reg = [0] * 16
        self.index = 0
        self.pc = 0x200
        self.stack = []
        self.delay_timer = 0
        self.sound_timer = 0
        self.screen = [[0] * 64 for _ in range(32)]
        self.keys = [0] * 16
        self.opcode = 0
        self.waiting_key = False
        self.waiting_register = None
        self.draw_callback = draw_callback

        # Load CHIP-8 font
        font = [
            0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
            0x20, 0x60, 0x20, 0x20, 0x70,  # 1
            0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
            0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
            0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
            0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
            0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
            0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
            0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
            0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
            0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
            0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
            0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
            0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
            0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
            0xF0, 0x80, 0xF0, 0x80, 0x80   # F
        ]
        for i, byte in enumerate(font):
            self.memory[i] = byte

    def load_rom(self, path):
        with open(path, "rb") as f:
            data = f.read()
        for i, byte in enumerate(data):
            self.memory[0x200 + i] = byte
        self.pc = 0x200

    def emulate_cycle(self):
        if self.waiting_key:
            return
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1
            if self.sound_timer == 0:
                play_beep()

        self.opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc += 2

        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        nnn = self.opcode & 0x0FFF
        kk = self.opcode & 0x00FF
        n = self.opcode & 0x000F

        if self.opcode == 0x00E0:
            self.screen = [[0] * 64 for _ in range(32)]
        elif self.opcode == 0x00EE:
            self.pc = self.stack.pop()
        elif (self.opcode & 0xF000) == 0x1000:
            self.pc = nnn
        elif (self.opcode & 0xF000) == 0x2000:
            self.stack.append(self.pc)
            self.pc = nnn
        elif (self.opcode & 0xF000) == 0x3000:
            if self.reg[x] == kk:
                self.pc += 2
        elif (self.opcode & 0xF000) == 0x4000:
            if self.reg[x] != kk:
                self.pc += 2
        elif (self.opcode & 0xF00F) == 0x5000:
            if self.reg[x] == self.reg[y]:
                self.pc += 2
        elif (self.opcode & 0xF000) == 0x6000:
            self.reg[x] = kk
        elif (self.opcode & 0xF000) == 0x7000:
            self.reg[x] = (self.reg[x] + kk) & 0xFF
        elif (self.opcode & 0xF00F) == 0x8000:
            self.reg[x] = self.reg[y]
        elif (self.opcode & 0xF00F) == 0x8001:
            self.reg[x] |= self.reg[y]
        elif (self.opcode & 0xF00F) == 0x8002:
            self.reg[x] &= self.reg[y]
        elif (self.opcode & 0xF00F) == 0x8003:
            self.reg[x] ^= self.reg[y]
        elif (self.opcode & 0xF00F) == 0x8004:
            res = self.reg[x] + self.reg[y]
            self.reg[0xF] = 1 if res > 255 else 0
            self.reg[x] = res & 0xFF
        elif (self.opcode & 0xF00F) == 0x8005:
            self.reg[0xF] = 1 if self.reg[x] > self.reg[y] else 0
            self.reg[x] = (self.reg[x] - self.reg[y]) & 0xFF
        elif (self.opcode & 0xF00F) == 0x8006:
            self.reg[0xF] = self.reg[x] & 0x1
            self.reg[x] >>= 1
        elif (self.opcode & 0xF00F) == 0x8007:
            self.reg[0xF] = 1 if self.reg[y] > self.reg[x] else 0
            self.reg[x] = (self.reg[y] - self.reg[x]) & 0xFF
        elif (self.opcode & 0xF00F) == 0x800E:
            self.reg[0xF] = (self.reg[x] >> 7) & 1
            self.reg[x] = (self.reg[x] << 1) & 0xFF
        elif (self.opcode & 0xF00F) == 0x9000:
            if self.reg[x] != self.reg[y]:
                self.pc += 2
        elif (self.opcode & 0xF000) == 0xA000:
            self.index = nnn
        elif (self.opcode & 0xF000) == 0xB000:
            self.pc = nnn + self.reg[0]
        elif (self.opcode & 0xF000) == 0xC000:
            self.reg[x] = random.randint(0, 255) & kk
        elif (self.opcode & 0xF000) == 0xD000:
            height = n
            self.reg[0xF] = 0
            for row in range(height):
                byte = self.memory[self.index + row]
                for col in range(8):
                    if (byte >> (7 - col)) & 1:
                        px = (self.reg[x] + col) % 64
                        py = (self.reg[y] + row) % 32
                        if self.screen[py][px] == 1:
                            self.reg[0xF] = 1
                        self.screen[py][px] ^= 1
            if self.draw_callback:
                self.draw_callback()
        elif (self.opcode & 0xF0FF) == 0xE09E:
            if self.keys[self.reg[x]]:
                self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xE0A1:
            if not self.keys[self.reg[x]]:
                self.pc += 2
        elif (self.opcode & 0xF0FF) == 0xF007:
            self.reg[x] = self.delay_timer
        elif (self.opcode & 0xF0FF) == 0xF00A:
            self.waiting_key = True
            self.waiting_register = x
        elif (self.opcode & 0xF0FF) == 0xF015:
            self.delay_timer = self.reg[x]
        elif (self.opcode & 0xF0FF) == 0xF018:
            self.sound_timer = self.reg[x]
        elif (self.opcode & 0xF0FF) == 0xF01E:
            self.index += self.reg[x]
        elif (self.opcode & 0xF0FF) == 0xF029:
            self.index = self.reg[x] * 5
        elif (self.opcode & 0xF0FF) == 0xF033:
            val = self.reg[x]
            self.memory[self.index] = val // 100
            self.memory[self.index + 1] = (val // 10) % 10
            self.memory[self.index + 2] = val % 10
        elif (self.opcode & 0xF0FF) == 0xF055:
            for i in range(x + 1):
                self.memory[self.index + i] = self.reg[i]
        elif (self.opcode & 0xF0FF) == 0xF065:
            for i in range(x + 1):
                self.reg[i] = self.memory[self.index + i]

    def key_press(self, key, pressed):
        self.keys[key] = pressed
        if self.waiting_key and pressed:
            self.reg[self.waiting_register] = key
            self.waiting_key = False
            self.waiting_register = None


# -------------------------------
# Sound
# -------------------------------
pygame.mixer.init()
beep_sound = None

def play_beep():
    global beep_sound
    if beep_sound is None:
        sample_rate = 22050
        duration = 0.1
        frequency = 800
        samples = int(sample_rate * duration)
        waves = [int(32767 * 0.5) if int((t * frequency * 2 / sample_rate)) % 2 else -int(32767 * 0.5) for t in range(samples)]
        sound_array = struct.pack('<' + 'h' * len(waves), *waves)
        beep_sound = pygame.mixer.Sound(buffer=sound_array)
    beep_sound.play()


# -------------------------------
# Tkinter GUI — BLACK buttons, BLUE text
# -------------------------------
class Chip8GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek's EMU CHIP-8 0.1")
        self.root.configure(bg="black")

        self.chip8 = Chip8(draw_callback=self.draw_screen)
        self.running = False

        # Button style: BLACK background, BLUE text
        button_style = {
            "bg": "black",
            "fg": "#0088FF",
            "activebackground": "#222222",
            "activeforeground": "#00AAFF",
            "font": ("Consolas", 10, "bold"),
            "relief": tk.RAISED,
            "bd": 2,
            "highlightbackground": "#0088FF",
            "highlightcolor": "#0088FF",
            "highlightthickness": 1
        }

        # Top button bar
        top_frame = tk.Frame(root, bg="black")
        top_frame.pack(pady=5)

        self.load_btn = tk.Button(top_frame, text="⬇️ LOAD ROM (.ch8)", command=self.load_rom, **button_style)
        self.load_btn.pack(side=tk.LEFT, padx=5)

        self.run_btn = tk.Button(top_frame, text="▶ RUN", command=self.run_emu, **button_style)
        self.run_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(top_frame, text="⏸ STOP", command=self.stop_emu, **button_style)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.reset_btn = tk.Button(top_frame, text="🔄 RESET", command=self.reset_emu, **button_style)
        self.reset_btn.pack(side=tk.LEFT, padx=5)

        # Canvas for display (64x32 scaled to 640x320)
        self.canvas = tk.Canvas(root, width=640, height=320, bg="black", highlightthickness=0)
        self.canvas.pack(pady=10)

        # Status label with blue text
        self.status_label = tk.Label(
            root, 
            text="Ready. Load a .ch8 ROM", 
            bg="black", 
            fg="#0088FF", 
            font=("Consolas", 9),
            anchor="w"
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

        # Keyboard mapping
        key_map = {
            "1": 0x1, "2": 0x2, "3": 0x3, "4": 0xC,
            "q": 0x4, "w": 0x5, "e": 0x6, "r": 0xD,
            "a": 0x7, "s": 0x8, "d": 0x9, "f": 0xE,
            "z": 0xA, "x": 0x0, "c": 0xB, "v": 0xF,
        }
        for key, chipkey in key_map.items():
            self.root.bind(key, lambda e, k=chipkey: self.key_press(k, True))
            self.root.bind(f"<KeyRelease-{key}>", lambda e, k=chipkey: self.key_press(k, False))

        self.draw_screen()

    def draw_screen(self):
        self.canvas.delete("all")
        for y in range(32):
            for x in range(64):
                if self.chip8.screen[y][x]:
                    self.canvas.create_rectangle(x*10, y*10, x*10+9, y*10+9, fill="#00AAFF", outline="")
        self.root.update_idletasks()

    def key_press(self, key, pressed):
        self.chip8.key_press(key, pressed)

    def load_rom(self):
        path = filedialog.askopenfilename(filetypes=[("CHIP-8 ROMs", "*.ch8"), ("All files", "*.*")])
        if path:
            self.stop_emu()
            self.chip8 = Chip8(draw_callback=self.draw_screen)
            self.chip8.load_rom(path)
            self.draw_screen()
            rom_name = path.split('/')[-1].split('\\')[-1]
            self.status_label.config(text=f"Loaded: {rom_name} | Press RUN to start")
            messagebox.showinfo("Loaded", f"Loaded ROM: {rom_name}\n\nPress RUN to begin emulation.")

    def emulation_loop(self):
        if self.running:
            for _ in range(8):
                self.chip8.emulate_cycle()
            self.draw_screen()
            self.root.after(2, self.emulation_loop)

    def run_emu(self):
        if not self.running:
            self.running = True
            self.status_label.config(text="Emulation running...")
            self.emulation_loop()

    def stop_emu(self):
        self.running = False
        self.status_label.config(text="Stopped. Press RUN to continue.")

    def reset_emu(self):
        self.stop_emu()
        self.chip8 = Chip8(draw_callback=self.draw_screen)
        self.draw_screen()
        self.status_label.config(text="Reset. Load a ROM and press RUN.")


if __name__ == "__main__":
    root = tk.Tk()
    app = Chip8GUI(root)
    root.mainloop()