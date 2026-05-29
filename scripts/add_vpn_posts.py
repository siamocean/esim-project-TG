import json, base64, os
import gspread
from google.oauth2.service_account import Credentials

creds_json = json.loads(base64.b64decode(os.environ["GOOGLE_CREDENTIALS"]))
scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
gc = gspread.authorize(creds)
ss = gc.open_by_key(os.environ["SPREADSHEET_ID"])
sh = ss.worksheet('@esimrussian')

# Get existing dates - every 8th row starting from row 8 (index 7)
all_data = sh.get_all_values()
header = all_data[0]
rows = all_data[1:]
dates = [rows[i][7] for i in range(7, len(rows), 8)]
print(f"Found {len(dates)} date slots: {dates[:5]}")

posts = [
    ("VPN or eSIM - what actually protects you abroad?", "Travelers always ask: do I need a VPN or an eSIM?\n\nShort answer: they solve different problems.\n\n🔒 VPN encrypts your traffic\n📡 eSIM gives you local data without ID\n\nFor Russia:\n✅ eSIM = no passport, no operator registration\n✅ VPN = hides what you browse\n\nTogether? Maximum protection.\n\nGet your eSIM first 👇", "Split screen: left VPN shield on phone, right eSIM QR scan, traveler at airport"),
    ("Why VPN alone is not enough in Russia", "Using a VPN in Russia?\n\nSmart move. But VPN doesn-t hide who you are from your operator.\n\nWith a regular SIM:\n❌ Operator has your passport data\n❌ Your number is linked to your identity\n\nWith eSIM from us:\n✅ No registration\n✅ No personal data\n\neSIM + VPN = the real combo 👇", "Person using laptop in Russian cafe with VPN active on screen, city street visible through window"),
    ("eSIM vs SIM - privacy comparison", "Buying a SIM in Russia:\n📋 Passport required\n📋 Biometric data collected\n📋 Linked to your identity forever\n\nOur eSIM:\n✅ No documents\n✅ No operator registration\n✅ Activate from anywhere\n\nFor privacy-conscious travelers - the choice is clear.\n\nGet yours 👇", "Physical SIM card with passport next to eSIM QR code on phone, minimal clean design"),
    ("Can you use eSIM and VPN at the same time?", "Yes. Absolutely.\n\n1️⃣ Activate eSIM - get anonymous local data\n2️⃣ Turn on VPN - encrypt your connection\n3️⃣ Browse freely - no operator trail\n\nWorks on iPhone and Android.\nWorks in Russia and 150+ countries.\n\nStack your privacy 👇", "Person holding phone showing VPN active and eSIM connected, confident smile, modern hotel room"),
    ("The truth about free VPNs abroad", "Free VPN sounds great.\n\nUntil you realize:\n❌ They log your activity\n❌ They sell your data\n❌ They get blocked in Russia\n\neSIM starts your privacy before you open any app.\n\nNo registration = no tracking starting point.\n\nBegin with eSIM 👇", "Phone showing free VPN app with warning signs, traveler looking skeptical at airport terminal"),
    ("How digital nomads stay private in Russia", "Working remotely from Russia?\n\n📡 eSIM - local data, zero paperwork\n🔒 VPN - encrypted connection\n🌐 Browser - private mode\n\nWith our eSIM you skip operator registration entirely.\n\nNo name. No address. No passport.\n\nJust internet. 👇", "Digital nomad at Russian city cafe, laptop with VPN active, eSIM phone nearby"),
    ("eSIM for journalists traveling to Russia", "Source protection starts with your SIM card.\n\nTraditional SIM:\n❌ Passport linked to number\n❌ Calls and data logged by operator\n\nOur eSIM:\n✅ No personal data required\n✅ Activate remotely before arrival\n\nProtect your sources from day one 👇", "Journalist with notebook and phone at Russian landmark, professional discreet look"),
    ("VPN gets blocked. eSIM doesn-t.", "Russia blocks VPN apps regularly.\n\nBut your eSIM connection?\n✅ Cannot be blocked\n✅ Works on all networks\n✅ Switches to best signal automatically\n\nUse eSIM as your foundation.\nAdd VPN on top when it works.\n\nReliable connection first 👇", "Phone showing VPN blocked notification vs clean eSIM signal bars, two travelers compared"),
    ("What happens to your data with a Russian SIM?", "When you buy a SIM in Russia:\n\n🗂 Passport photographed\n🗂 Biometrics may be taken\n🗂 All calls and data logged\n🗂 For 3 years minimum\n\nOur eSIM:\n✅ No documents\n✅ No logs\n✅ No trail\n\nStart clean 👇", "Russian phone store counter with forms and passport contrasted with clean eSIM activation screen"),
    ("eSIM for short trips to Russia", "Coming for 1-2 weeks?\n\nBuying a local SIM means:\n⏱ 30+ min at a phone store\n📋 Passport registration\n💸 Overpriced tourist plans\n\nOur eSIM:\n✅ Activate before you fly\n✅ No store visit\n✅ Better value\n\nSave time and stay private 👇", "Busy Russian phone store queue vs relaxed traveler at airport already connected"),
    ("Privacy is a feature, not a bonus", "Most eSIM providers still ask for your email and name.\n\nOur approach:\n✅ Minimal data collection\n✅ No operator registration in Russia\n✅ Activate and go\n\nFor travelers who value privacy - it-s not paranoia.\nIt-s basic digital hygiene.\n\nGet yours 👇", "Clean minimal phone screen with privacy checkmarks, modern traveler at international airport"),
    ("Which is faster - VPN or direct eSIM in Russia?", "VPN speed in Russia: 40-80 Mbps average\n\neSIM direct speed: 80-200 Mbps on MegaFon/Beeline\n\nVPN adds latency. Always.\n\nFor speed: eSIM direct\nFor privacy: eSIM + VPN\nFor balance: selective VPN use\n\nYour choice 👇", "Speed test results on phone in Russian city, digital nomad working fast on laptop"),
    ("Why expats in Russia choose eSIM", "Living in Russia as an expat?\n\nLocal SIM registration gets stricter every year.\n\nOur eSIM gives you:\n✅ Data without full registration\n✅ Works alongside your home number\n✅ Cancel anytime\n\nSimpler. Cleaner. More flexible. 👇", "Expat professional in Moscow or St Petersburg, dual SIM phone, working from coffee shop near landmark"),
    ("The eSIM + VPN setup that actually works", "Step-by-step for Russia travel:\n\n📲 Buy eSIM before departure\n📲 Activate on landing\n📲 Open VPN app\n📲 Choose server outside Russia\n📲 Browse freely\n\nTotal setup: under 5 minutes\n\nStart now 👇", "Step-by-step phone screens showing eSIM setup then VPN activation, confident traveler"),
    ("What Russian operators are required to log", "Operators store by law:\n\n📁 All calls metadata\n📁 SMS content\n📁 Data usage records\n📁 Location history\n\nFor 3-6 months minimum.\n\nWith our eSIM - no registration means less starting data.\nAdd VPN to reduce exposure further. 👇", "Abstract data collection visualization, traveler looking thoughtfully at phone, Russian urban background"),
    ("eSIM for business travel to Russia", "Business trip to Moscow or St Petersburg?\n\nKeep corporate data off local networks:\n\n✅ eSIM with no operator registration\n✅ VPN for corporate traffic\n✅ Separate from personal phone\n\nIT security teams recommend minimal local SIM exposure.\n\nOur eSIM makes it easy 👇", "Business executive at Moscow City district, suit, phone with eSIM and VPN active"),
    ("Does eSIM work with Russian banking apps?", "Yes - with some nuance.\n\nRussian banking apps work on eSIM data.\n\nBut:\n⚠️ Some apps block VPN connections\n⚠️ Turn off VPN temporarily for banking\n⚠️ eSIM data still works perfectly\n\neSIM = reliable base\nVPN = toggle when needed\n\nFlexible setup 👇", "Person using Russian banking app on phone with eSIM indicator, modern Russian apartment"),
    ("Traveling through Russia to other countries?", "Route: Europe to Russia to Asia?\n\nOur eSIM covers:\n✅ Russia (MegaFon/Beeline)\n✅ 150+ other countries\n✅ Auto-connects at each border\n\nNo SIM swaps. No phone stores.\n\nVPN works the same everywhere.\n\nOne plan. Entire journey. 👇", "World map route Europe-Russia-Asia, traveler at border crossing with phone showing eSIM coverage"),
    ("Why privacy travelers avoid local SIMs", "The case against local SIMs:\n\n1. Identity permanently linked\n2. Number can track your location\n3. Authorities can request operator data\n4. Hard to disconnect\n\neSIM advantages:\n✅ Minimal registration\n✅ Deactivate instantly\n✅ No physical card to confiscate 👇", "Person at checkpoint with phone showing clean eSIM data, privacy concept, minimal style"),
    ("eSIM myths debunked", "Myth: eSIM is less secure\n✅ False - same encryption\n\nMyth: You need ID for eSIM\n✅ False - not with us\n\nMyth: VPN makes eSIM unnecessary\n✅ False - different purposes\n\nMyth: eSIM is easier to track\n✅ False - no physical location\n\nGet the facts 👇", "Myth vs fact on phone screen, traveler with surprised expression, modern airport setting"),
    ("How to choose a Russia eSIM plan", "Ask yourself:\n\n📅 How long? 7-day vs 30-day\n📊 How much data? Light vs heavy\n🔒 Privacy priority? Minimal registration\n💰 Budget? Compare vs airport SIM\n\nOur plans:\n✅ Flexible duration\n✅ No registration\n✅ Better value\n\nFind your plan 👇", "Person comparing eSIM plan options on laptop, travel planning desk with passport and phone"),
    ("VPN in Russia - what actually works in 2026", "Many VPNs get blocked in Russia.\n\nOnes that still work:\n✅ Outline VPN\n✅ Shadowsocks protocol\n✅ WireGuard configs\n\nSpeed depends on your data connection.\n\nOur eSIM base speeds:\n⚡ MegaFon 4G/5G\n⚡ Beeline backup\n\nFast eSIM + reliable VPN = freedom 👇", "Phone showing VPN successfully connected in Russia, city skyline, relieved traveler expression"),
    ("Why your phone number reveals more than you think", "Your Russian number reveals:\n\n📍 Location via cell towers\n🆔 Your registered identity\n📱 Apps linked to that number\n💬 Who you communicate with\n\neSIM with minimal registration reduces this exposure.\nCombine with VPN for full coverage.\n\nPrivacy starts with the SIM 👇", "Abstract phone number data connections, person looking thoughtfully at phone, urban Russian background"),
    ("The eSIM advantage for long-term Russia residents", "Living in Russia long-term?\n\nWhy expats keep our eSIM active:\n\n✅ Backup when main SIM fails\n✅ Separate line for privacy\n✅ Easy top-up from abroad\n✅ Works during SIM registration changes\n\nSlot 1: Local SIM\nSlot 2: Our eSIM\n\nBest of both worlds 👇", "Expat in Russian apartment with dual SIM phone, home office environment, city view"),
    ("What to do if your VPN stops working in Russia", "VPN suddenly blocked?\n\nEmergency checklist:\n\n1️⃣ Switch VPN protocol (WireGuard/Shadowsocks)\n2️⃣ Change server location\n3️⃣ Try mobile data instead of WiFi\n4️⃣ Use obfuscated servers\n\nOur eSIM mobile data is harder to block than fixed IP VPNs.\n\nAlways have a backup 👇", "Frustrated traveler troubleshooting VPN on phone, then switching to eSIM successfully, hotel room"),
    ("eSIM + privacy apps - the full stack", "The privacy-conscious Russia traveler stack:\n\n📡 eSIM - anonymous data\n🔒 VPN - encrypted tunnel\n💬 Signal - encrypted messages\n🌐 Brave - private browser\n📧 ProtonMail - secure email\n\nStart with the foundation.\nNo registration eSIM = no identity at network level.\n\nBuild your stack 👇", "Phone showing privacy app icons stacked with eSIM indicator at top, digital privacy concept"),
]

# Get last row number for numbering
last_num = len(rows)

# Build rows to append: num, rubric, topic, text, link, img_desc, status, date
new_rows = []
for i, (topic, text, img_desc) in enumerate(posts):
    if i < len(dates):
        new_rows.append([
            last_num + i + 1,
            'VPN или eSIM?',
            topic,
            text,
            'https://t.me/Esimsdata_bot',
            img_desc,
            'Draft',
            dates[i]
        ])

sh.append_rows(new_rows, value_input_option='RAW')
print(f"Added {len(new_rows)} VPN posts successfully!")
print(f"First post date: {new_rows[0][7]}, Last post date: {new_rows[-1][7]}")
