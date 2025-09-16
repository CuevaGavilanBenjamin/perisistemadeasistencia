#!/usr/bin/env python3
# -*- coding: utf-8 -*-


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

def leer_hoja(service, sheet_id, nombre_hoja):
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
        df_pagos_check = leer_hoja(service, sheet_id, 'PAGOSCHECK')  # Control de fechas y envíos
        df_pagos_data = leer_hoja(service, sheet_id, 'PAGOS')        # Datos calculados de horas y montos
        df_calendario = leer_hoja(service, sheet_id, 'REGISTRO_CALENDARIO')
        df_vendedoras = leer_hoja(service, sheet_id, 'VENDEDORAS')
        
        if any(df is None for df in [df_pagos_check, df_pagos_data, df_calendario, df_vendedoras]):
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
            
            # 📊 CALCULAR Y ENVIAR RESUMEN ADMINISTRATIVO
            print(f"\n📊 Calculando resumen de horas...")
            resumen_horas = calcular_resumen_horas(resultados, df_pagos_data, df_vendedoras, df_pagos_check, fecha_hoy_str)
            
            if resumen_horas:
                print(f"📧 Enviando resumen administrativo con archivos Excel...")
                if enviar_resumen_administrativo(resumen_horas, fecha_hoy_str, resultados):
                    print(f"✅ Resumen enviado CORRECTAMENTE a nitza.peri.d@gmail.com - ARCHIVO ACTUALIZADO")
                else:
                    print(f"❌ Error enviando resumen administrativo")
        
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
Equipo de Proyectos de Peri Company

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

def calcular_resumen_horas(resultados, df_pagos_data, df_vendedoras, df_pagos_check, fecha_hoy_str):
    """
    Calcula el resumen de horas trabajadas por colaborador usando datos ya calculados de PAGOS
    filtrando por el período específico de cada colaborador
    """
    print("📊 Calculando resumen de horas por colaborador desde PAGOS...")
    
    resumen_por_colaborador = {}
    
    for resultado in resultados:
        colaborador = resultado['Colaborador']
        print(f"   📋 Procesando: {colaborador}")
        
        # Obtener información del período desde PAGOSCHECK para la fecha de pago de HOY
        info_pago = df_pagos_check[
            (df_pagos_check['Colaborador'] == colaborador) &
            (df_pagos_check['fecha_pago'] == fecha_hoy_str)
        ]
        
        if info_pago.empty:
            print(f"   ⚠️ No se encontró información de período para {colaborador} con fecha de pago {fecha_hoy_str}")
            continue
            
        periodo_inicio = info_pago.iloc[0]['periodo_inicio']
        periodo_fin = info_pago.iloc[0]['periodo_fin']
        
        print(f"   🔍 Buscando datos para período: {periodo_inicio} - {periodo_fin}")
        
        # Filtrar datos del colaborador desde PAGOS por período específico
        colaborador_pago = df_pagos_data[
            (df_pagos_data['Colaborador'] == colaborador) &
            (df_pagos_data['periodo_inicio'] == periodo_inicio) &
            (df_pagos_data['periodo_fin'] == periodo_fin)
        ]
        
        if colaborador_pago.empty:
            print(f"   ⚠️ No se encontraron datos de pago para {colaborador} en el período {periodo_inicio} - {periodo_fin}")
            continue
        
        # Usar los datos ya calculados del período específico
        registro = colaborador_pago.iloc[0]
        
        # Convertir horas manejando comas como separador decimal
        horas_normales_str = str(registro.get('horas_normales', '0')).replace(',', '.')
        horas_extra_str = str(registro.get('horas_extra', '0')).replace(',', '.')
        monto_total_str = str(registro.get('monto_total', '0')).replace(',', '.')
        
        horas_normales = float(horas_normales_str) if horas_normales_str and horas_normales_str != '' else 0
        horas_extra = float(horas_extra_str) if horas_extra_str and horas_extra_str != '' else 0
        monto_total = float(monto_total_str) if monto_total_str and monto_total_str != '' else 0
        
        total_horas = horas_normales + horas_extra
        
        # Obtener tarifa desde VENDEDORAS para mostrar en el reporte
        colaborador_info = df_vendedoras[df_vendedoras['Colaborador'] == colaborador]
        if not colaborador_info.empty:
            try:
                pago_hora_str = str(colaborador_info.iloc[0]['pago_por_hora']).replace(',', '.')
                pago_hora = float(pago_hora_str)
            except (ValueError, TypeError):
                print(f"   ⚠️ Error convirtiendo tarifa para {colaborador}, usando 6.41")
                pago_hora = 6.41
        else:
            # Calcular tarifa basada en el monto y horas si no está en VENDEDORAS
            pago_hora = monto_total / total_horas if total_horas > 0 else 6.41
        
        resumen_por_colaborador[colaborador] = {
            'horas': round(total_horas, 2),
            'horas_normales': round(horas_normales, 2),
            'horas_extra': round(horas_extra, 2),
            'registros': resultado['Registros_Asistencia'],
            'periodo': f"{periodo_inicio} - {periodo_fin}",
            'tarifa_hora': f"{pago_hora} PEN/hora",
            'total_pen': round(monto_total, 2)
        }
        
        print(f"   ✅ {colaborador}: {round(total_horas, 2)} horas ({round(horas_normales, 2)}+{round(horas_extra, 2)}) | {round(monto_total, 2)} PEN | Período: {periodo_inicio}-{periodo_fin}")
    
    return resumen_por_colaborador

def  enviar_resumen_administrativo(resumen_por_colaborador, fecha_hoy_str, resultados):
    """
    Envía el resumen consolidado de horas al administrador con archivos Excel adjuntos
    """
    try:
        load_dotenv()
        gmail_user = os.getenv('GMAIL_USER')
        gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        
        if not gmail_user or not gmail_password:
            print("⚠️ Credenciales de Gmail no configuradas para envío administrativo")
            return False
        
        # Crear mensaje
        msg = EmailMessage()
        msg['Subject'] = f'📊 Resumen de Reportes de Asistencia - {fecha_hoy_str}'
        msg['From'] = gmail_user
        msg['To'] = 'nitza.peri.d@gmail.com'

        # Construir el cuerpo del mensaje
        cuerpo = f"""Estimado Administrador,

Se han procesado los reportes de asistencia para la fecha: {fecha_hoy_str}

Resumen de horas por usuario:

"""
        
        total_horas_general = 0
        total_pen_general = 0
        
        for colaborador, datos in resumen_por_colaborador.items():
            horas = datos['horas']
            tarifa = datos['tarifa_hora']
            total_pen = datos['total_pen']
            
            cuerpo += f"{colaborador}: {horas} horas    {tarifa}    {total_pen} PEN\n"
            total_horas_general += horas
            total_pen_general += total_pen
        
        cuerpo += f"""
─────────────────────────────────────────────
TOTAL GENERAL: {round(total_horas_general, 2)} horas    {round(total_pen_general, 2)} PEN

Detalles del procesamiento:
• Total de colaboradores procesados: {len(resumen_por_colaborador)}
• Fecha de procesamiento: {fecha_hoy_str}
• Sistema: Asistencia General
• Archivos adjuntos: {len(resultados)} reportes Excel

Saludos cordiales,
Sistema Automatizado de Asistencia

---
Este correo fue generado automáticamente.
"""
        
        msg.set_content(cuerpo)
        
        # Adjuntar archivos Excel de cada colaborador
        directorio_reportes = "Reportes_Asistencia"
        archivos_adjuntados = 0
        
        for resultado in resultados:
            archivo_excel = resultado['Archivo_Excel']
            ruta_archivo = os.path.join(directorio_reportes, archivo_excel)
            
            try:
                if os.path.exists(ruta_archivo):
                    with open(ruta_archivo, 'rb') as f:
                        file_data = f.read()
                        file_name = os.path.basename(ruta_archivo)
                    
                    msg.add_attachment(file_data,
                                      maintype='application',
                                      subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                                      filename=file_name)
                    archivos_adjuntados += 1
                    print(f"   📎 Adjuntado: {file_name}")
                else:
                    print(f"   ⚠️ Archivo no encontrado: {ruta_archivo}")
            except Exception as e:
                print(f"   ❌ Error adjuntando {archivo_excel}: {e}")
        
        print(f"📎 Total archivos adjuntados: {archivos_adjuntados}")
        
        # Enviar
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
        
        print("✅ Resumen administrativo enviado exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando resumen administrativo: {e}")
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
