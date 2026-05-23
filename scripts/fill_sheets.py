import json, base64, os
import gspread
from google.oauth2.service_account import Credentials

creds_json = json.loads(base64.b64decode(os.environ["GOOGLE_CREDENTIALS"]))
scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
sheets = gspread.authorize(creds)
ss = sheets.open_by_key(os.environ["SPREADSHEET_ID"])

h = ['num','rubric','topic','text','link','img_desc','status','date']

# ===== @esim_5g_internet =====
sh5g = ss.worksheet('@esim_5g_internet')
sh5g.clear()
sh5g.append_row(h)
rows5g = [
[1,'Plan spotlight','5G eSIM - instant, global, ready','Tired of hunting for SIM cards at the airport?\n\nWith esim5g.com:\n✅ 5G speed in 150+ countries\n✅ Instant QR activation\n✅ No contracts\n\nYour trip starts the moment you land.','https://esim5g.com','Digital nomad activating eSIM at airport, 5G signal, modern lifestyle','Draft','22.05.2026'],
[2,'Travel guide','Connected before you land','Most travelers waste 30 min finding a SIM.\n\nSmart travelers activate before boarding.\n\nesim5g.com:\n✅ QR sent instantly\n✅ Works on any unlocked phone\n✅ 5G where available\n\nBe online from step one ✌️','https://esim5g.com','Traveler at gate checking phone map, natural light, confident and connected','Draft','25.05.2026'],
[3,'News','5G coverage just expanded','More cities. More countries. More speed.\n\nesim5g.com auto-connects to the best signal - 5G, 4G or LTE.\n\nNo switching. No roaming fees.\n\nStay fast ⚡','https://esim5g.com','City skyline at night with glowing 5G network signals, tech aesthetic','Draft','27.05.2026'],
[4,'Voice + Data','Work from anywhere. Really.','Digital nomads on esim5g.com report:\n✅ Seamless video calls abroad\n✅ Fast uploads from any cafe\n✅ Zero dead zones in major cities\n\nSlow internet abroad is not an option.','https://esim5g.com','Business person on laptop video call at outdoor cafe, European city, golden hour','Draft','29.05.2026'],
[5,'Privacy','No ID. No tracking. Just internet.','Local SIMs require your passport data.\n\nesim5g.com:\n🔒 No ID required\n🔒 No data shared\n🔒 Private from day one\n\nFast + private. Finally.','https://esim5g.com','Person using phone privately, minimal dark aesthetic, secure digital nomad','Draft','30.05.2026'],
[6,'Plan spotlight','150+ countries. One eSIM.','One QR code. 150+ countries.\n\nesim5g.com global plan:\n✅ Switch countries without changing plans\n✅ 5G auto-connect\n✅ Top up anytime\n\nPerfect for frequent travelers.','https://esim5g.com','World map with connection lines, person holding phone, travel energy','Draft','01.06.2026'],
[7,'Travel guide','Pre-travel checklist','Before your next trip:\n✅ Book flights\n✅ Pack bags\n✅ Get travel insurance\n✅ Activate esim5g.com eSIM\n\nDon-t be the one searching for WiFi in arrivals ⚡','https://esim5g.com','Backpacker with checklist at airport, pre-trip excitement, phone in hand','Draft','03.06.2026'],
[8,'Seasonal','Summer travel is back','Heading to Asia, Europe or Americas?\n\nesim5g.com has you covered.\n✅ 5G at top destinations\n✅ No roaming surprises\n✅ Instant setup\n\nWhere are you headed? 👇','https://esim5g.com','Couple at sunny beach destination, phones out, summer travel lifestyle','Draft','05.06.2026'],
]
for row in rows5g:
    sh5g.append_row(row)
print("5G done:", len(rows5g), "rows")

# ===== @esim_united_kingdom =====
shUK = ss.worksheet('@esim_united_kingdom')
shUK.clear()
shUK.append_row(h)
rowsUK = [
[1,'Plan spotlight','UK eSIM - arrive connected','Landing at Heathrow?\n\nSkip the SIM queue.\n\nOur UK eSIM:\n✅ Instant QR activation\n✅ Full 5G across England, Scotland, Wales\n✅ No contracts\n\nOnline from the moment you land 👇','https://t.me/topup_smm_bot','Traveler arriving at London airport, Big Ben view, phone in hand, UK arrival','Draft','22.05.2026'],
[2,'Travel guide','London on your own terms','Navigating London without data is a nightmare.\n\nTube maps. Google Maps. Bookings.\n\nOur UK eSIM:\n✅ 5G in central London\n✅ Nationwide coverage\n✅ Activate before you fly\n\nExplore more. Stress less ✌️','https://t.me/topup_smm_bot','Tourist with phone at Tower Bridge, authentic London travel moment','Draft','25.05.2026'],
[3,'News','5G expanding across UK cities','Manchester. Birmingham. Edinburgh. Bristol.\n\nOur UK eSIM connects to the best network automatically.\n\nNo switching. No extra cost.\n\nStay fast ⚡','https://t.me/topup_smm_bot','British city skyline at dusk, glowing network signals, modern urban UK','Draft','27.05.2026'],
[4,'Voice + Data','Work remotely from the UK','Remote work from London?\n\nOur UK eSIM:\n✅ Video calls without drops\n✅ Fast uploads from any UK cafe\n✅ Coverage in trains and rural areas\n\nDeadlines don-t care about time zones 👇','https://t.me/topup_smm_bot','Digital nomad on laptop in cozy British cafe, rainy window, warm lighting','Draft','29.05.2026'],
[5,'Travel guide','Beyond London','Scottish Highlands. Lake District. Cornwall.\n\nOur eSIM works across the entire UK.\n✅ Rural coverage\n✅ 4G minimum nationwide\n✅ No gaps on intercity trains\n\nExplore it all 🇬🇧','https://t.me/topup_smm_bot','Hiker in Scottish Highlands checking phone, epic British landscape','Draft','30.05.2026'],
[6,'Plan spotlight','7-day UK eSIM - perfect for short trips','Visiting for a week?\n\n7-day plan:\n✅ 10GB high-speed data\n✅ Full UK coverage\n✅ Instant QR delivery\n\nActivate from home. Arrive ready.','https://t.me/topup_smm_bot','Tourist activating eSIM QR code on phone, London street, modern travel','Draft','01.06.2026'],
[7,'Privacy','Travel UK without leaving a data trail','Airport SIMs require your passport.\n\nOur eSIM:\n🔒 No ID required\n🔒 Activate privately\n🔒 No personal data stored\n\nFast UK internet. Total privacy.','https://t.me/topup_smm_bot','Person on London Underground, privacy concept, minimal dark aesthetic, anonymous traveler','Draft','03.06.2026'],
[8,'Seasonal','British summer - stay connected','Wimbledon. Festivals. Road trips.\n\nThe UK summer is packed.\n✅ Live scores\n✅ Navigation on country roads\n✅ Share memories instantly\n\nGet your UK eSIM before you arrive 🇬🇧','https://t.me/topup_smm_bot','Friends at UK summer festival, British flags, sunny day, phones capturing memories','Draft','05.06.2026'],
]
for row in rowsUK:
    shUK.append_row(row)
print("UK done:", len(rowsUK), "rows")
print("All done!")
