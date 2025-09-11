## Inicio de sesión (contraseña)

La aplicación está protegida con un login. Debes definir **una** de estas variables de entorno (en `.env` o en tu sistema):

### Opción A (solo desarrollo, no recomendada en producción)
```env
ADMIN_PASSWORD=mi_secreta
```

### Opción B (recomendada en producción, con hash seguro)

Primero, genera un hash de la contraseña con werkzeug.security.generate_password_hash:

```bash
python
```

y dentro del intérprete:

```python
from werkzeug.security import generate_password_hash
print(generate_password_hash("mi_secreta"))
```

El resultado será algo como:

```
pbkdf2:sha256:600000$P8eWcJHg6K7jPjE3$6b0e0acb6c0...
```

Luego, colócalo en tu .env:

```env
ADMIN_PASSWORD_HASH=pbkdf2:sha256:600000$P8eWcJHg6K7jPjE3$6b0e0acb6c0...
```
# Flujo de Caja - Veterinaria (Flask)

Aplicación web mínima para registrar el flujo de caja diario en una clínica veterinaria.

## Requerimientos
- Python 3.10+
- pip

## Instalación y ejecución
```bash
cd vet_cashflow
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
set FLASK_APP=app.py  # Windows CMD
# $env:FLASK_APP="app.py"  # PowerShell
# export FLASK_APP=app.py  # Linux/macOS

python app.py  # abre http://127.0.0.1:5000
```

## Flujo
1. Crear un nuevo día (fecha, doctora/o, apertura de caja).
2. Agregar registros por categoría (Atenciones, Procedimientos, Farmacia, Exámenes, Peluquería) con tipo de pago: Débito/Crédito, Efectivo, Transferencia.
3. Ver totales por tipo de pago y por categoría, y calcular *Cierre de caja*.

## Estructura
- `models.py`: modelos `Day` y `Entry`.
- `forms.py`: formularios WTForms.
- `app.py`: rutas principales.
- `templates/`: vistas Jinja2.
- `static/styles.css`: estilos oscuros simples.

## Notas
- Los montos están en CLP (enteros).
- La lógica de cierre puede ajustarse según tu operación.

## Migraciones de Base de Datos

La aplicación utiliza Flask-Migrate para manejar cambios de esquema de base de datos de forma segura. **NUNCA** modifiques la base de datos directamente en producción.

### Configuración inicial de migraciones

Si es la primera vez que usas migraciones:

```bash
# Inicializar Flask-Migrate (solo una vez)
flask db init

# Crear la primera migración
flask db migrate -m "Initial migration"

# Aplicar la migración
flask db upgrade
```

### Flujo de trabajo para cambios de esquema

1. **Modifica los modelos** en `models.py`
2. **Genera la migración**:
   ```bash
   flask db migrate -m "Descripción del cambio"
   ```
3. **Revisa la migración** generada en `migrations/versions/`
4. **Aplica la migración**:
   ```bash
   flask db upgrade
   ```

### Comandos útiles de migración

```bash
# Ver historial de migraciones
flask db history

# Ver migración actual
flask db current

# Revertir a migración anterior (¡CUIDADO!)
flask db downgrade

# Aplicar una migración específica
flask db upgrade <revision_id>

# Ver diferencias sin aplicar
flask db show <revision_id>
```

### ⚠️ Importante para Producción

- **Siempre haz un backup** antes de aplicar migraciones en producción
- **Prueba las migraciones** en un entorno de desarrollo/staging primero
- **Revisa el código SQL** generado en las migraciones antes de aplicarlas
- **Ten un plan de rollback** en caso de problemas

## Backups de Base de Datos

La aplicación incluye un script automatizado para crear backups de PostgreSQL en formato SQL.

### Uso del script de backup

```bash
# Backup simple con timestamp
python backup_db.py

# Backup diario (sobrescribe backup del mismo día)
python backup_db.py --daily

# Backup comprimido
python backup_db.py --compress

# Mantener solo los últimos 7 backups
python backup_db.py --retention 7

# Combinando opciones
python backup_db.py --daily --compress --retention 30
```

### Configuración de backups automáticos

#### Opción 1: Cron (Linux/macOS)

Edita el crontab:
```bash
crontab -e
```

Añade estas líneas:
```bash
# Backup diario a las 2:00 AM
0 2 * * * cd /ruta/a/vet_cashflow && python backup_db.py --daily --compress --retention 30

# Backup cada 6 horas (opcional para entornos críticos)
0 */6 * * * cd /ruta/a/vet_cashflow && python backup_db.py --compress --retention 48
```

#### Opción 2: Scheduler de Windows

Crea un archivo `.bat`:
```batch
@echo off
cd C:\ruta\a\vet_cashflow
python backup_db.py --daily --compress --retention 30
```

Usa el Programador de Tareas de Windows para ejecutarlo diariamente.

### Backup manual usando pg_dump directamente

Si prefieres usar pg_dump directamente:

```bash
# Backup simple
pg_dump -h host -p puerto -U usuario -d database > backup.sql

# Backup comprimido
pg_dump -h host -p puerto -U usuario -d database | gzip > backup.sql.gz

# Backup con opciones recomendadas
pg_dump -h host -p puerto -U usuario -d database \
  --clean --if-exists --no-owner --no-privileges > backup.sql
```

### Restauración de backups

Para restaurar un backup:

```bash
# Desde archivo SQL normal
psql -h host -p puerto -U usuario -d database < backup.sql

# Desde archivo comprimido
gunzip -c backup.sql.gz | psql -h host -p puerto -U usuario -d database

# Con datos existentes (¡CUIDADO! Borra datos actuales)
psql -h host -p puerto -U usuario -d database < backup.sql
```

### ⚠️ Importante para Backups

- **Configura DATABASE_URL** correctamente en tu `.env`
- **Verifica los backups** periódicamente intentando restaurarlos en un entorno de prueba
- **Almacena backups en ubicaciones seguras** (diferentes servidores, cloud storage)
- **Documenta tu estrategia de restauración** para emergencias
- **Testa el proceso de restauración** antes de necesitarlo

### Estructura de archivos de backup

Los backups se guardan en el directorio `backups/` con esta nomenclatura:

```
backups/
├── vet_cashflow_2024-01-15.sql              # Backup diario
├── vet_cashflow_2024-01-15.sql.gz           # Backup diario comprimido
├── vet_cashflow_backup_20240115_143022.sql  # Backup con timestamp
└── vet_cashflow_backup_20240115_143022.sql.gz
```

## Seguridad y Mejores Prácticas

### Manejo de Errores de Base de Datos

La aplicación incluye manejo mejorado de errores de base de datos:

- **Rollback automático** en caso de errores
- **Mensajes informativos** para el usuario
- **Logging de errores** para diagnóstico
- **Operaciones atómicas** para evitar estados inconsistentes

### Variables de Entorno de Seguridad

```env
# Base de datos
DATABASE_URL=postgresql://usuario:password@host:puerto/database

# Autenticación (elige UNA opción)
ADMIN_PASSWORD=mi_password_seguro
# O mejor aún:
ADMIN_PASSWORD_HASH=pbkdf2:sha256:600000$...

# Seguridad
SECRET_KEY=clave_secreta_muy_larga_y_aleatoria
```

### Recomendaciones para Producción

1. **Usa PostgreSQL** en producción (ya configurado)
2. **Habilita SSL** en la conexión de base de datos
3. **Usa contraseñas hasheadas** (`ADMIN_PASSWORD_HASH`)
4. **Configura backups automáticos** diarios
5. **Monitorea el espacio en disco** del directorio de backups
6. **Documenta los procedimientos** de recuperación ante desastres
