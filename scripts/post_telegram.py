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
    lines = [l.strip() for l in post_text.split("\n")
             if l.strip() and not l.startswith("http") and len(l.strip()) > 10]
    context = lines[0][:80] if lines else ""
    return (
        f"Real lifestyle travel photography, vibrant and energetic. Authentic candid moment. "
        f"Scene: {img_desc}. Theme: {context}. "
        f"Show real people: business traveler at airport, digital nomad working at cafe, "
        f"couple exploring city, backpacker with phone at landmark, person using smartphone outdoors. "
        f"Color grading: steel blue and red accent tones, warm cinematic grade. "
        f"Brand colors visible as subtle color grade: blue #396396 dominant, red accent #f93f51. "
        f"NO robots. NO AI figures. NO abstract UI. NO floating tech elements. NO neon glows. "
        f"Photorealistic DSLR quality. Natural lighting. Real environments. Real humans. "
        f"Wide 1.91:1 horizontal, fills entire frame. "
        f"CRITICAL: No empty areas. All space filled with natural gradient, blurred background, "
        f"ambient light or texture continuation. No sharp photo edges. No solid color blocks. "
        "NO photo grids or collages. NO 2x2, 3x3 or equal rectangular photo layouts. "
        f"ONE main visual focus. Single unified composition. "
        f"If multiple elements exist, blend them seamlessly into one scene - different sizes, organic shapes, no white dividers. "
        f"The result must look like a premium travel or tech brand advertisement banner, not a photo collage."
    ).strip()

def build_esimuk_prompt(rubric, post_text, img_desc):
    lines = [l.strip() for l in post_text.split("\n")
             if l.strip() and not l.startswith("http") and len(l.strip()) > 10]
    context = lines[0][:80] if lines else ""
    return (
        f"Real travel photography in United Kingdom. Authentic candid moment. "
        f"Scene: {img_desc}. Theme: {context}. "
        f"Show real people: tourist at London landmark, digital nomad in British cafe, "
        f"traveler at Heathrow or Gatwick, hiker in Scottish Highlands, person on UK train. "
        f"Locations: London streets, Tower Bridge, Big Ben, British countryside, Scottish Highlands, "
        f"cozy English pub, UK train station, Brighton seafront. "
        f"Mood: authentic British atmosphere, warm overcast light or golden hour. "
        f"Color grading: warm tones, slightly desaturated cinematic British look. "
        f"NO robots. NO AI figures. NO abstract shapes. NO floating UI. NO neon. "
        f"Photorealistic DSLR quality. Real UK environments. Real diverse humans. "
        f"Wide 1.91:1 horizontal, fills entire frame edge to edge. "
        f"CRITICAL: No empty areas allowed. All space filled with natural gradient transitions, "
        f"blurred background, atmospheric haze or environmental continuation. No sharp edges. "
        "NO photo grids or collages. NO 2x2, 3x3 or equal rectangular photo layouts. "
        f"ONE main visual focus. Single unified composition. "
        f"If multiple elements exist, blend them seamlessly into one scene - different sizes, organic shapes, no white dividers. "
        f"The result must look like a premium travel or tech brand advertisement banner, not a photo collage."
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
        f"1280x670 pixels, no letterboxing, no pillarboxing, no empty areas. "
        f"CRITICAL: The image must fill the entire 1280x670 canvas. "
        f"If the main subject does not cover the full frame, all empty areas must be filled with "
        f"natural-looking extensions: smooth gradient transitions, blurred background continuation, "
        f"soft bokeh, ambient light, sky, environment texture, or atmospheric haze. "
        f"No sharp edges where the photo ends. No solid color blocks. No visible seams. "
        f"Every pixel of the canvas must feel like part of the same scene. "
        "NO photo grids or collages. NO 2x2, 3x3 or equal rectangular photo layouts. "
        f"ONE main visual focus. Single unified composition. "
        f"If multiple elements exist, blend them seamlessly into one scene - different sizes, organic shapes, no white dividers. "
        f"The result must look like a premium travel or tech brand advertisement banner, not a photo collage."
    ).strip()

def translate_to_russian(text):
    """Translate post text to natural Russian using Gemini."""
    try:
        client = genai.Client(api_key=GEMINI_KEY)
        prompt = (
            "ÐÐµÑÐµÐ²ÐµÐ´Ð¸ ÑÐ»ÐµÐ´ÑÑÑÐ¸Ð¹ ÑÐµÐºÑÑ Ð¿Ð¾ÑÑÐ° Ð´Ð»Ñ Telegram-ÐºÐ°Ð½Ð°Ð»Ð° Ð½Ð° ÑÑÑÑÐºÐ¸Ð¹ ÑÐ·ÑÐº. "
            "Ð¢ÑÐµÐ±Ð¾Ð²Ð°Ð½Ð¸Ñ Ðº Ð¿ÐµÑÐµÐ²Ð¾Ð´Ñ:\n"
            "- ÐÑÑÐµÑÑÐ²ÐµÐ½Ð½ÑÐ¹ ÑÐ°Ð·Ð³Ð¾Ð²Ð¾ÑÐ½ÑÐ¹ ÑÑÑÑÐºÐ¸Ð¹, Ð½Ðµ ÐºÐ°Ð½ÑÐµÐ»ÑÑÑÐºÐ¸Ð¹\n"
            "- Ð¡Ð¾ÑÑÐ°Ð½Ð¸ Ð²ÑÐµ ÑÐ¼Ð¾Ð´Ð·Ð¸ Ð½Ð° ÑÐµÑ Ð¶Ðµ Ð¼ÐµÑÑÐ°Ñ\n"
            "- Ð¡Ð¾ÑÑÐ°Ð½Ð¸ Ð²ÑÐµ ÑÑÑÐ»ÐºÐ¸ Ð±ÐµÐ· Ð¸Ð·Ð¼ÐµÐ½ÐµÐ½Ð¸Ð¹\n"
            "- Ð¡Ð¾ÑÑÐ°Ð½Ð¸ ÑÐ¾ÑÐ¼Ð°ÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð¸Ðµ: Ð¿ÐµÑÐµÐ½Ð¾ÑÑ ÑÑÑÐ¾Ðº, ÑÐ¿Ð¸ÑÐºÐ¸, ÑÑÑÐµÐ»ÐºÐ¸\n"
            "- ÐÐ°ÑÐºÐµÑÐ¸Ð½Ð³Ð¾Ð²ÑÐ¹ ÑÐ¾Ð½: Ð¶Ð¸Ð²Ð¾Ð¹, ÑÐ²ÐµÑÐµÐ½Ð½ÑÐ¹, Ð±ÐµÐ· ÐºÐ°Ð½ÑÐµÐ»ÑÑÐ¸ÑÐ°\n"
            "- ÐÐ Ð´Ð¾Ð±Ð°Ð²Ð»ÑÐ¹ Ð½Ð¸ÐºÐ°ÐºÐ¸Ñ Ð¿Ð¾ÑÑÐ½ÐµÐ½Ð¸Ð¹, ÑÐ¾Ð»ÑÐºÐ¾ Ð¿ÐµÑÐµÐ²ÐµÐ´ÑÐ½Ð½ÑÐ¹ ÑÐµÐºÑÑ\n\n"
            f"Ð¢ÐµÐºÑÑ Ð´Ð»Ñ Ð¿ÐµÑÐµÐ²Ð¾Ð´Ð°:\n{text}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=1500)
        )
        translated = response.text.strip()
        print(f"    Translated to Russian ({len(translated)} chars)")
        return translated
    except Exception as e:
        print(f"    Translation error: {e}, using original")
        return text

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
                img = ImageOps.fit(img, (IMAGE_W, IMAGE_H), Image.LANCZOS, centering=(0.5, 0.3))
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
        # Translate to Russian for @esimrussian channel
        if channel == "@esimrussian":
            post_text = translate_to_russian(post_text)
        # Build caption
        if channel == "@esimsdata_official":
            footer = (
                "\n\nInternet for every destination."
                "\n[📱 Mini App](https://t.me/Esimsdata_bot?start=esimsdata_official) | "
                "[🌐 Website](https://esimsdata.com/?utm_source=telegram&utm_medium=channel&utm_campaign=esimsdata_official)"
            )
            caption = post_text + footer
        else:
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
