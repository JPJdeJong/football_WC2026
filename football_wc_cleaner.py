import pandas as pd
import numpy as np

# get world cup 2026 data from data/ra/wfootball

# Football World Cup 2026 Player Data Cleaning Script
# clean the market value column to be numeric, and extract the age as a number as well. e.g. 30.00m is 30000000, 500k is 500000, and 1.5m is 1500000. Also extract the age as a number from the age column, which may have the format "30 (1990-01-01)". The output should be a cleaned CSV file with the same columns but with the market value and age columns cleaned.
def clean_market_value(mv):
    if isinstance(mv, str):
        mv = mv.lower().replace("€", "").strip()
        if "m" in mv:
            return float(mv.replace("m", "")) * 1_000_000
        elif "k" in mv:
            return float(mv.replace("k", "")) * 1_000
    return np.nan

# add which line a player plays, goalkeeper, defender, midfielder, or forward. This information is in the position column, but it may be in the format "Defender (Center Back)" or "Midfielder (Attacking Midfielder)". We want to extract the main position as a new column called "Main Position". The output should be a cleaned CSV file with the same columns but with the market value, age, and main position columns cleaned.
#  centre back goas to defender, winger to attacker, and so on. We want to extract the main position as a new column called "Main Position". The output should be a cleaned CSV file with the same columns but with the market value, age, and main position columns cleaned.
def add_player_line(position):
    if isinstance(position, str):
        position = position.lower()
        if "goalkeeper" in position:
            return "Goalkeeper"
        elif "forward" in position or "attacker" in position or "winger" in position or "striker" in position:
            return "Forward"
 
        elif "defender" in position or "back" in position or "full" in position:
            return "Defender"
        elif "midfielder" in position or "midfield":
            return "Midfielder"
        else:
            return "Other"
    return np.nan

# create a team overview df with columns: country, code, team market value, and average market value for defenders, midfielders, and forwards. based on the average of the 5 most valuable players per line. For goalkeeper take the value of the most valuable player.
def create_team_overview(df):
    team_overview = df.groupby(["World Cup Country", "Main Position"]).agg({
        "Transfermarkt Verein Code": "first",
        "Market Value": "sum"
    }).reset_index()
    # Pivot the table to have separate columns for each line's average market value
    team_overview = team_overview.pivot(index=["World Cup Country", "Transfermarkt Verein Code"], columns="Main Position", values="Market Value").reset_index()

    # Calculate average market value for each line
    for line in ["Defender", "Midfielder", "Forward"]:
        line_avg = df[df["Main Position"] == line].groupby("World Cup Country")["Market Value"].apply(lambda x: x.nlargest(5).median())
        team_overview[f"{line} Avg Market Value"] = team_overview["World Cup Country"].map(line_avg)
    
    # For Goalkeepers, take the value of the most valuable player
    goalkeeper_value = df[df["Main Position"] == "Goalkeeper"].groupby("World Cup Country")["Market Value"].max()
    
    # add the goalkeeper value to the defender value and average it to get a more balanced view of the team's defense, since the goalkeeper is an important part of the defense. We can call this "Defender Avg Market Value" as well, since it will be used in the same way as the defender market value in the predictor.
    team_overview["Goalkeeper Market Value"] = team_overview["World Cup Country"].map(goalkeeper_value)
    team_overview["Defender Avg Market Value"] = team_overview[["Defender Avg Market Value", "Goalkeeper Market Value"]].mean(axis=1)
    
    # drop goalkeeper mv
    team_overview = team_overview.drop(columns=["Goalkeeper Market Value"])

    return team_overview

def main_team_values(df_all_players: pd.DataFrame) -> pd.DataFrame:
    # # Load the raw data
    # raw_df = pd.read_csv("data/raw/football/world_cup_2026_all_players.csv")

    # 

    df = df_all_players.copy()
    # Clean the Market Value column
    df["Market Value"] = df["Market Value"].apply(clean_market_value)
    print(df["Market Value"].head())

    # add a column with main position
    df["Main Position"] = df["Position"].apply(add_player_line)
    # team strength df
    team_overview_df = create_team_overview(df)
    # print(team_overview_df.head())

    # load the eloratings.csv from raw/football
    eloratings_df = pd.read_csv("data/raw/football/eloratings.csv")

    # only keep latest ratings for each team, which is the row with the max date for each team
    eloratings_df = eloratings_df.sort_values("date").groupby("team").tail(1)
    
    # print(eloratings_df.head())
    # merge the team overview df with the eloratings df on the country name, which is in the "World Cup Country" column in the team overview df and in the "Country" column in the eloratings df. We want to keep all rows from the team overview df and only the matching rows from the eloratings df. The output should be a cleaned CSV file with the same columns as the team overview df plus a new column called "Elo Rating" from the eloratings df.
    team_overview_df = team_overview_df.merge(eloratings_df[["team", "rating"]], left_on="World Cup Country", right_on="team", how="left").drop(columns=["team"])
    # print(team_overview_df.head())

    # Save the cleaned data
    # df.to_csv("data/processed/football/world_cup_2026_all_players_cleaned_updated.csv", index=False)
    # team_overview_df.to_csv("data/processed/football/world_cup_2026_team_overview_updated.csv", index=False)

    # save both as excel files as well
    df.to_excel("data/processed/football/world_cup_2026_all_players_cleaned_updated.xlsx", index=False)
    team_overview_df.to_excel("data/processed/football/world_cup_2026_team_overview_updated.xlsx", index=False)

    return team_overview_df

if __name__ == "__main__":
    main_team_values()
# #     # Load the raw data
#     raw_df = pd.read_csv("data/raw/football/world_cup_2026_all_players.csv")

#     df = raw_df.copy()
#     # Clean the Market Value column
#     df["Market Value"] = df["Market Value"].apply(clean_market_value)
#     print(df["Market Value"].head())

#     # add a column with main position
#     df["Main Position"] = df["Position"].apply(add_player_line)
#     # team strength df
#     team_overview_df = create_team_overview(df)
#     # print(team_overview_df.head())

#     # load the eloratings.csv from raw/football
#     eloratings_df = pd.read_csv("data/raw/football/eloratings.csv")

#     # only keep latest ratings for each team, which is the row with the max date for each team
#     eloratings_df = eloratings_df.sort_values("date").groupby("team").tail(1)
    
#     # print(eloratings_df.head())
#     # merge the team overview df with the eloratings df on the country name, which is in the "World Cup Country" column in the team overview df and in the "Country" column in the eloratings df. We want to keep all rows from the team overview df and only the matching rows from the eloratings df. The output should be a cleaned CSV file with the same columns as the team overview df plus a new column called "Elo Rating" from the eloratings df.
#     team_overview_df = team_overview_df.merge(eloratings_df[["team", "rating"]], left_on="World Cup Country", right_on="team", how="left").drop(columns=["team"])
#     # print(team_overview_df.head())

#     # Save the cleaned data
#     df.to_csv("data/processed/football/world_cup_2026_all_players_cleaned_updated.csv", index=False)
#     team_overview_df.to_csv("data/processed/football/world_cup_2026_team_overview_updated.csv", index=False)

#     # save both as excel files as well
#     df.to_excel("data/processed/football/world_cup_2026_all_players_cleaned_updated.xlsx", index=False)
#     team_overview_df.to_excel("data/processed/football/world_cup_2026_team_overview_updated.xlsx", index=False)