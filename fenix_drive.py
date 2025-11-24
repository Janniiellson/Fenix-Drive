import tkinter as tk
from tkinter import ttk, messagebox
import subprocess # Módulo essencial para rodar comandos do sistema
import os # Necessário para rodar o comando wmic

class FenixDriveApp:
    def __init__(self, root):
        self.root = root
        root.title("Fênix Drive - Utilitário de Disco")
        root.geometry("600x450")
        
        # Variável para armazenar a lista de discos
        self.disk_list = []

        # --- Frames (Para organização) ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill='both', expand=True)

        # --- 1. Lista de Discos ---
        ttk.Label(main_frame, text="Discos Disponíveis:", font=("Arial", 10, "bold")).pack(pady=5, anchor='w')
        
        self.listbox = tk.Listbox(main_frame, height=10, relief="sunken")
        self.listbox.pack(fill='x', padx=5, pady=5)

        # --- 2. Botões de Ação ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)

        self.update_btn = ttk.Button(button_frame, text="Atualizar Discos", command=self.update_disk_list)
        self.update_btn.pack(side='left', padx=5)

        self.format_btn = ttk.Button(button_frame, text="Formatar Selecionado (CUIDADO!)", command=self.confirm_and_format, style="Danger.TButton")
        self.format_btn.pack(side='left', padx=10)
        
        # --- 3. Log de Status ---
        ttk.Label(main_frame, text="Log de Status:", font=("Arial", 10, "bold")).pack(pady=5, anchor='w')
        self.log_text = tk.Text(main_frame, height=8, state='disabled', wrap='word')
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Adicionar estilo de perigo (Opcional, pode variar dependendo do tema)
        s = ttk.Style()
        s.configure("Danger.TButton", foreground="red")
        
        # Chamada inicial para preencher a lista
        self.update_disk_list()

    def log(self, message):
        """Função utilitária para adicionar mensagens ao log de texto."""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END) # Scroll para o final
        self.log_text.config(state='disabled')
       
    def update_disk_list(self):
        self.log("Buscando discos no sistema via WMIC...")
        self.listbox.delete(0, tk.END)
        self.disk_list = [] # Limpa a lista de dados internos

        # Comando WMIC para listar discos (Caption, DeviceID, Size)
        # /c executa o comando e /Q desativa a saida do ECHO (simplifica o parsing)
        command = 'wmic diskdrive get Caption, DeviceID, Size /format:list'
        
        try:
            # Roda o comando e captura a saída
            result = subprocess.run(
                ['cmd.exe', '/c', command],
                capture_output=True,
                text=True,
                check=True, # Levanta erro se o comando falhar
                encoding='cp850' # Codificacao tipica do console Windows
            )
            output = result.stdout
            
            # --- Lógica de Análise (Parsing) ---
            disk_info = {}
            for line in output.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'Caption' or key == 'DeviceID' or key == 'Size':
                        disk_info[key] = value
                    
                    if key == 'Size' and disk_info:
                        # Quando encontra o Tamanho, assume que é o fim de um bloco de disco
                        
                        # Conversão para GB legível
                        size_bytes = int(disk_info.get('Size', 0))
                        size_gb = round(size_bytes / (1024**3), 2)
                        
                        # ID do Dispositivo (Ex: \\.\PHYSICALDRIVE1)
                        device_id = disk_info.get('DeviceID', 'N/A')
                        
                        # String para a ListBox
                        display_text = f"{disk_info.get('Caption')} ({size_gb} GB) - {device_id}"
                        
                        self.listbox.insert(tk.END, display_text)
                        
                        # Armazena os dados brutos internamente para uso posterior (diskpart)
                        self.disk_list.append({'caption': disk_info['Caption'], 'device_id': device_id})

                        disk_info = {} # Reset para o próximo disco

        except subprocess.CalledProcessError as e:
            self.log(f"ERRO (WMIC): Falha ao executar o comando. Certifique-se de estar rodando como Administrador.")
            self.log(f"Detalhes: {e.stderr}")
        except Exception as e:
            self.log(f"ERRO Desconhecido: {e}")

        self.log(f"Atualização concluída. {len(self.disk_list)} discos encontrados.")
        
        self.log("Atualização concluída.")

    def format_disk(self, disk_id):            
        """Executa o DISKPART para limpar e formatar o disco especificado.
        Requer privilégios de Administrador."""
        
        self.log(f"Preparando script DISKPART para o disco: {disk_id}")
        
        # Extrai o número do disco físico (Ex: \\.\PHYSICALDRIVE1 -> 1)
        disk_number = disk_id.replace('\\\\.\\PHYSICALDRIVE', '')
        
        # 1. Cria o script temporário do diskpart
        diskpart_script_content = f"""
            select disk {disk_number}
            clean
            create partition primary
            format fs=ntfs quick
            active
            assign
            exit
            """
        # Salva o script em um arquivo temporário
        script_path = "temp_diskpart_script.txt"
        with open(script_path, "w") as f:
            f.write(diskpart_script_content)

        # 2. Executa o DISKPART no modo silencioso (/s)
        command = f"diskpart /s {script_path}"
        self.log(f"Executando: {command}...")

        try:
            result = subprocess.run(
                ['cmd.exe', '/c', command],
                capture_output=True,
                text=True,
                check=True,
                encoding='cp850'
            )
            self.log("SUCESSO: Limpeza e Formatação concluídas (Verifique o log para detalhes).")
            self.log("--- Saída do Diskpart ---")
            self.log(result.stdout)
            self.log("-------------------------")
            
        except subprocess.CalledProcessError as e:
            self.log(f"ERRO CRÍTICO (Diskpart): Falha ao formatar o disco.")
            self.log(f"Detalhes: {e.stderr}")
        finally:
            # 3. Limpa o arquivo de script
            os.remove(script_path)
            self.update_disk_list() # Atualiza a lista após a operação

    def confirm_and_format(self):
        selected_index = self.listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Atenção", "Selecione um disco para formatar.")
            return

        index = selected_index[0]
        disk_data = self.disk_list[index]
        
        # ALERTA DE SEGURANÇA FINAL
        reply = messagebox.askyesno(
            "⚠️ ALERTA: DESTRUIÇÃO DE DADOS", 
            f"Tem certeza que deseja limpar e formatar:\n\n{self.listbox.get(index)}\n\nEsta ação APAGARÁ TODOS os dados. Deseja continuar?", 
            icon='warning'
        )

        if reply:
            self.log(f"\nConfirmação recebida. Iniciando operação de formatação.")
            self.format_disk(disk_data['device_id'])
        pass

# --- Ponto de Partida do Aplicativo ---
if __name__ == "__main__":
    # É fundamental que este aplicativo seja executado como Administrador para usar 'diskpart'.
    # Você terá que clicar com o botão direito no arquivo .py e selecionar 'Executar como Administrador'.
    
    root = tk.Tk()
    app = FenixDriveApp(root)
    root.mainloop()