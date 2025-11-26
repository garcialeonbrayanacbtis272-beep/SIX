from flask import Flask, render_template, request, redirect, url_for, session, flash 
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, date
import re
import random
import traceback

app = Flask(__name__, template_folder='flask_mongo_crud_alumnos/templates')
app.secret_key = "clave_super_secreta_six"

# ------------------ CONEXIÓN A MONGODB ------------------
try:
    client = MongoClient("mongodb://localhost:27017/six")
    db = client["six"]
    usuarios = db["usuarios"]
    productos = db["productos"]
    pagos = db["pagos"]
    print("✅ Conexión a MongoDB exitosa")
except Exception as e:
    print(f"❌ Error conectando a MongoDB: {e}")

# ------------------ FUNCIONES AUXILIARES ------------------
def calcular_edad(fecha_nacimiento):
    """Calcula la edad basándose en la fecha de nacimiento"""
    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad

def es_producto_restringido(categoria):
    """Determina si un producto tiene restricción de edad"""
    categorias_restringidas = ['alcohol', 'cigarros', 'licor', 'cerveza', 'tabaco', 'vino']
    if categoria:
        return any(restr in categoria.lower() for restr in categorias_restringidas)
    return False

def verificar_edad_usuario(usuario):
    """Verifica si el usuario es mayor de edad"""
    user = usuarios.find_one({"usuario": usuario})
    if user and "fecha_nacimiento" in user:
        try:
            if isinstance(user["fecha_nacimiento"], str):
                fecha_nac = datetime.strptime(user["fecha_nacimiento"], "%Y-%m-%d").date()
            else:
                fecha_nac = user["fecha_nacimiento"].date() if hasattr(user["fecha_nacimiento"], 'date') else user["fecha_nacimiento"]
            return calcular_edad(fecha_nac) >= 18
        except Exception as e:
            print(f"Error verificando edad: {e}")
            return False
    return False

def generar_numero_orden():
    """Genera un número de orden único"""
    return f"SIX-{random.randint(100000, 999999)}"

# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    mensaje = ""
    if request.method == "POST":
        usuario = request.form["usuario"].strip()
        contrasena = request.form["contrasena"].strip()

        user = usuarios.find_one({"usuario": usuario})
        if user:
            if user["contrasena"] == contrasena:
                session["usuario"] = usuario
                session["carrito"] = []
                session["mayor_edad"] = verificar_edad_usuario(usuario)
                flash("✅ ¡Bienvenido a Six!")
                return redirect(url_for("inicio"))
            else:
                mensaje = "⚠️ Contraseña incorrecta"
        else:
            mensaje = "⚠️ Usuario no encontrado"

    return render_template("login.html", mensaje=mensaje)

# ---------------------------------------------------------
# RECUPERAR CONTRASEÑA
# ---------------------------------------------------------
@app.route("/recuperar-contrasena", methods=["GET", "POST"])
def recuperar_contrasena():
    mensaje = ""
    if request.method == "POST":
        usuario = request.form["usuario"].strip()
        user = usuarios.find_one({"usuario": usuario})
        
        if user:
            mensaje = "✅ Se ha enviado un enlace de recuperación a tu correo registrado"
        else:
            mensaje = "❌ Usuario no encontrado"
    
    return render_template("recuperar_contrasena.html", mensaje=mensaje)

# ---------------------------------------------------------
# REGISTRO CON VERIFICACIÓN DE EDAD
# ---------------------------------------------------------
@app.route("/registro", methods=["GET", "POST"])
def registro():
    mensaje = ""
    if request.method == "POST":
        usuario = request.form["usuario"].strip()
        contrasena = request.form["contrasena"].strip()
        confirmar = request.form["confirmar"].strip()
        fecha_nacimiento_str = request.form.get("fecha_nacimiento", "")
        verificacion_edad = request.form.get("verificacion_edad") == "on"
        terminos = request.form.get("terminos") == "on"

        # Validaciones
        if not all([usuario, contrasena, confirmar, fecha_nacimiento_str]):
            mensaje = "Por favor completa todos los campos obligatorios."
        elif contrasena != confirmar:
            mensaje = "Las contraseñas no coinciden."
        elif len(contrasena) < 6:
            mensaje = "La contraseña debe tener al menos 6 caracteres."
        elif usuarios.find_one({"usuario": usuario}):
            mensaje = "Este nombre de usuario ya existe."
        elif not verificacion_edad:
            mensaje = "Debes confirmar que eres mayor de 18 años."
        elif not terminos:
            mensaje = "Debes aceptar los términos y condiciones."
        else:
            try:
                # Convertir string a datetime para MongoDB
                fecha_nacimiento_dt = datetime.strptime(fecha_nacimiento_str, "%Y-%m-%d")
                # Calcular edad usando date
                fecha_nacimiento_date = fecha_nacimiento_dt.date()
                edad = calcular_edad(fecha_nacimiento_date)
                
                if edad < 18:
                    mensaje = "Debes ser mayor de 18 años para registrarte en Six."
                else:
                    # Guardar como string en MongoDB para evitar problemas de serialización
                    usuarios.insert_one({
                        "usuario": usuario,
                        "contrasena": contrasena,
                        "fecha_nacimiento": fecha_nacimiento_str,
                        "fecha_registro": datetime.now(),
                        "mayor_edad": True,
                        "edad_actual": edad
                    })
                    flash("✅ Registro exitoso. Ahora puedes iniciar sesión.")
                    return redirect(url_for("login"))
                    
            except ValueError as e:
                mensaje = f"Formato de fecha inválido: {str(e)}"

    return render_template("registro.html", mensaje=mensaje)

# ---------------------------------------------------------
# INICIO - LISTA DE PRODUCTOS
# ---------------------------------------------------------
@app.route("/inicio")
def inicio():
    if "usuario" not in session:
        return redirect(url_for("login"))

    try:
        productos_list = list(productos.find())
        return render_template("inicio.html", 
                             productos=productos_list, 
                             usuario=session["usuario"],
                             mayor_edad=session.get("mayor_edad", False))
    except Exception as e:
        print(f"Error en inicio: {e}")
        flash("❌ Error al cargar los productos")
        return redirect(url_for("login"))

# ---------------------------------------------------------
# BUSCADOR
# ---------------------------------------------------------
@app.route("/buscar")
def buscar():
    if "usuario" not in session:
        return redirect(url_for("login"))

    try:
        q = request.args.get("q", "").strip()

        productos_list = list(productos.find({
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"brand": {"$regex": q, "$options": "i"}},
                {"category": {"$regex": q, "$options": "i"}}
            ]
        }))

        if not productos_list:
            flash("No se encontraron productos para tu búsqueda.")

        return render_template("inicio.html",
                               productos=productos_list,
                               usuario=session["usuario"],
                               mayor_edad=session.get("mayor_edad", False),
                               busqueda=q)
    except Exception as e:
        print(f"Error en buscar: {e}")
        flash("❌ Error en la búsqueda")
        return redirect(url_for("inicio"))

# ---------------------------------------------------------
# FILTRO POR CATEGORÍA
# ---------------------------------------------------------
@app.route("/categoria/<category>")
def categoria(category):
    if "usuario" not in session:
        return redirect(url_for("login"))

    try:
        productos_list = list(productos.find({"category": category}))

        if not productos_list:
            flash("No hay productos en esta categoría aún.")

        return render_template("inicio.html",
                               productos=productos_list,
                               usuario=session["usuario"],
                               mayor_edad=session.get("mayor_edad", False),
                               categoria=category)
    except Exception as e:
        print(f"Error en categoría: {e}")
        flash("❌ Error al cargar la categoría")
        return redirect(url_for("inicio"))

# ---------------------------------------------------------
# DETALLE DE PRODUCTO
# ---------------------------------------------------------
@app.route("/producto/<producto_id>")
def producto_detalle(producto_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    try:
        producto = productos.find_one({"_id": ObjectId(producto_id)})
        if not producto:
            flash("❌ Producto no encontrado")
            return redirect(url_for("inicio"))
            
        restringido = es_producto_restringido(producto.get("category", ""))
        
        return render_template("producto.html", 
                             producto=producto, 
                             usuario=session["usuario"],
                             mayor_edad=session.get("mayor_edad", False),
                             restringido=restringido)
    except Exception as e:
        print(f"Error en producto_detalle: {e}")
        flash("❌ Error al cargar el producto")
        return redirect(url_for("inicio"))

# ---------------------------------------------------------
# AGREGAR AL CARRITO CON VERIFICACIÓN DE EDAD
# ---------------------------------------------------------
@app.route("/agregar_carrito/<producto_id>", methods=["POST"])
def agregar_carrito(producto_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    try:
        producto = productos.find_one({"_id": ObjectId(producto_id)})
        if not producto:
            flash("❌ Producto no encontrado")
            return redirect(url_for("inicio"))
        
        # Verificar restricción de edad
        if es_producto_restringido(producto.get("category", "")) and not session.get("mayor_edad", False):
            flash("❌ Debes ser mayor de 18 años para comprar este producto.")
            return redirect(url_for("producto_detalle", producto_id=producto_id))

        carrito = session.get("carrito", [])

        # Buscar si el producto ya está en el carrito
        encontrado = False
        for item in carrito:
            if item["_id"] == str(producto["_id"]):
                item["cantidad"] += 1
                encontrado = True
                break
        
        # Si no está, agregarlo
        if not encontrado:
            carrito.append({
                "_id": str(producto["_id"]),
                "name": producto["name"],
                "price": float(producto["price"]),
                "img": producto.get("img", "https://via.placeholder.com/120"),
                "category": producto.get("category", ""),
                "cantidad": 1
            })

        session["carrito"] = carrito
        session.modified = True
        flash(f"✅ {producto['name']} agregado al carrito")
        return redirect(url_for("carrito"))
        
    except Exception as e:
        print(f"Error en agregar_carrito: {e}")
        flash("❌ Error al agregar producto al carrito")
        return redirect(url_for("inicio"))

# ---------------------------------------------------------
# CARRITO
# ---------------------------------------------------------
@app.route("/carrito")
def carrito():
    if "usuario" not in session:
        return redirect(url_for("login"))
        
    try:
        carrito = session.get("carrito", [])
        total = sum(item["price"] * item["cantidad"] for item in carrito)
        
        # Verificar productos restringidos en el carrito
        productos_restringidos = any(
            es_producto_restringido(item.get("category", "")) 
            for item in carrito
        )
        
        return render_template("carrito.html", 
                             carrito=carrito, 
                             total=total, 
                             usuario=session.get("usuario"),
                             mayor_edad=session.get("mayor_edad", False),
                             productos_restringidos=productos_restringidos)
    except Exception as e:
        print(f"Error en carrito: {e}")
        flash("❌ Error al cargar el carrito")
        return redirect(url_for("inicio"))

# ---------------------------------------------------------
# ACTUALIZAR CANTIDAD DEL CARRITO
# ---------------------------------------------------------
@app.route("/actualizar_cantidad/<producto_id>", methods=["POST"])
def actualizar_cantidad(producto_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    try:
        nueva_cantidad = int(request.form["cantidad"])
        carrito = session.get("carrito", [])

        for item in carrito:
            if item["_id"] == producto_id:
                item["cantidad"] = max(1, nueva_cantidad)
                break

        session["carrito"] = carrito
        session.modified = True
        return redirect(url_for("carrito"))
    except Exception as e:
        print(f"Error en actualizar_cantidad: {e}")
        flash("❌ Error al actualizar cantidad")
        return redirect(url_for("carrito"))

# ---------------------------------------------------------
# ELIMINAR PRODUCTO DEL CARRITO
# ---------------------------------------------------------
@app.route("/eliminar_carrito/<producto_id>", methods=["POST"])
def eliminar_carrito(producto_id):
    if "usuario" not in session:
        return redirect(url_for("login"))
        
    try:
        carrito = session.get("carrito", [])
        carrito = [item for item in carrito if item["_id"] != producto_id]
        session["carrito"] = carrito
        session.modified = True
        flash("✅ Producto eliminado del carrito")
        return redirect(url_for("carrito"))
    except Exception as e:
        print(f"Error en eliminar_carrito: {e}")
        flash("❌ Error al eliminar producto")
        return redirect(url_for("carrito"))

# ---------------------------------------------------------
# VACIAR CARRITO
# ---------------------------------------------------------
@app.route("/vaciar_carrito", methods=["POST"])
def vaciar_carrito():
    if "usuario" not in session:
        return redirect(url_for("login"))
        
    try:
        session["carrito"] = []
        session.modified = True
        flash("✅ Carrito vaciado")
        return redirect(url_for("carrito"))
    except Exception as e:
        print(f"Error en vaciar_carrito: {e}")
        flash("❌ Error al vaciar carrito")
        return redirect(url_for("carrito"))

# ---------------------------------------------------------
# PAGO CON VERIFICACIÓN FINAL - VERSIÓN CORREGIDA
# ---------------------------------------------------------
@app.route("/pago", methods=["GET", "POST"])
def pago():
    print("🔍 Entrando a la ruta /pago")
    
    if "usuario" not in session:
        print("❌ Usuario no en sesión")
        return redirect(url_for("login"))

    carrito = session.get("carrito", [])
    print(f"🛒 Carrito tiene {len(carrito)} productos")
    
    if not carrito:
        print("❌ Carrito vacío")
        flash("❌ Tu carrito está vacío")
        return redirect(url_for("inicio"))
        
    total = sum(item["price"] * item["cantidad"] for item in carrito)
    print(f"💰 Total: {total}")

    # Verificación final de productos restringidos
    productos_restringidos = [
        item for item in carrito 
        if es_producto_restringido(item.get("category", ""))
    ]
    
    if productos_restringidos and not session.get("mayor_edad", False):
        print("❌ Productos restringidos sin verificación de edad")
        flash("❌ No puedes comprar productos restringidos sin verificar tu edad")
        return redirect(url_for("carrito"))

    if request.method == "POST":
        print("📝 Procesando formulario POST")
        
        try:
            nombre = request.form.get("nombre", "").strip()
            tarjeta = request.form.get("tarjeta", "").strip()
            cvv = request.form.get("cvv", "").strip()
            fecha = request.form.get("fecha", "").strip()

            print(f"📋 Datos recibidos - Nombre: {nombre}, Tarjeta: {tarjeta}, CVV: {cvv}, Fecha: {fecha}")

            # Validaciones
            if not all([nombre, tarjeta, cvv, fecha]):
                flash("❌ Por favor completa todos los campos")
                print("❌ Campos incompletos")
                return redirect(url_for("pago"))
            
            # Limpiar número de tarjeta (quitar espacios)
            tarjeta_limpia = re.sub(r'\s+', '', tarjeta)
            
            if not re.match(r'^\d{13,19}$', tarjeta_limpia):
                flash("❌ Número de tarjeta inválido (debe tener entre 13 y 19 dígitos)")
                print("❌ Tarjeta inválida")
                return redirect(url_for("pago"))
                
            if not re.match(r'^\d{3,4}$', cvv):
                flash("❌ CVV inválido (debe tener 3 o 4 dígitos)")
                print("❌ CVV inválido")
                return redirect(url_for("pago"))

            # Validar formato de fecha (MM/AA)
            if not re.match(r'^(0[1-9]|1[0-2])\/[0-9]{2}$', fecha):
                flash("❌ Formato de fecha inválido. Usa MM/AA (ej: 12/25)")
                print("❌ Fecha inválida")
                return redirect(url_for("pago"))

            # Validar que la fecha no esté expirada
            try:
                mes, anio = fecha.split('/')
                mes_int = int(mes)
                anio_int = int(anio)
                current_year = datetime.now().year % 100
                current_month = datetime.now().month
                
                if anio_int < current_year or (anio_int == current_year and mes_int < current_month):
                    flash("❌ La tarjeta está expirada")
                    print("❌ Tarjeta expirada")
                    return redirect(url_for("pago"))
            except ValueError:
                flash("❌ Formato de fecha inválido")
                return redirect(url_for("pago"))

            # Generar número de orden
            numero_orden = generar_numero_orden()
            print(f"📦 Número de orden generado: {numero_orden}")

            # Guardar en la base de datos
            pago_data = {
                "usuario": session["usuario"],
                "carrito": carrito,
                "total": total,
                "nombre_tarjeta": nombre,
                "numero_tarjeta": tarjeta_limpia[-4:],  # Solo guardar últimos 4 dígitos
                "fecha_exp": fecha,
                "fecha_compra": datetime.now(),
                "productos_restringidos": len(productos_restringidos) > 0,
                "numero_orden": numero_orden
            }
            
            resultado = pagos.insert_one(pago_data)
            print(f"💾 Pago guardado en BD con ID: {resultado.inserted_id}")

            # Limpiar carrito
            session["carrito"] = []
            session.modified = True
            print("🛒 Carrito limpiado")

            # Redirigir a página de éxito
            print("✅ Redirigiendo a pago_exitoso")
            return render_template("pago_exitoso.html", 
                                 total=total, 
                                 usuario=session["usuario"],
                                 numero_orden=numero_orden)
                                 
        except Exception as e:
            print(f"💥 Error en procesamiento de pago: {str(e)}")
            print(traceback.format_exc())
            flash("❌ Error al procesar el pago. Intenta nuevamente.")
            return redirect(url_for("pago"))

    # GET request - mostrar formulario de pago
    print("📄 Mostrando formulario de pago (GET)")
    return render_template("pago.html", 
                         carrito=carrito, 
                         total=total,
                         productos_restringidos=len(productos_restringidos) > 0)

# ---------------------------------------------------------
# PAGO EXITOSO
# ---------------------------------------------------------
@app.route("/pago_exitoso")
def pago_exitoso():
    print("🔍 Entrando a pago_exitoso")
    if "usuario" not in session:
        return redirect(url_for("login"))
    
    try:
        # Obtener la última compra del usuario
        ultima_compra = pagos.find_one(
            {"usuario": session["usuario"]},
            sort=[("fecha_compra", -1)]
        )
        
        if not ultima_compra:
            flash("❌ No se encontró información de pago reciente")
            return redirect(url_for("inicio"))
        
        return render_template("pago_exitoso.html",
                             total=ultima_compra["total"],
                             usuario=session["usuario"],
                             numero_orden=ultima_compra.get("numero_orden", generar_numero_orden()))
    except Exception as e:
        print(f"Error en pago_exitoso: {e}")
        flash("❌ Error al cargar la confirmación de pago")
        return redirect(url_for("inicio"))

# ---------------------------------------------------------
# HISTORIAL DE COMPRAS
# ---------------------------------------------------------
@app.route("/historial")
def historial():
    if "usuario" not in session:
        return redirect(url_for("login"))
        
    try:
        compras = list(pagos.find({"usuario": session["usuario"]}).sort("fecha_compra", -1))
        return render_template("historial.html", 
                             compras=compras, 
                             usuario=session["usuario"])
    except Exception as e:
        print(f"Error en historial: {e}")
        flash("❌ Error al cargar el historial")
        return redirect(url_for("inicio"))

# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Sesión cerrada correctamente")
    return redirect(url_for("login"))

# ---------------------------------------------------------
# MANEJO DE ERRORES
# ---------------------------------------------------------
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
