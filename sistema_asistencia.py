#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Asistencia Automatizado
==================================
Procesa reportes de asistencia desde Google Sheets y los envía por correo electrónico.
Ejecuta solo para colaboradores con fecha de pago correspondiente al día actual.

Autor: Sistema Automatizado
Fecha: Septiembre 2025
"""

# 📦 IMPORTACIONES
import os
import pandas as pd
import pandasql as psql
from datetime import datetime
import smtplib
from email.message import EmailMessage
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
    Lee TODA la hoja completa desde Google Sheets, sin importar cuántas filas tenga.
    Se adapta automáticamente al crecimiento de datos y maneja celdas vacías.
    
    Args:
        nombre_hoja (str): Nombre de la hoja a leer
        
    Returns:
        pandas.DataFrame: DataFrame con los datos de la hoja o None si hay error
    """
    try:
        # Leer toda la hoja (sin especificar rango)
        range_name = f'{nombre_hoja}'
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, 
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if values:
            if len(values) > 1:
                # Obtener encabezados y número de columnas esperadas
                headers = values[0]
                num_columns = len(headers)
                
                # Normalizar todas las filas para que tengan el mismo número de columnas
                data_rows = []
                for row in values[1:]:
                    # Si la fila tiene menos columnas, completar con cadenas vacías
                    if len(row) < num_columns:
                        row_completa = row + [''] * (num_columns - len(row))
                        data_rows.append(row_completa)
                    else:
                        data_rows.append(row)
                
                df = pd.DataFrame(data_rows, columns=headers)
            else:
                df = pd.DataFrame(values)
            
            print(f"✅ Se leyeron {len(df)} filas de {nombre_hoja}")
            print(f"📊 Columnas: {list(df.columns)}")
            return df
        else:
            print("❌ No se encontraron datos")
            return None
            
    except Exception as e:
        print(f"❌ Error al leer la hoja {nombre_hoja}: {e}")
        return None


def obtener_correo_colaborador(colaborador, df_vendedoras):
    """
    Obtiene el correo del colaborador desde la columna 'Correo' en VENDEDORAS.
    
    Args:
        colaborador (str): Nombre del colaborador
        df_vendedoras (DataFrame): DataFrame con información de vendedoras
        
    Returns:
        str: Email del colaborador o None si no se encuentra
    """
    if 'Correo' not in df_vendedoras.columns:
        print(f"❌ No se encontró la columna 'Correo' en VENDEDORAS")
        return None
    
    # Buscar el colaborador
    resultado = df_vendedoras[df_vendedoras['Colaborador'] == colaborador]
    
    if not resultado.empty:
        correo = resultado.iloc[0]['Correo']
        if correo and str(correo).strip() and str(correo) != 'nan':
            return str(correo).strip()
    
    return None


def enviar_correo_con_excel(destinatario, colaborador, archivo_excel, fecha_pago):
    """
    Envía correo electrónico con el reporte de asistencia adjunto.
    
    Args:
        destinatario (str): Email del destinatario
        colaborador (str): Nombre del colaborador
        archivo_excel (str): Ruta del archivo Excel a adjuntar
        fecha_pago (str): Fecha de pago del período
        
    Returns:
        bool: True si el correo se envió exitosamente, False si hubo error
    """
    try:
        load_dotenv()
        gmail_user = os.getenv('GMAIL_USER')
        gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        
        # Crear mensaje
        msg = EmailMessage()
        msg['Subject'] = f'Reporte de Asistencia - {colaborador} ({fecha_pago})'
        msg['From'] = gmail_user
        msg['To'] = destinatario
        
        # Cuerpo del mensaje
        cuerpo = f"""Estimado/a {colaborador},

Te enviamos tu reporte de asistencia correspondiente al periodo de pago: {fecha_pago}.

En el archivo adjunto encontraras el detalle de tus registros de asistencia.

Si tienes alguna consulta, no dudes en contactarnos.

Saludos cordiales,
Equipo de Recursos Humanos

---
Este correo fue generado automaticamente por el Sistema de Asistencia.
"""
        
        msg.set_content(cuerpo)
        
        # Adjuntar Excel
        with open(archivo_excel, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(archivo_excel)
        
        msg.add_attachment(file_data,
                          maintype='application',
                          subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                          filename=file_name)
        
        # Enviar
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")
        return False


def procesar_reportes_hoy():
    """
    Función principal que procesa reportes para colaboradores con fecha de pago HOY.
    
    Flujo del proceso:
    1. Obtiene la fecha actual
    2. Carga datos desde Google Sheets
    3. Identifica colaboradores con fecha de pago hoy
    4. Genera reportes Excel individuales
    5. Envía correos electrónicos con los reportes adjuntos
    
    Returns:
        bool: True si se procesó al menos un colaborador, False si no hubo procesamiento
    """
    
    print("🚀 === PROCESANDO REPORTES PARA HOY ===")
    
    # 📅 OBTENER FECHA DE HOY
    hoy = datetime.today()
    fecha_hoy_str = hoy.strftime("%d/%m/%Y")
    print(f"📅 Fecha actual: {fecha_hoy_str}")
    
    # 📊 CARGAR DATOS
    print("\n📊 Cargando datos de Google Sheets...")
    df_pagos_check = leer_hoja('PAGOSCHECK')
    df_calendario = leer_hoja('REGISTRO_CALENDARIO')
    df_vendedoras = leer_hoja('VENDEDORAS')
    
    if any(df is None for df in [df_pagos_check, df_calendario, df_vendedoras]):
        print("❌ Error cargando datos necesarios")
        return False
    
    # 🔍 ENCONTRAR COLABORADORES CON FECHA DE PAGO HOY
    colaboradores_hoy = df_pagos_check[df_pagos_check['fecha_pago'] == fecha_hoy_str]
    
    if colaboradores_hoy.empty:
        print(f"ℹ️  No hay colaboradores con fecha de pago para hoy ({fecha_hoy_str})")
        print("\n📅 Fechas de pago programadas:")
        for idx, row in df_pagos_check.iterrows():
            estado = "✅ Listo" if row.get('check', '') == 'Listo' else "⏳ Pendiente"
            print(f"   • {row['Colaborador']}: {row['fecha_pago']} - {estado}")
        return False
    
    print(f"\n✅ Encontrados {len(colaboradores_hoy)} colaborador(es) con fecha de pago HOY:")
    for idx, row in colaboradores_hoy.iterrows():
        estado = "✅ Listo" if row.get('check', '') == 'Listo' else "⏳ Pendiente"
        print(f"   • {row['Colaborador']} - Período: {row['periodo_inicio']} a {row['periodo_fin']} - {estado}")
    
    # 📁 CREAR DIRECTORIO
    directorio_reportes = "Reportes_Asistencia"
    if not os.path.exists(directorio_reportes):
        os.makedirs(directorio_reportes)
        print(f"\n📁 Directorio '{directorio_reportes}' creado")
    
    # 📧 CONFIGURAR CORREO
    load_dotenv()
    gmail_user = os.getenv('GMAIL_USER')
    gmail_password = os.getenv('GMAIL_APP_PASSWORD')
    enviar_correos = gmail_user and gmail_password
    
    if enviar_correos:
        print(f"📧 Correos se enviarán desde: {gmail_user}")
    else:
        print("⚠️  Credenciales de Gmail no configuradas. Solo se generarán archivos Excel.")
    
    # 🔄 PROCESAR CADA COLABORADOR
    resultados = []
    
    for idx, row in colaboradores_hoy.iterrows():
        colaborador = row['Colaborador']
        fecha_pago = row['fecha_pago']
        periodo_inicio = row['periodo_inicio']
        periodo_fin = row['periodo_fin']
        
        print(f"\n🔄 Procesando: {colaborador}")
        print(f"   📅 Período: {periodo_inicio} - {periodo_fin}")
        
        try:
            # Convertir fechas del período a objetos datetime para comparación
            fecha_inicio_dt = datetime.strptime(periodo_inicio, "%d/%m/%Y")
            fecha_fin_dt = datetime.strptime(periodo_fin, "%d/%m/%Y")
            
            # Filtrar el DataFrame usando pandas
            print("   🔍 Filtrando registros de asistencia...")
            
            # Primero filtrar por colaborador
            df_colaborador = df_calendario[df_calendario['Colaborador'] == colaborador].copy()
            
            if df_colaborador.empty:
                print(f"   ⚠️  No hay registros para el colaborador {colaborador}")
                continue
            
            # Convertir FechaEntrada a datetime para comparación
            df_colaborador['FechaEntrada_dt'] = pd.to_datetime(
                df_colaborador['FechaEntrada'], 
                format="%d/%m/%Y", 
                errors='coerce'
            )
            
            # Filtrar por rango de fechas
            df_asistencia = df_colaborador[
                (df_colaborador['FechaEntrada_dt'] >= fecha_inicio_dt) & 
                (df_colaborador['FechaEntrada_dt'] <= fecha_fin_dt)
            ].copy()
            
            # Eliminar la columna auxiliar
            if 'FechaEntrada_dt' in df_asistencia.columns:
                df_asistencia = df_asistencia.drop('FechaEntrada_dt', axis=1)
            
            if df_asistencia.empty:
                print(f"   ⚠️  No hay registros de asistencia para {colaborador} en el período {periodo_inicio} - {periodo_fin}")
                
                # Mostrar diagnóstico
                print(f"   🔍 Diagnóstico:")
                print(f"     - Total registros del colaborador: {len(df_colaborador)}")
                if len(df_colaborador) > 0:
                    fechas_disponibles = df_colaborador['FechaEntrada'].unique()[:5]
                    print(f"     - Fechas disponibles (muestra): {fechas_disponibles}")
                continue
            
            print(f"   📋 Encontrados {len(df_asistencia)} registros de asistencia")
            
            # 📄 GENERAR ARCHIVO EXCEL
            nombre_archivo = f"Reporte_Asistencia_{colaborador.replace(' ', '_')}_{fecha_pago.replace('/', '-')}.xlsx"
            ruta_archivo = os.path.join(directorio_reportes, nombre_archivo)
            
            try:
                df_asistencia.to_excel(ruta_archivo, index=False, engine='openpyxl')
                print(f"   ✅ Excel generado: {nombre_archivo}")
                
                # 📧 ENVIAR CORREO (si está configurado)
                estado_correo = "No configurado"
                email_colaborador = "N/A"
                
                if enviar_correos:
                    # Buscar correo directamente de la columna 'Correo'
                    email_colaborador = obtener_correo_colaborador(colaborador, df_vendedoras)
                    
                    if email_colaborador:
                        print(f"   📧 Enviando correo a: {email_colaborador}")
                        
                        if enviar_correo_con_excel(email_colaborador, colaborador, ruta_archivo, fecha_pago):
                            print(f"   ✅ Correo enviado exitosamente")
                            estado_correo = "Enviado"
                        else:
                            print(f"   ❌ Error enviando correo")
                            estado_correo = "Error"
                    else:
                        print(f"   ⚠️  Email no encontrado para {colaborador}")
                        estado_correo = "Sin email"
                
                # 📝 REGISTRAR RESULTADO
                resultados.append({
                    'Colaborador': colaborador,
                    'Fecha_Pago': fecha_pago,
                    'Archivo_Excel': nombre_archivo,
                    'Estado_Correo': estado_correo,
                    'Email': email_colaborador,
                    'Registros_Asistencia': len(df_asistencia)
                })
                
            except Exception as e:
                print(f"   ❌ Error generando Excel: {e}")
                
        except ValueError as e:
            print(f"   ❌ Error procesando fechas para {colaborador}: {e}")
            print(f"      Período recibido: {periodo_inicio} - {periodo_fin}")
            continue
        except Exception as e:
            print(f"   ❌ Error procesando {colaborador}: {e}")
            continue
    
    # 📋 MOSTRAR RESUMEN
    print(f"\n📋 === RESUMEN DE PROCESAMIENTO ===")
    print(f"✅ Colaboradores procesados: {len(resultados)}")
    
    if resultados:
        for resultado in resultados:
            print(f"   • {resultado['Colaborador']}: {resultado['Archivo_Excel']} - Correo: {resultado['Estado_Correo']}")
    
    print("\n🎉 ¡Procesamiento completado!")
    return len(resultados) > 0


def main():
    """
    Función principal para ejecutar el sistema de asistencia.
    """
    print("🎯 === SISTEMA DE ASISTENCIA AUTOMATIZADO ===")
    print("    Procesando reportes para la fecha de hoy...")
    print("    Solo se procesarán colaboradores con fecha de pago HOY\n")
    
    try:
        resultado = procesar_reportes_hoy()
        
        if resultado:
            print("\n✅ Procesamiento exitoso. Revisa la carpeta 'Reportes_Asistencia' para los archivos generados.")
        else:
            print("\n⚠️  No se procesaron reportes hoy.")
            
    except Exception as e:
        print(f"\n❌ Error en el procesamiento: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
