import os, sqlite3, datetime
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ⚙️ 1. ĐIỀN THÔNG TIN CỦA BẠN
BOT_TOKEN = "8967910142:AAHW043Q1_nP7LwGE4olXBEwqs306DeGLv0"
ADMIN_ID = 8336161180

# 💳 2. THÔNG TIN NGÂN HÀNG (Để tạo QR)
BANK_ID = "MB"
BANK_ACCOUNT = "0333651484
BANK_OWNER = "Luong Duc Anh"

# 💰 3. CẤU HÌNH SẢN PHẨM
PRODUCTS = [
    {"name": "Token Discord Ngâm", "price": 1000, "desc": "Acc ngâm (trên 1 tháng), bao 24h"},
    {"name": "Token Discord Không Ngâm", "price": 700, "desc": "Acc không ngâm, bao 12h"}
]
DB, STOCK_DIR = "products.db", "stock"

# --- KHỞI TẠO DATABASE ---
def init_db():
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER, stock INTEGER, description TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY, user_id INTEGER, product_id INTEGER, quantity INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, total INTEGER, status TEXT, date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS order_items (id INTEGER PRIMARY KEY, order_id INTEGER, product_name TEXT, price INTEGER, quantity INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)") 
    conn.commit(); conn.close()

def setup_products():
    conn = sqlite3.connect(DB); c = conn.cursor()
    for p in PRODUCTS:
        c.execute("SELECT id FROM products WHERE name=?", (p['name'],))
        if not c.fetchone(): c.execute("INSERT INTO products (name, price, stock, description) VALUES (?,?,0,?)", (p['name'], p['price'], p['desc']))
        else: c.execute("UPDATE products SET price=?, description=? WHERE name=?", (p['price'], p['desc'], p['name']))
    conn.commit(); conn.close()

def get_balance(uid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)); row = c.fetchone()
    if not row: c.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (uid,)); conn.commit(); bal = 0
    else: bal = row[0]
    conn.close(); return bal

def update_balance(uid, amount):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
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

def make_qr(oid, amount, type="DH"):
    if not (BANK_ID and BANK_ACCOUNT): return None
    try:
        import requests
        url = f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT}-compact2.png?amount={amount}&addInfo={type}{oid}&accountName={BANK_OWNER}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200: return BytesIO(r.content)
    except: pass
    return None

# --- GIAO DIỆN KHÁCH HÀNG ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    bal = get_balance(uid)
    text = f"👋 **Chào mừng đến với Shop Token VIP!**\n\n💳 Số dư ví của bạn: **{bal:,}đ**\n👇 Chọn chức năng:"
    kb = [
        [InlineKeyboardButton("🛍️ Mua Token", callback_data="shop")],
        [InlineKeyboardButton("💳 Nạp tiền", callback_data="nap_tien")],
        [InlineKeyboardButton("🛒 Giỏ hàng", callback_data="cart"), InlineKeyboardButton("📦 Đơn của tôi", callback_data="my_orders")],
        [InlineKeyboardButton("📞 Liên hệ Admin", callback_data="contact")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def nap_tien(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    text = (
        "💳 **NẠP TIỀN VÀO VÍ**\n\n"
        "⚠️ **Lưu ý:** Số tiền nạp tối thiểu là **10.000đ**.\n"
        "Vui lòng chuyển khoản theo mã QR bên dưới.\n\n"
        "📌 Hệ thống sẽ tự động cộng tiền sau khi Admin kiểm tra (1-2 phút)."
    )
    kb = [[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    
    fake_oid = str(q.from_user.id)[-6:] 
    buf = make_qr(fake_oid, 10000, type="NAP") 
    if buf: await context.bot.send_photo(q.from_user.id, photo=buf, caption="Quét mã QR để nạp tối thiểu 10.000đ. Nội dung tự động điền.")

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products"); prods = c.fetchall(); conn.close()
    kb = []
    for p in prods:
        status = "🟢" if p[3] > 0 else "🔴 Hết"
        kb.append([InlineKeyboardButton(f"{p[1]} - {p[2]:,}đ ({status})", callback_data=f"prod_{p[0]}")])
    kb.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back")])
    await q.edit_message_text("🛍️ **Danh sách Token:**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; pid = int(q.data.split("_")[1])
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT name, price, stock, description FROM products WHERE id=?", (pid,)); p = c.fetchone(); conn.close()
    if not p or p[2] <= 0: await q.answer("Hết hàng!", show_alert=True); return
    kb = [[InlineKeyboardButton("➕ Thêm vào giỏ", callback_data=f"add_{pid}")], [InlineKeyboardButton("🔙 Quay lại", callback_data="shop")]]
    await q.edit_message_text(f"📦 **{p[0]}**\n💰 Giá: {p[1]:,}đ\n📊 Còn: {p[2]}\n\n{p[3]}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def add_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; pid = int(q.data.split("_")[1])
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT id FROM cart WHERE user_id=? AND product_id=?", (q.from_user.id, pid)); row = c.fetchone()
    if row: c.execute("UPDATE cart SET quantity=quantity+1 WHERE id=?", (row[0],))
    else: c.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?,?,1)", (q.from_user.id, pid))
    conn.commit(); conn.close(); await q.answer("✅ Đã thêm!")

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT c.id, p.name, p.price, c.quantity FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id=?", (q.from_user.id,)); items = c.fetchall(); conn.close()
    if not items: await q.edit_message_text("🛒 Trống.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]])); return
    text, total, kb = "🛒 **Giỏ hàng:**\n\n", 0, []
    for cid, name, price, qty in items:
        total += price * qty; text += f"• {name} x{qty} = {price*qty:,}đ\n"
        kb.append([InlineKeyboardButton(f"❌ Xóa {name}", callback_data=f"del_{cid}")])
    text += f"\n💰 **Tổng: {total:,}đ**"
    kb.append([InlineKeyboardButton("✅ Thanh toán bằng Ví", callback_data="checkout")]); 
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
    
    bal = get_balance(q.from_user.id)
    if bal < total:
        await q.answer(f"❌ Số dư không đủ! Bạn cần nạp thêm {total-bal:,}đ", show_alert=True)
        return
    
    update_balance(q.from_user.id, -total)
    date_now = datetime.datetime.now().strftime("%H:%M %d/%m/%Y")
    c.execute("INSERT INTO orders (user_id, total, status, date) VALUES (?,?, 'done', ?)", (q.from_user.id, total, date_now)); oid = c.lastrowid
    
    text = f"✅ **Thanh toán thành công!**\n🆔 Mã đơn: `#{oid}`\n💰 Đã trừ: **{total:,}đ**\n\n"
    for _, name, price, qty in items:
        c.execute("INSERT INTO order_items (order_id, product_name, price, quantity) VALUES (?,?,?,?)", (oid, name, price, qty))
        text += f"📦 **{name}**:\n"
        for _ in range(qty):
            token = pop_stock(name)
            text += f"`{token}`\n" if token else "⚠️ Hết hàng!\n"
        text += "\n"
    
    c.execute("DELETE FROM cart WHERE user_id=?", (q.from_user.id,)); conn.commit(); conn.close()
    await q.edit_message_text(text, parse_mode="Markdown")

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT id, total, status, date FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (q.from_user.id,)); orders = c.fetchall(); conn.close()
    if not orders: await q.edit_message_text("📭 Chưa có đơn hàng.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]])); return
    text = "📦 **Đơn hàng của bạn:**\n\n"
    for oid, total, status, date in orders:
        st = "⏳ Chờ TT" if status == "pending" else "✅ Đã giao"
        text += f"`#{oid}` - {total:,}đ - {st} ({date})\n"
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]), parse_mode="Markdown")

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    text = "📞 **LIÊN HỆ**\n\n👤 Admin: Đức Anh\n📱 Zalo: 0987.654.321\n🌐 FB: fb.com/tenban"
    kb = [[InlineKeyboardButton("💬 Nhắn tin Admin", url=f"tg://user?id={ADMIN_ID}")], [InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; bal = get_balance(q.from_user.id)
    text = f"👋 **Chào mừng!**\n💳 Số dư: **{bal:,}đ**\n👇 Chọn chức năng:"
    kb = [[InlineKeyboardButton("🛍️ Mua Token", callback_data="shop")], [InlineKeyboardButton("💳 Nạp tiền", callback_data="nap_tien")], [InlineKeyboardButton("🛒 Giỏ hàng", callback_data="cart"), InlineKeyboardButton("📦 Đơn của tôi", callback_data="my_orders")], [InlineKeyboardButton("📞 Liên hệ Admin", callback_data="contact")]]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- LỆNH ADMIN ---
async def admin_nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    args = context.args
    if len(args) < 2: 
        await update.message.reply_text("Cú pháp: /nap <user_id> <số_tiền>")
        return
    try: uid, amount = int(args[0]), int(args[1])
    except: return
    
    if amount < 10000:
        await update.message.reply_text("⚠️ Số tiền nạp tối thiểu là 10.000đ!")
        return
        
    update_balance(uid, amount)
    await update.message.reply_text(f"✅ Đã nạp {amount:,}đ vào ví của ID {uid}")
    try: await context.bot.send_message(uid, f"💳 Bạn đã được Admin nạp **{amount:,}đ** vào ví!", parse_mode="Markdown")
    except: pass

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT COUNT(id), SUM(total) FROM orders WHERE status='done'"); total_orders, total_money = c.fetchone()
    c.execute("SELECT SUM(stock) FROM products"); total_stock = c.fetchone()[0]
    conn.close()
    text = f"📊 **THỐNG KÊ SHOP**\n\n💰 Tổng doanh thu: **{total_money or 0:,}đ**\n✅ Đơn đã giao: **{total_orders or 0}**\n📦 Tồn kho hiện tại: **{total_stock or 0}** token"
    await update.message.reply_text(text, parse_mode="Markdown")

async def add_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    args = context.args
    if len(args) < 2: return
    loai = "Token Discord Ngâm" if args[0].lower() == "ngam" else "Token Discord Không Ngâm"
    p = get_stock_file(loai); os.makedirs(STOCK_DIR, exist_ok=True)
    with open(p, 'a', encoding='utf-8') as f:
        for i in args[1:]: f.write(i.strip() + '\n')
    with open(p, 'r', encoding='utf-8') as f: total = sum(1 for l in f if l.strip())
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("UPDATE products SET stock=? WHERE name=?", (total, loai)); conn.commit(); conn.close()
    await update.message.reply_text(f"✅ Đã nạp {len(args)-1} token vào {loai}. Tổng: {total}")

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    doc = update.message.document
    if not doc or not doc.file_name.endswith('.txt'): return
    caption = (update.message.caption or "").lower()
    if "khong" in caption: loai = "Token Discord Không Ngâm"
    elif "ngam" in caption: loai = "Token Discord Ngâm"
    else: await update.message.reply_text("⚠️ Gửi file kèm caption 'ngam' hoặc 'khongngam'"); return
    file = await doc.get_file(); content = await file.download_as_bytearray()
    items = [l.strip() for l in content.decode('utf-8', errors='ignore').splitlines() if l.strip()]
    p = get_stock_file(loai); os.makedirs(STOCK_DIR, exist_ok=True)
    with open(p, 'a', encoding='utf-8') as f:
        for i in items: f.write(i + '\n')
    with open(p, 'r', encoding='utf-8') as f: total = sum(1 for l in f if l.strip())
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("UPDATE products SET stock=? WHERE name=?", (total, loai)); conn.commit(); conn.close()
    await update.message.reply_text(f"✅ Đã nạp {len(items)} token từ file vào {loai}. Tổng: {total}")

def main():
    init_db(); setup_products()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nap", admin_nap))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("addtokens", add_tokens))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt") & filters.Chat(ADMIN_ID), upload_file))
    
    app.add_handler(CallbackQueryHandler(shop_menu, pattern="^shop$"))
    app.add_handler(CallbackQueryHandler(nap_tien, pattern="^nap_tien$"))
    app.add_handler(CallbackQueryHandler(product_detail, pattern="^prod_"))
    app.add_handler(CallbackQueryHandler(add_cart, pattern="^add_"))
    app.add_handler(CallbackQueryHandler(view_cart, pattern="^cart$"))
    app.add_handler(CallbackQueryHandler(del_cart, pattern="^del_"))
    app.add_handler(CallbackQueryHandler(checkout, pattern="^checkout$"))
    app.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    app.run_polling()

if __name__ == "__main__": main()
