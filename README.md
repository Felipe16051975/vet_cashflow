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
