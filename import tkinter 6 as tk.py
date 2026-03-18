import tkinter as tk
from tkinter import messagebox
import random

# --- CONFIGURAÇÕES TÉCNICAS ---
FPS = 60
MS_PER_FRAME = 1000 // FPS
TAM_CELULA = 80
LINHAS, COLUNAS = 7, 10

# --- BANCO DE DADOS ---
PLANTAS_DATA = {
    "Sunflower":  {"cor": "#FFD700", "custo": 25,  "hp": 75,  "sigla": "SF"},
    "Shotpeea":   {"cor": "#32CD32", "custo": 100, "hp": 175, "sigla": "SP"},
    "Wallnut":    {"cor": "#CD853F", "custo": 50,  "hp": 500, "sigla": "WN"},
    "Snowpea":    {"cor": "#00BFFF", "custo": 175, "hp": 100, "sigla": "SN"},
    "CheryBomb":  {"cor": "#FF0000", "custo": 150, "hp": 10,  "sigla": "CB"}
}

ZUMBIS_BASE = {
    "Normal":   {"hp": 250, "cor": "#3d2b1f"},
    "Balde":    {"hp": 350, "protect": 300, "cor": "#808080"},
    "Cone":     {"hp": 250, "protect": 150, "cor": "#ff6600"},
    "Corredor": {"hp": 450, "protect": 400, "cor": "#ff0000"}
}

class EnginePVZ:
    def __init__(self, root):
        self.root = root
        self.root.title("PVZ Atari - Gelo e Explosões")
        
        self.soles = 25
        self.planta_selecionada = None
        self.grade_plantas = {} 
        self.tiros = [] 
        self.zumbis = []
        
        self.primeira_planta_colocada = False
        self.zumbis_ativos = False
        self.mortes = 0
        self.mortes_objetivo = 60  # <-- META DE KILLS DEFINIDA AQUI
        self.bandeiras_ativas = 0
        self.multiplicador_hp = 1.0
        self.pool_zumbis = ["Normal"]
        
        self.mostrar_hp_plantas = False
        self.mostrar_hp_zumbis = False

        self.setup_ui()
        self.game_loop()

    def setup_ui(self):
        self.frame_topo = tk.Frame(self.root, bg="#222", pady=10)
        self.frame_topo.pack(fill="x")
        
        self.label_sol = tk.Label(self.frame_topo, text=f"☀ Sóis: {self.soles}", 
                                  font=("Arial", 12, "bold"), fg="yellow", bg="#222")
        self.label_sol.pack(side="left", padx=10)

        # --- NOVO CONTADOR DE KILLS NA UI ---
        self.label_kills = tk.Label(self.frame_topo, text=f"💀 Kills: {self.mortes}/{self.mortes_objetivo}", 
                                    font=("Arial", 10, "bold"), fg="white", bg="#222")
        self.label_kills.pack(side="left", padx=10)

        self.btn_hp_p = tk.Button(self.frame_topo, text="HP P", command=self.toggle_hp_plantas, bg="#444", fg="white")
        self.btn_hp_p.pack(side="left", padx=2)
        self.btn_hp_z = tk.Button(self.frame_topo, text="HP Z", command=self.toggle_hp_zumbis, bg="#444", fg="white")
        self.btn_hp_z.pack(side="left", padx=2)

        self.canvas_waves = tk.Canvas(self.frame_topo, width=120, height=35, bg="#222", highlightthickness=0)
        self.canvas_waves.pack(side="left", padx=10)
        self.bandeiras_visuais = []
        for i in range(3):
            b = self.canvas_waves.create_rectangle(i*35+5, 5, i*35+30, 30, fill="#555", outline="white")
            self.bandeiras_visuais.append(b)

        for nome in PLANTAS_DATA:
            btn = tk.Button(self.frame_topo, text=f"{nome}\n${PLANTAS_DATA[nome]['custo']}",
                            command=lambda n=nome: self.selecionar_planta(n), bg="#333", fg="white", font=("Arial", 7))
            btn.pack(side="left", padx=2)

        self.canvas = tk.Canvas(self.root, width=COLUNAS * TAM_CELULA, height=LINHAS * TAM_CELULA, bg="#4a852a")
        self.canvas.pack(pady=20, padx=20)
        self.desenhar_gramado()
        self.canvas.bind("<Button-1>", self.clique_gramado)

    def toggle_hp_plantas(self): self.mostrar_hp_plantas = not self.mostrar_hp_plantas
    def toggle_hp_zumbis(self): self.mostrar_hp_zumbis = not self.mostrar_hp_zumbis

    def desenhar_gramado(self):
        for r in range(LINHAS):
            for c in range(COLUNAS):
                cor = "#63b13a" if (r + c) % 2 == 0 else "#5ba333"
                self.canvas.create_rectangle(c*TAM_CELULA, r*TAM_CELULA, (c+1)*TAM_CELULA, (r+1)*TAM_CELULA, fill=cor, outline="#4a852a")

    def selecionar_planta(self, nome): self.planta_selecionada = nome

    def clique_gramado(self, event):
        col, row = event.x // TAM_CELULA, event.y // TAM_CELULA
        if not self.planta_selecionada or (row, col) in self.grade_plantas: return
        
        info = PLANTAS_DATA[self.planta_selecionada].copy()
        if self.soles >= info["custo"]:
            self.soles -= info["custo"]
            self.label_sol.config(text=f"☀ Sóis: {self.soles}")
            self.grade_plantas[(row, col)] = info
            self.plantar_visual(row, col, info)
            
            if not self.primeira_planta_colocada:
                self.primeira_planta_colocada = True
                self.root.after(12000, self.iniciar_spawn)

            if self.planta_selecionada == "Sunflower":
                self.root.after(6000, lambda: self.loop_girassol(row, col))
            elif self.planta_selecionada in ["Shotpeea", "Snowpea"]:
                self.loop_atirar(row, col)
            elif self.planta_selecionada == "CheryBomb":
                self.root.after(800, lambda: self.explodir_cherry(row, col))
            self.planta_selecionada = None

    def iniciar_spawn(self):
        self.zumbis_ativos = True
        self.spawn_zumbi_loop()

    def plantar_visual(self, row, col, info):
        tag = f"planta_{row}_{col}"
        x1, y1 = col*TAM_CELULA+20, row*TAM_CELULA+20
        x2, y2 = (col+1)*TAM_CELULA-20, (row+1)*TAM_CELULA-20
        self.canvas.create_oval(x1, y1, x2, y2, fill=info["cor"], outline="white", width=2, tags=(tag, "corpo"))
        self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=info["sigla"], font=("Arial", 8, "bold"), tags=tag)
        self.canvas.create_text((x1+x2)/2, y1-8, text="", fill="white", font=("Arial", 8, "bold"), tags=(tag, "hp_label"))

    def loop_girassol(self, row, col):
        if (row, col) in self.grade_plantas and self.grade_plantas[(row, col)]["sigla"] == "SF":
            self.soles += 25
            self.label_sol.config(text=f"☀ Sóis: {self.soles}")
            self.root.after(10000, lambda: self.loop_girassol(row, col))

    def loop_atirar(self, row, col):
        if (row, col) in self.grade_plantas:
            tipo = self.grade_plantas[(row, col)]["sigla"]
            if tipo in ["SP", "SN"]:
                cor = "#32CD32" if tipo == "SP" else "#00BFFF"
                x, y = (col+1)*TAM_CELULA-10, (row*TAM_CELULA)+40
                t_id = self.canvas.create_oval(x-4, y-4, x+4, y+4, fill=cor, outline="white", tags="tiro")
                self.tiros.append({"id": t_id, "row": row, "dano": 25, "gelo": (tipo == "SN")})
                self.root.after(2000, lambda: self.loop_atirar(row, col))

    def spawn_zumbi_loop(self):
        if not self.zumbis_ativos: return
        tipo = random.choice(self.pool_zumbis)
        dados = ZUMBIS_BASE[tipo].copy()
        row = random.randint(0, LINHAS-1)
        
        vel_base = TAM_CELULA / (FPS * 4.5) 
        x_spawn = COLUNAS * TAM_CELULA
        y_spawn = (row * TAM_CELULA) + 15
        tag_z = f"z_{random.random()}"
        
        z_id = self.canvas.create_rectangle(x_spawn, y_spawn, x_spawn+50, y_spawn+50, 
                                           fill=dados["cor"], outline="black", tags=("zumbi", tag_z))
        
        self.zumbis.append({
            "id": z_id, "tag": tag_z, "row": row, 
            "hp": dados["hp"] * self.multiplicador_hp, 
            "protect": dados.get("protect", 0) * self.multiplicador_hp, 
            "vel": vel_base, "vel_original": vel_base,
            "dps": 15, "congelado": False
        })
        
        intervalo = max(8000, 12000 - (self.bandeiras_ativas * 1500))
        self.root.after(random.randint(intervalo, intervalo+2000), self.spawn_zumbi_loop)

    def explodir_cherry(self, row, col):
        for z in self.zumbis[:]:
            z_pos = self.canvas.coords(z["id"])
            col_z = z_pos[0] // TAM_CELULA
            if abs(z["row"] - row) <= 1 and abs(col_z - col) <= 1:
                if z["protect"] > 0: z["protect"] -= 300
                else: z["hp"] -= 300
                if z["hp"] <= 0:
                    self.canvas.delete(z["tag"])
                    if z in self.zumbis: self.zumbis.remove(z)
                    self.atualizar_waves()
        
        self.canvas.delete(f"planta_{row}_{col}")
        if (row, col) in self.grade_plantas: del self.grade_plantas[(row, col)]

    def game_loop(self):
        for (r, c), p in self.grade_plantas.items():
            txt = f"HP: {int(p['hp'])}" if self.mostrar_hp_plantas else ""
            self.canvas.itemconfig(f"planta_{r}_{c} && hp_label", text=txt)

        for t in self.tiros[:]:
            self.canvas.move(t["id"], 7, 0)
            t_pos = self.canvas.coords(t["id"])
            if t_pos[0] > COLUNAS * TAM_CELULA:
                self.canvas.delete(t["id"]); self.tiros.remove(t); continue
            
            for z in self.zumbis:
                z_pos = self.canvas.coords(z["id"])
                if t["row"] == z["row"] and t_pos[2] >= z_pos[0] and t_pos[0] <= z_pos[2]:
                    if z["protect"] > 0: z["protect"] -= t["dano"]
                    else: z["hp"] -= t["dano"]
                    
                    if t["gelo"]:
                        z["vel"] = z["vel_original"] * 0.5
                        z["congelado"] = True
                        self.canvas.itemconfig(z["id"], outline="#00BFFF", width=2)
                    
                    self.canvas.delete(t["id"])
                    if t in self.tiros: self.tiros.remove(t)
                    
                    if z["hp"] <= 0:
                        self.canvas.delete(z["tag"])
                        if z in self.zumbis: self.zumbis.remove(z)
                        self.atualizar_waves()
                    break

        for z in self.zumbis[:]:
            z_pos = self.canvas.coords(z["id"])
            self.canvas.delete(f"hp_txt_{z['tag']}")
            if self.mostrar_hp_zumbis:
                self.canvas.create_text(z_pos[0]+25, z_pos[1]-10, text=f"HP:{int(z['hp']+z['protect'])}", 
                                        fill="yellow", font=("Arial", 8, "bold"), tags=f"hp_txt_{z['tag']}")

            col_frontal = int(z_pos[0] // TAM_CELULA)
            if (z["row"], col_frontal) in self.grade_plantas:
                planta = self.grade_plantas[(z["row"], col_frontal)]
                planta["hp"] -= z["dps"] / FPS
                if planta["hp"] <= 0:
                    self.canvas.delete(f"planta_{z['row']}_{col_frontal}")
                    del self.grade_plantas[(z["row"], col_frontal)]
            else:
                self.canvas.move(z["tag"], -z["vel"], 0)
            
            if z_pos[0] < 0:
                messagebox.showinfo("Fim", "Zumbis venceram!"); self.root.destroy(); return

        self.root.after(MS_PER_FRAME, self.game_loop)

    def atualizar_waves(self):
        self.mortes += 1
        # Atualiza o contador visual de kills
        self.label_kills.config(text=f"💀 Kills: {self.mortes}/{self.mortes_objetivo}")
        
        # --- CONDIÇÃO DE VITÓRIA ---
        if self.mortes >= self.mortes_objetivo:
            messagebox.showinfo("VITÓRIA!", f"Você eliminou {self.mortes_objetivo} zumbis e defendeu seu jardim!")
            self.root.destroy()
            return

        # Lógica original das bandeiras (a cada 10 mortes)
        if self.mortes % 10 == 0 and self.bandeiras_ativas < 3:
            self.canvas_waves.itemconfig(self.bandeiras_visuais[self.bandeiras_ativas], fill="red")
            self.bandeiras_ativas += 1
            self.multiplicador_hp += 0.5
            if self.bandeiras_ativas == 1: self.pool_zumbis.append("Balde")
            elif self.bandeiras_ativas == 2: self.pool_zumbis.append("Cone")
            elif self.bandeiras_ativas == 3: self.pool_zumbis.append("Corredor")

if __name__ == "__main__":
    root = tk.Tk(); app = EnginePVZ(root); root.mainloop()
