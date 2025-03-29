from telethon import TelegramClient, events, Button
import requests
import json
import os
from dotenv import load_dotenv
import time
import asyncio

# 📌 Load environment variables from exelans.env file
load_dotenv(dotenv_path="exelans.env")  # .env yerine exelans.env dosyasını yükleyin

# 📌 Telegram API bilgileri
API_ID = int(os.getenv("API_ID"))  # Ensure the correct type (integer)
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
admin_ids = {int(id) for id in os.getenv("ADMIN_IDS").split(",")}  # Convert to set of integers
LIVE_CHAT_ID = [int(id) for id in os.getenv("LIVE_CHAT_ID").split(",")]
BIN_API_BASE = os.getenv("BIN_API_BASE")
headers = json.loads(os.getenv("HEADERS"))
API_URL = os.getenv("API_URL")
REQUIRED_CHANNEL = os.getenv("KANAL")
adres1 = os.getenv("adres1")

# 📌 Telethon istemcisi oluştur
client = TelegramClient("exelanschecker_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# 📌 İşlem durumunu takip eden değişken
processing = {}

# 📌 Kara liste kontrol fonksiyonu (örnek kontrol)
def is_blacklisted(user_id):
    # Kara listeye kontrol mekanizması ekleyebilirsiniz
    blacklisted_users = [1234567890, 9876543210]  # Örnek kara liste
    return user_id in blacklisted_users

# 📌 Kredi kartı doğrulama fonksiyonu
def check_card(card_details):
    url = f"{API_URL}{card_details}"  

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  
        return response.json()  
        
    except requests.exceptions.RequestException as e:
        return {"error": 1, "msg": f"API hatası: {str(e)}"}

# 📌 /start komutunu yakala
@client.on(events.NewMessage(pattern=r"^/start$"))
async def info(event):
    gif_file = "exelans.png"

    await event.reply(
        "🔹 **Merhaba!** Kredi kartı bilgilerini kontrol etmek için kartları atıp yanıtlayıp /check yazın:\n\n"
        "✅ **Tek kart:** `4111111111111111|12|2025|123`\n"
        "✅ **Toplu kart (Maksimum 50 kart):** Birden fazla kartı alt alta yazın:\n"
        "```\n4111111111111111|12|2025|123\n5222333344445555|05|2026|321\n```\n"
        "📌 **Kullanım örneği için /help komutunu kullanın"
        "🚨 **İşlemi durdurmak için** `/stop` yazabilirsiniz.",
        buttons=[
            [Button.url('➕ Beni Grubuna Ekle', 'https://t.me/zayexpay_bot_bot?startgroup=a')],
            [Button.url('📢 Kanal', 'https://t.me//tedemcc'), 
             Button.url('🧑🏻‍💻 Sahibim', 'https://t.me/redcavalry')],
            [Button.url('🧑🏻‍💻 Sahibim', 'https://t.me/zayamed')]
        ],
        link_preview=False,
        file=gif_file
    )

# 📌 /stop komutunu yakala
@client.on(events.NewMessage(pattern="^/stop$"))
async def stop(event):
    user_id = event.sender_id
    processing[user_id] = False  
    await event.respond("⏹ **İşlem durduruldu!** Yeni bir mesaj gönderene kadar API'ye istek yapılmayacak.")

# Kara listeyi okuyan fonksiyon
def is_blacklisted(user_id):
    try:
        with open("karaliste.txt", "r") as file:
            blacklisted_users = file.readlines()
        
        # Her bir kullanıcı ID'sini kontrol et
        for line in blacklisted_users:
            if line.strip() == str(user_id):  # Kullanıcı ID'si kara listede mi?
                return True  # Eğer ID kara listede ise True döner
        return False  # ID kara listede değilse False döner
    except FileNotFoundError:
        return False  # Eğer dosya bulunmazsa, kara listeyi kontrol edemeyiz, o zaman False döner

#kanali kontrol et 
async def is_user_subscribed(user_id):
    """Kullanıcının belirli bir kanala katılıp katılmadığını kontrol eder."""
    try:
        participant = await client.get_participants(REQUIRED_CHANNEL)
        return any(user.id == user_id for user in participant)
    except Exception:
        return False  # Kanal bulunamazsa veya hata olursa False döner
        
@client.on(events.NewMessage(pattern=r"^/check$"))
async def check_cards_command(event):
    """Yanıtlanan mesajdaki kartları işler. Kara liste kontrolü yapar."""
    user_id = event.sender_id
    
    # Kara liste kontrolü
    if is_blacklisted(user_id):
        await event.reply("🚫 **Kara listeye eklenmişsiniz!** Geliştirici ile iletişime geçiniz.")
        return

       # Kullanıcının kanala katılıp katılmadığını kontrol et
    if not await is_user_subscribed(user_id):
        await event.reply(
            "📢 **Bu komutu kullanabilmek için kanalımıza katılmanız gerekmektedir!**",
            buttons=[Button.url("🔗 Kanala Katıl", f"https://t.me/{REQUIRED_CHANNEL.strip('@')}")]
        )
        return
    # Eğer komuta yanıt olarak kart listesi yoksa uyarı ver
    if not event.reply_to_msg_id:
        await event.reply("⚠️ **Lütfen komuta yanıt olarak kartları gönderin.**")
        return
        
    # Yanıtlanan mesajı al
    replied_message = await event.get_reply_message()
    if not replied_message.text:
        await event.reply("⚠️ **Yanıtladığınız mesajda kart bilgisi bulunamadı!**")
        return

    # Kartları al ve işle
    cards = replied_message.text.strip().split("\n")

    # Eğer kart sayısı 50'den fazlaysa işlem yapma
    if len(cards) > 50:
        await event.reply("🚨 **Üzgünüm!** En fazla 50 kart kontrol edebilirsiniz.\n📌 **Lütfen kart sayısını azaltın.**")
        return

    # Kartları işlemeye başla
    await process_cards(event, cards, user_id)


async def process_cards(event, cards, user_id):
    """Kredi kartlarını kontrol eder ve sonuçları gönderir."""
    processing[user_id] = True  

    for card in cards:
        if not processing.get(user_id, True):
            await event.reply("⏹ **İşlem durduruldu!** Yeni bir mesaj gönderene kadar API'ye istek yapılmayacak.")
            return

        card_info = card.strip().split("|")

        # Kart bilgileri doğru formatta mı kontrol et
        if len(card_info) != 4:
            await event.reply(f"⚠️ **Hatalı format:** `{card}`\n📌 **Doğru format:** `KARTNUMARASI|AY|YIL|CVV`", parse_mode="Markdown")
            continue  

        card_number, exp_month, exp_year, cvv = card_info
        
        # Kredi kartını kontrol et
        result = check_card(f"{card_number}|{exp_month}|{exp_year}|{cvv}")
        
        if "error" in result and result["error"] == 1:
            reply = f"❌ **API HATASI:** `{card}`\n"
        else:
            bank_name = result.get("bankName", "Bilinmiyor")
            status = result.get("status", "Bilinmiyor")
            
            reply = (
                f"✅ **Kart:** `{card}`\n"
                f"🏦 **Banka:** {bank_name}\n"
                f"📌 **Durum:** {status}\n"
            )

        # Kullanıcıya kartın durumu hakkında cevap gönder
        await event.reply(reply)

        # Eğer kart geçerli ise, canlı kartı başkalarına gönder
        if status.lower() == "live":
            live_message = (
                f"✅ **Geçerli Kart:** `{card}`\n"
                f"🏦 **Banka:** {bank_name}\n"
            )
            for chat_id in LIVE_CHAT_ID:
                await client.send_message(chat_id, live_message)

# 📌 /help komutunu yakala
@client.on(events.NewMessage(pattern="^/help$"))
async def help(event):
    user_id = event.sender_id
    # Resim dosyasının botun çalıştığı dizinde olması gerektiğini unutmayın
    image_file = "checker.jpg"  # Resim dosyasının adı

    # Resim gönderme
    try:
        await event.reply("🖼️ **Yardım resmi gönderiliyor...**")
        await client.send_file(user_id, image_file)
    except Exception as e:
        await event.reply(f"❌ **Hata oluştu:** {str(e)}")
        
# 📌 Kara listeye eklemek için fonksiyon
def add_to_blacklist(user_id):
    with open("karaliste.txt", "a") as file:
        file.write(f"{user_id}\n")

# 📌 Kara listeden çıkarmak için fonksiyon
def remove_from_blacklist(user_id):
    try:
        with open("karaliste.txt", "r") as file:
            blacklisted_users = file.readlines()
        
        with open("karaliste.txt", "w") as file:
            for line in blacklisted_users:
                if line.strip() != str(user_id):  # Eğer ID kara listede değilse, tekrar yaz
                    file.write(line)
    except FileNotFoundError:
        pass

# 📌 /block komutunu yakala
@client.on(events.NewMessage(pattern="^/block (\\d+)$"))
async def block(event):
    user_id = event.sender_id
    if user_id not in admin_ids:
        await event.reply("🚫 **Yetkisiz erişim!** Bu komutu yalnızca adminler kullanabilir.")
        return

    blocked_user_id = int(event.raw_text.split()[1])  # Block edilen kullanıcı ID'si
    add_to_blacklist(blocked_user_id)
    await event.reply(f"🚫 **{blocked_user_id}** başarıyla kara listeye eklendi.")

# 📌 /unblock komutunu yakala
@client.on(events.NewMessage(pattern="^/unblock (\\d+)$"))
async def unblock(event):
    user_id = event.sender_id
    if user_id not in admin_ids:
        await event.reply("🚫 **Yetkisiz erişim!** Bu komutu yalnızca adminler kullanabilir.")
        return

    unblocked_user_id = int(event.raw_text.split()[1])  # Unblock edilen kullanıcı ID'si
    remove_from_blacklist(unblocked_user_id)
    await event.reply(f"✅ **{unblocked_user_id}** kara listeden başarıyla çıkarıldı.")
    
        # chatid kaydetme
@client.on(events.ChatAction)
async def new_member(event):
    if event.user_added or event.user_joined:
        for user in event.users:
            if user.id == (await client.get_me()).id:  # Botun kendisi
                chat_id = event.chat_id
                save_chat_id(chat_id)
                await client.send_message(chat_id, "ᴍᴇʀʜᴀʙᴀ ɢʀᴜʙᴀ ᴇᴋʟᴇᴅɪ̇ɢ̆ɪ̇ɴɪ̇ᴢ ɪ̇ᴄ̧ɪ̇ɴ ᴛᴇꜱ̧ᴇᴋᴋᴜ̈ʀ ᴇᴅᴇʀɪ̇ᴍ")

 # 📌 Chat ID'leri kaydetme fonksiyonu
def save_chat_id(chat_id):
    """Chat ID'leri `chats.txt` dosyasına kaydeder, eğer zaten kayıtlıysa eklemez."""
    try:
        with open("chats.txt", "r") as file:
            chat_ids = {int(line.strip()) for line in file.readlines()}  # Set olarak oku
    except FileNotFoundError:
        chat_ids = set()

    if chat_id not in chat_ids:
        with open("chats.txt", "a") as file:
            file.write(f"{chat_id}\n")  # Yeni ID'yi ekle

# 📌 Bot gruba eklendiğinde chat ID'yi kaydetme
@client.on(events.ChatAction)
async def new_member(event):
    if event.user_added or event.user_joined:
        for user in event.users:
            if user.id == (await client.get_me()).id:  # Botun kendisi mi eklendi?
                chat_id = event.chat_id
                save_chat_id(chat_id)  # Chat ID'yi kaydet
                await client.send_message(chat_id, "✅ **Bot gruba eklendi!** Mesajlarınızı buradan kontrol edebilirsiniz.")

# 📌 /statik komutu - Kullanıcı ve grup sayısını göster
@client.on(events.NewMessage(pattern='/statik'))
async def statik_command(event):
    if event.sender_id not in admin_ids:
        await event.reply("🚫 **Bu komutu kullanma yetkiniz yok!**")
        return

    try:
        with open("chats.txt", "r") as file:
            chat_ids = {int(line.strip()) for line in file.readlines()}  # Set olarak oku

        user_ids = {chat_id for chat_id in chat_ids if chat_id >= 0}  # Bireysel kullanıcılar
        group_ids = {chat_id for chat_id in chat_ids if chat_id < 0}  # Gruplar

        await event.reply(
            f"📊 **Kayıtlı Kullanıcılar ve Gruplar**\n\n"
            f"👤 **Bireysel Kullanıcılar:** {len(user_ids)}\n"
            f"👥 **Gruplar:** {len(group_ids)}"
        )
    except FileNotFoundError:
        await event.reply("⚠️ **Henüz hiçbir kullanıcı veya grup kayıtlı değil.**")

# 📌 Botla özel mesajlaşan kullanıcıları kaydetme
@client.on(events.NewMessage(func=lambda event: event.is_private))
async def handle_private_message(event):
    chat_id = event.chat_id
    save_chat_id(chat_id)  # Chat ID'yi kaydet

# 📌 /broadcast komutu - Adminler duyuru yapabilir
@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast_message(event):
    """Adminlerin botu kullanan herkese duyuru yapmasını sağlar."""
    if event.sender_id not in admin_ids:
        await event.reply("🚫 **Bu komutu kullanma yetkiniz yok!**")
        return

    if event.is_reply:
        original_message = await event.get_reply_message()

        try:
            with open("chats.txt", "r") as file:
                chat_ids = {int(line.strip()) for line in file.readlines()}  # Set olarak oku

            sent_count = 0
            for chat_id in chat_ids:
                try:
                    await client.forward_messages(chat_id, original_message)  # Mesajı yönlendir
                    sent_count += 1
                except Exception:
                    pass  # Hata mesajlarını gizle

            await event.reply(f"✅ **Mesaj başarıyla {sent_count} kişiye/gruba iletildi.**")
        except FileNotFoundError:
            await event.reply("⚠️ **Henüz hiçbir kullanıcı veya grup kayıtlı değil.**")
    else:
        await event.reply("⚠️ **Lütfen duyuruyu içeren mesaja yanıt olarak /broadcast yazın.**")         
# Karalisteyi kontrol eden fonksiyon
def is_blacklisted(user_id):
    try:
        with open("karaliste.txt", "r") as file:
            blacklisted_ids = file.read().splitlines()  # Satırları listeye çevir
        return str(user_id) in blacklisted_ids  # Kullanıcı ID'si karalistede mi kontrol et
    except FileNotFoundError:
        return False  # Eğer dosya yoksa kimse yasaklı değil

# Kart bilgilerini sorgulayan fonksiyon
def get_bin_info(bin_number):
    api_url = f"{os.getenv('BIN_API_BASE')}{bin_number}"  

    try:
        response = requests.get(api_url, headers=json.loads(os.getenv("HEADERS")))  
        
        if response.status_code != 200:
            return "⚠️ Hatalı veya geçersiz kart numarası! Lütfen kontrol edip tekrar deneyin."
        
        data = response.json()
        
        if not data or "bank" not in data:
            return "⚠️ Geçersiz veya bulunamayan BIN numarası!"

        card_info = (
            f"💳 **Kart Bilgileri:**\n"
            f"• **Şema (Scheme):** {data.get('scheme', 'Bilinmiyor')}\n"
            f"• **Tip:** {data.get('type', 'Bilinmiyor')}\n"
            f"• **Marka:** {data.get('brand', 'Bilinmiyor')}\n"
            f"• **Ön Ödemeli mi?:** {'Evet' if data.get('prepaid') else 'Hayır'}\n\n"
            
            f"🌍 **Ülke Bilgisi:**\n"
            f"• **Ülke:** {data.get('country', {}).get('name', 'Bilinmiyor')} ({data.get('country', {}).get('alpha2', '-')}) {data.get('country', {}).get('emoji', '')}\n"
            f"• **Para Birimi:** {data.get('country', {}).get('currency', 'Bilinmiyor')}\n"
            f"• **Konum:** 📍 {data.get('country', {}).get('latitude', 'Bilinmiyor')}, {data.get('country', {}).get('longitude', 'Bilinmiyor')}\n\n"
            
            f"🏦 **Banka Bilgileri:**\n"
            f"• **Banka:** {data.get('bank', {}).get('name', 'Bilinmiyor')}\n"
            f"• **Web:** {data.get('bank', {}).get('url', 'Yok')}\n"
            f"• **Telefon:** {data.get('bank', {}).get('phone', 'Yok')}\n"
            f"• **Şehir:** {data.get('bank', {}).get('city', 'Bilinmiyor')}"
        )
        return card_info
    
    except Exception as e:
        return f"❌ Hata: {str(e)}"
                            
                                                       
# /bin komutu → Kullanıcıdan kart numarasını alır, önce karalisteyi kontrol eder, sonra çalıştırır
@client.on(events.NewMessage(pattern=r'/bin (\d{13,19}\|\d{2}\|\d{4}\|\d{3})'))
async def bin_checker(event):
    user_id = event.sender_id  # Kullanıcının Telegram ID'sini al
    
    # Kullanıcı karalistede mi kontrol et
    if is_blacklisted(user_id):
        await event.reply("🚫 **Kara listeye eklenmişsiniz!** Lütfen admin ile iletişime geçin.")
        return

    card_info = event.pattern_match.group(1)  
    card_number = card_info.split("|")[0][:6]  

    if not card_number.isdigit() or len(card_number) != 6:
        await event.reply("⚠️ Geçersiz kart numarası! Lütfen geçerli bir kart numarası girin.")
        return

#adres ilemci
async def get_address(tc):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    if "error" in data and data["error"] == "Sonuç bulunamadı":
                        return "Sonuç bulunamadı."
                    return "Adres bilgisi bulundu."
                except aiohttp.ContentTypeError:
                    return "Hata: Geçersiz içerik türü alındı, API yanıtı JSON formatında değil."
            else:
                return "Hata: API'ye erişilemiyor."

@client.on(events.NewMessage(pattern='/adres'))
async def adres_handler(event):
    args = event.message.text.split()
    if len(args) < 2:
        await event.reply("Lütfen bir TC numarası girin. Örnek: /adres 12345678901")
        return
    
    tc = args[1]
    if not tc.isdigit() or len(tc) != 11:
        await event.reply("Geçerli bir 11 haneli TC numarası girin.")
        return
    
    await event.reply("Adres bilgisi sorgulanıyor, lütfen bekleyin...")
    address_info = await get_address(tc)
    await event.reply(address_info)
                     
# 📌 Botu başlat
print("✅ **Bot çalışıyor...**")  
client.run_until_disconnected()
