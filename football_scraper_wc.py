import time
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Standard headers to bypass security walls
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Base URL to start page traversal
BASE_URL = "https://www.transfermarkt.com/vereins-statistik/wertvollstenationalmannschaften/marktwertetop?kontinent_id=0&plus=1"

# The complete list of 48 countries participating in the 2026 FIFA World Cup
# (This acts as a filtering mask so the scraper targets the exact tournament participants)
WORLD_UP_48_TEAMS = {'Algeria', 'Argentina', 'Australia', 'Austria', 'Belgium', 'Bosnia-Herzegovina', 
                     'Brazil', 'Cape Verde', 'Canada', 'Colombia', 'Croatia', 'Curaçao', 'Czechia', 
                     "Ivory Coast", 'Democratic Republic of the Congo', 'Ecuador', 'Egypt', 'England', 'France', 'Germany', 'Ghana',
                       'Haiti', 'Iran', 'Iraq', 'Japan', 'Jordan', 'Mexico', 'Morocco', 'Netherlands', 'New Zealand', 
                       'Norway', 'Panama', 'Paraguay', 'Portugal', 'Qatar', 'Saudi Arabia', 'Scotland', 'Senegal', 'South Africa',
                      'South Korea', 'Spain', 'Sweden', 'Switzerland', 'Tunisia', 'Turkiye', 'United States', 'Uruguay', 'Uzbekistan'
}
print(len(WORLD_UP_48_TEAMS))
# 'Haiti', 'Paraguay',
# print(list(world_up_48_teams.union(set(WORLD_UP_48_TEAMS))))

def get_world_cup_team_tokens():
    """Traverses Transfermarkt's paginated overview index to find target team metadata."""
    matched_teams = []
    page = 1
    
    # We will loop across multiple pages until we collect our target teams or hit page 6 (150 teams)
    while len(matched_teams) < len(WORLD_UP_48_TEAMS) and page <= 9:
        url = f"{BASE_URL}&page={page}"
        print(f"Searching index page {page} for World Cup teams...")
        
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code != 200:
                print(f"Failed to load page {page}. Stopping index traversal.")
                break
                
            soup = BeautifulSoup(res.content, "html.parser")
            table_container = soup.find("div", class_="responsive-table")
            tbody = table_container.find("table").find("tbody") if table_container else None
            
            if not tbody:
                print(f"No table rows found on page {page}.")
                break
                
            rows = tbody.find_all("tr", class_=["odd", "even"])
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    team_cell = cols[1].find("td", class_="hauptlink")
                    if team_cell and team_cell.find("a"):
                        anchor = team_cell.find("a")
                        display_name = anchor.text.strip()
                        relative_url = anchor.get("href")
                        
                        # Match parsed names with our 48-team validation set
                        if display_name in WORLD_UP_48_TEAMS:
                            # Skip duplicates if already processed
                            if any(t['name'] == display_name for t in matched_teams):
                                continue
                                
                            url_parts = relative_url.split("/")
                            if len(url_parts) >= 5:
                                matched_teams.append({
                                    "name": display_name,
                                    "slug": url_parts[1],
                                    "code": url_parts[4]
                                })
                                
            page += 1
            time.sleep(1.5) # Anti-ban sleep
            
        except Exception as e:
            print(f"Index parsing interrupted on page {page}: {e}")
            break
            
    return matched_teams

def scrape_deep_squad(team_meta):
    """Navigates to team_soup and harvests data for every player in the squad."""
    player_rows_collected = []
    profile_url = f"https://www.transfermarkt.com/{team_meta['slug']}/startseite/verein/{team_meta['code']}"
    print(f" -> Accessing squad table: {team_meta['name']} ({profile_url})")
    
    try:
        res = requests.get(profile_url, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            return []
            
        team_soup = BeautifulSoup(res.content, "html.parser")
        squad_wrappers = team_soup.find_all("div", class_="responsive-table")
        
        if not squad_wrappers:
            return []
            
        tbody = squad_wrappers[0].find("table").find("tbody")
        rows = tbody.find_all("tr", class_=["odd", "even"]) if tbody else []
        
        for row in rows:
            name_cell = row.find("td", class_="hauptlink")
            if not name_cell or not name_cell.find("a"):
                continue
                
            player_name = name_cell.find("a").text.strip()
            
            # Position extraction
            inline_table = row.find("table", class_="inline-table")
            position = "N/A"
            if inline_table:
                it_rows = inline_table.find_all("tr")
                if len(it_rows) > 1:
                    position = it_rows[1].text.strip()
                    
            # Age & Club extraction
            age, club = "N/A", "N/A"
            zentriert_cells = row.find_all("td", class_="zentriert")
            if len(zentriert_cells) >= 2:
                age_text = zentriert_cells[1].text.strip()
                age_match = re.search(r'\((\d+)\)', age_text)
                age = age_match.group(1) if age_match else age_text
                
            if len(zentriert_cells) >= 3:
                club_img = zentriert_cells[2].find("img")
                if club_img and club_img.get("title"):
                    club = club_img.get("title")
                    
            # Market Value extraction
            mv_cell = row.find("td", class_="rechts hauptlink")
            market_value = mv_cell.text.strip() if mv_cell else "N/A"
            
            player_rows_collected.append({
                "World Cup Country": team_meta["name"],
                "Country Slug": team_meta["slug"],
                "Transfermarkt Verein Code": team_meta["code"],
                "Player Name": player_name,
                "Position": position,
                "Age": age,
                "Current Club": club,
                "Market Value": market_value
            })
            
    except Exception as err:
        print(f"      Error collecting players for {team_meta['name']}: {err}")
        
    return player_rows_collected

if __name__ == "__main__":
    # 1. Harvest target codes for the 48 nations
    target_teams = get_world_cup_team_tokens()
    print(f"\nFound {len(target_teams)} out of 48 target World Cup nations on the index pages.")
    print(target_teams)
    print(WORLD_UP_48_TEAMS)
    print (f"Missing teams: {set(WORLD_UP_48_TEAMS) - set(t['name'] for t in target_teams)}")
    all_tournament_players = []
    
    # 2. Iterate through each country to parse all player items
    for index, team in enumerate(target_teams, start=1):
        print(f"[{index}/{len(target_teams)}] Scraping...")
        squad_data = scrape_deep_squad(team)
        all_tournament_players.extend(squad_data)
        
        # Throttling frequency timing to remain friendly to host servers
        time.sleep(2.0)
        
    # 3. Compile matrix into clean CSV format
    if all_tournament_players:
        full_df = pd.DataFrame(all_tournament_players)
        output_name = "world_cup_2026_all_players_updated.csv"
        
        # Save dataset using utf-8-sig format to safely keep special accents in player names
        full_df.to_csv(output_name, index=False, encoding="utf-8-sig")
        print(f"\nProcess Completed Successfully!")
        print(f"Extracted a total of {len(full_df)} rows. File saved as '{output_name}'")
    else:
        print("\nScraping routine yielded no players. Check connection parameters.")