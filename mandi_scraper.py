import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore

# ✅ Initialize Firebase
cred = credentials.Certificate("authenticationapp-c3711-firebase-adminsdk-fbsvc-f96d0b7bf3.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ✅ Define the scraping function
def scrape_agmarknet():
    url = "https://agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity=78&Tx_State=RJ&Tx_District=0&Tx_Market=0&DateFrom=15-May-2025&DateTo=15-May-2025&Fr_Date=15-May-2025&To_Date=15-May-2025&Tx_Trend=0&Tx_CommodityHead=Tomato&Tx_StateHead=Rajasthan&Tx_DistrictHead=--Select--&Tx_MarketHead=--Select--"

    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 🔍 Find the data table
        table = soup.find("table", {"id": "cphBody_GridPriceData"})
        
        mandi_prices = []
        
        if table:
            rows = table.find_all("tr")[1:]  # Skip header
            for row in rows:
             cols = row.find_all("td")
             print(f"Row text: {row.text.strip()}")
             print(f"Row columns count: {len(cols)}")  # Debug output

             if len(cols) >= 10:
              mandi = {
                  "market": cols[1].text.strip(),       # Market
                  "district": cols[2].text.strip(),     # District
                  "commodity": cols[3].text.strip(),    # Commodity
                  "variety": cols[4].text.strip(),      # Variety
                  "grade": cols[5].text.strip(),        # Grade
                  "min_price": cols[6].text.strip(),    # Min Price
                  "max_price": cols[7].text.strip(),    # Max Price
                  "modal_price": cols[8].text.strip(),  # Modal Price
                  "date": cols[9].text.strip()          # Date
              }
              mandi_prices.append(mandi)
              

             
            
            # ✅ Upload to Firestore
            for item in mandi_prices:
                doc_ref = db.collection("mandi_prices").document()
                doc_ref.set(item)
            
            print("✅ Mandi prices scraped and uploaded successfully.")
        
        else:
            print("❌ Data table not found on Agmarknet page.")
    else:
        print("❌ Failed to fetch page. Status code: {response.status_code}")

# ✅ Run scraper
if __name__ == "__main__":
    scrape_agmarknet()
