# Configuración de GitHub Secrets
# Ve a tu repositorio > Settings > Secrets and variables > Actions

## Secrets necesarios:

1. GOOGLE_SERVICE_ACCOUNT_JSON
   - Contenido completo de tu archivo service-account-key.json
   - Copia todo el JSON y pégalo como secret

2. GOOGLE_SHEET_ID
   - El ID de tu Google Sheet
   - Ejemplo: 14AtL1_MHWaN1JR_dbbddif9w0ujlx4wFrEuelmv6gfs

3. GITHUB_TOKEN (si usas webhook)
   - Token personal de GitHub con permisos de repositorio
   - Genera en: GitHub > Settings > Developer settings > Personal access tokens

## Ejemplo de secret GOOGLE_SERVICE_ACCOUNT_JSON:
{
  "type": "service_account",
  "project_id": "tu-proyecto",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "tu-service-account@proyecto.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}

## Pasos para configurar:
1. Ve a tu repo en GitHub
2. Settings > Secrets and variables > Actions
3. New repository secret
4. Nombre: GOOGLE_SERVICE_ACCOUNT_JSON
5. Valor: Pega todo el contenido de tu JSON
6. Add secret
7. Repite para GOOGLE_SHEET_ID
