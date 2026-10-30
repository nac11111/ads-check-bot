import os
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "9174103618:AAE2VDX3A_m3eygMT_AjWkeXUAfx-I1-5-w"
AD_LINK = "https://example.com"

bot = Bot(token=TOKEN)
dp = Dispatcher()

REWARD_PER_AD = 500.0  
MIN_WITHDRAW = 50000.0 

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance_vnd REAL DEFAULT 0.0,
            ads_watched INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (user_id, username, balance_vnd, ads_watched) VALUES (?, ?, 0.0, 0)', (user.id, user.username))
        conn.commit()
    conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 Xem Quảng Cáo Kiếm Tiền", callback_data="watch_ad")],
        [InlineKeyboardButton(text="💰 Số Dư Của Tôi", callback_data="check_balance"),
         InlineKeyboardButton(text="🤝 Giới Thiệu Bạn Bè", callback_data="referral")],
        [InlineKeyboardButton(text="💳 Rút Tiền VNĐ", callback_data="withdraw")]
    ])
    
    await message.answer(
        f"👋 Chào mừng **{user.first_name}** đến với hệ thống Kiếm Tiền VNĐ!\n\n"
        "Hãy bấm nút bên dưới để bắt đầu xem quảng cáo và tích lũy số dư vào ví nhé.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "check_balance")
async def process_balance(callback: types.CallbackQuery):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance_vnd, ads_watched FROM users WHERE user_id = ?', (callback.from_user.id,))
    res = cursor.fetchone()
    conn.close()
    balance, ads = res if res else (0.0, 0)
    
    await callback.message.answer(
        f"📊 **Thông tin tài khoản của bạn:**\n\n"
        f"💵 Số dư: `{balance:,.0f} VNĐ`\n"
        f"📺 Đã xem: `{ads}` quảng cáo",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "watch_ad")
async def process_watch_ad(callback: types.CallbackQuery):
    ad_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Mở Link Quảng Cáo", url=AD_LINK)],
        [InlineKeyboardButton(text="✅ Xác Nhận Đã Xem (Nhận Thưởng)", callback_data="claim_reward")]
    ])
    
    await callback.message.answer(
        f"📢 **Nhiệm vụ xem quảng cáo:**\n\n"
        f"1. Bấm vào nút **'Mở Link Quảng Cáo'** bên dưới.\n"
        f"2. Đợi trên trang web khoảng 10-15 giây.\n"
        f"3. Quay lại đây và bấm **'Xác Nhận Đã Xem'** để nhận ngay `+{REWARD_PER_AD:,.0f} VNĐ`.",
        reply_markup=ad_keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "claim_reward")
async def process_claim(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance_vnd = balance_vnd + ?, ads_watched = ads_watched + 1 WHERE user_id = ?', (REWARD_PER_AD, user_id))
    conn.commit()
    cursor.execute('SELECT balance_vnd FROM users WHERE user_id = ?', (user_id,))
    balance = cursor.fetchone()[0]
    conn.close()
    
    await callback.message.answer(
        f"🎉 Chúc mừng! Bạn nhận thành công `+{REWARD_PER_AD:,.0f} VNĐ`.\n"
        f"💰 Số dư hiện tại: `{balance:,.0f} VNĐ`",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "withdraw")
async def process_withdraw(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance_vnd FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    balance = res[0] if res else 0.0
    
    if balance < MIN_WITHDRAW:
        await callback.message.answer(
            f"⚠️ **Chưa đủ điều kiện rút tiền!**\n\n"
            f"Số dư hiện tại của bạn: `{balance:,.0f} VNĐ`\n"
            f"Hạn mức rút tối thiểu là: `{MIN_WITHDRAW:,.0f} VNĐ`\n"
            f"Hãy xem thêm quảng cáo để đạt mốc rút nhé!"
        )
    else:
        await callback.message.answer(
            f"💳 **Yêu cầu rút tiền VNĐ:**\n\n"
            f"Số dư khả dụng: `{balance:,.0f} VNĐ`\n\n"
            f"Vui lòng gửi thông tin rút tiền theo cú pháp:\n"
            f"`Rút [Số tiền] - [Ngân hàng/Momo] - [Số tài khoản] - [Tên chủ tài khoản]`"
        )
    await callback.answer()

@dp.callback_query(F.data == "referral")
async def process_referral(callback: types.CallbackQuery):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    await callback.message.answer(
        f"🤝 **Giới thiệu bạn bè:**\n\n"
        f"Chia sẻ đường link sau cho bạn bè. Khi họ tham gia, bạn sẽ nhận được hoa hồng:\n`{ref_link}`",
        parse_mode="Markdown"
    )
    await callback.answer()

async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
