from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, SelectField,
    DateField, SubmitField, TextAreaField
)
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import date

PAYMENT_CHOICES = [
    ("DEBITO/CREDITO", "Débito/Crédito"),
    ("EFECTIVO", "Efectivo"),
    ("TRANSFERENCIA", "Transferencia")
]

CATEGORY_CHOICES = [
    ("ATENCION", "Atención"),
    ("PROCEDIMIENTO", "Procedimiento"),
    ("FARMACIA", "Farmacia/Petshop"),
    ("EXAMEN", "Examen"),
    ("PELUQUERIA", "Peluquería"),
]

class DayForm(FlaskForm):
    fecha = DateField("Fecha", default=date.today, validators=[DataRequired()])
    doctor = StringField("Doctora/o", validators=[Optional()])
    apertura_caja = IntegerField("Apertura de caja (CLP)", validators=[Optional(), NumberRange(min=0)], default=0)
    cierre_caja = IntegerField("Cierre de caja (CLP)", validators=[Optional(), NumberRange(min=0)], default=0)
    submit = SubmitField("Guardar día")

class EntryForm(FlaskForm):
    categoria = SelectField("Tipo de registro", choices=CATEGORY_CHOICES, validators=[DataRequired()])
    servicio = SelectField("Servicio", choices=[], coerce=str, validators=[Optional()])
    descripcion = StringField("Detalle", validators=[Optional()])
    monto = IntegerField("Monto (CLP)", validators=[DataRequired(), NumberRange(min=0)])
    tipo_pago = SelectField("Tipo de pago", choices=PAYMENT_CHOICES, validators=[DataRequired()])

    # Opcionales (útiles para peluquería)
    tutor = StringField("Nombre tutor/a", validators=[Optional()])
    mascota = StringField("Mascota", validators=[Optional()])
    peso = StringField("Peso", validators=[Optional()])
    especie = StringField("Especie", validators=[Optional()])

    submit = SubmitField("Agregar")

class LoginForm(FlaskForm):
    password = StringField("Contraseña", validators=[DataRequired()])
    submit = SubmitField("Ingresar")

class CatalogItemForm(FlaskForm):
    # coerce=str evita "Not a valid choice" por tipos
    categoria = SelectField("Categoría", choices=CATEGORY_CHOICES, coerce=str, validators=[DataRequired()])
    nombre = StringField("Nombre del servicio/producto", validators=[DataRequired()])
    precio = IntegerField("Precio sugerido (CLP)", validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField("Guardar")
