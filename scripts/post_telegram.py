"""
post_telegram.py
Reads today's posts from Google Sheets, generates images via Gemini,
posts to Telegram channels, updates status, sends admin notification.
"""

import os, json, base64, io, time, requests, gspread
from datetime import date
from PIL import Image
from google import genai
from google.genai import types
from google.oauth2.service_account import Credentials

TODAY          = date.today().strftime("%d.%m.%Y")
DAY            = os.environ.get("DAY", "monday")
BOT_TOKEN      = os.environ["TELEGRAM_BOT_TOKEN"]
NOTIFY_CHAT_ID = os.environ.get("TELEGRAM_NOTIFY_CHAT_ID", "")
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GEMINI_KEY     = os.environ["GEMINI_API_KEY"]

IMAGE_MODEL    = "gemini-2.5-flash-image"
IMAGE_W, IMAGE_H = 1280, 720

# ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ ACTIVE CHANNELS (add others after configuring them) ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ
CHANNEL_IDS = {
    "@esimfrance": "-1002450687148",
    # "@esimthailand":       "-1001000000002",  # TODO: add real ID
    # "@esimvietnam":        "-1001000000003",  # TODO: add real ID
    # "@esimeurope":         "-1001000000004",
    # "@esimafrica":         "-1001000000005",
    # "@esimHongKong":       "-1001000000006",
    # "@esimindonesia":      "-1001000000007",
    # "@esimrussian":        "-1001000000008",
    # "@esimphilippine":     "-1001000000009",
    # "@eSIMmalaysia":       "-1001000000010",
    # "@CambodiaeSIM":       "-1001000000011",
    # "@esimamerica":        "-1001000000012",
    # "@esimsdata_official": "-1001000000013",
    # "@esimway":            "-1001000000014",
    # "@esimanonymous":      "-1001000000015",
}

CHANNEL_META = {
    "@esimfrance":         {"country":"France",      "city":"Paris",       "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ«ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ·","operator":"Orange France"},
    "@esimthailand":       {"country":"Thailand",    "city":"Bangkok",     "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¹ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ­","operator":"AIS"},
    "@esimvietnam":        {"country":"Vietnam",     "city":"Hanoi",       "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ»ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ³","operator":"MobiFone"},
    "@esimeurope":         {"country":"Europe",      "city":"EU cities",   "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ","operator":"Orange / Vodafone"},
    "@esimafrica":         {"country":"Africa",      "city":"varies",      "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ","operator":"Airtel / MTN"},
    "@esimHongKong":       {"country":"Hong Kong",   "city":"Hong Kong",   "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ­ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ°","operator":"HKT / 3HK"},
    "@esimindonesia":      {"country":"Indonesia",   "city":"Bali",        "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ®ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ©","operator":"Indosat / Telkomsel"},
    "@esimrussian":        {"country":"Russia",      "city":"Moscow",      "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ·ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂº","operator":"MegaFon"},
    "@esimphilippine":     {"country":"Philippines", "city":"Manila",      "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂµÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ­","operator":"Globe Telecom"},
    "@eSIMmalaysia":       {"country":"Malaysia",    "city":"Kuala Lumpur","flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ²ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¾","operator":"Maxis / U Mobile"},
    "@CambodiaeSIM":       {"country":"Cambodia",    "city":"Phnom Penh",  "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ­","operator":"Metfone"},
    "@esimamerica":        {"country":"USA",         "city":"New York",    "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂºÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¸","operator":"AT&T / Verizon"},
    "@esimsdata_official": {"country":"global",      "city":"travel",      "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ","operator":"various"},
    "@esimway":            {"country":"global",      "city":"travel",      "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ","operator":"various"},
    "@esimanonymous":      {"country":"global",      "city":"anonymous",   "flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ","operator":"anonymous"},
}

RUBRIC_MOOD = {
    "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¶ Plan spotlight":   "energetic, modern, travel-ready ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ smartphone with signal bars, city skyline",
    "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ Travel guide":     "adventurous, warm, discovery ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ traveler with phone against iconic landmark",
    "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ Privacy":          "dark, mysterious, secure ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ glowing shield, anonymous figure, deep shadows",
    "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ° News":             "dynamic, editorial, tech ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ abstract network signals, urban nightscape",
    "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ Voice + Data":     "connected, local, premium ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ smartphone close-up showing local number",
    "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ Seasonal":         "vibrant, joyful, travel lifestyle ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ airport departure or scenic destination",
    "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ± App feature":      "clean, minimal, tech UI ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ floating smartphone with app interface glow",
    "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ Islamic seasonal": "warm, golden, respectful ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ crescent moon, mosque silhouette, soft light",
}

def build_image_prompt(channel, rubric, post_text, img_description):
    meta = CHANNEL_META.get(channel, {"country":"global","city":"travel","flag":"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ","operator":"various"})
    country  = meta["country"]
    city     = meta["city"]
    flag     = meta["flag"]
    operator = meta["operator"]
    mood     = RUBRIC_MOOD.get(rubric, "professional, travel tech, dark premium")
    context_lines = [l.strip() for l in post_text.split("\n")
                     if l.strip() and not l.startswith("http") and len(l.strip()) > 10]
    context = context_lines[0][:80] if context_lines else ""
    logo_hint = ""
    if rubric in ("ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¶ Plan spotlight", "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ Voice + Data") and operator not in ("various", "anonymous"):
        logo_hint = f"The {operator} operator logo subtly visible on the smartphone screen."
    return f"""Cinematic dark tech aesthetic. Deep navy and dark purple tones with subtle blue-purple gradient lighting. Premium, minimalist, editorial photography style. eSIM digital connectivity and travel theme.

Country/Region: {country} {flag}. City reference: {city}.
Rubric mood: {mood}.
Post context: {context}
Visual description: {img_description}
{logo_hint}

No text overlays, no QR codes, no watermarks. 16:9 landscape format, 1280x720.""".strip()

def generate_image(channel, rubric, post_text, img_description):
    client = genai.Client(api_key=GEMINI_KEY)
    prompt = build_image_prompt(channel, rubric, post_text, img_description)
    print(f"    Gemini prompt preview: {prompt[:100]}...")
    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE","TEXT"])
        )
        for part in response.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                img = Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
                if img.size != (IMAGE_W, IMAGE_H):
                    img = img.resize((IMAGE_W, IMAGE_H), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                buf.seek(0)
                print(f"    Image OK ({img.size[0]}x{img.size[1]})")
                return buf
        print("    No image in response")
        return None
    except Exception as e:
        print(f"    Gemini error: {e}")
        return None

def get_sheets_client():
    creds_json = json.loads(base64.b64decode(os.environ["GOOGLE_CREDENTIALS"]))
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
    return gspread.authorize(creds)

def get_today_posts(sheets, sheet_name):
    try:
        ws = sheets.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        rows = ws.get_all_records()
        for i, r in enumerate(rows[:3]):
            print(f"  DEBUG row {i+2}: date='{r.get('ÃÂÃÂ°ÃÂÃÂ° ÃÂ¿ÃÂÃÂ±ÃÂ»ÃÂ¸ÃÂºÃÂ°ÃÂÃÂ¸ÃÂ¸','?')}' status='{r.get('ÃÂ¡ÃÂÃÂ°ÃÂÃÂÃÂ','?')}'")
        return [(i+2, r) for i, r in enumerate(rows)
                if str(r.get("ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ° ÃÂÃÂÃÂÃÂ¿ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ±ÃÂÃÂÃÂÃÂ»ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂºÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ¸","")).strip() == TODAY
                and "Draft" in str(r.get("ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ",""))]
    except Exception as e:
        print(f"  Sheet error [{sheet_name}]: {e}")
        return []

def update_status(sheets, sheet_name, row_index):
    try:
        ws = sheets.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        ws.update_cell(row_index, 7, "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ Published")
        ws.update_cell(row_index, 8, TODAY)
    except Exception as e:
        print(f"  Status update error: {e}")

def tg_send_photo(chat_id, image_buf, caption):
    resp = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
        files={"photo": ("post.jpg", image_buf, "image/jpeg")},
        timeout=30,
    )
    return resp.json()

def tg_send_message(chat_id, text):
    resp = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    return resp.json()

def notify_admin(message):
    if NOTIFY_CHAT_ID:
        tg_send_message(NOTIFY_CHAT_ID, message)

def main():
    print(f"\n{'='*50}")
    print(f"  eSIM Telegram bot | {DAY.upper()} | {TODAY}")
    print(f"{'='*50}\n")
    sheets = get_sheets_client()
    sent, errors = [], []

    for channel, channel_id in CHANNEL_IDS.items():
        posts = get_today_posts(sheets, channel)
        if not posts:
            print(f"  {channel}: no post today")
            continue
        row_idx, row = posts[0]
        rubric    = str(row.get("ÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ±ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂºÃÂÃÂÃÂÃÂ°","")).strip()
        post_text = str(row.get("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂºÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¿ÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ° (EN)","")).strip()
        link      = str(row.get("ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ»ÃÂÃÂÃÂÃÂºÃÂÃÂÃÂÃÂ°","")).strip()
        img_desc  = str(row.get("ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¿ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂµ ÃÂÃÂÃÂÃÂºÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂºÃÂÃÂÃÂÃÂ¸","travel landscape")).strip()
        print(f"\n  {channel} | {rubric}")
        caption = f"{post_text}\n\n{link}" if link else post_text
        caption = caption[:1024]
        img_buf = generate_image(channel, rubric, post_text, img_desc)
        try:
            result = tg_send_photo(channel_id, img_buf, caption) if img_buf else tg_send_message(channel_id, caption)
            if result.get("ok"):
                update_status(sheets, channel, row_idx)
                sent.append(f"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ {channel} ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ {rubric}")
                print(f"    Posted ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ")
            else:
                err = result.get("description","unknown")
                errors.append(f"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ {channel}: {err}")
                print(f"    Error: {err}")
        except Exception as e:
            errors.append(f"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ {channel}: {e}")
            print(f"    Exception: {e}")
        time.sleep(2)

    report = (f"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ <b>eSIM Telegram report</b>\n"
              f"ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ {TODAY} ({DAY.capitalize()})\n"
              f"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ Sent: {len(sent)} / {len(sent)+len(errors)}\n")
    if sent:   report += "\n" + "\n".join(sent)
    if errors: report += "\n\nÃÂÃÂ¢ÃÂÃÂÃÂÃÂ ÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ <b>Errors:</b>\n" + "\n".join(errors)
    notify_admin(report)
    print(f"\n{'='*50}")
    print(f"  Done: {len(sent)} sent, {len(errors)} errors")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
