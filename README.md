# Sistema de Asistencia Automatizado

Sistema automatizado para procesar reportes de asistencia desde Google Sheets y enviarlos por correo electrónico a los colaboradores.

## 🚀 Características

- **Procesamiento Selectivo**: Solo procesa colaboradores con fecha de pago correspondiente al día actual
- **Integración Google Sheets**: Lee datos directamente desde Google Sheets
- **Reportes Excel**: Genera archivos Excel individuales para cada colaborador
- **Envío Automático**: Envía reportes por Gmail con adjuntos
- **Configuración Flexible**: Uso de variables de entorno para credenciales

## 📋 Requisitos

### Dependencias Python
```bash
pip install pandas openpyxl python-dotenv google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pandasql
```

### Archivos de Configuración

1. **Archivo `.env`** con las siguientes variables:
```env
# Google Sheets API
GOOGLE_SERVICE_ACCOUNT_FILE=sistemaasistencia-470019-3f3d35327bca.json
GOOGLE_SHEET_ID=tu_sheet_id_aqui

# Gmail SMTP
GMAIL_USER=proyectosperi@gmail.com
GMAIL_APP_PASSWORD=nhdz wqvv lxwc mgto
```

2. **Archivo de credenciales de Google**: `sistemaasistencia-470019-3f3d35327bca.json`

## 🔧 Instalación

1. **Clonar o descargar** los archivos del sistema
2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configurar archivo .env** con tus credenciales
4. **Colocar archivo de credenciales** de Google Sheets en el directorio

## 📊 Estructura de Datos Requerida

El sistema espera las siguientes hojas en Google Sheets:

### PAGOSCHECK
- `Colaborador`: Nombre del colaborador
- `fecha_pago`: Fecha de pago (formato DD/MM/YYYY)
- `periodo_inicio`: Inicio del período (formato DD/MM/YYYY)
- `periodo_fin`: Fin del período (formato DD/MM/YYYY)
- `check`: Estado del pago (opcional)

### REGISTRO_CALENDARIO
- `Colaborador`: Nombre del colaborador
- `FechaEntrada`: Fecha de entrada (formato DD/MM/YYYY)
- Otras columnas de asistencia...

### VENDEDORAS
- `Colaborador`: Nombre del colaborador
- `Correo`: Dirección de correo electrónico

## 🏃‍♂️ Uso

### Opción 1: Ejecución Automática con GitHub Actions (Recomendado)
```bash
# Configurar secrets en GitHub (ver GITHUB_SETUP.md)
# El sistema se ejecutará automáticamente:
# - 01:00 UTC: sistema_asistencia.py
# - 02:00 UTC: checkpagos.py
```

### Opción 2: Ejecución Manual Local
```python
# Procesar reportes de asistencia
python sistema_asistencia.py

# Verificar y actualizar estados de pago
python checkpagos.py
```

### Opción 3: Ejecución Manual en GitHub
1. Ve a la pestaña **Actions** en tu repositorio
2. Selecciona **Sistema de Asistencia Automatizado**
3. Haz clic en **Run workflow**
4. Selecciona qué ejecutar: `sistema_asistencia`, `checkpagos` o `both`

## 📁 Archivos Generados

El sistema crea:
- **Directorio**: `Reportes_Asistencia/`
- **Archivos Excel**: `Reporte_Asistencia_{Colaborador}_{Fecha}.xlsx`
- **Logs en consola**: Información detallada del procesamiento

## 🔍 Funcionamiento

1. **Validación de Fecha**: Compara fecha actual con fechas de pago
2. **Carga de Datos**: Lee hojas desde Google Sheets
3. **Filtrado**: Selecciona registros del período correspondiente
4. **Generación**: Crea archivos Excel individuales
5. **Envío**: Envía correos con reportes adjuntos
6. **Reporte**: Muestra resumen del procesamiento

## ⚡ Ejecución Automática

### GitHub Actions (Recomendado)
El sistema se ejecuta automáticamente en GitHub:
- **01:00 UTC diario**: `sistema_asistencia.py` 
- **02:00 UTC diario**: `checkpagos.py`

Ver [GITHUB_SETUP.md](GITHUB_SETUP.md) para configuración completa.

### Programador Local (Alternativo)

#### Windows (Programador de Tareas)
1. Crear tarea básica en Programador de tareas
2. Configurar para ejecutar diariamente
3. Acción: `python C:\ruta\al\sistema\sistema_asistencia.py`

#### Linux/Mac (Cron)
```bash
# Editar crontab
crontab -e

# Agregar líneas para ejecutar diariamente
0 1 * * * cd /ruta/al/sistema && python sistema_asistencia.py
0 2 * * * cd /ruta/al/sistema && python checkpagos.py
```

## 🛠️ Solución de Problemas

### Error: "No se encontraron datos"
- Verificar nombres de las hojas en Google Sheets
- Revisar permisos del archivo de credenciales

### Error: "Credenciales de Gmail no configuradas"
- Verificar archivo `.env`
- Confirmar contraseña de aplicación de Gmail

### Error: "No hay colaboradores con fecha de pago para hoy"
- Normal si no hay pagos programados para la fecha actual
- Revisar formato de fechas (DD/MM/YYYY)

### Error de conexión a Google Sheets
- Verificar conexión a internet
- Confirmar que el archivo de credenciales es válido
- Revisar permisos de la cuenta de servicio

## 📝 Logs y Monitoreo

El sistema proporciona logs detallados:
- ✅ Operaciones exitosas
- ⚠️ Advertencias
- ❌ Errores
- 📊 Estadísticas de procesamiento

## 🔒 Seguridad

- **Credenciales**: Almacenadas en archivo `.env` (no incluir en repositorio)
- **Archivos temporales**: Los reportes se almacenan localmente
- **Conexiones**: Usa HTTPS/TLS para todas las comunicaciones

## 📞 Soporte

Para problemas o mejoras, revisar:
1. Logs de ejecución
2. Configuración de archivos `.env`
3. Permisos de Google Sheets API
4. Estado de credenciales de Gmail

---
*Sistema desarrollado para automatizar el procesamiento de reportes de asistencia*
