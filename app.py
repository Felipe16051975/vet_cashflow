# Helper para mostrar errores de formulario
def flash_form_errors(form):
    for field, errs in form.errors.items():
        label = getattr(getattr(form, field), "label", None)
        field_name = label.text if label else field
        for e in errs:
            flash(f"{field_name}: {e}", "danger")

# Helper para operaciones de base de datos seguras
def safe_db_operation(operation_func, success_message=None, error_message="Error en la operación de base de datos"):
    """
    Ejecuta una operación de base de datos con manejo de errores mejorado.
    
    Args:
        operation_func: Función que contiene la operación de DB
        success_message: Mensaje a mostrar en caso de éxito
        error_message: Mensaje a mostrar en caso de error
    
    Returns:
        True si la operación fue exitosa, False en caso contrario
    """
    try:
        result = operation_func()
        db.session.commit()
        if success_message:
            flash(success_message, "success")
        return result if result is not None else True
    except Exception as e:
        db.session.rollback()
        flash(f"{error_message}: {str(e)}", "danger")
        print(f"Database error: {e}")  # Log para desarrollo
        return False
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, datetime
import calendar as pycal
from config import Config
from models import db, Day, Entry, CatalogItem, User
from forms import DayForm, EntryForm, CatalogItemForm, CATEGORY_CHOICES
from sqlalchemy import func
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask_migrate import Migrate

# Inicialización de la app

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    db.init_app(app)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    with app.app_context():
        # Use migrations instead of db.create_all() for production safety
        # For development, you can still use db.create_all() if no migrations exist
        try:
            # Check if migrations directory exists
            import os
            if not os.path.exists('migrations'):
                print("No migrations directory found. Creating tables directly for development.")
                db.create_all()
        except Exception as e:
            print(f"Migration check failed, falling back to create_all(): {e}")
            db.create_all()
        
        # Seed admin user if not present with improved error handling
        try:
            admin_username = app.config.get("ADMIN_USERNAME", "admin")
            admin_user = User.query.filter_by(username=admin_username).first()
            
            if not admin_user:
                admin_password = app.config.get("ADMIN_PASSWORD")
                admin_password_hash = app.config.get("ADMIN_PASSWORD_HASH")
                
                if admin_password_hash:
                    # Use the pre-hashed password
                    admin_user = User(
                        username=admin_username,
                        password_hash=admin_password_hash,
                        role="admin",
                        is_active=True
                    )
                elif admin_password:
                    # Hash the plain password
                    admin_user = User(
                        username=admin_username,
                        role="admin",
                        is_active=True
                    )
                    admin_user.set_password(admin_password)
                else:
                    # Create with default password if none provided
                    admin_user = User(
                        username=admin_username,
                        role="admin",
                        is_active=True
                    )
                    admin_user.set_password("admin")  # Default password
                    
                db.session.add(admin_user)
                db.session.commit()
                print(f"Admin user '{admin_username}' created successfully.")
        except Exception as e:
            print(f"Error creating admin user: {e}")
            db.session.rollback()
        
    return app

app = create_app()

# Authentication protection
@app.before_request
def require_login():
    # Allow access to login page and static files
    if request.endpoint in ['login', 'static']:
        return
    
    # Check if user is logged in
    if not session.get("user_id"):
        return redirect(url_for("login"))

# Filtros personalizados
@app.template_filter("clp")
def clp(n):
    try:
        return f"$ {int(n):,}".replace(",", ".")
    except Exception:
        return n

@app.template_filter("pct")
def pct(n):
    try:
        return f"{float(n):.1f}%"
    except Exception:
        return n

def get_month_stats(year: int, month: int):
    import calendar as pycal
    _, last_day = pycal.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    categorias = ["ATENCION", "PROCEDIMIENTO", "FARMACIA", "EXAMEN", "PELUQUERIA"]
    tot_por_pago = {"DEBITO/CREDITO": 0, "EFECTIVO": 0, "TRANSFERENCIA": 0}
    tot_por_cat  = {c: 0 for c in categorias}

    pagos_raw = (
        db.session.query(Entry.tipo_pago, func.coalesce(func.sum(Entry.monto), 0))
        .join(Day, Entry.day_id == Day.id)
        .filter(Day.fecha.between(month_start, month_end))
        .group_by(Entry.tipo_pago)
        .all()
    )
    for tipo, suma in pagos_raw:
        if tipo in tot_por_pago:
            tot_por_pago[tipo] = int(suma or 0)

    cats_raw = (
        db.session.query(Entry.categoria, func.coalesce(func.sum(Entry.monto), 0))
        .join(Day, Entry.day_id == Day.id)
        .filter(Day.fecha.between(month_start, month_end))
        .group_by(Entry.categoria)
        .all()
    )
    for cat, suma in cats_raw:
        if cat in tot_por_cat:
            tot_por_cat[cat] = int(suma or 0)

    total_general = sum(tot_por_pago.values())

    tx_count = (
        db.session.query(func.count(Entry.id))
        .join(Day, Entry.day_id == Day.id)
        .filter(Day.fecha.between(month_start, month_end))
        .scalar() or 0
    )

    dias_con_mov = (
        db.session.query(func.count(func.distinct(Day.id)))
        .join(Entry, Entry.day_id == Day.id)
        .filter(Day.fecha.between(month_start, month_end))
        .scalar() or 0
    )

    promedio_diario = int(total_general / dias_con_mov) if dias_con_mov else 0

    sumas_por_dia = (
        db.session.query(Day.fecha, func.coalesce(func.sum(Entry.monto), 0))
        .join(Entry, Entry.day_id == Day.id)
        .filter(Day.fecha.between(month_start, month_end))
        .group_by(Day.fecha)
        .all()
    )
    sumas_por_dia = [(f, int(s or 0)) for f, s in sumas_por_dia]
    top5 = sorted(sumas_por_dia, key=lambda x: x[1], reverse=True)[:5]
    peak_day = top5[0][0] if top5 else None
    peak_total = top5[0][1] if top5 else 0

    categorias_list = ["ATENCION","PROCEDIMIENTO","FARMACIA","EXAMEN","PELUQUERIA"]
    cats_count_raw = (
        db.session.query(Entry.categoria, func.count(Entry.id))
        .join(Day, Entry.day_id == Day.id)
        .filter(Day.fecha.between(month_start, month_end))
        .group_by(Entry.categoria)
        .all()
    )
    count_por_cat = {c: 0 for c in categorias_list}
    for cat, cnt in cats_count_raw:
        if cat in count_por_cat:
            count_por_cat[cat] = int(cnt or 0)

    ticket_promedio = int(total_general / tx_count) if tx_count else 0
    ticket_promedio_cat = {
        c: (int(tot_por_cat[c] / count_por_cat[c]) if count_por_cat[c] else 0)
        for c in categorias_list
    }

    part_pago = {k: (100 * v / total_general if total_general else 0.0) for k, v in tot_por_pago.items()}
    part_cat  = {c: (100 * tot_por_cat[c] / total_general if total_general else 0.0) for c in categorias_list}

    return {
        "month_start": month_start, "month_end": month_end,
        "tot_por_pago": tot_por_pago, "tot_por_cat": tot_por_cat,
        "total_general": total_general, "tx_count": tx_count,
        "dias_con_mov": dias_con_mov, "promedio_diario": promedio_diario,
        "top5": top5, "peak_day": peak_day, "peak_total": peak_total,
        "ticket_promedio": ticket_promedio, "ticket_promedio_cat": ticket_promedio_cat,
        "part_pago": part_pago, "part_cat": part_cat
    }

MONTHS_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

@app.route("/calendar")
def calendar_view():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))

    cal = pycal.Calendar(firstweekday=6)  # 6 = domingo primero
    weeks = cal.monthdatescalendar(year, month)

    # Rango del mes
    _, last_day = pycal.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    # Días existentes en DB
    days = Day.query.filter(Day.fecha.between(month_start, month_end)).all()
    existing = {d.fecha: d for d in days}

    # Mini resumen por día: total y número de transacciones
    sums = (
        db.session.query(Day.fecha, func.coalesce(func.sum(Entry.monto), 0), func.count(Entry.id))
        .join(Entry, Entry.day_id == Day.id)
        .filter(Day.fecha.between(month_start, month_end))
        .group_by(Day.fecha)
        .all()
    )
    day_summ = {f: {"total": int(t or 0), "count": int(c or 0)} for f, t, c in sums}

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        weeks=weeks,
        existing=existing,
        day_summ=day_summ,
        month_name=MONTHS_ES[month],  # mes en español
    )

@app.route("/day/new", methods=["GET", "POST"])
def day_new():
    pre_date = request.args.get("date")
    form = DayForm()

    # Si viene ?date=YYYY-MM-DD, precargar la fecha en el formulario (solo en GET)
    if request.method == "GET" and pre_date:
        try:
            y, m, d = map(int, pre_date.split("-"))
            form.fecha.data = date(y, m, d)
        except ValueError:
            pass  # ignorar si viene mal formado

    if form.validate_on_submit():
        # si ya existe un día con esa fecha, redirigir a su detalle
        existente = Day.query.filter_by(fecha=form.fecha.data).first()
        if existente:
            flash("Ya existe un día con esa fecha. Se abrirá para edición.", "warning")
            return redirect(url_for("day_detail", day_id=existente.id))

        # crear nuevo día con manejo seguro de errores
        def create_day():
            d = Day(
                fecha=form.fecha.data,
                doctor=form.doctor.data or "",
                apertura_caja=form.apertura_caja.data or 0,
                cierre_caja=form.cierre_caja.data or 0,
            )
            db.session.add(d)
            return d
        
        day = safe_db_operation(create_day, "Día creado.", "Error al crear el día")
        if day:
            return redirect(url_for("day_detail", day_id=day.id))

    return render_template("day_edit.html", form=form, is_new=True)


@app.route("/day/<int:day_id>", methods=["GET", "POST"])
def day_detail(day_id):
    day = Day.query.get_or_404(day_id)
    form = EntryForm()

    # --- Prefill desde querystring para rapidez (seguir agregando al mismo paciente)
    qs_tutor = (request.args.get("tutor") or "").strip()
    qs_mascota = (request.args.get("mascota") or "").strip()
    if request.method == "GET":
        if qs_tutor:
            form.tutor.data = qs_tutor
        if qs_mascota:
            form.mascota.data = qs_mascota

    # --- Si viene POST y servicio de catálogo, setear choices y completar monto/detalle como ya hicimos
    if request.method == "POST":
        cat_post = (request.form.get("categoria") or "").upper()
        if cat_post:
            items = CatalogItem.query.filter_by(categoria=cat_post).order_by(CatalogItem.nombre.asc()).all()
            form.servicio.choices = [(str(i.id), i.nombre) for i in items]
        else:
            form.servicio.choices = []

        srv_id = request.form.get("servicio")
        if srv_id and srv_id.isdigit():
            item = CatalogItem.query.get(int(srv_id))
            try:
                monto_val = int(request.form.get("monto") or 0)
            except ValueError:
                monto_val = 0
            if item:
                if (not form.monto.data) or monto_val == 0:
                    form.monto.data = item.precio or 0
                if (not form.descripcion.data) or not form.descripcion.data.strip():
                    form.descripcion.data = item.nombre

    if form.validate_on_submit():
        def create_entry():
            e = Entry(
                day_id=day.id,
                categoria=form.categoria.data,
                descripcion=form.descripcion.data or "",
                monto=form.monto.data,
                tipo_pago=form.tipo_pago.data,
                tutor=(form.tutor.data or "").strip(),
                mascota=(form.mascota.data or "").strip(),
                peso=form.peso.data or "",
                especie=form.especie.data or "",
            )
            db.session.add(e)
            return e
        
        entry = safe_db_operation(create_entry, "Registro agregado.", "Error al crear el registro")
        if entry:
            # Redirigir conservando tutor/mascota para seguir cargando a la misma cuenta
            return redirect(url_for("day_detail", day_id=day.id, tutor=entry.tutor, mascota=entry.mascota))

    # --- Resúmenes existentes ---
    tot_pago = day.total_por_pago()
    tot_cat = day.total_por_categoria()

    # --- Agrupación por paciente (tutor + mascota) ---
    groups = (
        db.session.query(
            func.coalesce(Entry.tutor, ""),
            func.coalesce(Entry.mascota, ""),
            func.count(Entry.id),
            func.coalesce(func.sum(Entry.monto), 0),
        )
        .filter(Entry.day_id == day.id)
        .group_by(Entry.tutor, Entry.mascota)
        .all()
    )
    patient_groups = [
        {"tutor": t or "", "mascota": m or "", "count": int(c or 0), "total": int(s or 0)}
        for t, m, c, s in groups
    ]

    # --- Filtro opcional de una cuenta concreta (panel detallado) ---
    sel_tutor = (request.args.get("tutor") or "").strip()
    sel_mascota = (request.args.get("mascota") or "").strip()
    patient_entries = []
    patient_total = 0
    if sel_tutor or sel_mascota:
        q = Entry.query.filter_by(day_id=day.id)
        if sel_tutor:
            q = q.filter(func.coalesce(Entry.tutor, "") == sel_tutor)
        if sel_mascota:
            q = q.filter(func.coalesce(Entry.mascota, "") == sel_mascota)
        patient_entries = q.order_by(Entry.id.asc()).all()
        patient_total = sum(int(e.monto or 0) for e in patient_entries)

    return render_template(
        "day.html",
        day=day,
        form=form,
        tot_pago=tot_pago,
        tot_cat=tot_cat,
        patient_groups=patient_groups,
        sel_tutor=sel_tutor,
        sel_mascota=sel_mascota,
        patient_entries=patient_entries,
        patient_total=patient_total,
    )

@app.post("/day/<int:day_id>/close")
def day_close(day_id):
    day = Day.query.get_or_404(day_id)
    
    def close_day():
        # cierre de caja = apertura + total del día
        day.cierre_caja = (day.apertura_caja or 0) + day.total_dia()
        return day
    
    if safe_db_operation(close_day, "Cierre de caja calculado y guardado.", "Error al cerrar el día"):
        return redirect(url_for("day_close_confirm", day_id=day.id))
    else:
        return redirect(url_for("day_detail", day_id=day.id))

@app.get("/day/<int:day_id>/close/confirm")
def day_close_confirm(day_id):
    day = Day.query.get_or_404(day_id)
    return render_template("confirm_close.html", day=day)

@app.get("/day/<int:day_id>/report.pdf")
def day_report_pdf(day_id):
    day = Day.query.get_or_404(day_id)

    # Totales del día
    tot_pago = day.total_por_pago()
    tot_cat  = day.total_por_categoria()
    total_dia = day.total_dia()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Consulta Veterinaria Tin Tin — Resumen del día {day.fecha.strftime('%Y-%m-%d')}")
    y -= 22

    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Doctor/a: {day.doctor or '-'}"); y -= 16
    c.drawString(40, y, f"Apertura de caja: $ {(day.apertura_caja or 0):,}".replace(",", ".")); y -= 16
    c.drawString(40, y, f"Cierre de caja:   $ {(day.cierre_caja or 0):,}".replace(",", ".")); y -= 16
    c.drawString(40, y, f"Total del día:    $ {total_dia:,}".replace(",", ".")); y -= 24

    # Totales por tipo de pago
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Totales por tipo de pago"); y -= 18
    c.setFont("Helvetica", 11)
    def line(label, val):
        nonlocal y
        c.drawString(50, y, label)
        c.drawRightString(width-40, y, f"$ {int(val or 0):,}".replace(",", "."))
        y -= 16
    line("Débito/Crédito", tot_pago.get("DEBITO/CREDITO", 0))
    line("Efectivo",       tot_pago.get("EFECTIVO", 0))
    line("Transferencia",  tot_pago.get("TRANSFERENCIA", 0))
    y -= 10

    # Totales por categoría
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Totales por categoría"); y -= 18
    c.setFont("Helvetica", 11)
    for k, label in [
        ("ATENCION", "Atenciones"),
        ("PROCEDIMIENTO", "Procedimientos"),
        ("FARMACIA", "Farmacia/Petshop"),
        ("EXAMEN", "Exámenes"),
        ("PELUQUERIA", "Peluquería"),
    ]:
        line(label, tot_cat.get(k, 0))

    # Página nueva con tabla de movimientos (si hay)
    if day.entries:
        c.showPage()
        y = height - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Movimientos del día"); y -= 22
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, "Hora"); c.drawString(90, y, "Categoría")
        c.drawString(200, y, "Detalle"); c.drawString(420, y, "Pago")
        c.drawRightString(width-40, y, "Monto"); y -= 14
        c.setFont("Helvetica", 10)
        for e in day.entries:
            if y < 60:
                c.showPage(); y = height - 40
            hora = e.created_at.strftime('%H:%M') if e.created_at else "—"
            c.drawString(40, y, hora)
            c.drawString(90, y, e.categoria or "")
            c.drawString(200, y, (e.descripcion or "")[:40])
            c.drawString(420, y, e.tipo_pago or "")
            c.drawRightString(width-40, y, f"$ {int(e.monto or 0):,}".replace(",", "."))
            y -= 14

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    from flask import make_response
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f"inline; filename=Resumen_{day.fecha.strftime('%Y-%m-%d')}.pdf"
    return resp

@app.route("/day/<int:day_id>/edit", methods=["GET", "POST"])
def day_edit(day_id):
    day = Day.query.get_or_404(day_id)
    form = DayForm(obj=day)
    if form.validate_on_submit():
        def update_day():
            day.fecha = form.fecha.data
            day.doctor = form.doctor.data or ""
            day.apertura_caja = form.apertura_caja.data or 0
            day.cierre_caja = form.cierre_caja.data or 0
            return day
        
        if safe_db_operation(update_day, "Datos del día actualizados.", "Error al actualizar el día"):
            return redirect(url_for("day_detail", day_id=day.id))
    return render_template("day_edit.html", form=form, is_new=False, day=day)


# ====== LOGIN / LOGOUT ======
@app.route("/login", methods=["GET", "POST"])
def login():
    from forms import LoginForm
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        # Find user by username
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and user.check_password(password):
            # Store user info in session
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            session["logged_in"] = True  # Keep for backward compatibility
            flash("Bienvenido.", "success")
            return redirect(url_for("calendar_view"))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html", form=form)


@app.get("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))
# ============================


@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return redirect(url_for("calendar_view"))

@app.route("/calendar/report")
def calendar_report():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))
    stats = get_month_stats(year, month)
    month_name = pycal.month_name[month]
    return render_template(
        "report_month.html",
        year=year, month=month, month_name=month_name, **stats
    )

@app.route("/calendar/report.pdf")
def calendar_report_pdf():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))
    stats = get_month_stats(year, month)
    month_name = pycal.month_name[month]
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Resumen mensual - {month_name} {year}")
    y -= 24
    c.setFont("Helvetica", 11)
    def draw_line(label, value):
        nonlocal y
        c.drawString(40, y, f"{label}")
        c.drawRightString(width - 40, y, f"$ {int(value):,}".replace(",", "."))
        y -= 16
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Por tipo de pago"); y -= 18
    c.setFont("Helvetica", 11)
    draw_line("Débito/Crédito", stats["tot_por_pago"]["DEBITO/CREDITO"])
    draw_line("Efectivo",       stats["tot_por_pago"]["EFECTIVO"])
    draw_line("Transferencia",  stats["tot_por_pago"]["TRANSFERENCIA"])
    y -= 10
    c.setFont("Helvetica-Bold", 12); draw_line("TOTAL GENERAL", stats["total_general"]); y -= 8
    y -= 10
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Por categoría"); y -= 18
    c.setFont("Helvetica", 11)
    for k in ["ATENCION","PROCEDIMIENTO","FARMACIA","EXAMEN","PELUQUERIA"]:
        draw_line(k.title() if k!="FARMACIA" else "FARMACIA/PETSHOP", stats["tot_por_cat"][k])
    y -= 14
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Indicadores"); y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Días con movimiento: {stats['dias_con_mov']}"); y -= 16
    c.drawString(40, y, f"Transacciones: {stats['tx_count']}"); y -= 16
    c.drawString(40, y, f"Promedio diario: $ {stats['promedio_diario']:,}".replace(",", ".")); y -= 16
    c.drawString(40, y, f"Ticket promedio: $ {stats['ticket_promedio']:,}".replace(",", ".")); y -= 16
    if stats["peak_day"]:
        c.drawString(40, y, f"Pico: {stats['peak_day'].strftime('%Y-%m-%d')} — $ {stats['peak_total']:,}".replace(",", ".")); y -= 16
    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    from flask import make_response
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f"inline; filename=Resumen_{month_name}_{year}.pdf"
    return resp

@app.post("/entry/<int:entry_id>/delete", endpoint="entry_delete")
def delete_entry(entry_id):
    e = Entry.query.get_or_404(entry_id)
    day_id = e.day_id
    
    def delete_entry_op():
        db.session.delete(e)
        return True
    
    if safe_db_operation(delete_entry_op, "Registro eliminado.", "Error al eliminar el registro"):
        return redirect(url_for("day_detail", day_id=day_id))
    else:
        return redirect(url_for("day_detail", day_id=day_id))

@app.route("/catalog")
def catalog_list():
    q = (request.args.get("q") or "").strip()
    cat = (request.args.get("cat") or "").strip().upper()

    query = CatalogItem.query
    if cat:
        query = query.filter(CatalogItem.categoria == cat)
    if q:
        query = query.filter(CatalogItem.nombre.ilike(f"%{q}%"))

    items = query.order_by(CatalogItem.categoria.asc(), CatalogItem.nombre.asc()).all()

    return render_template(
        "catalog_list.html",
        items=items,
        q=q,
        cat=cat,
        CATEGORY_CHOICES=CATEGORY_CHOICES,
    )

@app.route("/catalog/new", methods=["GET", "POST"])
def catalog_new():
    form = CatalogItemForm()
    # asegurar choices en cada request
    form.categoria.choices = CATEGORY_CHOICES

    if form.validate_on_submit():
        exists = CatalogItem.query.filter(
            func.upper(CatalogItem.categoria) == form.categoria.data.upper(),
            func.upper(CatalogItem.nombre) == func.upper(form.nombre.data.strip())
        ).first()
        if exists:
            def update_existing():
                exists.precio = form.precio.data or 0
                return True
            
            if safe_db_operation(update_existing, "Servicio actualizado (ya existía).", "Error al actualizar el servicio existente"):
                return redirect(url_for("catalog_list"))
        else:
            def create_item():
                item = CatalogItem(
                    categoria=form.categoria.data,
                    nombre=form.nombre.data.strip(),
                    precio=form.precio.data or 0
                )
                db.session.add(item)
                return item
            
            if safe_db_operation(create_item, "Servicio creado.", "Error al crear el servicio"):
                return redirect(url_for("catalog_list"))

    # Si vino POST y falló validación, muestra motivos
    if request.method == "POST":
        flash_form_errors(form)
    return render_template("catalog_form.html", form=form, is_new=True)

@app.route("/catalog/<int:item_id>/edit", methods=["GET", "POST"])
def catalog_edit(item_id):
    item = CatalogItem.query.get_or_404(item_id)
    form = CatalogItemForm(obj=item)
    form.categoria.choices = CATEGORY_CHOICES

    if form.validate_on_submit():
        def update_catalog_item():
            item.categoria = form.categoria.data
            item.nombre = form.nombre.data.strip()
            item.precio = form.precio.data or 0
            return item
        
        if safe_db_operation(update_catalog_item, "Servicio actualizado.", "Error al actualizar el servicio"):
            return redirect(url_for("catalog_list"))

    if request.method == "POST":
        flash_form_errors(form)
    return render_template("catalog_form.html", form=form, is_new=False, item=item)

@app.post("/catalog/<int:item_id>/delete")
def catalog_delete(item_id):
    item = CatalogItem.query.get_or_404(item_id)
    
    def delete_catalog_item():
        db.session.delete(item)
        return True
    
    if safe_db_operation(delete_catalog_item, "Servicio eliminado.", "Error al eliminar el servicio"):
        return redirect(url_for("catalog_list"))
    else:
        return redirect(url_for("catalog_list"))

@app.get("/api/catalog")
def api_catalog():
    cat = request.args.get("categoria", "").upper()
    if not cat:
        return jsonify([])
    items = CatalogItem.query.filter_by(categoria=cat).order_by(CatalogItem.nombre.asc()).all()
    return jsonify([i.as_dict() for i in items])

@app.get("/day/<int:day_id>/patient.pdf")
def day_patient_pdf(day_id):
    tutor = (request.args.get("tutor") or "").strip()
    mascota = (request.args.get("mascota") or "").strip()
    day = Day.query.get_or_404(day_id)

    q = Entry.query.filter_by(day_id=day.id)
    if tutor:
        q = q.filter(func.coalesce(Entry.tutor, "") == tutor)
    if mascota:
        q = q.filter(func.coalesce(Entry.mascota, "") == mascota)
    items = q.order_by(Entry.id.asc()).all()

    total = sum(int(e.monto or 0) for e in items)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Consulta Veterinaria Tin Tin — Cuenta del Paciente"); y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Fecha: {day.fecha.strftime('%Y-%m-%d')}"); y -= 14
    c.drawString(40, y, f"Tutor/a: {tutor or '-'}"); y -= 14
    c.drawString(40, y, f"Mascota: {mascota or '-'}"); y -= 20

    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Detalle"); c.drawRightString(w-40, y, "Monto"); y -= 14
    c.setFont("Helvetica", 10)
    for e in items:
        if y < 60:
            c.showPage(); y = h - 40
        desc = e.descripcion or e.categoria or ""
        c.drawString(40, y, desc[:70])
        c.drawRightString(w-40, y, f"$ {int(e.monto or 0):,}".replace(",", "."))
        y -= 14

    y -= 8
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w-40, y, f"TOTAL: $ {int(total):,}".replace(",", "."))

    c.showPage(); c.save()
    pdf = buf.getvalue(); buf.close()

    from flask import make_response
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f"inline; filename=Cuenta_{day.fecha}.pdf"
    return resp

if __name__ == "__main__":
    app.run(debug=True)
