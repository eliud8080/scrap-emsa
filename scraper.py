import pandas as pd
from datetime import datetime
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
# CONFIG SELENIUM (compatible con GitHub Actions Ubuntu)
def get_driver():
    chrome_options = Options()
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service("/usr/lib/chromium-browser/chromedriver")
    return webdriver.Chrome(service=service,options=chrome_options)
    
# FUNCIONES COMUNES
def escribir_fecha(input_element, fecha_string):
    input_element.click()
    input_element.send_keys(Keys.CONTROL, "a")
    input_element.send_keys(Keys.BACKSPACE)
    input_element.send_keys(fecha_string)
    time.sleep(0.3)
    
def cargar_iframe(driver):
    # Espera a que aparezca al menos 1 iframe
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )

    # Cambia al iframe que realmente contiene la app
    WebDriverWait(driver, 30).until(
        EC.frame_to_be_available_and_switch_to_it(
            (By.XPATH, "//iframe[contains(@src,'emmsa')]")
        )
    )
    
# SCRAPING PRECIOS DIARIOS
def scraper_precios(driver, fecha_hoy):

    print("🔎 Scraping PRECIOS...")

    url = "https://www.emmsa.com.pe/index.php/precios-diarios/"
    driver.get(url)

    cargar_iframe(driver)

    fecha_input = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, "txtfecha1"))
    )
    
    escribir_fecha(fecha_input, fecha_hoy)
    
    driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/table/tbody/tr[2]/td/table/tbody/tr/td[1]/input").click()
    
    try:
        WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.ID, "chkChanging"))
         ).click()
    except:
        pass

    boton = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Consultar')]"))
    )
    boton.click()
    
    time.sleep(1)

    driver.switch_to.default_content()
    cargar_iframe(driver)

    # Leer la tabla
    try:
        tabla = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "timecard"))
        )
    except:
        print("⚠ No hay tabla de precios")
        return None

    headers = [
        th.text.strip()
        for th in tabla.find_elements(By.TAG_NAME, "th")
        if th.text.strip() != "Precios x Kg en S/"
    ]

    filas = tabla.find_elements(By.XPATH, ".//tr[td]")
    datos = []

    for fila in filas:
        celdas = [td.text.strip() for td in fila.find_elements(By.TAG_NAME, "td")]
        if len(celdas) == len(headers):
            datos.append(celdas)

    if not datos:
        return None

    df = pd.DataFrame(datos, columns=headers)
    df["Fecha"] = fecha_hoy

    return df

# SCRAPING VOLUMENES DIARIOS
def scraper_volumenes(driver, fecha_hoy):

    print("🔎 Scraping VOLUMENES...")

    url = "https://www.emmsa.com.pe/index.php/precios-diarios/"
    driver.get(url)

    cargar_iframe(driver)
    
    fecha_input = WebDriverWait(driver, 15).until(
    EC.element_to_be_clickable((By.ID, "txtfecha1"))
    )
    escribir_fecha(fecha_input, fecha_hoy)
    
    # 👇 Cerrar el datepicker antes del click
    fecha_input.send_keys(Keys.ESCAPE)
    time.sleep(0.5)
    
    driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/table/tbody/tr[2]/td/table/tbody/tr/td[2]/input").click()
    try:
        WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.ID, "chkChanging"))
        ).click()
    except:
        pass
    boton = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Consultar')]"))
    )
    boton.click()

    time.sleep(1)

    driver.switch_to.default_content()
    cargar_iframe(driver)

    # Leer tabla volumenes
    try:
        tbody = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".dataTables_scrollBody tbody"))
        )
    except:
        print("⚠ No hay tabla de volúmenes")
        return None

    thead = driver.find_element(By.CSS_SELECTOR, ".dataTables_scrollHead thead")
    headers = [th.text.strip() for th in thead.find_elements(By.TAG_NAME, "th")]

    filas = tbody.find_elements(By.TAG_NAME, ".//tr[td]")
    datos = []

    for fila in filas:
        celdas = [td.text.strip() for td in fila.find_elements(By.TAG_NAME, "td")]
        if len(celdas) == len(headers):
            datos.append(celdas)

    if not datos:
        return None

    df = pd.DataFrame(datos, columns=headers)
    df["Fecha"] = fecha_hoy

    return df

# PROGRAMA PRINCIPAL
def main():
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    print(f"📅 Fecha: {fecha_hoy}")

    # Archivos CSV
    csv_precios = "ArchPowerBI/precios_historico_emmsa.csv"
    csv_volumenes = "ArchPowerBI/volumen_historico_emmsa.csv"

    # VALIDAR PRECIOS: ¿ya existe la fecha en el CSV?
    fecha_ya_existe_precios = False
    if os.path.exists(csv_precios):
        df_p = pd.read_csv(csv_precios)
        if "Fecha" in df_p.columns and fecha_hoy in df_p["Fecha"].astype(str).values:
            fecha_ya_existe_precios = True
            print("⛔ Los precios para hoy ya están en el CSV. No se hace scraping.")

    # VALIDAR VOLUMENES
    fecha_ya_existe_volumenes = False
    if os.path.exists(csv_volumenes):
        df_v = pd.read_csv(csv_volumenes)
        if "Fecha" in df_v.columns and fecha_hoy in df_v["Fecha"].astype(str).values:
            fecha_ya_existe_volumenes = True
            print("⛔ Los volúmenes para hoy ya están en el CSV. No se hace scraping.")

    if fecha_ya_existe_precios and fecha_ya_existe_volumenes:
        print("✔ Datos del día ya registrados.")
        return

    driver = get_driver()

    # SCRAPER PRECIOS (solo si falta)
    if not fecha_ya_existe_precios:
        df_precios_new = scraper_precios(driver, fecha_hoy)
        if df_precios_new is not None:
            df_old = pd.read_csv(csv_precios) if os.path.exists(csv_precios) else pd.DataFrame()
            df_total = pd.concat([df_old, df_precios_new], ignore_index=True).drop_duplicates()
            df_total.to_csv(csv_precios, index=False, encoding="utf-8-sig")
            print("💾 CSV precios actualizado.")

    # SCRAPER VOLUMENES (solo si falta)
    if not fecha_ya_existe_volumenes:
        df_vol_new = scraper_volumenes(driver, fecha_hoy)
        if df_vol_new is not None:
            df_old = pd.read_csv(csv_volumenes) if os.path.exists(csv_volumenes) else pd.DataFrame()
            df_total = pd.concat([df_old, df_vol_new], ignore_index=True).drop_duplicates()
            df_total.to_csv(csv_volumenes, index=False, encoding="utf-8-sig")
            print("💾 CSV volúmenes actualizado.")

    driver.quit()


if __name__ == "__main__":
    main()