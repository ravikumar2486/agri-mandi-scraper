import os
import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta

# ✅ Write credentials from environment variable to a temp file OR read local file
firebase_json_str = os.environ.get("FIREBASE_CREDENTIALS_JSON")

if firebase_json_str:
    with open("temp_firebase.json", "w") as f:
        f.write(firebase_json_str)
    cred_file = "temp_firebase.json"
else:
    cred_file = "authenticationapp-c3711-firebase-adminsdk-fbsvc-f96d0b7bf3.json"

# ✅ Initialize Firebase
cred = credentials.Certificate(cred_file)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ✅ Define commodities with their Agmarknet codes
commodity_codes = {
    "Tomato": "78",
    "Potato": "80",
    "Onion": "79",
    "Wheat": "15",
    "Maize": "17",
    "Gram": "68",
    # ➕ Add more commodities with their correct codes here
}

# ✅ Define scraping function with per-crop date fallback
def scrape_agmarknet():
    for commodity_name, code in commodity_codes.items():
        data_found_for_commodity = False

        for days_back in range(0, 3):  # Check today, yesterday, day before yesterday
            date_check = datetime.today() - timedelta(days=days_back)
            date_str = date_check.strftime('%d-%b-%Y')
            print(f"🔎 Trying {commodity_name} for date: {date_str}")

            url = f"https://agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity={code}&Tx_State=RJ&Tx_District=0&Tx_Market=0&DateFrom={date_str}&DateTo={date_str}&Fr_Date={date_str}&To_Date={date_str}&Tx_Trend=0&Tx_CommodityHead={commodity_name}&Tx_StateHead=Rajasthan&Tx_DistrictHead=--Select--&Tx_MarketHead=--Select--"

            response = requests.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                table = soup.find("table", {"id": "cphBody_GridPriceData"})

                if table:
                    rows = table.find_all("tr")[1:]  # Skip header
                    mandi_prices = []

                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) >= 10:
                            mandi = {
                                "market": cols[1].text.strip(),
                                "district": cols[2].text.strip(),
                                "commodity": commodity_name,
                                "variety": cols[4].text.strip(),
                                "grade": cols[5].text.strip(),
                                "min_price": cols[6].text.strip(),
                                "max_price": cols[7].text.strip(),
                                "modal_price": cols[8].text.strip(),
                                "date": cols[9].text.strip()
                            }
                            mandi_prices.append(mandi)
                        else:
                            print("Skipping row with insufficient columns")

                    # ✅ Upload to Firestore with duplicate check
                    uploaded_any = False
                    for item in mandi_prices:
                        existing_docs = db.collection("mandi_prices") \
                            .where("commodity", "==", item["commodity"]) \
                            .where("market", "==", item["market"]) \
                            .where("date", "==", item["date"]) \
                            .stream()

                        if any(existing_docs):
                            print(f"⚠️ Data for {item['commodity']} in {item['market']} on {item['date']} already exists. Skipping upload.")
                        else:
                            doc_ref = db.collection("mandi_prices").document()
                            doc_ref.set(item)
                            print(f"✅ Uploaded {item['commodity']} price for {item['market']} on {item['date']}.")
                            uploaded_any = True

                    if mandi_prices:
                        if uploaded_any:
                            print(f"✅ {commodity_name} prices for {date_str} processed and uploaded successfully.")
                        else:
                            print(f"ℹ️ {commodity_name} prices for {date_str} already exist in Firestore.")
                        data_found_for_commodity = True
                        break  # ✅ Exit date loop for this crop if data found
                    else:
                        print(f"❌ No rows with valid data for {commodity_name} on {date_str}")
                else:
                    print(f"❌ No data table found for {commodity_name} on {date_str}")
            else:
                print(f"❌ Failed to fetch {commodity_name} for {date_str}. Status: {response.status_code}")

        if not data_found_for_commodity:
            print(f"❌ No data found for {commodity_name} in last 3 days.")

# ✅ Run scraper
if __name__ == "__main__":
    try:
        scrape_agmarknet()
    finally:
        if firebase_json_str:
            os.remove("temp_firebase.json")
