"""
post_telegram.py
Reads posts from Google Sheets (English headers: num,rubric,topic,text,link,img_desc,status,date)
Generates images via Gemini, posts to Telegram, updates status.
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

IMAGE_MODEL      = "gemini-2.5-flash-image"
IMAGE_W, IMAGE_H = 1280, 720

CHANNEL_IDS = {
    "@esimfrance": "-1002450687148",
}

CHANNEL_META = {
    "@esimfrance":         {"country": "France",      "city": "Paris",      "operator": "Orange France"},
    "@esimthailand":       {"country": "Thailand",    "city": "Bangkok",    "operator": "AIS"},
    "@esimvietnam":        {"country": "Vietnam",     "city": "Hanoi",      "operator": "MobiFone"},
    "@esimeurope":         {"country": "Europe",      "city": "EU cities",  "operator": "Orange"},
    "@esimafrica":         {"country": "Africa",      "city": "varies",     "operator": "Airtel"},
    "@esimHongKong":       {"country": "Hong Kong",   "city": "Hong Kong",  "operator": "HKT"},
    "@esimindonesia":      {"country": "Indonesia",   "city": "Bali",       "operator": "Indosat"},
    "@esimrussian":        {"country": "Russia",      "city": "Moscow",     "operator": "MegaFon"},
    "@esimphilippine":     {"country": "Philippines", "city": "Manila",     "operator": "Globe"},
    "@eSIMmalaysia":       {"country": "Malaysia",    "city": "KL",         "operator": "Maxis"},
    "@CambodiaeSIM":       {"country": "Cambodia",    "city": "Phnom Penh", "operator": "Metfone"},
    "@esimamerica":        {"country": "USA",         "city": "New York",   "operator": "AT&T"},
    "@esimsdata_official": {"country": "global",      "city": "travel",     "operator": "various"},
    "@esimway":            {"country": "global",      "city": "travel",     "operator": "various"},
    "@esimanonymous":      {"country": "global",      "city": "anonymous",  "operator": "anonymous"},
}

RUBRIC_MOOD = {
    "Plan spotlight":  "energetic, modern, travel-ready -- smartphone with signal bars, city skyline",
    "Travel guide":    "adventurous, warm, discovery -- traveler with phone against iconic landmark",
    "Privacy":         "dark, mysterious, secure -- glowing shield, anonymous figure, deep shadows",
    "News":            "dynamic, editorial, tech -- abstract network signals, urban nightscape",
    "Voice":           "connected, local, premium -- smartphone close-up showing local number",
    "Seasonal":        "vibrant, joyful, travel lifestyle -- airport departure or scenic destination",
    "App feature":     "clean, minimal, tech UI -- floating smartphone with app interface glow",
    "Islamic":         "warm, golden, respectful -- crescent moon, mosque silhouette, soft light",
}


def build_prompt(channel, rubric, post_text, img_desc):
    meta     = CHANNEL_META.get(channel, {"country": "global", "city": "travel", "operator": "various"})
    operator = meta["operator"]
    mood     = "professional, travel tech, dark premium"
    for key, val in RUBRIC_MOOD.items():
        if key.lower() in rubric.lower():
            mood = val
            break
    lines   = [l.strip() for l in post_text.split("\n")
               if l.strip() and not l.startswith("http") and len(l.strip()) > 10]
    context = lines[0][:80] if lines else ""
    logo    = ""
    if ("plan" in rubric.lower() or "voice" in rubric.lower()) and operator not in ("various", "anonymous"):
        logo = f"The {operator} operator logo subtly visible on the smartphone screen."
    return (
        f"Cinematic dark tech aesthetic. Deep navy and dark purple tones with subtle "
        f"blue-purple gradient lighting. Premium, minimalist, editorial photography style. "
        f"eSIM digital connectivity and travel theme.\n\n"
        f"Country: {meta['country']}. City: {meta['city']}.\n"
        f"Rubric mood: {mood}.\n"
        f"Post context: {context}\n"
        f"Visual: {img_desc}\n"
        f"{logo}\n\n"
        f"No text overlays, no QR codes, no watermarks. 16:9 landscape 1280x720."
    ).strip()


def generate_image(channel, rubric, post_text, img_desc):
    client = genai.Client(api_key=GEMINI_KEY)
    prompt = build_prompt(channel, rubric, post_text, img_desc)
    print(f"    Gemini image: {prompt[:80]}...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            )
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                img = Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
                if img.size != (IMAGE_W, IMAGE_H):
                    img = img.resize((IMAGE_W, IMAGE_H), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                buf.seek(0)
                print(f"    Image OK {img.size}")
                return buf
        print("    No image in response")
        return None
    except Exception as e:
        print(f"    Gemini error: {e}")
        return None

def get_sheets_client():
    creds_json = json.loads(base64.b64decode(os.environ["GOOGLE_CREDENTIALS"]))
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
    return gspread.authorize(creds)


def get_today_posts(sheets, sheet_name):
    # Sheet headers (row 1): num, rubric, topic, text, link, img_desc, status, date
    try:
        ws   = sheets.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        rows = ws.get_all_records()
        print(f"  {sheet_name}: {len(rows)} rows, keys: {list(rows[0].keys()) if rows else 'empty'}")
        return [
            (i + 2, r) for i, r in enumerate(rows)
            if str(r.get("date", "")).strip() == TODAY
            and "Draft" in str(r.get("status", ""))
        ]
    except Exception as e:
        print(f"  Sheet error [{sheet_name}]: {e}")
        return []


def update_status(sheets, sheet_name, row_index):
    try:
        ws = sheets.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        ws.update_cell(row_index, 7, "Published")
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
        rubric    = str(row.get("rubric", "")).strip()
        post_text = str(row.get("text", "")).strip()
        link      = str(row.get("link", "")).strip()
        img_desc  = str(row.get("img_desc", "travel landscape eSIM")).strip()
        print(f"\n  {channel} | {rubric}")
        caption = f"{post_text}\n\n{link}" if link else post_text
        caption = caption[:1024]
        img_buf = generate_image(channel, rubric, post_text, img_desc)
        try:
            result = (tg_send_photo(channel_id, img_buf, caption)
                      if img_buf else tg_send_message(channel_id, caption))
            if result.get("ok"):
                update_status(sheets, channel, row_idx)
                sent.append(f"OK {channel} - {rubric}")
                print("    Posted OK")
            else:
                err = result.get("description", "unknown")
                errors.append(f"ERR {channel}: {err}")
                print(f"    Error: {err}")
        except Exception as e:
            errors.append(f"ERR {channel}: {e}")
            print(f"    Exception: {e}")
        time.sleep(2)

    report = (f"eSIM Telegram report\n{TODAY} ({DAY})\n"
              f"Sent: {len(sent)} / {len(sent) + len(errors)}\n")
    if sent:
        report += "\n" + "\n".join(sent)
    if errors:
        report += "\nErrors:\n" + "\n".join(errors)
    notify_admin(report)
    print(f"\n{'='*50}")
    print(f"  Done: {len(sent)} sent, {len(errors)} errors")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
