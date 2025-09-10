from datetime import date, datetime
from enum import StrEnum
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class PaymentType(StrEnum):
    DEBITO_CREDITO = "DEBITO/CREDITO"
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"

class Category(StrEnum):
    ATENCION = "ATENCION"
    PROCEDIMIENTO = "PROCEDIMIENTO"
    FARMACIA = "FARMACIA"
    EXAMEN = "EXAMEN"
    PELUQUERIA = "PELUQUERIA"

class Day(db.Model):
    __tablename__ = "days"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, unique=True, nullable=False, index=True)
    doctor = db.Column(db.String(120), default="")
    apertura_caja = db.Column(db.Integer, default=0)  # CLP
    cierre_caja = db.Column(db.Integer, default=0)    # CLP
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    entries = db.relationship("Entry", backref="day", cascade="all, delete-orphan")

    def total_por_pago(self):
        tot = {"DEBITO/CREDITO":0, "EFECTIVO":0, "TRANSFERENCIA":0}
        for e in self.entries:
            tot[e.tipo_pago] += e.monto
        return tot

    def total_por_categoria(self):
        tot = {c.value:0 for c in Category}
        for e in self.entries:
            tot[e.categoria] += e.monto
        return tot

    def total_dia(self):
        return sum(e.monto for e in self.entries)

class Entry(db.Model):
    __tablename__ = "entries"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=False)

    categoria = db.Column(db.String(20), nullable=False)   # Category
    descripcion = db.Column(db.String(255), default="")
    monto = db.Column(db.Integer, nullable=False, default=0)

    tipo_pago = db.Column(db.String(20), nullable=False)   # PaymentType

    # Campos opcionales para peluquería, etc.
    tutor = db.Column(db.String(120), default="")
    mascota = db.Column(db.String(120), default="")
    peso = db.Column(db.String(40), default="")
    especie = db.Column(db.String(60), default="")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "categoria": self.categoria,
            "descripcion": self.descripcion,
            "monto": self.monto,
            "tipo_pago": self.tipo_pago,
            "tutor": self.tutor,
            "mascota": self.mascota,
            "peso": self.peso,
            "especie": self.especie,
        }

# Nuevo modelo para catálogo de servicios/productos
class CatalogItem(db.Model):
    __tablename__ = "catalog_items"
    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(32), index=True, nullable=False)  # ATENCION, PROCEDIMIENTO, EXAMEN, etc.
    nombre = db.Column(db.String(120), nullable=False)
    precio = db.Column(db.Integer, nullable=True)  # precio sugerido

    def as_dict(self):
        return {
            "id": self.id,
            "categoria": self.categoria,
            "nombre": self.nombre,
            "precio": self.precio or 0,
        }
