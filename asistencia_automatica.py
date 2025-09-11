#!/usr/bin/env python3
"""
🎯 SISTEMA DE ASISTENCIA AUTOMATIZADO
Procesa automáticamente entradas, salidas y cálculo de minutos
Optimizado para evitar límites de cuota de Google Sheets API

Funciones principales:
1. Procesar nuevas entradas al REGISTRO_CALENDARIO
2. Actualizar salidas pendientes con batch updates
3. Calcular minutos trabajados y actualizar con batch updates
"""

import os
import pandas as pd
import pandasql as ps
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
import json
import sys

class SistemaAsistencia:
    def __init__(self):
        """Inicializa el sistema de asistencia"""
        self.service = None
        self.sheet_id = None
        self.configurar_google_sheets()
        
    def configurar_google_sheets(self):
        """
        Configura la conexión a Google Sheets
        Funciona tanto localmente (con .env) como en GitHub Actions (con secrets)
        """
        # Cargar variables de entorno
        load_dotenv()
        
        # Configuración
        self.sheet_id = os.getenv('GOOGLE_SHEET_ID')
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        
        if not self.sheet_id:
            raise ValueError("❌ GOOGLE_SHEET_ID no está configurado")
        
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
        self.service = build('sheets', 'v4', credentials=creds)
        print(f"✅ Conectado a Google Sheet: {self.sheet_id}")

    def leer_hoja(self, nombre_hoja='REGISTRO_DIARIO'):
        """
        Lee TODA la hoja completa desde Google Sheets
        
        Args:
            nombre_hoja (str): Nombre de la hoja a leer
            
        Returns:
            pandas.DataFrame: DataFrame con los datos de la hoja o None si hay error
        """
        try:
            # Leer toda la hoja (sin especificar rango)
            range_name = f'{nombre_hoja}'
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id, 
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
                return df
            else:
                print("❌ No se encontraron datos")
                return None
                
        except Exception as e:
            print(f"❌ Error al leer la hoja {nombre_hoja}: {e}")
            return None

    def escribir_a_sheets(self, nombre_hoja, datos):
        """
        Escribe datos directamente a Google Sheets al final de la hoja
        
        Args:
            nombre_hoja (str): Nombre de la hoja
            datos (list): Lista de listas con los datos
        """
        try:
            # Obtener última fila
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f'{nombre_hoja}!A:A'
            ).execute()
            
            ultima_fila = len(result.get('values', [])) + 1
            
            # Escribir datos
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=f'{nombre_hoja}!A{ultima_fila}',
                valueInputOption='USER_ENTERED',
                body={'values': datos}
            ).execute()
            
            print(f"✅ {len(datos)} filas escritas en {nombre_hoja}")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def procesar_nuevas_entradas(self):
        """
        🎯 FUNCIÓN 1: Procesa nuevas entradas y las agrega a REGISTRO_CALENDARIO
        """
        print("\n🚀 === PROCESANDO NUEVAS ENTRADAS ===")
        
        try:
            # Leer hojas
            registro_calendario = self.leer_hoja("REGISTRO_CALENDARIO")
            registro_diario = self.leer_hoja("REGISTRO_DIARIO")
            
            if registro_calendario is None or registro_diario is None:
                print("❌ Error al leer las hojas")
                return False
            
            # Buscar nuevos registros
            filas_calendario = len(registro_calendario)
            filas_diarios = len(registro_diario)
            
            if filas_calendario == 0 or filas_diarios == 0:
                print("❌ No hay datos para procesar")
                return False
            
            ultimo_id = registro_calendario.loc[filas_calendario - 1, "ID_Registro"]
            index_nuevo = 0
            
            for i in range(filas_diarios):
                if ultimo_id == registro_diario.loc[filas_diarios - 1 - i, "ID"]:
                    index_nuevo = filas_diarios - 1 - i
                    break
            
            index_nuevo = index_nuevo + 1
            entradas = []
            
            for j in range(index_nuevo, filas_diarios):
                if registro_diario.loc[j, "Etapa"] == "Entrada":
                    entrada = {
                        "Colaborador": registro_diario.loc[j, "Colaborador"],
                        "HoraEntrada": registro_diario.loc[j, "Hora"],
                        "FechaEntrada": registro_diario.loc[j, "Fecha"],
                        "ID_Registro": registro_diario.loc[j, "ID"]
                    }
                    entradas.append(entrada)
            
            if not entradas:
                print("ℹ️ No hay nuevas entradas para procesar")
                return True
            
            # Convertir entradas para escribir
            datos_para_escribir = []
            for entrada in entradas:
                fila = [
                    entrada["Colaborador"],
                    entrada["HoraEntrada"],
                    "",
                    entrada["FechaEntrada"], 
                    "",
                    "",  # HoraSalida vacía
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    entrada["ID_Registro"]
                ]
                datos_para_escribir.append(fila)
            
            # Escribir a la hoja
            resultado = self.escribir_a_sheets("REGISTRO_CALENDARIO", datos_para_escribir)
            
            if resultado:
                print(f"🎉 Se procesaron {len(entradas)} nuevas entradas")
                return True
            else:
                print("❌ Error al escribir entradas")
                return False
                
        except Exception as e:
            print(f"❌ Error al procesar entradas: {e}")
            return False

    def actualizar_salidas(self):
        """
        🎯 FUNCIÓN 2: Busca y actualiza salidas pendientes
        """
        print("\n🚀 === ACTUALIZANDO SALIDAS ===")
        
        try:
            # Leer hojas
            registro_calendario = self.leer_hoja("REGISTRO_CALENDARIO")
            registro_diario = self.leer_hoja("REGISTRO_DIARIO")
            
            if registro_calendario is None or registro_diario is None:
                print("❌ Error al leer las hojas")
                return False
            
            filas_calendario = len(registro_calendario)
            filas_diarios = len(registro_diario)
            salidas = []
            
            # Buscar salidas pendientes
            for i in range(filas_calendario):
                if registro_calendario.loc[filas_calendario - 1 - i, "HoraSalida"] == "":
                    colaborador = registro_calendario.loc[filas_calendario - 1 - i, "Colaborador"] 
                    id_registro = registro_calendario.loc[filas_calendario - 1 - i, "ID_Registro"] 
                    
                    for j in range(filas_diarios):
                        if registro_diario.loc[filas_diarios - 1 - j, "ID"] == id_registro:
                            index = filas_diarios - 1 - j
                            
                            for z in range(index, filas_diarios):
                                horas_extra = ""
                                if registro_diario.loc[z, "Captura de petición de horas extra"] == "":
                                    horas_extra = "No"
                                else:
                                    horas_extra = "Si"
                                    
                                if (registro_diario.loc[z, "Etapa"] == "Salida" and 
                                    registro_diario.loc[z, "Colaborador"] == colaborador):
                                    
                                    salida = {
                                        "Colaborador": colaborador,
                                        "HoraSalida": registro_diario.loc[z, "Hora"],
                                        "FechaSalida": registro_diario.loc[z, "Fecha"],
                                        "ID_Calendario": registro_calendario.loc[filas_calendario - 1 - i, "ID_Calendario"],
                                        "Descripcion": registro_diario.loc[z, "Descripcion"],
                                        "Extratime": horas_extra,
                                        "ID_Registro": id_registro
                                    }
                                    salidas.append(salida)
                                    break
            
            if not salidas:
                print("ℹ️ No hay salidas pendientes para actualizar")
                return True
            
            # Actualizar salidas usando batch update
            resultado = self._actualizar_salidas_sheets(salidas)
            
            if resultado:
                print(f"🎉 Se actualizaron {len(salidas)} salidas")
                return True
            else:
                print("❌ Error al actualizar salidas")
                return False
                
        except Exception as e:
            print(f"❌ Error al actualizar salidas: {e}")
            return False

    def _actualizar_salidas_sheets(self, salidas):
        """
        Actualiza las horas, fechas, descripción y horas extras de salida usando batch update
        """
        if not salidas:
            return False
        
        print(f"🔄 Preparando actualización de {len(salidas)} salidas...")
        
        try:
            # Leer toda la hoja
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range='REGISTRO_CALENDARIO!A:N'
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print("❌ No se encontraron datos en REGISTRO_CALENDARIO")
                return False
            
            # Obtener encabezados
            headers = values[0]
            
            # Encontrar índices de las columnas
            try:
                col_id_calendario = headers.index('ID_Calendario')
                col_hora_salida = headers.index('HoraSalida')
                col_fecha_salida = headers.index('FechaSalida')
                col_descripcion = headers.index('Descripcion')
                col_extratime = headers.index('Extratime')
            except ValueError as e:
                print(f"❌ Error: No se encontró una columna requerida: {e}")
                return False
            
            # Preparar batch updates
            batch_updates = []
            
            for salida in salidas:
                id_calendario_buscado = salida["ID_Calendario"]
                
                # Buscar la fila correspondiente
                fila_encontrada = None
                for i, fila in enumerate(values[1:], start=2):
                    if len(fila) > col_id_calendario and fila[col_id_calendario] == id_calendario_buscado:
                        fila_encontrada = i
                        break
                
                if fila_encontrada:
                    # Agregar las 4 actualizaciones al batch
                    batch_updates.extend([
                        {
                            'range': f'REGISTRO_CALENDARIO!{chr(ord("A") + col_hora_salida)}{fila_encontrada}',
                            'values': [[salida["HoraSalida"]]]
                        },
                        {
                            'range': f'REGISTRO_CALENDARIO!{chr(ord("A") + col_fecha_salida)}{fila_encontrada}',
                            'values': [[salida["FechaSalida"]]]
                        },
                        {
                            'range': f'REGISTRO_CALENDARIO!{chr(ord("A") + col_descripcion)}{fila_encontrada}',
                            'values': [[salida["Descripcion"]]]
                        },
                        {
                            'range': f'REGISTRO_CALENDARIO!{chr(ord("A") + col_extratime)}{fila_encontrada}',
                            'values': [[salida["Extratime"]]]
                        }
                    ])
            
            if not batch_updates:
                print("❌ No se encontraron registros para actualizar")
                return False
            
            # Ejecutar batch update
            batch_update_request = {
                'valueInputOption': 'USER_ENTERED',
                'data': batch_updates
            }
            
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.sheet_id,
                body=batch_update_request
            ).execute()
            
            print(f"🎉 Se ejecutaron {len(batch_updates)} actualizaciones en batch")
            return True
            
        except Exception as e:
            print(f"❌ Error al actualizar salidas: {e}")
            return False

    def parsear_hora(self, hora_str):
        """
        Convierte diferentes formatos de hora a datetime
        """
        if not hora_str or hora_str == "":
            return None
            
        # Limpiar espacios
        hora_str = str(hora_str).strip()
        
        # Casos especiales para formatos como "0:00" -> "00:00:00"
        if hora_str.count(':') == 1:
            partes = hora_str.split(':')
            if len(partes) == 2:
                hora_str = f"{partes[0].zfill(2)}:{partes[1].zfill(2)}:00"
        
        # Casos especiales para formatos como "6:29:47" -> "06:29:47"
        if hora_str.count(':') == 2:
            partes = hora_str.split(':')
            if len(partes[0]) == 1:
                hora_str = f"{partes[0].zfill(2)}:{partes[1]}:{partes[2]}"
        
        # Intentar parsear con formato estándar
        try:
            return datetime.strptime(hora_str, "%H:%M:%S")
        except ValueError:
            print(f"⚠️ No se pudo parsear la hora: '{hora_str}'")
            return None

    def calcular_minutos(self):
        """
        🎯 FUNCIÓN 3: Calcula minutos trabajados y los actualiza
        """
        print("\n🚀 === CALCULANDO MINUTOS ===")
        
        try:
            # Leer hojas
            registro_calendario = self.leer_hoja("REGISTRO_CALENDARIO")
            horario_laboral = self.leer_hoja("HORARIOLABORAL")
            
            if registro_calendario is None or horario_laboral is None:
                print("❌ Error al leer las hojas")
                return False
            
            # Mapeo días inglés → español
            dias_map = {
                'Monday': 'Lunes',
                'Tuesday': 'Martes', 
                'Wednesday': 'Miercoles',
                'Thursday': 'Jueves',
                'Friday': 'Viernes',
                'Saturday': 'Sabado',
                'Sunday': 'Domingo'
            }
            
            dias_name = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
            filas_calendario = len(registro_calendario)
            minutos_calculados = []
            
            for i in range(filas_calendario):
                if (registro_calendario.loc[filas_calendario - 1 - i, "Minutos"] == "" and 
                    registro_calendario.loc[filas_calendario - 1 - i, "HoraSalida"] != ""):
                    
                    colaborador = registro_calendario.loc[filas_calendario - 1 - i, "Colaborador"]
                    hora_entrada = registro_calendario.loc[filas_calendario - 1 - i, "HoraEntrada"]
                    hora_salida = registro_calendario.loc[filas_calendario - 1 - i, "HoraSalida"]
                    fecha_entrada = registro_calendario.loc[filas_calendario - 1 - i, "FechaEntrada"]
                    id_calendario = registro_calendario.loc[filas_calendario - 1 - i, "ID_Calendario"]
                    
                    # Buscar horario del colaborador
                    query = f'SELECT * FROM horario_laboral WHERE Colaborador="{colaborador}"'
                    resultado = ps.sqldf(query, locals())
                    
                    # Calcular minutos totales
                    hora_entrada_dt = self.parsear_hora(hora_entrada)
                    hora_salida_dt = self.parsear_hora(hora_salida)
                    
                    if not hora_entrada_dt or not hora_salida_dt:
                        continue
                        
                    minutos = hora_salida_dt - hora_entrada_dt
                    minutos = int(minutos.total_seconds() / 60)
                    
                    if minutos < 0:
                        minutos = minutos + 1440
                    
                    minutos_normales = 0
                    minutos_extras = 0
                    
                    # Obtener día de la semana en español
                    fecha_dt = pd.to_datetime(fecha_entrada)
                    dia_ingles = fecha_dt.day_name()
                    dia_espanol = dias_map.get(dia_ingles, dia_ingles)
                    
                    # Buscar horario correspondiente
                    for j in range(len(resultado)):
                        rango_dias = resultado.loc[j, "dias"].split("-")
                        inicio = dias_name.index(rango_dias[0])
                        fin = dias_name.index(rango_dias[-1])
                        new_rango_dias = dias_name[inicio:fin + 1]
                        
                        if dia_espanol in new_rango_dias:
                            hora_inicio = resultado.loc[j, "hora_entrada"]
                            hora_fin = resultado.loc[j, "hora_salida"]
                            hora_inicio_dt = self.parsear_hora(hora_inicio)
                            hora_fin_dt = self.parsear_hora(hora_fin)
                            
                            if not hora_inicio_dt or not hora_fin_dt:
                                continue
                            
                            minutos_extras = 0
                            if hora_inicio_dt > hora_entrada_dt:
                                minutos_extras += (hora_inicio_dt - hora_entrada_dt).total_seconds() / 60
                            if hora_fin_dt < hora_salida_dt:
                                minutos_extras += (hora_salida_dt - hora_fin_dt).total_seconds() / 60
                                
                            minutos_normales = minutos - minutos_extras
                            break
                    
                    minutos_normales = int(minutos_normales)
                    minutos_extras = int(minutos_extras)
                    
                    calculo = {
                        "Minutos": minutos,
                        "Minutos_normales": minutos_normales,
                        "Minutos_extras": minutos_extras,
                        "ID_Calendario": id_calendario
                    }
                    
                    minutos_calculados.append(calculo)
            
            if not minutos_calculados:
                print("ℹ️ No hay cálculos de minutos pendientes")
                return True
            
            # Actualizar minutos usando batch update
            resultado = self._actualizar_minutos_sheets(minutos_calculados)
            
            if resultado:
                print(f"🎉 Se calcularon y actualizaron {len(minutos_calculados)} registros")
                return True
            else:
                print("❌ Error al actualizar minutos")
                return False
                
        except Exception as e:
            print(f"❌ Error al calcular minutos: {e}")
            return False

    def _actualizar_minutos_sheets(self, minutos_calculados):
        """
        Actualiza los minutos en REGISTRO_CALENDARIO usando batch update
        """
        if not minutos_calculados:
            return False
        
        print(f"🔄 Preparando actualización de {len(minutos_calculados)} registros...")
        
        try:
            # Leer toda la hoja
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range='REGISTRO_CALENDARIO!A:N'
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print("❌ No se encontraron datos en REGISTRO_CALENDARIO")
                return False
            
            # Obtener encabezados
            headers = values[0]
            
            # Encontrar índices de las columnas
            try:
                col_id_calendario = headers.index('ID_Calendario')
                col_minutos = headers.index('Minutos')
                col_minutos_normales = headers.index('Minutos_normales')
                col_minutos_extras = headers.index('Minutos_extras')
            except ValueError as e:
                print(f"❌ Error: No se encontró una columna requerida: {e}")
                return False
            
            # Preparar batch updates
            batch_updates = []
            
            for calculo in minutos_calculados:
                id_calendario_buscado = calculo["ID_Calendario"]
                
                # Buscar la fila correspondiente
                fila_encontrada = None
                for i, fila in enumerate(values[1:], start=2):
                    if len(fila) > col_id_calendario and fila[col_id_calendario] == id_calendario_buscado:
                        fila_encontrada = i
                        break
                
                if fila_encontrada:
                    # Agregar las 3 actualizaciones al batch
                    batch_updates.extend([
                        {
                            'range': f'REGISTRO_CALENDARIO!{chr(ord("A") + col_minutos)}{fila_encontrada}',
                            'values': [[calculo["Minutos"]]]
                        },
                        {
                            'range': f'REGISTRO_CALENDARIO!{chr(ord("A") + col_minutos_normales)}{fila_encontrada}',
                            'values': [[calculo["Minutos_normales"]]]
                        },
                        {
                            'range': f'REGISTRO_CALENDARIO!{chr(ord("A") + col_minutos_extras)}{fila_encontrada}',
                            'values': [[calculo["Minutos_extras"]]]
                        }
                    ])
            
            if not batch_updates:
                print("❌ No se encontraron registros para actualizar")
                return False
            
            # Ejecutar batch update
            batch_update_request = {
                'valueInputOption': 'USER_ENTERED',
                'data': batch_updates
            }
            
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.sheet_id,
                body=batch_update_request
            ).execute()
            
            print(f"🎉 Se ejecutaron {len(batch_updates)} actualizaciones en batch")
            return True
            
        except Exception as e:
            print(f"❌ Error al actualizar minutos: {e}")
            return False

    def ejecutar_proceso_completo(self):
        """
        🎯 EJECUTA EL PROCESO COMPLETO DE ASISTENCIA
        """
        print("\n" + "="*60)
        print("🎯 INICIANDO SISTEMA DE ASISTENCIA AUTOMATIZADO")
        print("="*60)
        
        resultados = {
            'entradas': False,
            'salidas': False,
            'minutos': False
        }
        
        try:
            # 1. Procesar nuevas entradas
            resultados['entradas'] = self.procesar_nuevas_entradas()
            
            # 2. Actualizar salidas
            resultados['salidas'] = self.actualizar_salidas()
            
            # 3. Calcular minutos
            resultados['minutos'] = self.calcular_minutos()
            
            # Resumen final
            print("\n" + "="*60)
            print("📊 RESUMEN DE EJECUCIÓN")
            print("="*60)
            print(f"✅ Entradas procesadas: {'Sí' if resultados['entradas'] else 'No'}")
            print(f"✅ Salidas actualizadas: {'Sí' if resultados['salidas'] else 'No'}")
            print(f"✅ Minutos calculados: {'Sí' if resultados['minutos'] else 'No'}")
            
            exito_total = all(resultados.values())
            if exito_total:
                print("\n🎉 ¡PROCESO COMPLETADO EXITOSAMENTE!")
            else:
                print("\n⚠️ Proceso completado con algunos errores")
            
            return exito_total
            
        except Exception as e:
            print(f"\n❌ ERROR CRÍTICO EN EL PROCESO: {e}")
            return False

def main():
    """Función principal"""
    try:
        sistema = SistemaAsistencia()
        exito = sistema.ejecutar_proceso_completo()
        
        # Código de salida para GitHub Actions
        sys.exit(0 if exito else 1)
        
    except Exception as e:
        print(f"❌ ERROR FATAL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
