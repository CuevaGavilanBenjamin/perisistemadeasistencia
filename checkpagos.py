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
import json
import tempfile

def configurar_google_sheets():
    """
    Configura la conexión a Google Sheets
    Funciona tanto localmente (con .env) como en GitHub Actions (con secrets)
    """
    # Cargar variables de entorno
    load_dotenv()
    
    # Configuración
    SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    # Método 1: Intentar usar archivo JSON local (para ejecución local)
    SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
        print("🔑 Usando archivo JSON local para autenticación")
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    else:
        # Método 2: Usar JSON desde variable de entorno (para GitHub Actions)
        SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if SERVICE_ACCOUNT_JSON:
            print("🔑 Usando JSON desde variable de entorno para autenticación")
            # Crear archivo temporal con el JSON
            service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
            creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        else:
            raise ValueError("❌ No se encontraron credenciales de Google. Configura GOOGLE_SERVICE_ACCOUNT_FILE o GOOGLE_SERVICE_ACCOUNT_JSON")
    
    # Crear servicio
    service = build('sheets', 'v4', credentials=creds)
    
    return service, SHEET_ID

def leer_hoja(service, sheet_id, nombre_hoja='PAGOS'):
    """
    Lee una hoja específica de Google Sheets
    """
    try:
        range_name = f'{nombre_hoja}'
        
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, 
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

def escribir_hoja(service, sheet_id, nombre_hoja, df):
    """
    Escribe un DataFrame completo a una hoja de Google Sheets
    """
    try:
        # Convertir DataFrame a lista de listas (incluyendo headers)
        headers = [df.columns.tolist()]
        data_rows = df.values.tolist()
        values = headers + data_rows
        
        # Limpiar la hoja primero
        range_name = f'{nombre_hoja}'
        
        # Escribir los nuevos datos
        body = {
            'values': values
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"✅ Hoja {nombre_hoja} actualizada: {result.get('updatedCells')} celdas modificadas")
        return True
        
    except Exception as e:
        print(f"❌ Error al escribir en la hoja {nombre_hoja}: {e}")
        return False

def verificar_y_actualizar_pagos():
    """
    Función principal que verifica fechas de pago y actualiza estados
    """
    print("🚀 === VERIFICACIÓN Y ACTUALIZACIÓN DE PAGOS ===")
    
    try:
        # Configurar conexión a Google Sheets
        service, sheet_id = configurar_google_sheets()
        print(f"📊 Conectado a Google Sheet: {sheet_id}")
        
        # Leer datos de PAGOS
        print("\n📊 Leyendo datos de PAGOS...")
        df_pagos = leer_hoja(service, sheet_id, 'PAGOS')
        
        if df_pagos is None:
            print("❌ No se pudieron cargar los datos de PAGOS")
            return False
        
        # Generar DataFrame consolidado de períodos de pago
        print("\n🔄 Procesando períodos de pago...")
        query = """
        SELECT Colaborador, periodo_inicio, periodo_fin, fecha_pago
        FROM df_pagos
        GROUP BY Colaborador, fecha_pago
        """
        
        periodos = psql.sqldf(query, locals())
        periodos["check"] = ""
        
        print(f"📋 Total de períodos encontrados: {len(periodos)}")
        
        # Verificar fechas y marcar estados
        hoy = datetime.today()
        print(f"📅 Fecha actual: {hoy.strftime('%d/%m/%Y')}")
        
        estados_actualizados = 0
        pendientes = 0
        
        for i in range(len(periodos)):
            fecha_pago_str = periodos.loc[i, "fecha_pago"]
            try:
                fecha_pago = datetime.strptime(fecha_pago_str, "%d/%m/%Y")
                
                if fecha_pago < hoy:
                    periodos.loc[i, "check"] = "Listo"
                    estados_actualizados += 1
                else:
                    periodos.loc[i, "check"] = ""  # Pendiente
                    pendientes += 1
                    
            except ValueError as e:
                print(f"⚠️  Error procesando fecha {fecha_pago_str}: {e}")
                periodos.loc[i, "check"] = ""
        
        print(f"✅ Estados marcados como 'Listo': {estados_actualizados}")
        print(f"⏳ Estados pendientes: {pendientes}")
        
        # Mostrar pagos pendientes
        if pendientes > 0:
            print("\n📅 Próximos pagos pendientes:")
            pagos_pendientes = periodos[periodos["check"] == ""]
            for idx, row in pagos_pendientes.iterrows():
                print(f"   • {row['Colaborador']}: {row['fecha_pago']}")
        
        # Escribir datos actualizados a PAGOSCHECK
        print(f"\n💾 Actualizando hoja PAGOSCHECK...")
        if escribir_hoja(service, sheet_id, 'PAGOSCHECK', periodos):
            print("✅ Actualización exitosa en Google Sheets")
        else:
            print("❌ Error al actualizar Google Sheets")
            return False
        
        print(f"\n🎉 ¡Verificación completada exitosamente!")
        print(f"📊 Resumen:")
        print(f"   • Total registros: {len(periodos)}")
        print(f"   • Marcados como 'Listo': {estados_actualizados}")
        print(f"   • Pendientes: {pendientes}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error general en verificación de pagos: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Ejecutar verificación de pagos
    exito = verificar_y_actualizar_pagos()
    
    if exito:
        print("\n✅ Script checkpagos.py ejecutado exitosamente")
        exit(0)
    else:
        print("\n❌ Script checkpagos.py falló")
        exit(1)
