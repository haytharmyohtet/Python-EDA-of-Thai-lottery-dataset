import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime

# Map Thai month names to English month names
thai_to_english_months = {
    'มกราคม': 'January',
    'กุมภาพันธ์': 'February',
    'มีนาคม': 'March',
    'เมษายน': 'April',
    'พฤษภาคม': 'May',
    'มิถุนายน': 'June',
    'กรกฎาคม': 'July',
    'สิงหาคม': 'August',
    'กันยายน': 'September',
    'ตุลาคม': 'October',
    'พฤศจิกายน': 'November',
    'ธันวาคม': 'December'
}

# Map Thai numerals to normal numerals
thai_to_arabic_digits = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')

def convert_thai_date(thai_date_text):
    thai_date_text = thai_date_text.translate(thai_to_arabic_digits)
    match = re.search(r'งวด\s+(\d+)\s+(\w+)\s+(\d+)', thai_date_text)
    if match:
        day, month_thai, year_thai = match.groups()
        month = thai_to_english_months.get(month_thai, month_thai)
        try:
            year = str(int(year_thai) - 543)
        except ValueError:
            year = year_thai
        return f"{month} {day}, {year}"
    # fallback simple split approach
    parts = thai_date_text.split()
    for i, part in enumerate(parts):
        if part == "งวด" and i+3 < len(parts):
            day, month_thai, year_thai = parts[i+1], parts[i+2], parts[i+3]
            month = thai_to_english_months.get(month_thai, month_thai)
            try:
                year = str(int(year_thai) - 543)
            except ValueError:
                year = year_thai
            return f"{month} {day}, {year}"
    return thai_date_text

def process_year_page(url):
    print(f"Processing URL: {url}")
    data = []
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', id='dl_lottery_stats_list')
        if not table:
            print(f" Table not found for {url}")
            return data
        for row in table.find_all('tr'):
            a = row.find('a')
            dr = row.find('div', class_='lot-dr')
            if not (a and dr):
                continue
            thai_date = a.get_text(strip=True)
            eng_date = convert_thai_date(thai_date)
            prizes = [d.get_text(strip=True) for d in dr.find_all('div', class_='lot-dc')]
            if len(prizes) >= 4:
                data.append({
                    'Date': eng_date,
                    'First Prize': prizes[0],
                    '3 Front Numbers': prizes[1],
                    '3 Last Numbers': prizes[2],
                    '2 Last Numbers': prizes[3],
                })
    except Exception as e:
        print(f"Error on {url}: {e}")
    return data


current_ad = datetime.now().year
current_be = current_ad + 543

years = []
for i in range(31):
    years.append(current_be - i)

all_data = []
for be_year in years:
    url = f"https://www.myhora.com/lottery/result-{be_year}.aspx"
    year_data = process_year_page(url)
    print(f" → {be_year}: {len(year_data)} entries")
    all_data.extend(year_data)

# Build DataFrame and sort
df = pd.DataFrame(all_data)
df['DateObj'] = pd.to_datetime(df['Date'], format='%B %d, %Y')
df = df.sort_values('DateObj', ascending=False).drop('DateObj', axis=1)

print(f"\nTotal entries: {len(df)}")
# Export the data to excel
df.to_excel('lottery_data.xlsx', index=False)

# Split the '3 Front Numbers' column by spaces
front = (
    df[['Date', '3 Front Numbers']]  # Select the relevant columns
    .assign(Number=lambda d: d['3 Front Numbers'].str.split())  # Split the 3 Front Numbers column into lists
    .explode('Number')  # Explode the list into separate rows
    .drop(columns='3 Front Numbers')  # Drop the original '3 Front Numbers' column
)

# Strip leading/trailing spaces and remove rows with empty strings or spaces
front['Number'] = front['Number'].str.strip()

# Filter out rows where 'Number' is empty or only contains spaces
front = front[front['Number'] != '']

# Drop rows with NaN values (in case there were any non-numeric values)
front = front.dropna(subset=['Number'])

# First, make sure 'Number' is an integer with 3 digits
front['Number'] = front['Number'].astype(int)

# Extract hundreds, tens, and ones digits
front['Hundreds'] = front['Number'] // 100          # Divide by 100
front['Tens'] = (front['Number'] // 10) % 10         # Remove hundreds, then get tens
front['Ones'] = front['Number'] % 10                 # Remainder gives ones place

# Now, count the appearances for each digit at each position
hundreds_count = front['Hundreds'].value_counts().sort_index()
tens_count = front['Tens'].value_counts().sort_index()
ones_count = front['Ones'].value_counts().sort_index()

# Combine the counts into a single DataFrame for easy viewing
front_digit_counts = pd.DataFrame({
    'Hundreds Place': hundreds_count,
    'Tens Place': tens_count,
    'Ones Place': ones_count
}).fillna(0).astype(int)  # Fill missing digits with 0 and make sure integers

# Show result
front_digit_counts

import matplotlib.pyplot as plt

front_digit_counts.plot(kind='bar', figsize=(12, 6))
plt.title('Frequency of Digits in 3 Front Numbers by Place')
plt.xlabel('Digit')
plt.ylabel('Frequency')
plt.xticks(rotation=0)
plt.legend(title='Digit Place')
plt.tight_layout()
plt.show()
