import os
import sqlite3
import threading
from datetime import datetime

from flask import Flask
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "DAZKAMPREMOWNERVIEW")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN belum diisi di Environment Variables Render.")

DB_NAME = "database.db"
QRIS_FILE = "qris.png"

# =========================================================
# FLASK - UNTUK RENDER
# =========================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "AM Prem Bot is running."


@web_app.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
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
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_user(user):
    conn = get_db()

    username = user.username or "-"
    first_name = user.first_name or "-"

    conn.execute("""
        INSERT INTO users
        (telegram_id, username, first_name, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
    """, (
        user.id,
        username,
        first_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    return InlineKeyboardMarkup([
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
    ])


def back_main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬅️ Kembali",
                callback_data="back_main"
            )
        ]
    ])


def donation_amount_keyboard():
    buttons = []

    amounts = [
        1000, 2000,
        3000, 4000,
        5000, 6000,
        7000, 8000,
        9000, 10000,
    ]

    for i in range(0, len(amounts), 2):
        buttons.append([
            InlineKeyboardButton(
                f"Rp{amounts[i]:,}".replace(",", "."),
                callback_data=f"don_amt_{amounts[i]}"
            ),
            InlineKeyboardButton(
                f"Rp{amounts[i+1]:,}".replace(",", "."),
                callback_data=f"don_amt_{amounts[i+1]}"
            ),
        ])

    buttons.append([
        InlineKeyboardButton(
            "✏️ Custom",
            callback_data="don_custom"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Kembali",
            callback_data="back_main"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def custom_keypad(amount=""):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1", callback_data="num_1"),
            InlineKeyboardButton("2", callback_data="num_2"),
            InlineKeyboardButton("3", callback_data="num_3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="num_4"),
            InlineKeyboardButton("5", callback_data="num_5"),
            InlineKeyboardButton("6", callback_data="num_6"),
        ],
        [
            InlineKeyboardButton("7", callback_data="num_7"),
            InlineKeyboardButton("8", callback_data="num_8"),
            InlineKeyboardButton("9", callback_data="num_9"),
        ],
        [
            InlineKeyboardButton("⌫", callback_data="num_back"),
            InlineKeyboardButton("0", callback_data="num_0"),
            InlineKeyboardButton("✅", callback_data="num_confirm"),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Kembali",
                callback_data="custom_back"
            )
        ],
    ])


def claim_step_1_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❌ No, saya bukan bot",
                callback_data="verify_1"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Kembali",
                callback_data="back_main"
            )
        ]
    ])


def claim_step_2_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Ya, saya ingin klaim",
                callback_data="verify_2"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Kembali",
                callback_data="verify_back_1"
            )
        ]
    ])


def claim_step_3_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎵 Buka TikTok @dazkedit1",
                url="https://www.tiktok.com/@dazkedit1"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Sudah Follow",
                callback_data="verify_3"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Kembali",
                callback_data="verify_back_2"
            )
        ]
    ])


def final_claim_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎁 KLAIM AM PREM 1 TAHUN FREE",
                callback_data="final_claim"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Kembali",
                callback_data="back_main"
            )
        ]
    ])


def owner_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📋 Pending Claim",
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
                "📨 Kirim Pesan",
                callback_data="owner_message"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Kembali",
                callback_data="back_main"
            )
        ],
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)

    context.user_data.clear()

    text = (
        "🔥 *AM PREM*\n\n"
        "Selamat datang di bot AM Prem.\n\n"
        "🎁 Klaim AM Prem gratis\n"
        "💳 Support melalui donation\n"
        "👑 Menu khusus owner\n\n"
        "Pilih menu di bawah."
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )


# =========================================================
# CLAIM FLOW
# =========================================================

async def show_claim_step_1(query):
    await query.edit_message_text(
        "🤖 *VERIFIKASI 1/3*\n\n"
        "Apakah Anda bukan bot?\n\n"
        "Jika bukan bot, tekan tombol di bawah.",
        parse_mode="Markdown",
        reply_markup=claim_step_1_keyboard()
    )


async def show_claim_step_2(query):
    await query.edit_message_text(
        "🎁 *VERIFIKASI 2/3*\n\n"
        "Apakah Anda ingin mengklaim\n"
        "*AM Prem gratis?*",
        parse_mode="Markdown",
        reply_markup=claim_step_2_keyboard()
    )


async def show_claim_step_3(query):
    await query.edit_message_text(
        "🎵 *VERIFIKASI 3/3*\n\n"
        "Apakah Anda sudah follow TikTok\n"
        "@dazkedit1?\n\n"
        "Silakan buka TikTok lalu follow terlebih dahulu.",
        parse_mode="Markdown",
        reply_markup=claim_step_3_keyboard()
    )


async def show_final_claim(query):
    await query.edit_message_text(
        "✅ *VERIFIKASI SELESAI*\n\n"
        "Semua langkah verifikasi telah dilewati.\n\n"
        "Sekarang kamu bisa mengklaim:\n\n"
        "🎁 *AM PREM 1 TAHUN FREE*",
        parse_mode="Markdown",
        reply_markup=final_claim_keyboard()
    )


async def process_final_claim(query):
    user = query.from_user

    conn = get_db()

    existing = conn.execute("""
        SELECT id FROM claims
        WHERE telegram_id = ?
        AND status = 'pending'
        LIMIT 1
    """, (user.id,)).fetchone()

    if existing:
        conn.close()

        await query.edit_message_text(
            "⏳ *CLAIM SUDAH TERKIRIM*\n\n"
            "Claim kamu masih menunggu diproses admin.\n\n"
            f"🆔 Telegram ID: `{user.id}`",
            parse_mode="Markdown",
            reply_markup=back_main_keyboard()
        )
        return

    conn.execute("""
        INSERT INTO claims
        (telegram_id, username, status, created_at)
        VALUES (?, ?, 'pending', ?)
    """, (
        user.id,
        user.username or "-",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    await query.edit_message_text(
        "🔄 *MENGHUBUNGKAN KE ADMIN...*\n\n"
        "Silahkan tunggu.\n\n"
        "Claim kamu sudah masuk ke daftar pending.",
        parse_mode="Markdown",
        reply_markup=back_main_keyboard()
    )


# =========================================================
# DONATION
# =========================================================

async def show_donation(query):
    await query.edit_message_text(
        "💳 *DONATION*\n\n"
        "Pilih nominal donation.\n\n"
        "Atau gunakan Custom untuk memasukkan nominal sendiri.\n\n"
        "Minimum Custom: *Rp1.000*",
        parse_mode="Markdown",
        reply_markup=donation_amount_keyboard()
    )


async def send_qris(update, context, amount):
    context.user_data["donation_amount"] = amount
    context.user_data["state"] = "donation_transaction"

    amount_text = f"Rp{amount:,}".replace(",", ".")

    text = (
        "💳 *PEMBAYARAN DONATION*\n\n"
        f"Nominal: *{amount_text}*\n\n"
        "Silakan scan QRIS di bawah.\n\n"
        "Setelah transfer selesai, kirim *Transaction ID* "
        "atau nomor referensi transaksi kamu."
    )

    if os.path.exists(QRIS_FILE):
        with open(QRIS_FILE, "rb") as photo:
            await update.effective_message.reply_photo(
                photo=photo,
                caption=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "❌ Batalkan",
                            callback_data="donation_cancel"
                        )
                    ]
                ])
            )
    else:
        await update.effective_message.reply_text(
            text +
            "\n\n⚠️ *qris.png belum ditemukan di server.*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "❌ Batalkan",
                        callback_data="donation_cancel"
                    )
                ]
            ])
        )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    data = query.data

    save_user(query.from_user)

    # -----------------------------------------------------
    # MAIN
    # -----------------------------------------------------

    if data == "back_main":
        context.user_data.clear()

        await query.edit_message_text(
            "🏠 *MENU UTAMA*\n\n"
            "Pilih menu yang ingin digunakan.",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
        return

    # -----------------------------------------------------
    # CLAIM
    # -----------------------------------------------------

    if data == "claim":
        context.user_data.clear()
        context.user_data["claim_step"] = 1

        await show_claim_step_1(query)
        return

    if data == "verify_1":
        context.user_data["claim_step"] = 2

        await show_claim_step_2(query)
        return

    if data == "verify_2":
        context.user_data["claim_step"] = 3

        await show_claim_step_3(query)
        return

    if data == "verify_3":
        context.user_data["claim_verified"] = True

        await show_final_claim(query)
        return

    if data == "verify_back_1":
        context.user_data["claim_step"] = 1

        await show_claim_step_1(query)
        return

    if data == "verify_back_2":
        context.user_data["claim_step"] = 2

        await show_claim_step_2(query)
        return

    if data == "final_claim":
        await process_final_claim(query)
        return

    # -----------------------------------------------------
    # DONATION MENU
    # -----------------------------------------------------

    if data == "donation":
        context.user_data.clear()
        await show_donation(query)
        return

    if data.startswith("don_amt_"):
        amount = int(data.replace("don_amt_", ""))

        await send_qris(
            update,
            context,
            amount
        )
        return

    if data == "don_custom":
        context.user_data["state"] = "custom_amount"
        context.user_data["custom_amount"] = ""

        await query.edit_message_text(
            "✏️ *CUSTOM DONATION*\n\n"
            "Masukkan nominal menggunakan keypad.\n\n"
            "Minimum: *Rp1.000*\n\n"
            "Nominal: `Rp0`",
            parse_mode="Markdown",
            reply_markup=custom_keypad()
        )
        return

    if data == "custom_back":
        context.user_data.pop("custom_amount", None)
        context.user_data.pop("state", None)

        await show_donation(query)
        return

    # -----------------------------------------------------
    # CUSTOM KEYPAD
    # -----------------------------------------------------

    if data.startswith("num_"):
        state = context.user_data.get("state")

        if state != "custom_amount":
            return

        current = context.user_data.get(
            "custom_amount",
            ""
        )

        if data == "num_back":
            current = current[:-1]

        elif data == "num_confirm":
            if not current:
                await query.answer(
                    "Masukkan nominal terlebih dahulu.",
                    show_alert=True
                )
                return

            amount = int(current)

            if amount < 1000:
                await query.answer(
                    "Minimum donation adalah Rp1.000.",
                    show_alert=True
                )
                return

            context.user_data["custom_amount"] = current

            await send_qris(
                update,
                context,
                amount
            )
            return

        else:
            digit = data.replace("num_", "")

            if len(current) >= 9:
                await query.answer(
                    "Nominal terlalu panjang.",
                    show_alert=True
                )
                return

            current += digit

        # Hapus leading zero
        current = current.lstrip("0")

        if not current:
            display = "Rp0"
        else:
            display = "Rp" + f"{int(current):,}".replace(",", ".")

        context.user_data["custom_amount"] = current

        await query.edit_message_text(
            "✏️ *CUSTOM DONATION*\n\n"
            "Masukkan nominal menggunakan keypad.\n\n"
            "Minimum: *Rp1.000*\n\n"
            f"Nominal: `{display}`",
            parse_mode="Markdown",
            reply_markup=custom_keypad(current)
        )
        return

    if data == "donation_cancel":
        context.user_data.clear()

        await query.edit_message_text(
            "❌ Donation dibatalkan.",
            reply_markup=main_keyboard()
        )
        return

    # -----------------------------------------------------
    # OWNER
    # -----------------------------------------------------

    if data == "owner":
        context.user_data.clear()
        context.user_data["state"] = "owner_password"

        await query.edit_message_text(
            "🔐 *OWNER MENU*\n\n"
            "Masukkan password owner.",
            parse_mode="Markdown",
            reply_markup=back_main_keyboard()
        )
        return

    if data == "owner_claims":
        if not context.user_data.get("owner_verified"):
            await query.edit_message_text(
                "❌ Akses ditolak.",
                reply_markup=main_keyboard()
            )
            return

        await show_owner_claims(query)
        return

    if data == "owner_donations":
        if not context.user_data.get("owner_verified"):
            await query.edit_message_text(
                "❌ Akses ditolak.",
                reply_markup=main_keyboard()
            )
            return

        await show_owner_donations(query)
        return

    if data == "owner_message":
        if not context.user_data.get("owner_verified"):
            await query.edit_message_text(
                "❌ Akses ditolak.",
                reply_markup=main_keyboard()
            )
            return

        context.user_data["state"] = "owner_message_user"

        await query.edit_message_text(
            "📨 *KIRIM PESAN*\n\n"
            "Masukkan Telegram User ID tujuan.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅️ Kembali",
                        callback_data="owner_back"
                    )
                ]
            ])
        )
        return

    if data == "owner_back":
        if context.user_data.get("owner_verified"):
            context.user_data["state"] = "owner_menu"

            await query.edit_message_text(
                "👑 *OWNER MENU*\n\n"
                "Pilih menu.",
                parse_mode="Markdown",
                reply_markup=owner_keyboard()
            )
        else:
            context.user_data.clear()

            await query.edit_message_text(
                "🏠 *MENU UTAMA*",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )
        return


# =========================================================
# OWNER CLAIMS
# =========================================================

async def show_owner_claims(query):
    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM claims
        WHERE status = 'pending'
        ORDER BY id DESC
        LIMIT 50
    """).fetchall()

    conn.close()

    if not rows:
        text = (
            "📋 *PENDING CLAIM*\n\n"
            "Tidak ada claim pending."
        )
    else:
        parts = [
            "📋 *PENDING CLAIM*\n"
        ]

        for i, row in enumerate(rows, 1):
            username = row["username"]

            if username != "-":
                username = "@" + username

            parts.append(
                f"*{i}. {username}*\n"
                f"🆔 `{row['telegram_id']}`\n"
                f"🕐 {row['created_at']}\n"
            )

        text = "\n".join(parts)

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔄 Refresh",
                    callback_data="owner_claims"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Kembali",
                    callback_data="owner_back"
                )
            ]
        ])
    )


# =========================================================
# OWNER DONATIONS
# =========================================================

async def show_owner_donations(query):
    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM donations
        ORDER BY id DESC
        LIMIT 30
    """).fetchall()

    conn.close()

    if not rows:
        text = (
            "💰 *DONATION*\n\n"
            "Belum ada transaksi."
        )
    else:
        parts = ["💰 *DONATION TERBARU*\n"]

        for i, row in enumerate(rows, 1):
            username = row["username"]

            if username != "-":
                username = "@" + username

            amount = f"Rp{row['amount']:,}".replace(",", ".")

            parts.append(
                f"*{i}. {username}*\n"
                f"💵 {amount}\n"
                f"🆔 `{row['telegram_id']}`\n"
                f"🧾 `{row['transaction_id']}`\n"
                f"📌 {row['status']}\n"
                f"🕐 {row['created_at']}\n"
            )

        text = "\n".join(parts)

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔄 Refresh",
                    callback_data="owner_donations"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Kembali",
                    callback_data="owner_back"
                )
            ]
        ])
    )


# =========================================================
# TEXT MESSAGE HANDLER
# =========================================================

async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    text = update.message.text.strip()

    save_user(user)

    state = context.user_data.get("state")

    # -----------------------------------------------------
    # OWNER PASSWORD
    # -----------------------------------------------------

    if state == "owner_password":

        if text == OWNER_PASSWORD:

            context.user_data["owner_verified"] = True
            context.user_data["state"] = "owner_menu"

            await update.message.reply_text(
                "✅ *PASSWORD BENAR*\n\n"
                "Selamat datang di Owner Menu.",
                parse_mode="Markdown",
                reply_markup=owner_keyboard()
            )

        else:
            await update.message.reply_text(
                "❌ Password salah.\n\n"
                "Coba masukkan kembali.",
                reply_markup=back_main_keyboard()
            )

        return

    # -----------------------------------------------------
    # DONATION TRANSACTION ID
    # -----------------------------------------------------

    if state == "donation_transaction":

        if len(text) < 2:
            await update.message.reply_text(
                "⚠️ Transaction ID tidak valid.\n"
                "Silakan kirim Transaction ID."
            )
            return

        context.user_data["transaction_id"] = text
        context.user_data["state"] = "donation_proof"

        await update.message.reply_text(
            "📸 *KIRIM BUKTI TRANSFER*\n\n"
            "Silakan kirim foto/screenshot bukti pembayaran.\n\n"
            "Pastikan nominal dan transaksi terlihat jelas.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "❌ Batalkan",
                        callback_data="donation_cancel"
                    )
                ]
            ])
        )

        return

    # -----------------------------------------------------
    # OWNER MESSAGE - USER ID
    # -----------------------------------------------------

    if state == "owner_message_user":

        try:
            target_id = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ User ID harus berupa angka."
            )
            return

        context.user_data["target_user_id"] = target_id
        context.user_data["state"] = "owner_message_text"

        await update.message.reply_text(
            f"✅ Target User ID: `{target_id}`\n\n"
            "Sekarang masukkan pesan yang ingin dikirim.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅️ Kembali",
                        callback_data="owner_back"
                    )
                ]
            ])
        )

        return

    # -----------------------------------------------------
    # OWNER MESSAGE - TEXT
    # -----------------------------------------------------

    if state == "owner_message_text":

        target_id = context.user_data.get("target_user_id")

        if not target_id:
            context.user_data["state"] = "owner_menu"

            await update.message.reply_text(
                "❌ Target tidak ditemukan.",
                reply_markup=owner_keyboard()
            )
            return

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "📩 *PESAN DARI OWNER AM PREM*\n\n"
                    + text
                ),
                parse_mode="Markdown"
            )

            await update.message.reply_text(
                "✅ Pesan berhasil dikirim.",
                reply_markup=owner_keyboard()
            )

        except Exception as e:
            await update.message.reply_text(
                "❌ Gagal mengirim pesan.\n\n"
                "Pastikan user tersebut sudah pernah "
                "memulai/interaksi dengan bot.",
                reply_markup=owner_keyboard()
            )

        context.user_data["state"] = "owner_menu"
        return

    # -----------------------------------------------------
    # DEFAULT
    # -----------------------------------------------------

    await update.message.reply_text(
        "Silakan gunakan tombol menu.",
        reply_markup=main_keyboard()
    )


# =========================================================
# PHOTO HANDLER
# =========================================================

async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    save_user(user)

    state = context.user_data.get("state")

    if state != "donation_proof":
        await update.message.reply_text(
            "Foto diterima, tetapi saat ini bot "
            "tidak sedang menunggu bukti pembayaran."
        )
        return

    transaction_id = context.user_data.get(
        "transaction_id"
    )

    amount = context.user_data.get(
        "donation_amount"
    )

    if not transaction_id or not amount:
        await update.message.reply_text(
            "❌ Data transaksi tidak lengkap."
        )
        return

    photo = update.message.photo[-1]

    conn = get_db()

    conn.execute("""
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
        user.username or "-",
        amount,
        transaction_id,
        photo.file_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    amount_text = f"Rp{amount:,}".replace(",", ".")

    context.user_data.clear()

    await update.message.reply_text(
        "✅ *DONATION TERKIRIM*\n\n"
        f"💵 Nominal: *{amount_text}*\n"
        f"🧾 Transaction ID: `{transaction_id}`\n\n"
        "Bukti pembayaran sudah diterima.\n"
        "Silakan tunggu proses dari admin.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    print("ERROR:", context.error)


# =========================================================
# MAIN
# =========================================================

def main():

    init_db()

    # Jalankan server Flask untuk Render
    threading.Thread(
        target=run_web,
        daemon=True
    ).start()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(callback_handler)
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

    application.add_error_handler(
        error_handler
    )

    print("===================================")
    print("       AM PREM BOT STARTED")
    print("===================================")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
