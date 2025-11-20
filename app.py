from flask import Flask, render_template, request, redirect, url_for, session, flash 
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, date
import re

app = Flask(__name__, template_folder='flask_mongo_crud_alumnos/templates')
app.secret_key = "clave_super_secreta_six"

# ------------------ CONEXIÓN A MONGODB ------------------
client = MongoClient("mongodb+srv://garcialeonbrayanacbtis272_db_user:0hcpySZAsjYw3tLD@six.p5epooe.mongodb.net/six")
db = client["six"]
usuarios = db["usuarios"]
productos = db["productos"]
pagos = db["pagos"]

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
    categorias_restringidas = ['alcohol', 'cigarros']
    return categoria in categorias_restringidas

def verificar_edad_usuario(usuario):
    """Verifica si el usuario es mayor de edad"""
    user = usuarios.find_one({"usuario": usuario})
    if user and "fecha_nacimiento" in user:
        # Convertir string de fecha guardada a datetime para cálculo
        if isinstance(user["fecha_nacimiento"], str):
            fecha_nac = datetime.strptime(user["fecha_nacimiento"], "%Y-%m-%d").date()
        else:
            # Si ya es datetime, convertir a date
            fecha_nac = user["fecha_nacimiento"].date() if hasattr(user["fecha_nacimiento"], 'date') else user["fecha_nacimiento"]
        return calcular_edad(fecha_nac) >= 18
    return False

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
# REGISTRO CON VERIFICACIÓN DE EDAD - CORREGIDO
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
                        "fecha_nacimiento": fecha_nacimiento_str,  # Guardar como string
                        "fecha_registro": datetime.now(),
                        "mayor_edad": True,
                        "edad_actual": edad  # Guardar la edad calculada
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

    productos_list = list(productos.find())
    return render_template("inicio.html", 
                         productos=productos_list, 
                         usuario=session["usuario"],
                         mayor_edad=session.get("mayor_edad", False))

# ---------------------------------------------------------
# BUSCADOR
# ---------------------------------------------------------
@app.route("/buscar")
def buscar():
    if "usuario" not in session:
        return redirect(url_for("login"))

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

# ---------------------------------------------------------
# FILTRO POR CATEGORÍA
# ---------------------------------------------------------
@app.route("/categoria/<category>")
def categoria(category):
    if "usuario" not in session:
        return redirect(url_for("login"))

    productos_list = list(productos.find({"category": category}))

    if not productos_list:
        flash("No hay productos en esta categoría aún.")

    return render_template("inicio.html",
                           productos=productos_list,
                           usuario=session["usuario"],
                           mayor_edad=session.get("mayor_edad", False),
                           categoria=category)

# ---------------------------------------------------------
# DETALLE DE PRODUCTO
# ---------------------------------------------------------
@app.route("/producto/<producto_id>")
def producto_detalle(producto_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    producto = productos.find_one({"_id": ObjectId(producto_id)})
    restringido = es_producto_restringido(producto.get("category", ""))
    
    return render_template("producto.html", 
                         producto=producto, 
                         usuario=session["usuario"],
                         mayor_edad=session.get("mayor_edad", False),
                         restringido=restringido)

# ---------------------------------------------------------
# AGREGAR AL CARRITO CON VERIFICACIÓN DE EDAD
# ---------------------------------------------------------
@app.route("/agregar_carrito/<producto_id>", methods=["POST"])
def agregar_carrito(producto_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    producto = productos.find_one({"_id": ObjectId(producto_id)})
    
    # Verificar restricción de edad
    if es_producto_restringido(producto.get("category", "")) and not session.get("mayor_edad", False):
        flash("❌ Debes ser mayor de 18 años para comprar este producto.")
        return redirect(url_for("producto_detalle", producto_id=producto_id))

    carrito = session.get("carrito", [])

    for item in carrito:
        if item["_id"] == str(producto["_id"]):
            item["cantidad"] += 1
            break
    else:
        carrito.append({
            "_id": str(producto["_id"]),
            "name": producto["name"],
            "price": producto["price"],
            "img": producto.get("img", ""),
            "category": producto.get("category", ""),
            "cantidad": 1
        })

    session["carrito"] = carrito
    flash(f"✅ {producto['name']} agregado al carrito")
    return redirect(url_for("carrito"))

# ---------------------------------------------------------
# CARRITO
# ---------------------------------------------------------
@app.route("/carrito")
def carrito():
    if "usuario" not in session:
        return redirect(url_for("login"))
        
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

# ---------------------------------------------------------
# ACTUALIZAR CANTIDAD DEL CARRITO
# ---------------------------------------------------------
@app.route("/actualizar_cantidad/<producto_id>", methods=["POST"])
def actualizar_cantidad(producto_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    nueva_cantidad = int(request.form["cantidad"])
    carrito = session.get("carrito", [])

    for item in carrito:
        if item["_id"] == producto_id:
            item["cantidad"] = max(1, nueva_cantidad)
            break

    session["carrito"] = carrito
    return redirect(url_for("carrito"))

# ---------------------------------------------------------
# ELIMINAR PRODUCTO DEL CARRITO
# ---------------------------------------------------------
@app.route("/eliminar_carrito/<producto_id>", methods=["POST"])
def eliminar_carrito(producto_id):
    if "usuario" not in session:
        return redirect(url_for("login"))
        
    carrito = session.get("carrito", [])
    carrito = [item for item in carrito if item["_id"] != producto_id]
    session["carrito"] = carrito
    flash("✅ Producto eliminado del carrito")
    return redirect(url_for("carrito"))

# ---------------------------------------------------------
# VACIAR CARRITO
# ---------------------------------------------------------
@app.route("/vaciar_carrito", methods=["POST"])
def vaciar_carrito():
    if "usuario" not in session:
        return redirect(url_for("login"))
        
    session["carrito"] = []
    flash("✅ Carrito vaciado")
    return redirect(url_for("carrito"))

# ---------------------------------------------------------
# PAGO CON VERIFICACIÓN FINAL
# ---------------------------------------------------------
@app.route("/pago", methods=["GET", "POST"])
def pago():
    if "usuario" not in session:
        return redirect(url_for("login"))

    carrito = session.get("carrito", [])
    
    if not carrito:
        flash("❌ Tu carrito está vacío")
        return redirect(url_for("inicio"))
        
    total = sum(item["price"] * item["cantidad"] for item in carrito)

    # Verificación final de productos restringidos
    productos_restringidos = [
        item for item in carrito 
        if es_producto_restringido(item.get("category", ""))
    ]
    
    if productos_restringidos and not session.get("mayor_edad", False):
        flash("❌ No puedes comprar productos restringidos sin verificar tu edad")
        return redirect(url_for("carrito"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        tarjeta = request.form["tarjeta"]
        cvv = request.form["cvv"]
        fecha = request.form["fecha"]

        # Validación básica de tarjeta
        if not re.match(r'^\d{16}$', tarjeta.replace(" ", "")):
            flash("❌ Número de tarjeta inválido")
            return redirect(url_for("pago"))
            
        if not re.match(r'^\d{3,4}$', cvv):
            flash("❌ CVV inválido")
            return redirect(url_for("pago"))

        pagos.insert_one({
            "usuario": session["usuario"],
            "carrito": carrito,
            "total": total,
            "nombre_tarjeta": nombre,
            "numero_tarjeta": tarjeta,
            "cvv": cvv,
            "fecha_exp": fecha,
            "fecha_compra": datetime.now(),
            "productos_restringidos": len(productos_restringidos) > 0
        })

        session["carrito"] = []
        session["compra_realizada"] = True

        return render_template("pago_exitoso.html", 
                             total=total, 
                             usuario=session["usuario"])

    return render_template("pago.html", 
                         carrito=carrito, 
                         total=total,
                         productos_restringidos=len(productos_restringidos) > 0)

# ---------------------------------------------------------
# HISTORIAL DE COMPRAS
# ---------------------------------------------------------
@app.route("/historial")
def historial():
    if "usuario" not in session:
        return redirect(url_for("login"))
        
    compras = list(pagos.find({"usuario": session["usuario"]}).sort("fecha_compra", -1))
    return render_template("historial.html", 
                         compras=compras, 
                         usuario=session["usuario"])

# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Sesión cerrada correctamente")
    return redirect(url_for("login"))

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
