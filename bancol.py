import firebase_admin
from firebase_admin import credentials, firestore, auth
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime

# ========= CONFIG =========
TOKEN = "8675613049:AAGRozfMcApMqv07vcb87t80DVz61FIcxXM"
SUPREMO_ID = 8116120039

cred = credentials.Certificate("bancolombia-6064d-firebase-adminsdk-fbsvc-01630197c4.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# ========= PERMISOS =========

def is_supremo(user_id):
    return user_id == SUPREMO_ID

def is_seller(user_id):
    doc = db.collection("sellers").document(str(user_id)).get()
    return doc.exists

# ========= UTIL =========

async def notificar_supremo(context, update, accion):
    user = update.effective_user

    username = f"@{user.username}" if user.username else user.first_name

    mensaje = f"""
╔═══👑 𝗔𝗖𝗧𝗜𝗩𝗜𝗗𝗔𝗗 𝗦𝗘𝗟𝗟𝗘𝗥 👑═══╗

🧑‍💼 Vendedor: {username}
🆔 ID: {user.id}

📌 Acción realizada:
{accion}

⏰ {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

╚═══════════════════════════╝
"""

    await context.bot.send_message(SUPREMO_ID, mensaje)

# ========= START =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👑 Bienvenido al sistema Ultra\n\nUsa /help para ver el panel."
    )

# ========= HELP PANEL =========

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_supremo(user_id):
        mensaje = """
╔═══👑 PANEL SUPREMO 👑═══╗

🛡 Gestión de Sellers
/addseller ID
/delseller ID

👤 Gestión de Usuarios
/crear email clave saldo
/addsaldo email cantidad
/ban email
/unban email
/lista

╚════════════════════════╝
"""
    elif is_seller(user_id):
        mensaje = """
╔═══💼 PANEL SELLER 💼═══╗

/crear email clave saldo
/addsaldo email cantidad

╚═══════════════════════╝
"""
    else:
        mensaje = "❌ No tienes permisos."

    await update.message.reply_text(mensaje)

# ========= ADD SELLER =========

async def addseller(update, context):
    if not is_supremo(update.effective_user.id):
        return

    seller_id = context.args[0]

    db.collection("sellers").document(seller_id).set({
        "activo": True,
        "fecha": datetime.utcnow()
    })

    await update.message.reply_text(f"✅ Seller {seller_id} agregado.")

# ========= DEL SELLER =========

async def delseller(update, context):
    if not is_supremo(update.effective_user.id):
        return

    seller_id = context.args[0]
    db.collection("sellers").document(seller_id).delete()

    await update.message.reply_text(f"🗑️ Seller {seller_id} eliminado.")

# ========= CREAR USUARIO =========

async def crear(update, context):
    user_id = update.effective_user.id

    if not (is_supremo(user_id) or is_seller(user_id)):
        return

    email = context.args[0]
    clave = context.args[1]
    saldo = context.args[2]

    try:
        user = auth.create_user(email=email, password=clave)
        uid = user.uid

        db.collection("users").document(uid).set({
            "Saldo": str(saldo),
            "banned": False
        })

        await update.message.reply_text(
            f"""✅ Usuario registrado con éxito

📱 User: {email.split("@")[0]}
🔒 PIN: {clave[:4]}
💰 Saldo: {saldo}

🎯 Usuario activado y listo."""
        )

        if is_seller(user_id):
            await notificar_supremo(
                context,
                update,
                f"Creó usuario {email} con saldo {saldo}"
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ========= ADD SALDO =========

async def addsaldo(update, context):
    user_id = update.effective_user.id

    if not (is_supremo(user_id) or is_seller(user_id)):
        return

    email = context.args[0]
    agregar = int(context.args[1])

    try:
        user = auth.get_user_by_email(email)
        uid = user.uid

        doc_ref = db.collection("users").document(uid)
        doc = doc_ref.get()

        if not doc.exists:
            await update.message.reply_text("❌ Documento no existe.")
            return

        saldo_actual = int(doc.to_dict()["Saldo"])
        nuevo_saldo = saldo_actual + agregar

        doc_ref.update({
            "Saldo": str(nuevo_saldo)
        })

        await update.message.reply_text(
            f"""✅ Recarga exitosa

💰 Saldo agregado: {agregar}
🏦 Saldo total: {nuevo_saldo}"""
        )

        if is_seller(user_id):
            await notificar_supremo(
                context,
                update,
                f"Recargó {agregar} a {email}"
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ========= BAN =========

async def ban(update, context):
    if not is_supremo(update.effective_user.id):
        return

    email = context.args[0]
    user = auth.get_user_by_email(email)
    uid = user.uid

    db.collection("users").document(uid).update({
        "banned": True
    })

    await update.message.reply_text("🚫 Usuario baneado.")

# ========= UNBAN =========

async def unban(update, context):
    if not is_supremo(update.effective_user.id):
        return

    email = context.args[0]
    user = auth.get_user_by_email(email)
    uid = user.uid

    db.collection("users").document(uid).update({
        "banned": False
    })

    await update.message.reply_text("✅ Usuario desbaneado.")

# ========= LISTA =========

async def lista(update, context):
    if not is_supremo(update.effective_user.id):
        await update.message.reply_text("❌ Solo el supremo puede usar esto.")
        return

    usuarios = db.collection("users").stream()

    mensaje = "📋 LISTA DE USUARIOS\n\n"

    for user_doc in usuarios:
        uid = user_doc.id
        data = user_doc.to_dict()

        saldo = data.get("Saldo", "0")
        banned = data.get("banned", False)

        try:
            user_auth = auth.get_user(uid)
            email = user_auth.email
        except:
            email = "No encontrado"

        mensaje += (
            f"📧 {email}\n"
            f"🆔 {uid}\n"
            f"💰 {saldo}\n"
            f"🚫 {banned}\n\n"
        )

    await update.message.reply_text(mensaje)

# ========= MAIN =========

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("addseller", addseller))
app.add_handler(CommandHandler("delseller", delseller))
app.add_handler(CommandHandler("crear", crear))
app.add_handler(CommandHandler("addsaldo", addsaldo))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CommandHandler("lista", lista))

print("👑 BOT ULTRA ACTIVO...")
app.run_polling()
