import os, sqlite3
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ⚙️ 1. ĐIỀN TOKEN VÀ ID CỦA BẠN
BOT_TOKEN = "8967910142:AAG55eUm4_iccFioySJj0SbPHnxJQg9qcyo"
ADMIN_ID = 8336161180

# 📞 2. ĐIỀN THÔNG TIN LIÊN HỆ CỦA BẠN
ADMIN_NAME = "Đức Anh"
ADMIN_PHONE = "0334525528"
ADMIN_FACEBOOK = "Luong Đức Anh"

# 💳 3. ĐIỀN THÔNG TIN NGÂN HÀNG ĐỂ TẠO MÃ QR
BANK_ID = "MB"                   
BANK_ACCOUNT = "0333651484"   
BANK_OWNER = "Luong Duc Anh"     

# 💰 CẤU HÌNH GIÁ SẢN PHẨM (ĐÃ CẬP NHẬT THEO YÊU CẦU)
PRODUCTS = [
    {"name": "Token Discord Ngâm", "price": 1000, "desc": "✅ Acc ngâm (trên 1 tháng)\n✅ Full quyền, bao 24h"},
    {"name": "Token Discord Không Ngâm", "price": 700, "desc": "✅ Acc không ngâm\n✅ Full quyền, bao 12h"}
]
DB, STOCK_DIR = "products.db", "stock"

# --- HÀM HỖ TRỢ ---
def init_db():
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER, stock INTEGER, description TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY, user_id INTEGER, product_id INTEGER, quantity INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, total INTEGER, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS order_items (id INTEGER PRIMARY KEY, order_id INTEGER, product_name TEXT, price INTEGER, quantity INTEGER)")
    conn.commit(); conn.close()

def setup_products():
    conn = sqlite3.connect(DB); c = conn.cursor()
    for p in PRODUCTS:
        c.execute("SELECT id FROM products WHERE name=?", (p['name'],))
        if not c.fetchone(): c.execute("INSERT INTO products (name, price, stock, description) VALUES (?,?,0,?)", (p['name'], p['price'], p['desc']))
        else: c.execute("UPDATE products SET price=?, description=? WHERE name=?", (p['price'], p['desc'], p['name']))
    conn.commit(); conn.close()

def get_stock_file(name): return os.path.join(STOCK_DIR, f"{name.replace(' ', '_')}.txt")

def pop_stock(name):
    p = get_stock_file(name)
    if not os.path.exists(p): return None
    with open(p, 'r', encoding='utf-8') as f: lines = [l.strip() for l in f if l.strip()]
    if not lines: return None
    item = lines[0]
    with open(p, 'w', encoding='utf-8') as f: f.write('\n'.join(lines[1:]))
    return item

def make_vietqr(oid, amount):
    if not (BANK_ID and BANK_ACCOUNT): return None
    try:
        import requests
        url = f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT}-compact2.png?amount={amount}&addInfo=DH{oid}&accountName={BANK_OWNER}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200: return BytesIO(r.content)
    except: pass
    return None

# --- GIAO DIỆN KHÁCH HÀNG ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 **Chào mừng đến với Shop Token Discord!**\n\n"
        "🤖 Bot tự động 24/7 - Giao hàng ngay lập tức.\n"
        "🛡️ Bảo hành đầy đủ theo từng loại.\n\n"
        "👇 Chọn chức năng bên dưới:"
    )
    kb = [
        [InlineKeyboardButton("🛍️ Mua Token", callback_data="shop")],
        [InlineKeyboardButton("🛒 Giỏ hàng", callback_data="cart"), InlineKeyboardButton("📦 Đơn của tôi", callback_data="my_orders")],
        [InlineKeyboardButton("📞 Liên hệ Admin", callback_data="contact")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    text = (
        "📞 **THÔNG TIN LIÊN HỆ**\n\n"
        f"👤 Admin: {ADMIN_NAME}\n"
        f"📱 SĐT/Zalo: {ADMIN_PHONE}\n"
        f"🌐 Facebook: {ADMIN_FACEBOOK}\n"
        "⏰ Giờ làm việc: 8h - 22h hàng ngày\n\n"
        "👉 Bạn có thể nhắn tin trực tiếp cho Admin qua nút bên dưới."
    )
    kb = [
        [InlineKeyboardButton("💬 Nhắn tin cho Admin", url=f"tg://user?id={ADMIN_ID}")],
        [InlineKeyboardButton("🔙 Quay lại", callback_data="back")]
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products"); prods = c.fetchall(); conn.close()
    kb = []
    for p in prods:
        status = "🟢" if p[3] > 0 else "🔴 Hết hàng"
        kb.append([InlineKeyboardButton(f"{p[1]} - {p[2]:,}đ ({status})", callback_data=f"prod_{p[0]}")])
    kb.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back")])
    await q.edit_message_text("🛍️ **Danh sách Token:**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; pid = int(q.data.split("_")[1])
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT name, price, stock, description FROM products WHERE id=?", (pid,)); p = c.fetchone(); conn.close()
    if not p or p[2] <= 0: await q.answer("Sản phẩm đã hết hàng!", show_alert=True); return
    kb = [
        [InlineKeyboardButton("➕ Thêm vào giỏ", callback_data=f"add_{pid}")],
        [InlineKeyboardButton("🔙 Quay lại", callback_data="shop")]
    ]
    await q.edit_message_text(f"📦 **{p[0]}**\n💰 Giá: {p[1]:,}đ\n📊 Còn: {p[2]}\n\n{p[3]}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def add_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; pid = int(q.data.split("_")[1])
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT id FROM cart WHERE user_id=? AND product_id=?", (q.from_user.id, pid)); row = c.fetchone()
    if row: c.execute("UPDATE cart SET quantity=quantity+1 WHERE id=?", (row[0],))
    else: c.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?,?,1)", (q.from_user.id, pid))
    conn.commit(); conn.close(); await q.answer("✅ Đã thêm vào giỏ hàng!")

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT c.id, p.name, p.price, c.quantity FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id=?", (q.from_user.id,)); items = c.fetcháoall(); conn.close()
    if not items: await q.edit_message_text("🛒 Giỏ hàng trống.", reply_markup=InlineKeyboardMarkup([[InlineKeyboard choButton("🔙 Quay lại", callback_data="back")]])); return
    text, total = "🛒 **Giỏ hàng của bạn Admin:**\n\n", 0
    kb = []
    for cid, name, price, qty in items:
        total += price * ki qty; text += f"• {name} x{qty} = {price*qty:,}đ\n"
        kb.append([InlineKeyboardButton(f"❌ Xóa {name}", callback_data=f"del_{cid}")])
    text += f"\n💰 **Tổng: {total:,}đ**"
    kb.append([InlineKeyboardButton("✅ Đặt hàng", callback_data="checkout")])
    kb.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back")])
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def del_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; cid = int(q.data.split("_")[1])
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("DELETE FROM cart WHERE id=?", (cid,)); conn.commit(); conn.close()
    await view_cart(update, context)

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT c.id, p.name, p.price, c.quantity FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id=?", (q.from_user.id,)); items = c.fetchall()
    if not items: return
    total = sum(p*q for _,_,p,q in items)
    c.execute("INSERT INTO orders (user_id, total, status) VALUES (?,?, 'pending')", (q.from_user.id, total)); oid = c.lastrowid
    for _, name, price, qty in items: c.execute("INSERT INTO order_items (order_id, product_name, price, quantity) VALUES (?,?,?,?)", (oid, name, price, qty))
    c.execute("DELETE FROM cart WHERE user_id=?", (q.from_user.id,)); conn.commit(); conn.close()
    
    await q.edit_message_text(f"✅ **Đặt hàng thành công!**\n\n🆔 Mã đơn: `#{oid}`\n💰 Tổng: **{total:,}đ**\n\nVui lòng quét mã QR bên dưới để thanh toán.", parse_mode="Markdown")
    buf = make_vietqr(oid, total)
    kb = [[InlineKeyboardButton("📤 Tôi đã chuyển khoản", callback_data=f"confirm_{oid}")]]
    if buf: await context.bot.send_photo(q.from_user.id, photo=buf, caption=f"💳 Chuyển khoản đơn #{oid} | Nội dung: DH{oid}", reply_markup=InlineKeyboardMarkup(kb))
    
    if ADMIN_ID:
        await context.bot.send_message(ADMIN_ID, f"🔔 **ĐƠN MỚI #{oid}**\nKhách: `{q.from_user.id}`\nTổng: **{total:,}đ**\nTrạng thái: Chờ chuyển khoản", 
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Duyệt & Giao", callback_data=f"paid_{oid}")]]), parse_mode="Markdown")

async def confirm_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; oid = int(q.data.split("_")[1])
    await q.answer("⏳ Đã ghi nhận, chờ shop duyệt!", show_alert=True)
    await q.message.reply_text("📩 Đã bểm tra. Bạn vui lòng đợi trong giây lát nhé!")
    if ADMIN_ID: await context.bot.send_message(ADMIN_ID, f"💸 Khách vừa báo đã chuyển khoản đơn `#{oid}`. Vui lòng kiểm tra!", parse_mode="Markdown")

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    kb = [[InlineKeyboardButton("🛍️ Mua Token", callback_data="shop")], [InlineKeyboardButton("🛒 Giỏ hàng", callback_data="cart"), InlineKeyboardButton("📦 Đơn của tôi", callback_data="my_orders")], [InlineKeyboardButton("📞 Liên hệ Admin", callback_data="contact")]]
    await q.edit_message_text("👋 **Chào mừng!**\n\n👇 Chọn chức năng:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- ADMIN DUYỆT & GIAO HÀNG ---
async def admin_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID: return
    oid = int(q.data.split("_")[1]); conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT user_id FROM orders WHERE id=?", (oid,)); row = c.fetchone()
    if not row: return
    uid = row[0]
    c.execute("SELECT product_name, quantity FROM order_items WHERE order_id=?", (oid,)); items = c.fetchall()
    c.execute("UPDATE orders SET status='done' WHERE id=?", (oid,)); conn.commit(); conn.close()
    
    text = f"🎁 **HÀNG CỦA BẠN (Đơn #{oid}):**\n\n"
    for name, qty in items:
        text += f"📦 **{name}**:\n"
        for _ in range(qty):
            token = pop_stock(name)
            if token: text += f"`{token}`\n"
            else: text += "⚠️ Tạm hết hàng, shop bù sau!\n"
        text += "\n"
    text += "Cảm ơn bạn đã ủng hộ shop!"
    try:
        await context.bot.send_message(uid, text, parse_mode="Markdown")
        await q.edit_message_text(f"✅ Đã duyệt và giao đơn #{oid} thành công!")
    except Exception as e:
        await q.edit_message_text(f"⚠️ Lỗi gửi: {e}")

# --- ADMIN THÊM TOKEN (GÕ TAY HOẶC GỬI FILE) ---
async def add_tokens_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    args = context.args
    if len(args) < 2: 
        await update.message.reply_text("Cú pháp: /addtokens <ngam|khongngam> <token1> <token2>...")
        return
    loai = "Token Discord Ngâm" if args[0].lower() == "ngam" else "Token Discord Không Ngâm"
    p = get_stock_file(loai); os.makedirs(STOCK_DIR, exist_ok=True)
    
    with open(p, 'a', encoding='utf-8') as f:
        for i in args[1:]: f.write(i.strip() + '\n')
    
    with open(p, 'r', encoding='utf-8') as f: total = sum(1 for l in f if l.strip())
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("UPDATE products SET stock=? WHERE name=?", (total, loai)); conn.commit(); conn.close()
    await update.message.reply_text(f"✅ Đã nạp {len(args)-1} token vào {loai}. Tổng kho: {total}")

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    doc = update.message.document
    if not doc or not doc.file_name.endswith('.txt'): return
    
    caption = (update.message.caption or "").lower()
    if "khong" in caption or "không" in caption: loai = "Token Discord Không Ngâm"
    elif "ngam" in caption or "ngâm" in caption: loai = "Token Discord Ngâm"
    else:
        await update.message.reply_text("⚠️ Gửi lại file kèm caption 'ngam' hoặc 'khongngam'")
        return

    file = await doc.get_file()
    content = await file.download_as_bytearray()
    items = [l.strip() for l in content.decode('utf-8', errors='ignore').splitlines() if l.strip()]
    
    p = get_stock_file(loai); os.makedirs(STOCK_DIR, exist_ok=True)
    with open(p, 'a', encoding='utf-8') as f:
        for i in items: f.write(i + '\n')
        
    with open(p, 'r', encoding='utf-8') as f: total = sum(1 for l in f if l.strip())
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("UPDATE products SET stock=? WHERE name=?", (total, loai)); conn.commit(); conn.close()
    await update.message.reply_text(f"✅ Đã nạp {len(items)} token từ file vào {loai}. Tổng kho: {total}")

async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args) < 2: return
    try: np = int(context.args[-1].replace(",", "").replace(".", ""))
    except: return
    name = " ".join(context.args[:-1])
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("UPDATE products SET price=? WHERE name=?", (np, name)); conn.commit(); conn.close()
    await update.message.reply_text(f"✅ Đã đổi giá {name} thành **{np:,}đ**", parse_mode="Markdown")

def main():
    init_db(); setup_products()
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Đăng ký lệnh
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addtokens", add_tokens_cmd))
    app.add_handler(CommandHandler("setprice", set_price))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt") & filters.Chat(ADMIN_ID), upload_file))
    
    # Đăng ký nút bấm
    app.add_handler(CallbackQueryHandler(shop_menu, pattern="^shop$"))
    app.add_handler(CallbackQueryHandler(product_detail, pattern="^prod_"))
    app.add_handler(CallbackQueryHandler(add_cart, pattern="^add_"))
    app.add_handler(CallbackQueryHandler(view_cart, pattern="^cart$"))
    app.add_handler(CallbackQueryHandler(del_cart, pattern="^del_"))
    app.add_handler(CallbackQueryHandler(checkout, pattern="^checkout$"))
    app.add_handler(CallbackQueryHandler(confirm_transfer, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(admin_paid, pattern="^paid_"))
    app.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    
    print("Bot đang chạy thành công...")
    app.run_polling()

if __name__ == "__main__": main()
