# ============================================================
#   SHOPBOT BÁN TOKEN DISCORD — 2 LOẠI: NGÂM + KHÔNG NGÂM
#   Chỉ sửa 2 dòng: BOT_TOKEN + ADMIN_ID
# ============================================================

import os
import sqlite3
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ⚙️ SỬA 2 DÒNG DƯỚI
BOT_TOKEN = "8967910142:AAGwqNC9wXGOThSZG2aU7k8Flm6tsBgFVpI"
ADMIN_ID = 8336161180
# 💳 Thanh toán — chọn 1 trong 2:
QR_IMAGE = ""       # Cách A: ảnh QR tĩnh (đặt file cùng thư mục)
BANK_ID = "MB"               # Cách B: VD "MB", "VCB", "TPB"
BANK_ACCOUNT = "0333651484"          # Số tài khoản
BANK_OWNER = "Luong Duc Anh"            # Tên không dấu

# 🎮 CẤU HÌNH 2 SẢN PHẨM
PRODUCTS = [
    {
        "name": "Token Discord Ngâm",
        "price": 1100,
        "desc": (
            "🎮 **Token Discord — Acc Ngâm**\n\n"
            "✅ Acc tạo lâu (trên 1 tháng)\n"
            "✅ Có lịch sử hoạt động\n"
            "✅ Full quyền, không bị flag\n"
            "✅ Giao ngay sau thanh toán\n"
            "✅ Bảo hành 24h\n\n"
            "💰 **Giá: 1.100đ / token**\n\n"
            "⚠️ Đổi mật khẩu ngay sau khi nhận"
        ),
    },
    {
        "name": "Token Discord Không Ngâm",
        "price": 8000,
        "desc": (
            "🎮 **Token Discord — Acc Không Ngâm**\n\n"
            "✅ Acc mới tạo\n"
            "✅ Full quyền cơ bản\n"
            "✅ Giao ngay sau thanh toán\n"
            "✅ Bảo hành 12h\n\n"
            "💰 **Giá: 800đ / token**\n\n"
            "⚠️ Đổi mật khẩu ngay sau khi nhận\n"
            "⚠️ Giá rẻ — phù hợp test"
        ),
    },
]

DB = "products.db"
STOCK_DIR = "stock"


# ============================================================
#   DATABASE
# ============================================================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER,
        stock INTEGER DEFAULT 0, description TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        product_id INTEGER, quantity INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, total INTEGER,
        status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER,
        product_id INTEGER, product_name TEXT, price INTEGER, quantity INTEGER)""")
    conn.commit()
    conn.close()


def get_all_products():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products WHERE stock > 0")
    r = c.fetchall()
    conn.close()
    return r


def get_product(pid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock, description FROM products WHERE id=?", (pid,))
    r = c.fetchone()
    conn.close()
    return r


def get_product_by_name(name):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, stock FROM products WHERE name=?", (name,))
    r = c.fetchone()
    conn.close()
    return r


def add_product(name, price, stock, desc=""):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, stock, description) VALUES (?,?,?,?)",
              (name, price, stock, desc))
    conn.commit()
    conn.close()


def add_to_cart(uid, pid, qty=1):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, quantity FROM cart WHERE user_id=? AND product_id=?", (uid, pid))
    row = c.fetchone()
    if row:
        c.execute("UPDATE cart SET quantity=quantity+? WHERE id=?", (qty, row[0]))
    else:
        c.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?,?,?)", (uid, pid, qty))
    conn.commit()
    conn.close()


def get_cart(uid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT c.id, p.id, p.name, p.price, c.quantity
                 FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id=?""", (uid,))
    r = c.fetchall()
    conn.close()
    return r


def clear_cart(uid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM cart WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()


def remove_from_cart(cid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM cart WHERE id=?", (cid,))
    conn.commit()
    conn.close()


def create_order(uid, items):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    total = sum(price * qty for _, _, _, price, qty in items)
    c.execute("INSERT INTO orders (user_id, total) VALUES (?,?)", (uid, total))
    oid = c.lastrowid
    for _, pid, name, price, qty in items:
        c.execute("""INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
                     VALUES (?,?,?,?,?)""", (oid, pid, name, price, qty))
        c.execute("UPDATE products SET stock = stock - ? WHERE id=?", (qty, pid))
    conn.commit()
    conn.close()
    return oid, total


def get_order(oid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, user_id, total, status FROM orders WHERE id=?", (oid,))
    order = c.fetchone()
    c.execute("SELECT product_name, price, quantity FROM order_items WHERE order_id=?", (oid,))
    items = c.fetchall()
    conn.close()
    return order, items


def get_user_orders(uid, limit=10):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, total, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?",
              (uid, limit))
    r = c.fetchall()
    conn.close()
    return r


def get_stock_file(name):
    safe = name.replace(' ', '_')
    return os.path.join(STOCK_DIR, f"{safe}.txt")


def count_stock(name):
    p = get_stock_file(name)
    if not os.path.exists(p):
        return 0
    with open(p, 'r', encoding='utf-8') as f:
        return sum(1 for l in f if l.strip())


def pop_stock(name):
    p = get_stock_file(name)
    if not os.path.exists(p):
        return None
    with open(p, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        return None
    item = lines[0]
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines[1:]))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE products SET stock=? WHERE name=?", (len(lines) - 1, name))
    conn.commit()
    conn.close()
    return item


def add_stock(name, items):
    p = get_stock_file(name)
    os.makedirs(STOCK_DIR, exist_ok=True)
    with open(p, 'a', encoding='utf-8') as f:
        for it in items:
            if it.strip():
                f.write(it.strip() + '\n')
    total = count_stock(name)
    prod = get_product_by_name(name)
    if prod:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE products SET stock=? WHERE name=?", (total, name))
        conn.commit()
        conn.close()
    return total


def sync_stock(name):
    total = count_stock(name)
    prod = get_product_by_name(name)
    if prod:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE products SET stock=? WHERE id=?", (total, prod[0]))
        conn.commit()
        conn.close()
    return total


# ============================================================
#   THANH TOÁN
# ============================================================
def make_vietqr(oid, amount):
    if not (BANK_ID and BANK_ACCOUNT):
        return None
    try:
        import requests
        url = (f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT}-compact2.png"
               f"?amount={amount}&addInfo=DH{oid}&accountName={BANK_OWNER}")
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return BytesIO(r.content)
    except Exception as e:
        print(f"VietQR: {e}")
    return None


def get_static_qr():
    if QR_IMAGE and os.path.exists(QR_IMAGE):
        return QR_IMAGE
    return None


# ============================================================
#   SETUP 2 SẢN PHẨM
# ============================================================
def setup_products():
    for p in PRODUCTS:
        name = p["name"]
        price = p["price"]
        desc = p["desc"]
        stock = count_stock(name)
        prod = get_product_by_name(name)

        if not prod:
            add_product(name, price, stock, desc)
            print(f"✅ Tạo '{name}' | Tồn: {stock} | Giá: {price:,}đ")
        else:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("UPDATE products SET price=?, description=? WHERE name=?",
                      (price, desc, name))
            conn.commit()
            conn.close()
            sync_stock(name)
            print(f"🔄 Cập nhật '{name}' | Tồn: {stock} | Giá: {price:,}đ")


# ============================================================
#   MENU
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🛍️ Mua Token", callback_data="shop")],
        [InlineKeyboardButton("🛒 Giỏ hàng", callback_data="cart"),
         InlineKeyboardButton("📦 Đơn của tôi", callback_data="my_orders")],
        [InlineKeyboardButton("📞 Liên hệ", callback_data="contact")],
    ]
    price_text = ""
    for p in PRODUCTS:
        price_text += f"• {p['name']}: **{p['price']:,}đ**\n"

    await update.message.reply_text(
        f"👋 Chào **{update.effective_user.first_name}**!\n\n"
        f"🎮 **Token Discord**\n\n{price_text}\n"
        "Chọn chức năng:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )


async def back_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("🛍️ Mua Token", callback_data="shop")],
        [InlineKeyboardButton("🛒 Giỏ hàng", callback_data="cart"),
         InlineKeyboardButton("📦 Đơn của tôi", callback_data="my_orders")],
        [InlineKeyboardButton("📞 Liên hệ", callback_data="contact")],
    ]
    price_text = ""
    for p in PRODUCTS:
        price_text += f"• {p['name']}: **{p['price']:,}đ**\n"
    await q.edit_message_text(
        f"🏠 **Menu**\n\n{price_text}",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )


async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    products = get_all_products()
    if not products:
        await q.edit_message_text("📭 Hết hàng.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]))
        return
    kb = []
    for pid, name, price, stock in products:
        kb.append([InlineKeyboardButton(f"{name} — {price:,}đ (còn {stock})", callback_data=f"prod_{pid}")])
    kb.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back")])
    await q.edit_message_text("🛍️ **Sản phẩm:**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pid = int(q.data.split("_")[1])
    prod = get_product(pid)
    if not prod:
        await q.edit_message_text("❌ SP không tồn tại.")
        return
    pid, name, price, stock, desc = prod
    kb = [
        [InlineKeyboardButton("➕ Thêm vào giỏ", callback_data=f"add_{pid}")],
        [InlineKeyboardButton("🛒 Giỏ", callback_data="cart")],
        [InlineKeyboardButton("🔙 Quay lại", callback_data="shop")],
    ]
    await q.edit_message_text(
        f"📦 **{name}**\n\n💰 **{price:,}đ**\n📊 Còn: {stock}\n\n{desc}",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )


async def add_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    pid = int(q.data.split("_")[1])
    add_to_cart(q.from_user.id, pid)
    await q.answer("✅ Đã thêm!")
    await q.message.reply_text("✅ Đã thêm. /start để tiếp tục.")


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    items = get_cart(q.from_user.id)
    if not items:
        await q.edit_message_text("🛒 Giỏ trống.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]))
        return
    text = "🛒 **Giỏ hàng:**\n\n"
    total = 0
    kb = []
    for cid, pid, name, price, qty in items:
        sub = price * qty
        total += sub
        text += f"• {name} x{qty} = {sub:,}đ\n"
        kb.append([InlineKeyboardButton(f"❌ Xoá {name}", callback_data=f"del_{cid}")])
    text += f"\n💰 **Tổng: {total:,}đ**"
    kb.append([InlineKeyboardButton("✅ Đặt hàng", callback_data="checkout")])
    kb.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back")])
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def del_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split("_")[1])
    remove_from_cart(cid)
    await q.answer("🗑️ Xoá rồi")
    await view_cart(update, context)


async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    items = get_cart(q.from_user.id)
    if not items:
        await q.edit_message_text("🛒 Giỏ trống.")
        return
    oid, total = create_order(q.from_user.id, items)
    clear_cart(q.from_user.id)
    await q.edit_message_text(
        f"✅ **Đặt hàng thành công!**\n\n🆔 Đơn: `#{oid}`\n💰 Tổng: **{total:,}đ**",
        parse_mode="Markdown"
    )
    await send_qr(context, q.from_user.id, oid, total)
    if ADMIN_ID:
        _, oitems = get_order(oid)
        text = f"🔔 **ĐƠN MỚI #{oid}**\n\n👤 `{q.from_user.id}` — {q.from_user.full_name}\n"
        for pname, price, qty in oitems:
            text += f"• {pname} x{qty} = {price*qty:,}đ\n"
        text += f"\n💰 **Tổng: {total:,}đ**"
        kb = [[
            InlineKeyboardButton("✅ Đã nhận tiền", callback_data=f"paid_{oid}"),
            InlineKeyboardButton("❌ Huỷ", callback_data=f"reject_{oid}"),
        ]]
        try:
            await context.bot.send_message(ADMIN_ID, text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception as e:
            print(f"Admin: {e}")


async def send_qr(context, uid, oid, amount):
    caption = (
        f"💳 **THANH TOÁN ĐƠN #{oid}**\n\n"
        f"💰 Số tiền: **{amount:,}đ**\n"
        f"📝 Nội dung CK: `DH{oid}`\n\n"
        f"👉 CK đúng nội dung. Xong nhấn nút dưới."
    )
    kb = [[InlineKeyboardButton("📤 Tôi đã chuyển khoản", callback_data=f"confirm_{oid}")]]
    buf = make_vietqr(oid, amount)
    if buf:
        await context.bot.send_photo(uid, photo=buf, caption=caption,
                                      reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return
    img = get_static_qr()
    if img:
        with open(img, 'rb') as f:
            await context.bot.send_photo(uid, photo=f, caption=caption,
                                          reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return
    await context.bot.send_message(uid, caption + "\n\n⚠️ Chưa cấu hình QR.",
                                    reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def confirm_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    oid = int(q.data.split("_")[1])
    await q.message.reply_text(f"⏳ Đã ghi nhận! Shop xác nhận `#{oid}` trong ít phút.", parse_mode="Markdown")
    if ADMIN_ID:
        try:
            await context.bot.send_message(ADMIN_ID, f"💸 Khách `{q.from_user.id}` báo đã CK đơn `#{oid}`.", parse_mode="Markdown")
        except:
            pass


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    orders = get_user_orders(q.from_user.id)
    if not orders:
        await q.edit_message_text("📭 Chưa có đơn.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]))
        return
    emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
    text = "📦 **Đơn của bạn:**\n\n"
    for oid, total, status, created in orders:
        text += f"{emoji.get(status,'❓')} `#{oid}` — {total:,}đ — {status}\n"
    await q.edit_message_text(text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]),
        parse_mode="Markdown")


async def admin_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("⛔ Không có quyền!", show_alert=True)
        return
    oid = int(q.data.split("_")[1])
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE orders SET status='approved' WHERE id=?", (oid,))
    conn.commit()
    conn.close()

    order, items = get_order(oid)
    if not order:
        await q.edit_message_text("❌ Không thấy đơn.")
        return
    uid = order[1]
    deliver = f"🎁 **HÀNG CỦA BẠN — Đơn #{oid}**\n\n"
    tokens = []
    for pname, price, qty in items:
        deliver += f"📦 **{pname}** x{qty}\n"
        for _ in range(qty):
            item = pop_stock(pname)
            if item:
                tokens.append(item)
                deliver += f"`{item}`\n"
            else:
                deliver += "⚠️ *Tạm hết*\n"
        deliver += "\n"
    deliver += ("━━━━━━━━━━━━\n⚠️ **Lưu ý:**\n• Đổi mật khẩu ngay\n• Không share token\n• Bảo hành theo loại")
    kb = [[InlineKeyboardButton("🛠️ Bảo hành", callback_data=f"warranty_{oid}")]]
    try:
        if len(tokens) > 20:
            content = '\n'.join(tokens).encode('utf-8')
            buf = BytesIO(content)
            buf.name = f"tokens_don{oid}.txt"
            await context.bot.send_document(uid, document=buf,
                caption=f"🎁 {len(tokens)} token — Đơn #{oid}\n⚠️ Đổi pass ngay!",
                reply_markup=InlineKeyboardMarkup(kb))
        else:
            await context.bot.send_message(uid, deliver, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb))
        await q.edit_message_text(f"✅ Đã giao đơn #{oid}")
    except Exception as e:
        await q.edit_message_text(f"⚠️ Lỗi gửi: {e}")


async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("⛔", show_alert=True)
        return
    oid = int(q.data.split("_")[1])
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE orders SET status='rejected' WHERE id=?", (oid,))
    c.execute("SELECT user_id FROM orders WHERE id=?", (oid,))
    row = c.fetchone()
    conn.commit()
    conn.close()
    await q.edit_message_text(f"❌ Đã huỷ đơn #{oid}")
    if row:
        try:
            await context.bot.send_message(row[0], f"❌ Đơn `#{oid}` đã huỷ.", parse_mode="Markdown")
        except:
            pass


async def warranty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    oid = int(q.data.split("_")[1])
    if ADMIN_ID:
        try:
            await context.bot.send_message(ADMIN_ID,
                f"🚨 **BẢO HÀNH**\n👤 `{q.from_user.id}`\n📦 Đơn `#{oid}`",
                parse_mode="Markdown")
        except:
            pass
    await q.message.reply_text("📩 Đã gửi shop. Phản hồi 24h.")


async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📞 **Liên hệ:**\n\n👤 Admin: @your_username\n📱 0123 456 789",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]),
        parse_mode="Markdown")


# ============================================================
#   ADMIN COMMANDS
# ============================================================
async def add_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /addtokens <ngam|khongngam> token1 token2 ..."""
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "📖 **Cách dùng:**\n\n"
            "`/addtokens ngam token1 token2 ...` — Token ngâm\n"
            "`/addtokens khongngam token1 token2 ...` — Token không ngâm\n\n"
            "Hoặc gửi file .txt kèm caption `ngam` / `khongngam`",
            parse_mode="Markdown"
        )
        return

    loai = context.args[0].lower()
    tokens = context.args[1:]

    if loai in ("ngam", "ngâm"):
        name = "Token Discord Ngâm"
    elif loai in ("khongngam", "khong", "không"):
        name = "Token Discord Không Ngâm"
    else:
        await update.message.reply_text("⚠️ Loại phải là `ngam` hoặc `khongngam`", parse_mode="Markdown")
        return

    total = add_stock(name, tokens)
    await update.message.reply_text(
        f"✅ Đã thêm **{len(tokens)}** token vào **{name}**\n📦 Tổng: {total}",
        parse_mode="Markdown"
    )


async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin gửi file .txt kèm caption chọn loại"""
    if update.effective_user.id != ADMIN_ID:
        return
    doc = update.message.document
    if not doc or not doc.file_name.endswith('.txt'):
        await update.message.reply_text("📎 Gửi file .txt")
        return

    caption = (update.message.caption or "").lower()
    if "khongngam" in caption or "khong" in caption or "không" in caption:
        name = "Token Discord Không Ngâm"
    elif "ngam" in caption or "ngâm" in caption:
        name = "Token Discord Ngâm"
    else:
        await update.message.reply_text(
            "⚠️ Gửi lại file kèm caption:\n"
            "• `ngam` — Token ngâm\n"
            "• `khongngam` — Token không ngâm",
            parse_mode="Markdown"
        )
        return

    file = await doc.get_file()
    content = await file.download_as_bytearray()
    items = [l.strip() for l in content.decode('utf-8', errors='ignore').splitlines() if l.strip()]
    if not items:
        await update.message.reply_text("⚠️ File rỗng.")
        return
    total = add_stock(name, items)
    await update.message.reply_text(
        f"✅ Đã nạp **{len(items)}** token vào **{name}**\n📦 Tổng: {total}",
        parse_mode="Markdown"
    )


async def check_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name, price, stock FROM products ORDER BY name")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("📭 Chưa có SP.")
        return
    text = "📊 **TỒN KHO**\n\n"
    for name, price, stock in rows:
        icon = "🔴" if stock == 0 else "🟡" if stock < 5 else "🟢"
        text += f"{icon} **{name}**\n   💰 {price:,}đ | 📦 {stock} cái\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Dùng: `/setprice <tên SP> <giá>`\n"
            "VD: `/setprice Token Discord Ngâm 1500`",
            parse_mode="Markdown"
        )
        return
    try:
        np = int(context.args[-1].replace(",", "").replace(".", ""))
    except:
        await update.message.reply_text("⚠️ Giá phải số.")
        return
    name = " ".join(context.args[:-1])
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE products SET price=? WHERE name=?", (np, name))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Đổi giá **{name}** → **{np:,}đ**", parse_mode="Markdown")


# ============================================================
#   MAIN
# ============================================================
def main():
    init_db()
    setup_products()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addtokens", add_tokens))
    app.add_handler(CommandHandler("stock", check_stock))
    app.add_handler(CommandHandler("setprice", set_price))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt") & filters.Chat(ADMIN_ID), upload_file))

    app.add_handler(CallbackQueryHandler(shop_menu, pattern="^shop$"))
    app.add_handler(CallbackQueryHandler(product_detail, pattern="^prod_"))
    app.add_handler(CallbackQueryHandler(add_cart, pattern="^add_"))
    app.add_handler(CallbackQueryHandler(view_cart, pattern="^cart$"))
    app.add_handler(CallbackQueryHandler(del_cart, pattern="^del_"))
    app.add_handler(CallbackQueryHandler(checkout, pattern="^checkout$"))
    app.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(admin_paid, pattern="^paid_"))
    app.add_handler(CallbackQueryHandler(reject_order, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(confirm_transfer, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(warranty, pattern="^warranty_"))
    app.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
    app.add_handler(CallbackQueryHandler(back_menu, pattern="^back$"))

    print("🎮 Bot đang chạy...")
    app.run_polling()


if __name__ == "__main__":
    main()
