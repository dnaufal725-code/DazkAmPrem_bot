import os
import sqlite3
import logging
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN belum diatur di Environment Variables Render.")

if not OWNER_PASSWORD:
    raise RuntimeError("OWNER_PASSWORD belum diatur di Environment Variables Render.")

DB_FILE = "database.db"
QRIS_FILE = "qris.png"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# DATABASE
# =========================================================

def db():
    return sqlite3.connect(DB_FILE)


def init_database():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            amount INTEGER,
            transaction_id TEXT,
            proof_file_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_user(user):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users
        (telegram_id, username, first_name, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()


def create_claim(user):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM claims
        WHERE telegram_id = ?
        AND status = 'pending'
    """, (user.id,))

    existing = cur.fetchone()

    if existing:
        conn.close()
        return False

    cur.execute("""
        INSERT INTO claims
        (telegram_id, username, status, created_at)
        VALUES (?, ?, 'pending', ?)
    """, (
        user.id,
        user.username or "",
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()

    return True


def get_pending_claims():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, telegram_id, username, created_at
        FROM claims
        WHERE status = 'pending'
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return rows


def create_donation(user, amount, transaction_id, proof_file_id):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO donations
        (
            telegram_id,
            username,
            amount,
            transaction_id,
            proof_file_id,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (
        user.id,
        user.username or "",
        amount,
        transaction_id,
        proof_file_id,
        datetime.now().isoformat(),
    ))

    donation_id = cur.lastrowid

    conn.commit()
    conn.close()

    return donation_id


# =========================================================
# KEYBOARDS
# =========================================================

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🎁 Klaim AM Prem",
                callback_data="claim"
            )
        ],
        [
            InlineKeyboardButton(
                "💳 Donation",
                callback_data="donation"
            )
        ],
        [
            InlineKeyboardButton(
                "👑 Owner Menu",
                callback_data="owner"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def claim_verification_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "▶️ Verifikasi 1/3",
                callback_data="verify_1"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def claim_button():
    keyboard = [
        [
            InlineKeyboardButton(
                "🎁 Klaim AM Prem 1 Tahun FREE",
                callback_data="final_claim"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    save_user(user)

    text = (
        "👋 *Selamat datang di AM Prem!*\n\n"
        "Nikmati layanan AM Prem dan gunakan menu di bawah "
        "untuk melanjutkan.\n\n"
        "Silakan pilih menu:"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


# =========================================================
# BUTTON HANDLER
# =========================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user
    save_user(user)

    data = query.data

    # -----------------------------------------------------
    # CLAIM
    # -----------------------------------------------------

    if data == "claim":

        context.user_data["verify_count"] = 0

        await query.edit_message_text(
            "🛡️ *Verifikasi Klaim*\n\n"
            "Untuk melanjutkan klaim AM Prem 1 tahun, "
            "selesaikan 3 tahap verifikasi.\n\n"
            "Tahap 1 dari 3.",
            parse_mode="Markdown",
            reply_markup=claim_verification_menu()
        )

    # -----------------------------------------------------
    # VERIFICATION 1
    # -----------------------------------------------------

    elif data == "verify_1":

        context.user_data["verify_count"] = 1

        keyboard = [
            [
                InlineKeyboardButton(
                    "▶️ Verifikasi 2/3",
                    callback_data="verify_2"
                )
            ]
        ]

        await query.edit_message_text(
            "✅ Verifikasi 1 selesai.\n\n"
            "Lanjutkan ke tahap 2.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # -----------------------------------------------------
    # VERIFICATION 2
    # -----------------------------------------------------

    elif data == "verify_2":

        context.user_data["verify_count"] = 2

        keyboard = [
            [
                InlineKeyboardButton(
                    "▶️ Verifikasi 3/3",
                    callback_data="verify_3"
                )
            ]
        ]

        await query.edit_message_text(
            "✅ Verifikasi 2 selesai.\n\n"
            "Lanjutkan ke tahap terakhir.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # -----------------------------------------------------
    # VERIFICATION 3
    # -----------------------------------------------------

    elif data == "verify_3":

        context.user_data["verify_count"] = 3

        await query.edit_message_text(
            "🎉 *Verifikasi selesai!*\n\n"
            "Sekarang kamu bisa melakukan klaim.",
            parse_mode="Markdown",
            reply_markup=claim_button()
        )

    # -----------------------------------------------------
    # FINAL CLAIM
    # -----------------------------------------------------

    elif data == "final_claim":

        created = create_claim(user)

        if not created:

            await query.edit_message_text(
                "⏳ *Klaim kamu sudah tercatat.*\n\n"
                "Silakan tunggu admin memberikan AM Prem.",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )

            return

        await query.edit_message_text(
            "🔄 *Menghubungkan ke admin...*\n\n"
            "Permintaan klaim kamu sudah diterima.\n\n"
            "👤 Username: "
            + ("@" + user.username if user.username else "Tidak tersedia")
            + "\n"
            "🆔 User ID: "
            + str(user.id)
            + "\n\n"
            "Silakan tunggu. Admin akan memproses akun kamu.",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    # -----------------------------------------------------
    # DONATION
    # -----------------------------------------------------

    elif data == "donation":

        context.user_data["state"] = "donation_amount"

        await query.edit_message_text(
            "💳 *Donation*\n\n"
            "Masukkan nominal donation.\n\n"
            "Contoh:\n"
            "`5000`\n"
            "`10000`\n"
            "`25000`",
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # OWNER
    # -----------------------------------------------------

    elif data == "owner":

        context.user_data["state"] = "owner_password"

        await query.edit_message_text(
            "🔐 *Owner Verification*\n\n"
            "Masukkan password owner:",
            parse_mode="Markdown"
        )


# =========================================================
# MESSAGE HANDLER
# =========================================================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user = update.effective_user
    save_user(user)

    text = update.message.text or ""
    state = context.user_data.get("state")

    # =====================================================
    # OWNER PASSWORD
    # =====================================================

    if state == "owner_password":

        if text == OWNER_PASSWORD:

            context.user_data["owner_verified"] = True
            context.user_data["state"] = "owner_menu"

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📋 Klaim Belum Diproses",
                        callback_data="owner_claims"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💰 Donation",
                        callback_data="owner_donations"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💬 Kirim Pesan ke User",
                        callback_data="owner_message"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Keluar Owner",
                        callback_data="owner_exit"
                    )
                ],
            ]

            await update.message.reply_text(
                "👑 *Owner Menu*\n\n"
                "Akses owner berhasil.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        else:

            context.user_data["state"] = None

            await update.message.reply_text(
                "❌ Password salah.",
                reply_markup=main_menu()
            )

        return

    # =====================================================
    # DONATION AMOUNT
    # =====================================================

    if state == "donation_amount":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ Nominal harus berupa angka.\n\n"
                "Contoh: `10000`",
                parse_mode="Markdown"
            )

            return

        amount = int(text)

        if amount < 1000:

            await update.message.reply_text(
                "❌ Minimal donation Rp1.000."
            )

            return

        context.user_data["donation_amount"] = amount
        context.user_data["state"] = "donation_transaction"

        # QRIS
        if os.path.exists(QRIS_FILE):

            with open(QRIS_FILE, "rb") as photo:

                await update.message.reply_photo(
                    photo=photo,
                    caption=(
                        "💳 *QRIS Donation*\n\n"
                        f"Nominal: *Rp{amount:,}*\n\n"
                        "Silakan lakukan pembayaran sesuai nominal "
                        "yang kamu masukkan.\n\n"
                        "Setelah transfer, kirim Transaction ID."
                    ).replace(",", "."),
                    parse_mode="Markdown"
                )

        else:

            await update.message.reply_text(
                f"💳 *QRIS Donation*\n\n"
                f"Nominal: *Rp{amount:,}*\n\n"
                "⚠️ File QRIS belum tersedia.\n"
                "Owner perlu mengupload `qris.png`.",
                parse_mode="Markdown"
            )

        await update.message.reply_text(
            "🧾 Sekarang kirim *Transaction ID* kamu.",
            parse_mode="Markdown"
        )

        return

    # =====================================================
    # DONATION TRANSACTION
    # =====================================================

    if state == "donation_transaction":

        context.user_data["transaction_id"] = text
        context.user_data["state"] = "donation_proof"

        await update.message.reply_text(
            "✅ Transaction ID diterima.\n\n"
            "Sekarang kirim *bukti transfer* berupa foto/screenshot.",
            parse_mode="Markdown"
        )

        return

    # =====================================================
    # OWNER SEND MESSAGE
    # =====================================================

    if state == "owner_message_user":

        if not context.user_data.get("owner_verified"):

            await update.message.reply_text(
                "❌ Akses owner tidak aktif."
            )

            return

        if not text.isdigit():

            await update.message.reply_text(
                "❌ User ID harus berupa angka."
            )

            return

        context.user_data["target_user_id"] = int(text)
        context.user_data["state"] = "owner_message_text"

        await update.message.reply_text(
            "💬 Sekarang masukkan pesan yang ingin dikirim."
        )

        return

    if state == "owner_message_text":

        if not context.user_data.get("owner_verified"):

            await update.message.reply_text(
                "❌ Akses owner tidak aktif."
            )

            return

        target = context.user_data.get("target_user_id")

        try:

            await context.bot.send_message(
                chat_id=target,
                text=(
                    "📩 *Pesan dari Owner AM Prem*\n\n"
                    + text
                ),
                parse_mode="Markdown"
            )

            await update.message.reply_text(
                "✅ Pesan berhasil dikirim."
            )

        except Exception as e:

            logger.error(e)

            await update.message.reply_text(
                "❌ Gagal mengirim pesan.\n\n"
                "Pastikan user tersebut pernah membuka/menekan "
                "/start pada bot."
            )

        context.user_data["state"] = "owner_menu"

        return

    # =====================================================
    # UNKNOWN MESSAGE
    # =====================================================

    await update.message.reply_text(
        "Gunakan menu di bawah:",
        reply_markup=main_menu()
    )


# =========================================================
# PHOTO HANDLER
# =========================================================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    state = context.user_data.get("state")

    if state != "donation_proof":
        return

    user = update.effective_user

    photo = update.message.photo[-1]
    file_id = photo.file_id

    amount = context.user_data.get("donation_amount", 0)
    transaction_id = context.user_data.get(
        "transaction_id",
        ""
    )

    donation_id = create_donation(
        user,
        amount,
        transaction_id,
        file_id
    )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ *Bukti transfer diterima!*\n\n"
        f"Donation ID: `#{donation_id}`\n"
        f"Nominal: *Rp{amount:,}*\n\n"
        "Data sudah masuk ke sistem dan akan diperiksa owner.",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


# =========================================================
# OWNER CALLBACKS
# =========================================================

async def owner_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not context.user_data.get("owner_verified"):
        await query.edit_message_text(
            "❌ Sesi owner tidak aktif."
        )
        return

    data = query.data

    # -----------------------------------------------------
    # CLAIM LIST
    # -----------------------------------------------------

    if data == "owner_claims":

        claims = get_pending_claims()

        if not claims:

            text = (
                "📋 *Klaim Belum Diproses*\n\n"
                "Tidak ada klaim yang menunggu."
            )

        else:

            text = "📋 *Klaim Belum Diproses*\n\n"

            for claim in claims:

                claim_id, telegram_id, username, created = claim

                username_text = (
                    "@" + username
                    if username
                    else "Tidak ada username"
                )

                text += (
                    f"#{claim_id}\n"
                    f"👤 {username_text}\n"
                    f"🆔 `{telegram_id}`\n"
                    f"🕐 {created}\n\n"
                )

        keyboard = [
            [
                InlineKeyboardButton(
                    "💬 Kirim Pesan ke User",
                    callback_data="owner_message"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Kembali",
                    callback_data="owner_back"
                )
            ],
        ]

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # -----------------------------------------------------
    # DONATIONS
    # -----------------------------------------------------

    elif data == "owner_donations":

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                telegram_id,
                username,
                amount,
                transaction_id,
                status
            FROM donations
            ORDER BY id DESC
            LIMIT 20
        """)

        rows = cur.fetchall()
        conn.close()

        if not rows:

            text = (
                "💰 *Donation*\n\n"
                "Belum ada transaksi."
            )

        else:

            text = "💰 *Donation Terbaru*\n\n"

            for row in rows:

                donation_id, telegram_id, username, amount, trx, status = row

                username_text = (
                    "@" + username
                    if username
                    else "Tidak ada username"
                )

                text += (
                    f"#{donation_id}\n"
                    f"👤 {username_text}\n"
                    f"🆔 `{telegram_id}`\n"
                    f"💵 Rp{amount:,}\n"
                    f"🧾 {trx}\n"
                    f"📌 {status}\n\n"
                )

        keyboard = [
            [
                InlineKeyboardButton(
                    "⬅️ Kembali",
                    callback_data="owner_back"
                )
            ]
        ]

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # -----------------------------------------------------
    # SEND MESSAGE
    # -----------------------------------------------------

    elif data == "owner_message":

        context.user_data["state"] = "owner_message_user"

        await query.edit_message_text(
            "💬 *Kirim Pesan ke User*\n\n"
            "Masukkan Telegram User ID tujuan.",
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # BACK
    # -----------------------------------------------------

    elif data == "owner_back":

        keyboard = [
            [
                InlineKeyboardButton(
                    "📋 Klaim Belum Diproses",
                    callback_data="owner_claims"
                )
            ],
            [
                InlineKeyboardButton(
                    "💰 Donation",
                    callback_data="owner_donations"
                )
            ],
            [
                InlineKeyboardButton(
                    "💬 Kirim Pesan ke User",
                    callback_data="owner_message"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Keluar Owner",
                    callback_data="owner_exit"
                )
            ],
        ]

        await query.edit_message_text(
            "👑 *Owner Menu*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # -----------------------------------------------------
    # EXIT
    # -----------------------------------------------------

    elif data == "owner_exit":

        context.user_data.clear()

        await query.edit_message_text(
            "🔒 Sesi owner telah ditutup.\n\n"
            "Kembali ke menu utama.",
            reply_markup=main_menu()
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):

    logger.error(
        "Exception while handling update:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    init_database()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_callback,
            pattern="^owner_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler
        )
    )

    application.add_error_handler(error_handler)

    logger.info("AM Prem Bot started.")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
