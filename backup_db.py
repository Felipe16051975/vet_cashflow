#!/usr/bin/env python3
"""
Script para realizar backups automáticos de la base de datos PostgreSQL.
Genera archivos .sql con pg_dump y los organiza por fecha.

Uso:
    python backup_db.py                    # Backup simple con timestamp
    python backup_db.py --daily            # Backup diario (sobrescribe backup del día)
    python backup_db.py --retention 7      # Mantener solo 7 backups más recientes
    python backup_db.py --compress         # Comprimir backup con gzip
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
import gzip
import shutil
from pathlib import Path
import glob
from urllib.parse import urlparse
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def parse_database_url(database_url):
    """
    Parsea la URL de la base de datos y extrae los componentes.
    
    Args:
        database_url (str): URL de la base de datos PostgreSQL
        
    Returns:
        dict: Diccionario con los componentes de conexión
    """
    if not database_url:
        raise ValueError("DATABASE_URL no está configurada")
    
    # Manejar URLs que empiezan con postgres:// (Heroku legacy)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    parsed = urlparse(database_url)
    
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:],  # Remover el '/' inicial
        'username': parsed.username,
        'password': parsed.password
    }

def create_backup_directory():
    """
    Crea el directorio de backups si no existe.
    
    Returns:
        Path: Ruta al directorio de backups
    """
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    return backup_dir

def generate_backup_filename(daily=False, compress=False):
    """
    Genera el nombre del archivo de backup.
    
    Args:
        daily (bool): Si es True, usa formato diario (vet_cashflow_YYYY-MM-DD.sql)
        compress (bool): Si es True, añade extensión .gz
        
    Returns:
        str: Nombre del archivo de backup
    """
    if daily:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"vet_cashflow_{timestamp}.sql"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vet_cashflow_backup_{timestamp}.sql"
    
    if compress:
        filename += ".gz"
    
    return filename

def create_backup(db_config, output_file, compress=False):
    """
    Crea un backup de la base de datos usando pg_dump.
    
    Args:
        db_config (dict): Configuración de conexión a la base de datos
        output_file (Path): Archivo donde guardar el backup
        compress (bool): Si es True, comprime el archivo con gzip
        
    Returns:
        bool: True si el backup fue exitoso, False en caso contrario
    """
    try:
        # Construir comando pg_dump
        cmd = [
            "pg_dump",
            f"--host={db_config['host']}",
            f"--port={db_config['port']}",
            f"--username={db_config['username']}",
            f"--dbname={db_config['database']}",
            "--no-password",  # Usar PGPASSWORD env var
            "--verbose",
            "--clean",  # Incluir comandos DROP antes de CREATE
            "--if-exists",  # No fallar si los objetos no existen al hacer DROP
            "--no-owner",  # No incluir comandos de ownership
            "--no-privileges",  # No incluir comandos de privilegios
        ]
        
        # Configurar variables de entorno para pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config['password']
        
        print(f"Iniciando backup de la base de datos '{db_config['database']}'...")
        print(f"Servidor: {db_config['host']}:{db_config['port']}")
        print(f"Usuario: {db_config['username']}")
        print(f"Archivo de salida: {output_file}")
        
        if compress:
            # Ejecutar pg_dump y comprimir directamente
            with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )
        else:
            # Ejecutar pg_dump normalmente
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )
        
        if result.returncode == 0:
            file_size = output_file.stat().st_size
            print(f"✓ Backup completado exitosamente")
            print(f"  Tamaño del archivo: {file_size:,} bytes")
            return True
        else:
            print(f"✗ Error en pg_dump:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("✗ Error: pg_dump no está instalado o no está en el PATH")
        print("  Instala PostgreSQL client tools o asegúrate de que pg_dump esté disponible")
        return False
    except Exception as e:
        print(f"✗ Error inesperado durante el backup: {e}")
        return False

def cleanup_old_backups(backup_dir, retention_days):
    """
    Elimina backups antiguos basado en la retención configurada.
    
    Args:
        backup_dir (Path): Directorio de backups
        retention_days (int): Número de días de retención
    """
    if retention_days <= 0:
        return
    
    print(f"\nLimpiando backups antiguos (retención: {retention_days} días)...")
    
    # Buscar archivos de backup
    patterns = [
        "vet_cashflow_backup_*.sql",
        "vet_cashflow_backup_*.sql.gz",
        "vet_cashflow_20*.sql",
        "vet_cashflow_20*.sql.gz"
    ]
    
    all_backups = []
    for pattern in patterns:
        all_backups.extend(backup_dir.glob(pattern))
    
    if not all_backups:
        print("  No se encontraron backups para limpiar")
        return
    
    # Ordenar por tiempo de modificación (más reciente primero)
    all_backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Mantener solo los archivos más recientes
    to_keep = all_backups[:retention_days]
    to_delete = all_backups[retention_days:]
    
    print(f"  Manteniendo {len(to_keep)} backup(s) más recientes")
    print(f"  Eliminando {len(to_delete)} backup(s) antiguos")
    
    for backup_file in to_delete:
        try:
            backup_file.unlink()
            print(f"    ✓ Eliminado: {backup_file.name}")
        except Exception as e:
            print(f"    ✗ Error eliminando {backup_file.name}: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Crear backup de la base de datos PostgreSQL de la veterinaria",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python backup_db.py                    # Backup con timestamp único
  python backup_db.py --daily            # Backup diario
  python backup_db.py --retention 7      # Mantener solo 7 backups
  python backup_db.py --compress         # Comprimir el backup
  python backup_db.py --daily --compress --retention 30
        """
    )
    
    parser.add_argument(
        '--daily',
        action='store_true',
        help='Crear backup diario (formato: vet_cashflow_YYYY-MM-DD.sql)'
    )
    
    parser.add_argument(
        '--compress',
        action='store_true',
        help='Comprimir el backup con gzip'
    )
    
    parser.add_argument(
        '--retention',
        type=int,
        default=0,
        help='Número de backups a mantener (0 = mantener todos)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('backups'),
        help='Directorio donde guardar los backups (default: ./backups)'
    )
    
    args = parser.parse_args()
    
    try:
        # Obtener configuración de la base de datos
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("✗ Error: Variable de entorno DATABASE_URL no está configurada")
            print("  Configura DATABASE_URL con la URL de conexión a PostgreSQL")
            print("  Ejemplo: postgresql://usuario:password@host:puerto/database")
            return 1
        
        # Verificar que es una URL de PostgreSQL
        if not any(database_url.startswith(prefix) for prefix in ['postgresql://', 'postgres://']):
            print("✗ Error: DATABASE_URL debe ser una URL de PostgreSQL")
            print(f"  URL actual: {database_url}")
            print("  Debe empezar con postgresql:// o postgres://")
            return 1
        
        db_config = parse_database_url(database_url)
        
        # Crear directorio de backups
        backup_dir = args.output_dir
        backup_dir.mkdir(exist_ok=True)
        
        # Generar nombre del archivo
        filename = generate_backup_filename(daily=args.daily, compress=args.compress)
        output_file = backup_dir / filename
        
        print("=" * 60)
        print("BACKUP DE BASE DE DATOS - VETERINARIA TIN TIN")
        print("=" * 60)
        
        # Crear backup
        success = create_backup(db_config, output_file, compress=args.compress)
        
        if success:
            # Limpiar backups antiguos si se especificó retención
            if args.retention > 0:
                cleanup_old_backups(backup_dir, args.retention)
            
            print("\n" + "=" * 60)
            print("✓ BACKUP COMPLETADO EXITOSAMENTE")
            print("=" * 60)
            print(f"Archivo: {output_file}")
            print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return 0
        else:
            print("\n" + "=" * 60)
            print("✗ BACKUP FALLÓ")
            print("=" * 60)
            return 1
            
    except KeyboardInterrupt:
        print("\n✗ Backup cancelado por el usuario")
        return 1
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())