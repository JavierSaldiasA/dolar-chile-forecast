import bcchapi
import pandas as pd
import numpy as np
import os
from datetime import datetime
from getpass import getpass
from dotenv import load_dotenv


def obtener_credenciales():
    """
    Obtiene credenciales del Banco Central.
    Primero busca en .env, si no existe pide por consola.
    """
    load_dotenv()
    email = os.getenv("BCCH_EMAIL")
    password = os.getenv("BCCH_PASSWORD")
    
    if email and password:
        print("\nCredenciales cargadas desde archivo .env")
        return email, password
    
    print("-" * 50)
    print("\nCredenciales del Banco Central de Chile")
    print("Tip: Crea un archivo .env para no escribirlas cada vez")
    print("-" * 50)
    
    email = input("Email: ")
    password = getpass("Contraseña: ")
    
    return email, password


def conectar_bcch():
    """
    Crea la conexion con la API del Banco Central.
    """
    email, password = obtener_credenciales()
    siete = bcchapi.Siete(email, password)
    print("Conexion establecida con Banco Central de Chile")
    return siete


def menu_buscar(siete):
    """
    Menu interactivo para buscar series por nombre.
    Con paginacion para no saturar la terminal.
    """
    while True:
        print("\n" + "=" * 50)
        print("BUSCADOR DE SERIES")
        print("=" * 50)
        print("Escribe una palabra clave para buscar")
        print("Ejemplos:\n- Tipo de Cambio\n -> Para dolar: CLP/USD\n -> Para euro: Solo EURO\n- Cobre\n- IPC\n- TPM\n- UF\n- IMACEC\n- Etc.")
        print("Escribe 'salir' para volver al menu principal")
        print("-" * 50)
        
        busqueda = input("Buscar: ").strip()
        
        if busqueda.lower() == "salir":
            break
        
        if not busqueda:
            print("Debes escribir algo para buscar")
            continue
        
        try:
            resultados = siete.buscar(busqueda)
            
            if len(resultados) == 0:
                print("No se encontraron resultados")
                continue
            
            total = len(resultados)
            print(f"\nSe encontraron {total} resultados")
            
            # Mostrar en paginas de 10
            mostrar_paginacion(resultados, total)
            
            # Opcion para guardar TODOS los resultados en CSV
            guardar = input("\nGuardar TODOS los resultados en CSV? (s/n): ").strip().lower()
            if guardar == "s":
                nombre_archivo = f"busqueda_{busqueda.replace(' ', '_')}.csv"
                ruta = os.path.join("data", "raw", nombre_archivo)
                os.makedirs(os.path.dirname(ruta), exist_ok=True)
                resultados.to_csv(ruta, index=False)
                print(f"Resultados guardados en: {ruta}")
                
        except Exception as e:
            print(f"Error en la busqueda: {e}")


def mostrar_paginacion(resultados, total, por_pagina=10):
    """
    Muestra los resultados paginados para no saturar la terminal.
    """
    # Preparar columnas que vamos a mostrar
    columnas_mostrar = ["seriesId", "frequencyCode", "spanishTitle"]
    
    # Acortar titulos muy largos para que quepan en pantalla
    resultados_copia = resultados.copy()
    resultados_copia["spanishTitle"] = resultados_copia["spanishTitle"].apply(
        lambda x: x[:60] + "..." if len(str(x)) > 60 else x
    )
    
    inicio = 0
    
    while inicio < total:
        fin = min(inicio + por_pagina, total)
        
        print(f"\n--- Mostrando {inicio + 1} a {fin} de {total} ---")
        print(resultados_copia[columnas_mostrar].iloc[inicio:fin].to_string())
        
        # Si quedan mas resultados, preguntar
        if fin < total:
            continuar = input(f"\nMostrar siguiente pagina? (s/n): ").strip().lower()
            if continuar != "s":
                print(f"Se omitieron {total - fin} resultados. Usa la opcion de guardar CSV para ver todos.")
                break
        else:
            print(f"\n--- Fin de resultados ({total} total) ---")
        
        inicio = fin


def menu_descargar(siete):
    """
    Menu interactivo para descargar series conocidas.
    """
    print("\n" + "=" * 50)
    print("DESCARGA DE SERIES")
    print("=" * 50)
    
    # Pedir datos al usuario
    series_id = input("Series ID (ej: F073.TCO.PRE.Z.D): ").strip()
    nombre = input("Nombre corto para la columna (ej: usd_clp): ").strip()
    
    fecha_desde = input("Fecha desde (YYYY-MM-DD) [default: 2015-01-01]: ").strip()
    if not fecha_desde:
        fecha_desde = "2015-01-01"
    
    fecha_hasta = input("Fecha hasta (YYYY-MM-DD) [default: hoy]: ").strip()
    if not fecha_hasta:
        fecha_hasta = datetime.now().strftime("%Y-%m-%d")
    
    nombre_archivo = input("Nombre del archivo CSV (ej: usd_clp.csv): ").strip()
    if not nombre_archivo:
        nombre_archivo = f"{nombre}.csv"
    
    print("\nDescargando...")
    
    try:
        df = siete.cuadro(
            series=[series_id],
            nombres=[nombre],
            desde=fecha_desde,
            hasta=fecha_hasta
        )
        
        # Resetear indice para que la fecha sea columna
        df = df.reset_index()
        df = df.rename(columns={"index": "date"})
        
        print(f"Registros descargados: {len(df)}")
        print(f"Rango: {df['date'].min()} hasta {df['date'].max()}")
        print(f"\nPrimeras 5 filas:")
        print(df.head())
        
        # Guardar
        ruta_carpeta = os.path.join("data", "raw")
        os.makedirs(ruta_carpeta, exist_ok=True)
        ruta_archivo = os.path.join(ruta_carpeta, nombre_archivo)
        df.to_csv(ruta_archivo, index=False)
        print(f"\nGuardado en: {ruta_archivo}")
        
    except Exception as e:
        print(f"Error al descargar: {e}")
        print("Tip: Verifica que el Series ID sea correcto")


def menu_principal():
    """
    Menu principal del script.
    """
    print("\n" + "=" * 50)
    print("DATA COLLECTION - BANCO CENTRAL DE CHILE")
    print("=" * 50)
    print("1. Buscar series por nombre (si no conoces el ID)")
    print("2. Descargar series por ID (si ya conoces el codigo)")
    print("3. Salir")
    print("-" * 50)
    
    opcion = input("Elige una opcion (1/2/3): ").strip()
    return opcion


def main():
    """
    Funcion principal que ejecuta el flujo completo.
    """
    # Conectar a la API
    try:
        siete = conectar_bcch()
    except Exception as e:
        print(f"Error al conectar: {e}")
        print("Verifica tus credenciales en el archivo .env")
        return
    
    # Loop del menu
    while True:
        opcion = menu_principal()
        
        if opcion == "1":
            menu_buscar(siete)
        elif opcion == "2":
            menu_descargar(siete)
        elif opcion == "3":
            print("Hasta luego!")
            break
        else:
            print("Opcion no valida, intenta de nuevo")


if __name__ == "__main__":
    main()