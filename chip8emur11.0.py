import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pygame
import random
import struct
import os

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
        self.last_opcode = 0
        self.rom_name = ""
        self.rom_size = 0

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
        self.rom_name = os.path.basename(path)
        self.rom_size = len(data)

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
        self.last_opcode = self.opcode
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
        
        return self.opcode

    def step(self):
        """Execute a single instruction (for debugging)"""
        if not self.waiting_key:
            return self.emulate_cycle()
        return 0

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
# Tkinter GUI with Debug Panel
# -------------------------------
class Chip8GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek's EMU CHIP-8 0.1 - Debug Edition")
        self.root.configure(bg="black")
        self.root.geometry("1100x700")

        self.chip8 = Chip8(draw_callback=self.draw_screen)
        self.running = False
        self.step_mode = False

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

        # Main layout: left side (display + controls), right side (debug panel)
        main_paned = tk.PanedWindow(root, bg="black", orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---------- LEFT PANEL ----------
        left_frame = tk.Frame(main_paned, bg="black")
        main_paned.add(left_frame, width=700)

        # Top button bar
        top_frame = tk.Frame(left_frame, bg="black")
        top_frame.pack(pady=5)

        self.load_btn = tk.Button(top_frame, text="⬇️ LOAD ROM (.ch8)", command=self.load_rom, **button_style)
        self.load_btn.pack(side=tk.LEFT, padx=5)

        self.run_btn = tk.Button(top_frame, text="▶ RUN", command=self.run_emu, **button_style)
        self.run_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(top_frame, text="⏸ STOP", command=self.stop_emu, **button_style)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.reset_btn = tk.Button(top_frame, text="🔄 RESET", command=self.reset_emu, **button_style)
        self.reset_btn.pack(side=tk.LEFT, padx=5)

        self.step_btn = tk.Button(top_frame, text="⏯ STEP", command=self.step_emu, **button_style)
        self.step_btn.pack(side=tk.LEFT, padx=5)

        # Canvas for display (64x32 scaled to 640x320)
        self.canvas = tk.Canvas(left_frame, width=640, height=320, bg="black", highlightthickness=1, highlightbackground="#0088FF")
        self.canvas.pack(pady=10)

        # Status label
        self.status_label = tk.Label(
            left_frame, 
            text="Ready. Load a .ch8 ROM", 
            bg="black", 
            fg="#0088FF", 
            font=("Consolas", 9),
            anchor="w"
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

        # Keyboard mapping hint
        key_hint = tk.Label(
            left_frame,
            text="Keys: 1-4 | Q-R | A-F | Z-V",
            bg="black",
            fg="#0055AA",
            font=("Consolas", 8)
        )
        key_hint.pack(pady=5)

        # ---------- RIGHT PANEL (DEBUG) ----------
        right_frame = tk.Frame(main_paned, bg="black", width=350)
        main_paned.add(right_frame, width=350)

        # Debug title
        debug_title = tk.Label(
            right_frame,
            text="=== DEBUGGER PANEL ===",
            bg="black",
            fg="#00AAFF",
            font=("Consolas", 11, "bold")
        )
        debug_title.pack(pady=5)

        # Registers frame
        reg_frame = tk.LabelFrame(right_frame, text="Registers (V0-VF)", bg="black", fg="#0088FF", font=("Consolas", 9))
        reg_frame.pack(fill=tk.X, padx=5, pady=5)

        self.reg_labels = []
        for i in range(16):
            row = i // 8
            col = i % 8
            if col == 0:
                subframe = tk.Frame(reg_frame, bg="black")
                subframe.pack(side=tk.LEFT, padx=5, pady=2)
            label = tk.Label(
                subframe, 
                text=f"V{i:X}: 00", 
                bg="black", 
                fg="#00AAFF" if i == 0xF else "#0088FF",
                font=("Consolas", 9),
                width=8,
                anchor="w"
            )
            label.pack()
            self.reg_labels.append(label)

        # Special registers frame
        special_frame = tk.LabelFrame(right_frame, text="System State", bg="black", fg="#0088FF", font=("Consolas", 9))
        special_frame.pack(fill=tk.X, padx=5, pady=5)

        self.pc_label = tk.Label(special_frame, text="PC: 0x200", bg="black", fg="#00AAFF", font=("Consolas", 9), anchor="w")
        self.pc_label.pack(padx=5, pady=2)

        self.index_label = tk.Label(special_frame, text="I: 0x000", bg="black", fg="#00AAFF", font=("Consolas", 9), anchor="w")
        self.index_label.pack(padx=5, pady=2)

        self.opcode_label = tk.Label(special_frame, text="Last OP: 0x0000", bg="black", fg="#FFAA00", font=("Consolas", 9), anchor="w")
        self.opcode_label.pack(padx=5, pady=2)

        self.delay_label = tk.Label(special_frame, text="Delay: 0", bg="black", fg="#0088FF", font=("Consolas", 9), anchor="w")
        self.delay_label.pack(padx=5, pady=2)

        self.sound_label = tk.Label(special_frame, text="Sound: 0", bg="black", fg="#0088FF", font=("Consolas", 9), anchor="w")
        self.sound_label.pack(padx=5, pady=2)

        self.stack_label = tk.Label(special_frame, text="Stack: []", bg="black", fg="#0088FF", font=("Consolas", 9), anchor="w")
        self.stack_label.pack(padx=5, pady=2)

        # ROM Info frame
        rom_frame = tk.LabelFrame(right_frame, text="ROM Information", bg="black", fg="#0088FF", font=("Consolas", 9))
        rom_frame.pack(fill=tk.X, padx=5, pady=5)

        self.rom_name_label = tk.Label(rom_frame, text="Name: -", bg="black", fg="#00AAFF", font=("Consolas", 9), anchor="w")
        self.rom_name_label.pack(padx=5, pady=2)

        self.rom_size_label = tk.Label(rom_frame, text="Size: 0 bytes", bg="black", fg="#00AAFF", font=("Consolas", 9), anchor="w")
        self.rom_size_label.pack(padx=5, pady=2)

        self.rom_addr_label = tk.Label(rom_frame, text="Load Addr: 0x200", bg="black", fg="#00AAFF", font=("Consolas", 9), anchor="w")
        self.rom_addr_label.pack(padx=5, pady=2)

        # Keyboard mapping for CHIP-8
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
        self.update_debug_panel()

    def draw_screen(self):
        self.canvas.delete("all")
        for y in range(32):
            for x in range(64):
                if self.chip8.screen[y][x]:
                    self.canvas.create_rectangle(x*10, y*10, x*10+9, y*10+9, fill="#00AAFF", outline="")
        self.root.update_idletasks()

    def update_debug_panel(self):
        """Update all debug information"""
        # Update registers V0-VF
        for i in range(16):
            self.reg_labels[i].config(text=f"V{i:X}: {self.chip8.reg[i]:02X}")
        
        # Update special registers
        self.pc_label.config(text=f"PC: 0x{self.chip8.pc:04X}")
        self.index_label.config(text=f"I: 0x{self.chip8.index:04X}")
        self.opcode_label.config(text=f"Last OP: 0x{self.chip8.last_opcode:04X}")
        self.delay_label.config(text=f"Delay: {self.chip8.delay_timer}")
        self.sound_label.config(text=f"Sound: {self.chip8.sound_timer}")
        
        # Update stack display (show last 8 entries)
        stack_display = self.chip8.stack[-8:] if len(self.chip8.stack) > 8 else self.chip8.stack
        self.stack_label.config(text=f"Stack: {[hex(s) for s in stack_display]}")
        
        # Update ROM info
        if self.chip8.rom_name:
            self.rom_name_label.config(text=f"Name: {self.chip8.rom_name[:30]}")
            self.rom_size_label.config(text=f"Size: {self.chip8.rom_size} bytes")
        else:
            self.rom_name_label.config(text="Name: -")
            self.rom_size_label.config(text="Size: 0 bytes")
        
        # Schedule next update
        if self.running or self.step_mode:
            self.root.after(50, self.update_debug_panel)

    def key_press(self, key, pressed):
        self.chip8.key_press(key, pressed)

    def load_rom(self):
        path = filedialog.askopenfilename(filetypes=[("CHIP-8 ROMs", "*.ch8"), ("All files", "*.*")])
        if path:
            was_running = self.running
            self.stop_emu()
            self.chip8 = Chip8(draw_callback=self.draw_screen)
            self.chip8.load_rom(path)
            self.draw_screen()
            self.update_debug_panel()
            rom_name = path.split('/')[-1].split('\\')[-1]
            self.status_label.config(text=f"Loaded: {rom_name} | Press RUN to start")
            messagebox.showinfo("Loaded", f"Loaded ROM: {rom_name}\nSize: {self.chip8.rom_size} bytes\nLoad Address: 0x200")

    def emulation_loop(self):
        if self.running:
            # Execute 8 instructions per frame for smooth performance
            for _ in range(8):
                self.chip8.emulate_cycle()
            self.draw_screen()
            self.update_debug_panel()
            # 16ms = ~60 FPS (much smoother!)
            self.root.after(16, self.emulation_loop)

    def run_emu(self):
        if not self.running:
            self.running = True
            self.step_mode = False
            self.status_label.config(text="Emulation running... (60 FPS)")
            self.emulation_loop()

    def stop_emu(self):
        self.running = False
        self.step_mode = False
        self.status_label.config(text="Stopped. Press RUN to continue.")

    def step_emu(self):
        """Execute a single instruction"""
        self.stop_emu()
        self.step_mode = True
        self.chip8.step()
        self.draw_screen()
        self.update_debug_panel()
        self.status_label.config(text="Single step executed. Press STEP again or RUN.")
        self.step_mode = False

    def reset_emu(self):
        was_running = self.running
        self.stop_emu()
        rom_path = None
        if self.chip8.rom_name:
            # We need to reload the ROM - but we don't have the path stored
            self.status_label.config(text="Reset: Load ROM again to restore")
            self.chip8 = Chip8(draw_callback=self.draw_screen)
        else:
            self.chip8 = Chip8(draw_callback=self.draw_screen)
        self.draw_screen()
        self.update_debug_panel()
        self.status_label.config(text="Reset. Load a ROM and press RUN.")


if __name__ == "__main__":
    root = tk.Tk()
    app = Chip8GUI(root)
    root.mainloop()