# Configuración de GitHub Actions

Este documento explica cómo configurar el repositorio de GitHub para ejecutar automáticamente el Sistema de Asistencia.

## 🔧 Configuración Inicial

### 1. Secrets Requeridos en GitHub

Ve a tu repositorio en GitHub → Settings → Secrets and variables → Actions → New repository secret

Necesitas configurar estos secrets:

#### `GOOGLE_SHEET_ID`
```
ID de tu Google Sheet (desde la URL)
Ejemplo: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
```

#### `GMAIL_USER`
```
proyectosperi@gmail.com
```

#### `GMAIL_APP_PASSWORD`
```
nhdz wqvv lxwc mgto
```

#### `GOOGLE_SERVICE_ACCOUNT_JSON`
```json
{
  "type": "service_account",
  "project_id": "sistemaasistencia-470019",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```
**(Copia TODO el contenido del archivo sistemaasistencia-470019-3f3d35327bca.json)**

## ⏰ Horarios de Ejecución

### Automático (Programado)
- **01:00 UTC**: Ejecuta `sistema_asistencia.py` (procesa reportes del día)
- **02:00 UTC**: Ejecuta `checkpagos.py` (actualiza estados de pago)

### Manual (On Demand)
Puedes ejecutar manualmente desde GitHub → Actions → Sistema de Asistencia Automatizado → Run workflow

Opciones disponibles:
- **sistema_asistencia**: Solo procesar reportes
- **checkpagos**: Solo verificar pagos  
- **both**: Ejecutar ambos (predeterminado)

## 🚀 Funcionalidades

### Ejecución Automática
```yaml
# Todos los días a las 01:00 UTC
- cron: '0 1 * * *'  # sistema_asistencia.py

# Todos los días a las 02:00 UTC  
- cron: '0 2 * * *'  # checkpagos.py
```

### Ejecución Manual
- Ve a la pestaña **Actions** en tu repositorio
- Selecciona **Sistema de Asistencia Automatizado**
- Haz clic en **Run workflow**
- Selecciona qué script ejecutar
- Haz clic en **Run workflow**

## 📁 Artifacts

Los reportes Excel generados se guardan como artifacts en GitHub por 30 días:
- Nombre: `reportes-asistencia-{run_number}`
- Ubicación: Actions → Run específico → Artifacts

## 🔍 Monitoreo

### Ver Ejecuciones
1. Ve a la pestaña **Actions**
2. Selecciona el workflow **Sistema de Asistencia Automatizado**
3. Revisa el historial de ejecuciones

### Ver Logs
1. Haz clic en una ejecución específica
2. Haz clic en el job correspondiente:
   - `sistema-asistencia`: Logs del procesamiento de reportes
   - `verificacion-pagos`: Logs de la verificación de pagos
3. Expande los steps para ver detalles

### Estados Posibles
- ✅ **Success**: Ejecutado correctamente
- ❌ **Failure**: Error en la ejecución
- ⏸️ **Cancelled**: Cancelado manualmente
- 🔄 **In Progress**: Ejecutándose actualmente

## 🛠️ Solución de Problemas

### Error: "Secret not found"
- Verifica que todos los secrets estén configurados correctamente
- Los nombres deben ser exactos (case-sensitive)

### Error: "Google Sheets API"
- Verifica que el JSON de credenciales sea correcto
- Confirma que el SHEET_ID sea válido
- Revisa permisos de la cuenta de servicio

### Error: "Gmail SMTP"
- Confirma credenciales de Gmail en secrets
- Verifica que la contraseña de aplicación esté activa

### Workflow no se ejecuta automáticamente
- Los horarios están en UTC, ajusta según tu zona horaria
- GitHub Actions puede tener retrasos de hasta 15 minutos
- Verifica que el repositorio esté activo (commits recientes)

## 📝 Personalización de Horarios

Para cambiar los horarios de ejecución, edita el archivo `.github/workflows/sistema_asistencia.yml`:

```yaml
schedule:
  # Cambiar estos valores según tus necesidades
  - cron: '0 6 * * *'  # 06:00 UTC = 01:00 Peru (UTC-5)
  - cron: '0 7 * * *'  # 07:00 UTC = 02:00 Peru (UTC-5)
```

### Conversor de Horarios
- **UTC a Peru**: UTC - 5 horas
- **01:00 Peru** = **06:00 UTC**
- **02:00 Peru** = **07:00 UTC**

## 🔐 Seguridad

- Los secrets están encriptados en GitHub
- No se muestran en los logs
- Solo accesibles durante la ejecución del workflow
- Rotación recomendada cada 90 días

## 📊 Ejemplo de Uso Manual

```bash
# 1. Ve a GitHub Actions
# 2. Selecciona "Sistema de Asistencia Automatizado"  
# 3. Click "Run workflow"
# 4. Selecciona la acción:
#    - sistema_asistencia: Solo procesar reportes de hoy
#    - checkpagos: Solo actualizar estados de pago
#    - both: Ejecutar ambos procesos
# 5. Click "Run workflow"
```

El workflow se ejecutará inmediatamente y podrás ver el progreso en tiempo real.

---
*Configuración creada para automatizar el Sistema de Asistencia con GitHub Actions*
