# 🤖 Workflows de GitHub Actions - Sistema de Proyectos

Este documento describe los workflows automatizados para el sistema de gestión de proyectos.

## 📋 Workflows Disponibles

### 1. `checkproy.yml` - Verificación de Pagos de Proyectos
- **Archivo**: `checkproy.py`
- **Función**: Verifica y controla los pagos pendientes de proyectos
- **Frecuencia**: Cada hora de lunes a viernes
- **Datos**: Lee y actualiza CHECKPROY

### 2. `asistencia_proy.yml` - Reportes de Asistencia de Proyectos  
- **Archivo**: `asistencia_proy.py`
- **Función**: Genera y envía reportes de asistencia de proyectos
- **Frecuencia**: Cada hora de lunes a viernes
- **Datos**: Lee CHECKPROY, PAGOSPROY, REGISTRO_CALENDARIO_PROYECTOS, VENDEDORAS

### 3. `proyectos_completo.yml` - Workflow Completo (RECOMENDADO)
- **Archivos**: `checkproy.py` → `asistencia_proy.py`
- **Función**: Ejecuta el flujo completo en secuencia
- **Frecuencia**: Cada hora de lunes a viernes
- **Ventaja**: Garantiza el orden correcto de ejecución

## ⚙️ Configuración de Secretos

Los workflows requieren los siguientes secretos en GitHub:

```
GOOGLE_SERVICE_ACCOUNT_JSON  # Credenciales de Google Sheets API
GMAIL_USER                   # Email para envío de reportes
GMAIL_APP_PASSWORD          # Contraseña de aplicación de Gmail
```

## 🔄 Orden de Ejecución Recomendado

1. **checkproy.py** - Verifica los pagos y actualiza estados
2. **asistencia_proy.py** - Genera reportes basado en verificaciones

## 📅 Horarios de Ejecución

- **Cron**: `0 * * * 1-5` (cada hora de lunes a viernes UTC)
- **Zona horaria Perú**: UTC-5
- **Ejemplo**: 15:00 UTC = 10:00 AM Perú

## 🎯 Características

### ✅ Funcionalidades
- ✅ Ejecución automática programada
- ✅ Ejecución manual via workflow_dispatch
- ✅ Logs detallados con timestamps
- ✅ Subida automática de reportes generados
- ✅ Manejo de errores y recuperación

### 📊 Monitoreo
- **Artifacts**: Reportes Excel y logs se suben automáticamente
- **Retención**: 7 días
- **Debug**: Información de zona horaria y contexto

## 🚀 Ejecución Manual

Para ejecutar manualmente:
1. Ve a "Actions" en GitHub
2. Selecciona el workflow deseado
3. Click en "Run workflow"
4. Confirma la ejecución

## 📈 Flujo de Datos

```
CHECKPROY (Control) ←→ checkproy.py
     ↓
PAGOSPROY (Cálculos) ←→ asistencia_proy.py
     ↓
REGISTRO_CALENDARIO_PROYECTOS (Asistencia)
     ↓
📧 Reportes Excel → Colaboradores + Administrador
```

## 🔧 Mantenimiento

- **Logs**: Revisar en la sección "Actions" de GitHub
- **Reportes**: Descargar desde "Artifacts" 
- **Errores**: Monitorear notificaciones de GitHub Actions
- **Actualización**: Los scripts se actualizan automáticamente con cada commit

---
*Última actualización: Septiembre 2025*
