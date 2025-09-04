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
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
import json
import tempfile
import smtplib
from email.message import EmailMessage

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
            # Crear credenciales desde el JSON
            service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
            creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        else:
            raise ValueError("❌ No se encontraron credenciales de Google. Configura GOOGLE_SERVICE_ACCOUNT_FILE o GOOGLE_SERVICE_ACCOUNT_JSON")
    
    # Crear servicio
    service = build('sheets', 'v4', credentials=creds)
    
    return service, SHEET_ID

def leer_hoja(service, sheet_id, nombre_hoja='REGISTRO_DIARIO'):
    """
    Lee TODA la hoja completa, sin importar cuántas filas tenga
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

def procesar_reportes_hoy():
    """
    Procesa reportes para colaboradores con fecha de pago HOY
    """
    
    print("🚀 === PROCESANDO REPORTES PARA HOY ===")
    
    try:
        # Configurar conexión a Google Sheets
        service, sheet_id = configurar_google_sheets()
        print(f"📊 Conectado a Google Sheet: {sheet_id}")
        
        # 📅 OBTENER FECHA DE HOY
        hoy = datetime.today()
        fecha_hoy_str = hoy.strftime("%d/%m/%Y")
        print(f"📅 Fecha actual: {fecha_hoy_str}")
        
        # 📊 CARGAR DATOS
        print("\n📊 Cargando datos de Google Sheets...")
        df_pagos_check = leer_hoja(service, sheet_id, 'PAGOSCHECK')
        df_calendario = leer_hoja(service, sheet_id, 'REGISTRO_CALENDARIO')
        df_vendedoras = leer_hoja(service, sheet_id, 'VENDEDORAS')
        
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
            return True  # No es error, simplemente no hay pagos hoy
        
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
            
            # 🔧 MÉTODO CORREGIDO: Convertir fechas antes de comparar
            try:
                # Convertir fechas del período a objetos datetime para comparación
                fecha_inicio_dt = datetime.strptime(periodo_inicio, "%d/%m/%Y")
                fecha_fin_dt = datetime.strptime(periodo_fin, "%d/%m/%Y")
                
                # Filtrar el DataFrame usando pandas en lugar de SQL
                print("   🔍 Filtrando registros de asistencia...")
                
                # Primero filtrar por colaborador
                df_colaborador = df_calendario[df_calendario['Colaborador'] == colaborador].copy()
                
                if df_colaborador.empty:
                    print(f"   ⚠️  No hay registros para el colaborador {colaborador}")
                    continue
                
                # Convertir FechaEntrada a datetime para comparación
                df_colaborador['FechaEntrada_dt'] = pd.to_datetime(df_colaborador['FechaEntrada'], format="%d/%m/%Y", errors='coerce')
                
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
        return True
        
    except Exception as e:
        print(f"❌ Error general en sistema de asistencia: {e}")
        import traceback
        traceback.print_exc()
        return False

def obtener_correo_colaborador(colaborador, df_vendedoras):
    """
    Obtiene el correo del colaborador desde la columna 'Correo' en VENDEDORAS
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
    """Envía correo con Excel adjunto"""
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

if __name__ == "__main__":
    # Ejecutar procesamiento de reportes
    exito = procesar_reportes_hoy()
    
    if exito:
        print("\n✅ Script sistema_asistencia.py ejecutado exitosamente")
        exit(0)
    else:
        print("\n❌ Script sistema_asistencia.py falló")
        exit(1)
