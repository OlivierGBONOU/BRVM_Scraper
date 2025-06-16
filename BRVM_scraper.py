import subprocess
import sys
import json
import os
from datetime import datetime, timedelta

# Fonction pour installer les packages
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Installation automatique des packages
required_packages = ["selenium", "beautifulsoup4", "pandas", "webdriver-manager"]

for package in required_packages:
    try:
        __import__(package if package != "beautifulsoup4" else "bs4")
    except ImportError:
        install(package)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

class BRVMScraper:
    def __init__(self, config=None):
        self.config = config or {}
        self.driver = None
        self.progress_callback = None
        self.log_callback = None
        
    def set_callbacks(self, progress_callback=None, log_callback=None):
        self.progress_callback = progress_callback
        self.log_callback = log_callback
    
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        if self.log_callback:
            self.log_callback(log_message)
    
    def update_progress(self, value, message=""):
        if self.progress_callback:
            self.progress_callback(value, message)

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        
        if self.config.get('headless', True):
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        return webdriver.Chrome(options=options)

    def wait_for_element(self, by, value, timeout=None):
        timeout = timeout or self.config.get('timeout', 10)
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def select_dropdown_option(self, value_text):
        select_element = self.wait_for_element(By.ID, "dpShares")
        dropdown = Select(select_element)
        dropdown.select_by_visible_text(value_text)

    def click_historiques(self):
        try:
            hist_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "HISTORIQUES"))
            )
            hist_link.click()
            self.log("Clic sur 'HISTORIQUES' réussi.")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'datefrom'))
            )
            return True
        except Exception as e:
            self.log(f"ERREUR clic HISTORIQUES : {e}")
            return False

    def fill_date_range(self, date_from, date_to):
        # Remplir les dates
        self.driver.execute_script(f"document.getElementById('datefrom').value = '{date_from}';")
        self.driver.execute_script(f"document.getElementById('dateto').value = '{date_to}';")
        
        # Attendre que le message d'alerte disparaisse
        WebDriverWait(self.driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "alertMsg"))
        )

        # Cliquer sur le bouton
        btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "btnChange"))
        )
        btn.click()
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'tblhistos'))
        )

    def has_data(self):
        notif_errs = self.driver.find_elements(By.CLASS_NAME, 'notif_err')
        if notif_errs and notif_errs[0].value_of_css_property('display') == 'block':
            msg = self.driver.find_element(By.ID, 'alertMsg').text
            return not ('Pas de données à ces dates là' in msg)
        return True

    def parse_table(self):
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        table = soup.find('table', id='tblhistos')
        if not table:
            return pd.DataFrame()
        
        headers = [th.text.strip() for th in table.find('thead').find_all('th')]
        rows = []
        for tr in table.find('tbody').find_all('tr'):
            cells = [td.text.strip().replace('\xa0', '').replace(',', '.') for td in tr.find_all('td')]
            if cells:
                rows.append(cells)

        return pd.DataFrame(rows, columns=headers)

    def scrape_data(self, start_date, end_date, interval_days=30):
        """
        Fonction principale de scraping avec gestion des callbacks
        """
        self.driver = self.setup_driver()
        all_data = pd.DataFrame()
        
        try:
            self.log("🔍 Connexion au site BRVM...")
            self.driver.get("https://www.sikafinance.com/premium/articles")
            
            wait = WebDriverWait(self.driver, 10)
            select_element = wait.until(EC.presence_of_element_located((By.ID, "dpShares")))
            dropdown = Select(select_element)
            options_text = [opt.text for opt in dropdown.options if opt.get_attribute("value")]
            
            self.log(f"📋 {len(options_text)} actions trouvées")
            
            total_combinations = 0
            current_combination = 0
            
            # Calculer le nombre total de combinaisons
            for option_text in options_text:
                current_start = start_date
                while current_start < end_date:
                    current_end = min(current_start + timedelta(days=interval_days), end_date)
                    total_combinations += 1
                    current_start = current_end + timedelta(days=1)

            for option_index, option_text in enumerate(options_text):
                try:
                    self.log(f"\n📊 Traitement de l'action : {option_text} ({option_index + 1}/{len(options_text)})")
                    self.select_dropdown_option(option_text)

                    if not self.click_historiques():
                        continue

                    current_start = start_date
                    while current_start < end_date:
                        current_end = min(current_start + timedelta(days=interval_days), end_date)
                        date_from_str = current_start.strftime('%Y-%m-%d')
                        date_to_str = current_end.strftime('%Y-%m-%d')
                        
                        current_combination += 1
                        progress_percent = current_combination / total_combinations
                        
                        self.log(f"📅 Scraping du {date_from_str} au {date_to_str}")
                        self.update_progress(
                            progress_percent, 
                            f"Action: {option_text} | Période: {date_from_str} - {date_to_str}"
                        )

                        try:
                            self.fill_date_range(date_from_str, date_to_str)

                            if not self.has_data():
                                self.log(f"⚠ Pas de données entre {date_from_str} et {date_to_str}")
                                current_start = current_end + timedelta(days=1)
                                continue

                            monthly_data = self.parse_table()
                            if not monthly_data.empty:
                                monthly_data['ACTION'] = option_text
                                all_data = pd.concat([all_data, monthly_data], ignore_index=True)
                                
                                # Sauvegarde temporaire
                                all_data.to_csv('stock_data_temp.csv', index=False, encoding='utf-8-sig')
                                self.log(f"✅ {len(monthly_data)} enregistrements ajoutés")
                            else:
                                self.log("⚠ Table vide détectée.")

                        except Exception as e:
                            self.log(f"❌ ERREUR scraping du {date_from_str} au {date_to_str} : {e}")
                            current_start = current_end + timedelta(days=1)
                            continue 

                        current_start = current_end + timedelta(days=1)

                    # Retourner à la page principale pour la prochaine action
                    self.driver.get("https://www.sikafinance.com/premium/articles")
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "dpShares"))
                    )

                except Exception as e:
                    self.log(f"❌ ERREUR option '{option_text}' : {e}")
                    continue

        finally:
            if self.driver:
                self.driver.quit()

            # Post-traitement des données
            try:
                if not all_data.empty:
                    self.log("🔄 Post-traitement des données...")
                    
                    # Suppression des doublons
                    initial_count = len(all_data)
                    all_data.drop_duplicates(inplace=True)
                    self.log(f"🗑 {initial_count - len(all_data)} doublons supprimés")
                    
                    # Tri par date
                    all_data['Date'] = pd.to_datetime(all_data['Date'], format='%d/%m/%Y', errors='coerce')
                    all_data = all_data.sort_values(by='Date')
                    all_data['Date'] = all_data['Date'].dt.strftime('%d/%m/%Y')
                    all_data.reset_index(drop=True, inplace=True)

                    # Sauvegarde finale
                    all_data.to_csv('stock_data.csv', index=False, encoding='utf-8-sig')
                    self.log(f"✅ Fichier final 'stock_data.csv' généré avec {len(all_data)} enregistrements.")
                    
                    return {
                        'success': True,
                        'records': len(all_data),
                        'actions': all_data['ACTION'].nunique() if 'ACTION' in all_data.columns else 0,
                        'file': 'stock_data.csv'
                    }
                else:
                    self.log("⚠ Aucune donnée collectée.")
                    return {'success': False, 'message': 'Aucune donnée collectée'}
                    
            except Exception as e:
                self.log(f"⚠ Erreur post-traitement : {e}")
                all_data.to_csv('stock_data_fallback.csv', index=False, encoding='utf-8-sig')
                self.log("⚠ Données sauvegardées dans 'stock_data_fallback.csv' sans tri.")
                return {
                    'success': False, 
                    'message': f'Erreur post-traitement: {e}',
                    'fallback_file': 'stock_data_fallback.csv'
                }

"""def main():
    """    """Fonction principale pour utilisation en standalone""""""
    # Configuration par défaut
    config = {
        'headless': True,
        'timeout': 10,
        'retry_attempts': 3
    }
    
    scraper = BRVMScraper(config)
    
    # Dates par défaut
    start_date = datetime(2023, 1, 1)
    end_date = datetime.today()
    
    result = scraper.scrape_data(start_date, end_date, interval_days=30)
    
    if result['success']:
        print(f"✅ Scraping terminé avec succès: {result['records']} enregistrements")
    else:
        print(f"❌ Erreur lors du scraping: {result.get('message', 'Erreur inconnue')}")

if __name__ == "__main__":
    main()
"""