#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Verificación de Pagos
================================
Actualiza el estado de los pagos en Google Sheets basado en las fechas.
Marca como "Listo" los pagos cuya fecha ya pasó.

Autor: Sistema Automatizado
Fecha: Septiembre 2025
"""

# 📦 IMPORTACIONES
import os
import pandas as pd
import pandasql as psql
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# 🔐 CONFIGURACIÓN GLOBAL
load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Autenticación Google Sheets
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)


def leer_hoja(nombre_hoja='REGISTRO_DIARIO'):
    """
    Lee TODA la hoja completa desde Google Sheets.
    
    Args:
        nombre_hoja (str): Nombre de la hoja a leer
        
    Returns:
        pandas.DataFrame: DataFrame con los datos de la hoja o None si hay error
    """
    try:
        range_name = f'{nombre_hoja}'
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, 
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if values:
            if len(values) > 1:
                headers = values[0]
                num_columns = len(headers)
                
                data_rows = []
                for row in values[1:]:
                    if len(row) < num_columns:
                        row_completa = row + [''] * (num_columns - len(row))
                        data_rows.append(row_completa)
                    else:
                        data_rows.append(row)
                
                df = pd.DataFrame(data_rows, columns=headers)
            else:
                df = pd.DataFrame(values)
            
            print(f"✅ Se leyeron {len(df)} filas de {nombre_hoja}")
            return df
        else:
            print("❌ No se encontraron datos")
            return None
            
    except Exception as e:
        print(f"❌ Error al leer la hoja {nombre_hoja}: {e}")
        return None


def actualizar_hoja(nombre_hoja, df):
    """
    Actualiza una hoja completa en Google Sheets con los datos del DataFrame.
    
    Args:
        nombre_hoja (str): Nombre de la hoja a actualizar
        df (DataFrame): DataFrame con los datos a escribir
        
    Returns:
        bool: True si se actualizó correctamente, False si hubo error
    """
    try:
        # Preparar datos para Google Sheets (incluir headers)
        values = [df.columns.values.tolist()] + df.values.tolist()
        
        # Limpiar la hoja primero
        range_clear = f'{nombre_hoja}'
        service.spreadsheets().values().clear(
            spreadsheetId=SHEET_ID,
            range=range_clear
        ).execute()
        
        # Escribir nuevos datos
        body = {
            'values': values
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f'{nombre_hoja}!A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"✅ Hoja {nombre_hoja} actualizada: {result.get('updatedCells')} celdas")
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando hoja {nombre_hoja}: {e}")
        return False


def procesar_checkpagos():
    """
    Función principal que verifica y actualiza el estado de los pagos.
    
    Proceso:
    1. Lee datos de la hoja PAGOS
    2. Genera estructura para PAGOSCHECK con estados actualizados
    3. Marca como "Listo" los pagos cuya fecha ya pasó
    4. Actualiza la hoja PAGOSCHECK en Google Sheets
    
    Returns:
        bool: True si se procesó correctamente, False si hubo error
    """
    
    print("🔍 === VERIFICANDO ESTADO DE PAGOS ===")
    
    # 📅 OBTENER FECHA ACTUAL
    hoy = datetime.today()
    print(f"📅 Fecha actual: {hoy.strftime('%d/%m/%Y %H:%M:%S')}")
    
    # 📊 CARGAR DATOS DE PAGOS
    print("\n📊 Cargando datos de PAGOS desde Google Sheets...")
    df_pagos = leer_hoja('PAGOS')
    
    if df_pagos is None:
        print("❌ Error cargando datos de PAGOS")
        return False
    
    # 🔄 GENERAR ESTRUCTURA PAGOSCHECK
    print("\n� Procesando datos para PAGOSCHECK...")
    
    try:
        # Usar SQL para agrupar por colaborador y fecha de pago
        query = """
        SELECT Colaborador, periodo_inicio, periodo_fin, fecha_pago
        FROM df_pagos
        GROUP BY Colaborador, fecha_pago
        ORDER BY Colaborador, fecha_pago
        """
        
        df_pagos_check = psql.sqldf(query, locals())
        
        # Agregar columna check
        df_pagos_check["check"] = ""
        
        print(f"� Procesando {len(df_pagos_check)} registros de pago...")
        
        # � VERIFICAR FECHAS Y ACTUALIZAR ESTADO
        actualizados = 0
        pendientes = 0
        
        for i in range(len(df_pagos_check)):
            colaborador = df_pagos_check.loc[i, "Colaborador"]
            fecha_pago_str = df_pagos_check.loc[i, "fecha_pago"]
            
            try:
                # Convertir fecha de pago a datetime
                fecha_pago = datetime.strptime(fecha_pago_str, "%d/%m/%Y")
                
                # Comparar con fecha actual
                if fecha_pago < hoy:
                    df_pagos_check.loc[i, "check"] = "Listo"
                    print(f"   ✅ {colaborador}: {fecha_pago_str} - Marcado como Listo")
                    actualizados += 1
                else:
                    df_pagos_check.loc[i, "check"] = ""
                    print(f"   ⏳ {colaborador}: {fecha_pago_str} - Pendiente")
                    pendientes += 1
                    
            except ValueError as e:
                print(f"   ❌ Error procesando fecha para {colaborador}: {fecha_pago_str} - {e}")
                df_pagos_check.loc[i, "check"] = ""
        
        print(f"\n📊 Resumen de procesamiento:")
        print(f"   ✅ Pagos marcados como Listo: {actualizados}")
        print(f"   ⏳ Pagos pendientes: {pendientes}")
        
        # 💾 ACTUALIZAR HOJA PAGOSCHECK
        print(f"\n💾 Actualizando hoja PAGOSCHECK en Google Sheets...")
        
        if actualizar_hoja('PAGOSCHECK', df_pagos_check):
            print("✅ Hoja PAGOSCHECK actualizada exitosamente")
            return True
        else:
            print("❌ Error actualizando hoja PAGOSCHECK")
            return False
            
    except Exception as e:
        print(f"❌ Error en procesamiento: {e}")
        return False


def main():
    """
    Función principal para ejecutar la verificación de pagos.
    """
    print("� === SISTEMA DE VERIFICACIÓN DE PAGOS ===")
    print("    Verificando y actualizando estados de pago...")
    print("    Marcando como 'Listo' los pagos cuya fecha ya pasó\n")
    
    try:
        resultado = procesar_checkpagos()
        
        if resultado:
            print("\n✅ Verificación completada exitosamente")
            print("📊 Estados de pago actualizados en Google Sheets")
        else:
            print("\n❌ Error en la verificación de pagos")
            
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
