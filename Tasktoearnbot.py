import time
import os
import telebot
import ReferAndEarnDb
from telebot import types
import requests


BOT_TOKEN = ""
bot = telebot.TeleBot(BOT_TOKEN)
CHANNELS = ["@"]
PAYOUT_CHANNEL = "@"
reward_amount = 1
currency = "TON"
min_withdraw = 1


@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    username = message.from_user.username or ""

    user, exists = ReferAndEarnDb.control_user("refer_and_earn.db", "user_exists", {"telegram_id": user_id})

    if not exists:
        if len(message.text.split()) > 1:
            ref_code = message.text.split()[1]
            if ref_code != user_id:
                referred_by = ref_code if ReferAndEarnDb.control_user("refer_and_earn.db","user_exists",{"telegram_id":ref_code}) else None
                ReferAndEarnDb.control_user(
                    "refer_and_earn.db",
                    "add_user",
                    {
                        "telegram_id": user_id,
                        "username": username,
                        "First_name": first_name,
                        "Last_name": last_name,

                        "referred_by": referred_by
                    }
                )
        else:

            referred_by = None
            ReferAndEarnDb.control_user(
                "refer_and_earn.db",
                "add_user",
                {
                    "telegram_id": user_id,
                    "username": username,
                    "First_name": first_name,
                    "Last_name": last_name,

                    "referred_by": referred_by
                }
            )
    keybord = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Joined", callback_data="joined")

    for i in CHANNELS:
        keybord.add(types.InlineKeyboardButton(f"Join {i}", url=f"https://t.me/{i[1:]}"))
    keybord.add(types.InlineKeyboardButton("Join Payout Channel", url=f"https://t.me/{PAYOUT_CHANNEL[1:]}"))
    keybord.add(button)
    bot.send_message(message.chat.id, f"Welcome {first_name}! \n Join Our Channels", parse_mode='Markdown', reply_markup=keybord)


@bot.callback_query_handler(func=lambda call: call.data == "joined")
def callback_query(call):
    user_id = str(call.from_user.id)
    user, user_exists = ReferAndEarnDb.control_user("refer_and_earn.db", "get_user", {"telegram_id": user_id})

    if not user_exists:
        bot.answer_callback_query(call.id, "User not found.", show_alert=True)
        return

    all_joined = True
    for channel in CHANNELS + [PAYOUT_CHANNEL]:
        try:
            member = bot.get_chat_member(channel, int(user_id))
            if member.status not in ['member', 'creator', 'administrator']:
                all_joined = False
                break
        except Exception:
            all_joined = False
            break

    if not all_joined:
        bot.answer_callback_query(call.id, "⚠ Please join all channels to proceed.", show_alert=True)
        return

    referred_by = user[6]
    if referred_by and referred_by != user_id:
        ref_user, ref_exists = ReferAndEarnDb.control_user("refer_and_earn.db", "get_user", {"telegram_id": referred_by})
        if ref_exists:
            referrals = ref_user[5]
            ref_list = referrals.split(",") if referrals else []

            if user_id not in ref_list:
                ref_list.append(user_id)
                new_referrals = ",".join(ref_list)

                ReferAndEarnDb.control_user(
                    "refer_and_earn.db",
                    "update_referrals",
                    {"telegram_id": referred_by, "new_referral_id": new_referrals}
                )

                new_balance = ref_user[7] + reward_amount
                ReferAndEarnDb.control_user(
                    "refer_and_earn.db",
                    "update_balance",
                    {"telegram_id": referred_by, "balance": new_balance}
                )

                bot.send_message(
                    referred_by,
                    f"🎉 Congratulations! You earned {reward_amount} TON for referring {user[3]}!"
                )
    keybord = types.InlineKeyboardMarkup()
    keybord.add(types.InlineKeyboardButton("💰 Check Balance", callback_data="check_balance"))
    keybord.add(types.InlineKeyboardButton("🔗 Refer More Friends", callback_data=f"refer_box"))
    keybord.add(types.InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"))
    keybord.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh"))
    bot.answer_callback_query(call.id, "✅ You have successfully joined!", show_alert=True)
    bot.send_message(user_id, "You have successfully joined all channels!", reply_markup=keybord)

@bot.callback_query_handler(func=lambda call: call.data == "check_balance")
def check_balance(call):
    user_id = str(call.from_user.id)
    user, user_exists = ReferAndEarnDb.control_user("refer_and_earn.db", "get_user", {"telegram_id": user_id})

    if not user_exists:
        bot.answer_callback_query(call.id, "User not found.", show_alert=True)
        return

    balance = user[7]


    bot.answer_callback_query(call.id)
    bot.send_message(
        user_id,
        f"💰 Your Balance: {balance} {currency}"
        f"\nEarn more by referring friends!"
    )

@bot.callback_query_handler(func=lambda call: call.data == "refer_box")
def refer_box(call):
    user_id = str(call.from_user.id)
    user, user_exists = ReferAndEarnDb.control_user("refer_and_earn.db", "get_user", {"telegram_id": user_id})

    if not user_exists:
        bot.answer_callback_query(call.id, "User not found.", show_alert=True)
        return


    bot.send_message(
        user_id,
        f"🔗 Share your referral link to invite friends and earn rewards!"
        f"\nYour referral link: https://t.me/{bot.get_me().username}?start={user_id}"
        f"\nYou earn {reward_amount} {currency} for each successful referral."
        f"\nYour total referrals: {len(user[5].split(',')) if user[5] else 0}"
    )
@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def withdraw(call):
    user_id = str(call.from_user.id)
    user, user_exists = ReferAndEarnDb.control_user("refer_and_earn.db", "get_user", {"telegram_id": user_id})

    if not user_exists:
        bot.answer_callback_query(call.id, "User not found.", show_alert=True)
        return

    balance = user[7]
    if balance < (min_withdraw):
        bot.answer_callback_query(call.id, f"⚠ Minimum withdrawal amount is {min_withdraw} {currency}.", show_alert=True)
        return
    new_balance = 0
    if ReferAndEarnDb.control_user("refer_and_earn.db", "update_balance", {"telegram_id": user_id,"balance":new_balance}):

        bot.send_message(PAYOUT_CHANNEL, f"💸 New withdrawal request from @{user[2]} (ID: {user_id})\nAmount: {balance} {currency}\nPlease process this request.")
        bot.answer_callback_query(call.id, "Withdrawal instructions sent!", show_alert=True)
        bot.send_message(user_id, "Your withdrawal request has been sent to the admin. You will be contacted soon.")
@bot.callback_query_handler(func=lambda call: call.data == "refresh")
def refresh(call):
    user_id = str(call.from_user.id)
    bot.answer_callback_query(call.id, "🔄 Refreshed!", show_alert=True)
    keybord = types.InlineKeyboardMarkup()
    keybord.add(types.InlineKeyboardButton("💰 Check Balance", callback_data="check_balance"))
    keybord.add(types.InlineKeyboardButton("🔗 Refer More Friends", callback_data=f"refer_box"))
    keybord.add(types.InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"))
    keybord.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh"))
    bot.send_message(user_id, "Menu refreshed!", reply_markup=keybord)

"""
SCHEMA
user[0] → id

user[1] → telegram_id

user[2] → username

user[3] → First_name

user[4] → Last_name

user[5] → referrals

user[6] → referred_by

user[7] → balance
"""

if __name__ == "__main__":
    ReferAndEarnDb.create_table("refer_and_earn.db")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"⚠️ Error occurred: {e}\nRestarting in 5 seconds...")
            time.sleep(5)
