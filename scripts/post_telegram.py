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
IMAGE_W, IMAGE_H = 1280, 670

CHANNEL_IDS = {
    "@esimfrance":         "-1002450687148",
    "@esimthailand":       "-1002194034807",
    "@esimvietnam":        "-1002224251795",
    "@esimeurope":         "-1002286006244",
    "@esimafrica":         "-1002348896395",
    "@esimHongKong":       "-1002258444792",
    "@esimindonesia":      "-1002407600794",
    "@esimrussian":        "-1002254473506",
    "@esimphilippine":     "-1002275103508",
    "@eSIMmalaysia":       "-1002429758669",
    "@CambodiaeSIM":       "-1002351647232",
    "@esimamerica":        "-1002480277739",
    "@esimsdata_official": "-1003710694261",
    "@esimway":            "-1002249121447",
    "@esimanonymous":      "-1002315349916",
    "@esim_5g_internet":   "-1003624254307",
    "@esim_united_kingdom":"-1003704526342",
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
    "@esimsdata_official": {"country": "global",      "city": "travel",     "operator": "eSIMsData", "brand_colors": "#582c4f, white #f8fbff, gradient #b86aa8 to #552a4c"},
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


def build_esimdata_prompt(rubric, post_text, img_desc):
    """Special prompt for @esimsdata_official with brand colors and lifestyle photography."""
    lines = [l.strip() for l in post_text.split("\n")
             if l.strip() and not l.startswith("http") and len(l.strip()) > 10]
    context = lines[0][:80] if lines else ""
    return (
        f"Lifestyle travel photography, warm and vibrant. Real people traveling, "
        f"authentic moments: traveler at airport, tourist exploring city, person using smartphone outdoors, "
        f"couple at cafe with phone, backpacker in nature. No robots, no AI figures, no tech UI, no devices floating. "
        f"Real human emotion and travel energy.\n\n"
        f"Color palette: deep plum #582c4f as dominant background tone, "
        f"soft white #f8fbff and #EEEEEE as accent highlights, "
        f"gradient overlay from #b86aa8 to #552a4c (left to right, subtle, 30% opacity). "
        f"Cinematic warm lighting, premium editorial style.\n\n"
        f"Post context: {context}\n"
        f"Visual direction: {img_desc}\n\n"
        f"Horizontal landscape format 1.91:1 ratio (1280x670px). Fill the entire frame edge to edge, no empty space, no borders. No text overlays, no QR codes, no watermarks."
    ).strip()

def build_esimway_prompt(rubric, post_text, img_desc):
    """Special prompt for @esimway with brand colors: navy #0A284C, blue #2267DF, light blue #6394E7, white #F8FBFF."""
    lines = [l.strip() for l in post_text.split("\n")
             if l.strip() and not l.startswith("http") and len(l.strip()) > 10]
    context = lines[0][:80] if lines else ""
    return (
        f"Lifestyle travel photography, vibrant and energetic. Real people traveling: "
        f"happy traveler at airport, tourist exploring landmarks, friends on adventure, "
        f"person with phone in beautiful location, couple discovering new city. "
        f"Authentic human moments, genuine emotions, no robots, no AI figures, no floating devices, no tech UI.\n\n"
        f"Color palette: deep navy #0A284C as dominant background, bright blue #2267DF as main accent, "
        f"light blue #6394E7 for highlights, soft white #F8FBFF for bright areas. "
        f"Gradient overlay from #2267DF to #0A284C (left to right, subtle 25% opacity). "
        f"Clean, modern, premium travel brand aesthetic.\n\n"
        f"Post context: {context}\n"
        f"Visual direction: {img_desc}\n\n"
        f"16:9 wide landscape format, 1280x720px. No text overlays, no QR codes, no watermarks."
    ).strip()

def build_esim5g_prompt(rubric, post_text, img_desc):
    """@esim_5g_internet - same theme as esimway but with 5G brand colors."""
    lines = [l.strip() for l in post_text.split("\n")
             if l.strip() and not l.startswith("http") and len(l.strip()) > 10]
    context = lines[0][:80] if lines else ""
    return (
        f"Lifestyle photography, vibrant and dynamic. Real people in motion: "
        f"business traveler at airport lounge, digital nomad working on laptop in cafe, "
        f"couple exploring city streets, backpacker with phone in scenic location, "
        f"professional checking phone with city skyline behind. "
        f"High energy, modern, connected lifestyle. No robots, no AI figures, no floating UI.\n\n"
        f"Color palette: steel blue #396396 as dominant tone, "
        f"vibrant red #f93f51 as accent highlight, soft white #f8fbff for bright areas. "
        f"Gradient overlay left to right from #f93f51 to #243b63 (subtle 25% opacity). "
        f"Clean, premium, high-speed internet brand aesthetic.\n\n"
        f"Post context: {context}\n"
        f"Visual direction: {img_desc}\n\n"
        f"Horizontal landscape 1.91:1, 1280x670px. Fill frame edge to edge. No text, no QR, no watermarks."
    ).strip()

def build_esimuk_prompt(rubric, post_text, img_desc):
    """@esim_united_kingdom - same theme as esimrussian but for UK."""
    lines = [l.strip() for l in post_text.split("\n")
             if l.strip() and not l.startswith("http") and len(l.strip()) > 10]
    context = lines[0][:80] if lines else ""
    return (
        f"Lifestyle travel photography set in United Kingdom atmosphere: "
        f"business traveler at London landmarks, digital nomad in British cafe, "
        f"tourist exploring UK countryside, professional with phone near Big Ben or Tower Bridge, "
        f"person with eSIM phone in British city. Authentic, warm, premium British travel feel. "
        f"No robots, no AI figures, no floating UI.\n\n"
        f"British travel and connectivity theme. Warm cinematic lighting, editorial photography style. "
        f"Colors: deep navy and Union Jack inspired accents (red, white, blue). "
        f"Premium, modern, professional aesthetic.\n\n"
        f"Post context: {context}\n"
        f"Visual direction: {img_desc}\n\n"
        f"Horizontal landscape 1.91:1, 1280x670px. Fill frame edge to edge. No text, no QR, no watermarks."
    ).strip()

def build_prompt(channel, rubric, post_text, img_desc):
    meta    = CHANNEL_META.get(channel, {"country": "global", "city": "travel", "operator": "various"})
    country = meta.get("country", "global")
    city    = meta.get("city", "travel destination")
    lines   = [l.strip() for l in post_text.split("\n")
               if l.strip() and not l.startswith("http") and len(l.strip()) > 10]
    context = lines[0][:80] if lines else ""
    return (
        f"Real lifestyle travel photography. Authentic candid moment, professional DSLR quality. "
        f"Specific scene: {img_desc}. Location: {city}, {country}. "
        f"Theme: {context}. "
        f"Style: photorealistic, warm cinematic lighting, natural colors, shallow depth of field. "
        f"Show real humans - diverse travelers, business people or digital nomads - "
        f"in real-world situations. Emotions: happy, confident, relaxed. "
        f"Environment: real airport terminal, cafe, city street, hotel lobby, beach, train. "
        f"NO robots. NO AI figures. NO abstract shapes. NO floating UI. NO tech diagrams. "
        f"NO dark neon backgrounds. Wide horizontal scene fills entire frame edge to edge. "
        f"Natural daylight or warm golden hour lighting. 35mm lens, shallow bokeh background. "
        f"1280x670 pixels, no letterboxing, no pillarboxing, no empty areas."
    ).strip()

def generate_image(channel, rubric, post_text, img_desc):
    client = genai.Client(api_key=GEMINI_KEY)
    if channel == "@esimsdata_official":
        prompt = build_esimdata_prompt(rubric, post_text, img_desc)
    elif channel == "@esimway":
        prompt = build_esimway_prompt(rubric, post_text, img_desc)
    elif channel == "@esim_5g_internet":
        prompt = build_esim5g_prompt(rubric, post_text, img_desc)
    elif channel == "@esim_united_kingdom":
        prompt = build_esimuk_prompt(rubric, post_text, img_desc)
    else:
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
                # Scale to fill 1280x670 then center crop - Telegram optimal format
                from PIL import ImageOps
                img = ImageOps.fit(img, (IMAGE_W, IMAGE_H), Image.LANCZOS, centering=(0.5, 0.4))
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
        caption = f"{post_text}\n\n{link}" if link and link not in post_text else post_text
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
