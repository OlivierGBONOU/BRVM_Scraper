import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter.ttk import Progressbar
import threading
from datetime import datetime, timedelta
import os
import sys
import pandas as pd

# Import du scraper original
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from BRVM_scraper import BRVMScraper

class BRVMScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BRVM Stock Data Scraper")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Configuration du style
        self.setup_styles()
        
        # Variables
        self.scraper = None
        self.is_scraping = False
        
        # Interface
        self.create_widgets()
        
    def setup_styles(self):
        """Configure les styles pour une interface moderne"""
        style = ttk.Style()
        
        # Configuration du thème
        try:
            style.theme_use('clam')
        except:
            pass
            
        # Styles personnalisés
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        
    def create_widgets(self):
        """Crée tous les widgets de l'interface"""
        # Frame principal avec padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration du redimensionnement
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Titre
        title_label = ttk.Label(main_frame, text="🏛️ BRVM Stock Data Scraper", 
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Section Configuration
        config_frame = ttk.LabelFrame(main_frame, text="📋 Configuration", padding="15")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # Dates
        ttk.Label(config_frame, text="📅 Date de début:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.start_date_var = tk.StringVar(value="2023-01-01")
        start_date_entry = ttk.Entry(config_frame, textvariable=self.start_date_var, width=15)
        start_date_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Label(config_frame, text="📅 Date de fin:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        end_date_entry = ttk.Entry(config_frame, textvariable=self.end_date_var, width=15)
        end_date_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Intervalle
        ttk.Label(config_frame, text="⏱️ Intervalle (jours):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.interval_var = tk.StringVar(value="30")
        interval_entry = ttk.Entry(config_frame, textvariable=self.interval_var, width=10)
        interval_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Options avancées
        options_frame = ttk.LabelFrame(main_frame, text="⚙️ Options avancées", padding="15")
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.headless_var = tk.BooleanVar(value=True)
        headless_check = ttk.Checkbutton(options_frame, text="Mode invisible (headless)", 
                                        variable=self.headless_var)
        headless_check.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(options_frame, text="⏳ Timeout (secondes):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.StringVar(value="10")
        timeout_entry = ttk.Entry(options_frame, textvariable=self.timeout_var, width=10)
        timeout_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Boutons de contrôle
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="🚀 Démarrer le scraping", 
                                      command=self.start_scraping, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="⏹️ Arrêter", 
                                     command=self.stop_scraping, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.export_button = ttk.Button(control_frame, text="💾 Exporter CSV", 
                                       command=self.export_data, state='disabled')
        self.export_button.pack(side=tk.LEFT)
        
        # Barre de progression
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = Progressbar(progress_frame, variable=self.progress_var, 
                                       mode='determinate', length=400)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="Prêt à démarrer...")
        self.progress_label.grid(row=1, column=0, pady=5)
        
        # Zone de statut
        status_frame = ttk.LabelFrame(main_frame, text="📊 Statut", padding="10")
        status_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        self.status_labels = {}
        status_items = [
            ("Actions traitées:", "actions_count"),
            ("Enregistrements:", "records_count"),
            ("Fichier de sortie:", "output_file")
        ]
        
        for i, (label, key) in enumerate(status_items):
            ttk.Label(status_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            self.status_labels[key] = ttk.Label(status_frame, text="0", style='Header.TLabel')
            self.status_labels[key].grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Console de logs
        log_frame = ttk.LabelFrame(main_frame, text="📝 Journal d'activité", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, width=80, 
                                                 wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Bouton pour effacer les logs
        clear_log_button = ttk.Button(log_frame, text="🗑️ Effacer les logs", 
                                     command=self.clear_logs)
        clear_log_button.grid(row=1, column=0, pady=5)
        
    def log_message(self, message):
        """Ajoute un message au journal"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_progress(self, value, message=""):
        """Met à jour la barre de progression"""
        self.progress_var.set(value * 100)
        if message:
            self.progress_label.config(text=message)
        self.root.update_idletasks()
        
    def update_status(self, **kwargs):
        """Met à jour les informations de statut"""
        for key, value in kwargs.items():
            if key in self.status_labels:
                self.status_labels[key].config(text=str(value))
        self.root.update_idletasks()
        
    def validate_inputs(self):
        """Valide les entrées utilisateur"""
        try:
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d")
            
            if start_date >= end_date:
                raise ValueError("La date de début doit être antérieure à la date de fin")
                
            interval = int(self.interval_var.get())
            if interval <= 0:
                raise ValueError("L'intervalle doit être un nombre positif")
                
            timeout = int(self.timeout_var.get())
            if timeout <= 0:
                raise ValueError("Le timeout doit être un nombre positif")
                
            return True, start_date, end_date, interval, timeout
            
        except ValueError as e:
            messagebox.showerror("Erreur de validation", str(e))
            return False, None, None, None, None
            
    def start_scraping(self):
        """Démarre le processus de scraping"""
        # Validation des entrées
        valid, start_date, end_date, interval, timeout = self.validate_inputs()
        if not valid:
            return
            
        # Configuration de l'interface
        self.is_scraping = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.export_button.config(state='disabled')
        
        # Réinitialisation
        self.progress_var.set(0)
        self.progress_label.config(text="Initialisation...")
        self.update_status(actions_count=0, records_count=0, output_file="En cours...")
        
        # Configuration du scraper
        config = {
            'headless': self.headless_var.get(),
            'timeout': timeout
        }
        
        self.scraper = BRVMScraper(config)
        self.scraper.set_callbacks(
            progress_callback=self.update_progress,
            log_callback=self.log_message
        )
        
        # Démarrage dans un thread séparé
        self.scraping_thread = threading.Thread(
            target=self.run_scraping,
            args=(start_date, end_date, interval),
            daemon=True
        )
        self.scraping_thread.start()
        
    def run_scraping(self, start_date, end_date, interval):
        """Exécute le scraping dans un thread séparé"""
        try:
            result = self.scraper.scrape_data(start_date, end_date, interval)
            
            # Mise à jour de l'interface dans le thread principal
            self.root.after(0, self.scraping_completed, result)
            
        except Exception as e:
            error_result = {
                'success': False,
                'message': f'Erreur inattendue: {str(e)}'
            }
            self.root.after(0, self.scraping_completed, error_result)
            
    def scraping_completed(self, result):
        """Called when scraping is completed"""
        self.is_scraping = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        if result['success']:
            self.log_message("✅ Scraping terminé avec succès!")
            self.update_status(
                actions_count=result.get('actions', 0),
                records_count=result.get('records', 0),
                output_file=result.get('file', 'N/A')
            )
            self.export_button.config(state='normal')
            self.progress_label.config(text="Terminé avec succès!")
            messagebox.showinfo("Succès", 
                              f"Scraping terminé!\n"
                              f"Enregistrements: {result.get('records', 0)}\n"
                              f"Actions: {result.get('actions', 0)}")
        else:
            self.log_message(f"❌ Erreur: {result.get('message', 'Erreur inconnue')}")
            self.progress_label.config(text="Erreur lors du scraping")
            messagebox.showerror("Erreur", result.get('message', 'Erreur inconnue'))
            
        self.progress_var.set(100 if result['success'] else 0)
        
    def stop_scraping(self):
        """Arrête le processus de scraping"""
        if self.is_scraping and self.scraper:
            self.log_message("🛑 Arrêt demandé par l'utilisateur...")
            # Note: L'arrêt forcé nécessiterait une implémentation plus complexe
            # du scraper avec des points de vérification
            self.is_scraping = False
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.progress_label.config(text="Arrêté par l'utilisateur")
            
    def export_data(self):
        """Exporte les données vers un fichier CSV"""
        try:
            # Vérifier si le fichier existe
            if not os.path.exists('stock_data.csv'):
                messagebox.showerror("Erreur", "Aucun fichier de données trouvé. Effectuez d'abord un scraping.")
                return
                
            # Demander où sauvegarder
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
                title="Sauvegarder les données"
            )
            
            if filename:
                # Copier le fichier
                import shutil
                shutil.copy2('stock_data.csv', filename)
                self.log_message(f"📁 Données exportées vers: {filename}")
                messagebox.showinfo("Succès", f"Données exportées vers:\n{filename}")
                
        except Exception as e:
            self.log_message(f"❌ Erreur lors de l'export: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de l'export:\n{e}")
            
    def clear_logs(self):
        """Efface le contenu du journal"""
        self.log_text.delete(1.0, tk.END)

def main():
    """Fonction principale"""
    root = tk.Tk()
    app = BRVMScraperGUI(root)
    
    # Configuration pour fermer proprement
    def on_closing():
        if app.is_scraping:
            if messagebox.askokcancel("Quitter", "Un scraping est en cours. Voulez-vous vraiment quitter?"):
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()