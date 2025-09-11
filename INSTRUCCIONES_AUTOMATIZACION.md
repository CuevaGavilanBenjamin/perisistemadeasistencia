# 🎯 Sistema de Asistencia Automatizado

Sistema automatizado que procesa entradas, salidas y cálculo de minutos desde Google Sheets cada hora usando GitHub Actions.

## 📋 Funciones Principales

### 1. 🚪 Procesar Nuevas Entradas
- Lee nuevos registros de `REGISTRO_DIARIO`
- Identifica entradas no procesadas
- Las agrega automáticamente a `REGISTRO_CALENDARIO`

### 2. 🚶‍♂️ Actualizar Salidas
- Busca registros sin hora de salida en `REGISTRO_CALENDARIO`
- Encuentra las salidas correspondientes en `REGISTRO_DIARIO`
- Actualiza: HoraSalida, FechaSalida, Descripcion, Extratime
- Usa **batch updates** para evitar límites de cuota de Google API

### 3. ⏱️ Calcular Minutos
- Calcula minutos trabajados para registros completos
- Diferencia entre minutos normales y extras según `HORARIOLABORAL`
- Actualiza: Minutos, Minutos_normales, Minutos_extras
- Usa **batch updates** para optimizar llamadas API

## 🔧 Configuración Requerida

### 1. Variables de Entorno (.env para local)
```env
GOOGLE_SHEET_ID=tu_id_de_google_sheet
GOOGLE_SERVICE_ACCOUNT_FILE=ruta/al/archivo/credenciales.json
```

### 2. GitHub Secrets (para automatización)
En tu repositorio GitHub, ve a **Settings > Secrets and variables > Actions** y agrega:

- `GOOGLE_SHEET_ID`: El ID de tu Google Sheet
- `GOOGLE_SERVICE_ACCOUNT_JSON`: El contenido completo del archivo JSON de credenciales

#### 🔑 Cómo obtener las credenciales de Google Sheets:

1. **Ir a Google Cloud Console**
   - https://console.cloud.google.com/

2. **Crear o seleccionar proyecto**
   - Crea un nuevo proyecto o selecciona uno existente

3. **Habilitar Google Sheets API**
   - Ir a "APIs & Services > Library"
   - Buscar "Google Sheets API"
   - Hacer clic en "Enable"

4. **Crear Service Account**
   - Ir a "APIs & Services > Credentials"
   - Hacer clic en "Create Credentials > Service Account"
   - Llenar los datos y crear

5. **Generar clave JSON**
   - En la lista de Service Accounts, hacer clic en el que creaste
   - Ir a la pestaña "Keys"
   - "Add Key > Create New Key > JSON"
   - Descargar el archivo

6. **Compartir Google Sheet**
   - Abrir tu Google Sheet
   - Hacer clic en "Share"
   - Agregar el email del service account (está en el JSON)
   - Dar permisos de "Editor"

## 🚀 Uso

### Ejecución Local
```bash
python asistencia_automatica.py
```

### Ejecución Automática
El workflow de GitHub Actions se ejecuta:
- **Automáticamente**: Cada hora (minuto 0)
- **Manualmente**: Desde la pestaña "Actions" en GitHub

## 📊 Estructura de Hojas Requeridas

El script necesita estas hojas en Google Sheets:

- **REGISTRO_DIARIO**: Registros originales de entrada/salida
- **REGISTRO_CALENDARIO**: Registros procesados y consolidados
- **HORARIOLABORAL**: Configuración de horarios por colaborador

## ⚡ Optimizaciones

- **Batch Updates**: Todas las actualizaciones se hacen en lotes para evitar límites de cuota
- **Validación de datos**: Verificación antes de procesar
- **Manejo de errores**: Logs detallados para debugging
- **Códigos de salida**: Para integración con CI/CD

## 📅 Programación

El workflow está configurado para ejecutarse cada hora:
```yaml
schedule:
  - cron: '0 * * * *'  # Minuto 0 de cada hora
```

Para cambiar la frecuencia, modifica el cron en `.github/workflows/asistencia-automatica.yml`:
- Cada 30 minutos: `'0,30 * * * *'`
- Cada 2 horas: `'0 */2 * * *'`
- Solo días laborales: `'0 * * * 1-5'`

## 🐛 Solución de Problemas

### Error de autenticación
- Verificar que `GOOGLE_SERVICE_ACCOUNT_JSON` esté correctamente configurado
- Asegurarse de que el service account tenga acceso al Sheet

### Error de cuota excedida
- El sistema usa batch updates, pero si persiste, aumentar intervalos
- Verificar límites en Google Cloud Console

### Datos no encontrados
- Verificar nombres de hojas (sensible a mayúsculas/minúsculas)
- Confirmar estructura de columnas requeridas

## 📈 Monitoreo

Puedes ver el estado de las ejecuciones en:
- GitHub > Tu repositorio > Actions
- Logs detallados de cada ejecución
- Notificaciones por email si falla

---

⭐ **¡Sistema optimizado para procesar miles de registros sin límites de cuota!**
