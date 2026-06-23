
import numpy as np
import pandas as pd
from datetime import datetime

def load_data():
    """
    Function to load the necessary data for the tournament simulations, including the matches, teams and team overview data. It reads the data from the specified file paths and returns them as DataFrames.
    Returns:
    - matches_df: DataFrame containing the match information for the group stage matches.
    - teams_df: DataFrame containing the team information for all teams participating in the tournament.
    - team_overview_df: DataFrame containing the overview information for each team
    """
    # load the matches.csv and teams.csv from raw/football
    matches_df = pd.read_excel("data/raw/football/matches_grouprounds.xlsx")
    teams_df = pd.read_csv("data/raw/football/teams.csv")
    # load the processed world_cup_2026_team_overview.xlsx
    team_overview_df = pd.read_excel("data/raw/football/world_cup_2026_team_overview.xlsx")
    return matches_df, teams_df, team_overview_df

def save_data(df_team_advancement, tournament_predictions_df, third_placement_info, fn_tournament_predictions, fn_match_predictions, config, time = datetime.now().strftime("%Y%m%d_%H%M")):
    """
    Args:
    - df_team_advancement: DataFrame containing the advancement information for each team in the tournament, including how far they advanced (e.g., group stage, round of 16, quarterfinals, etc.).
    - tournament_predictions_df: DataFrame containing the predictions for each match in the tournament, including the predicted scorelines and probabilities for each outcome.
    - third_placement_info: list of dictionaries containing information about the teams that finished in third place in their groups, which is relevant for determining which teams advance to the knockout stage.
    - fn_tournament_predictions: string containing the file name for saving the tournament predictions, which includes the advancement information for each team in the tournament.
    - fn_match_predictions: string containing the file name for saving the match predictions, which includes the predicted scorelines and probabilities for each match.
    Returns:
    - tournament_predictions_df: DataFrame containing the predictions for each match in the tournament, which is saved to an Excel file.
    - df_team_advancement_sorted: DataFrame containing the advancement information for each team in the
    tournament, sorted by how far they advanced, which is saved to an Excel file.
    - third_place_df: DataFrame containing the information about the teams that finished in third place in their groups, which is saved to an Excel file.
    """
    
    # sort df team advancement by Winner, then Final, then SF, then QF, then R16, then R32 in descending order
    df_team_advancement_sorted = df_team_advancement.sort_values(["Winner", "Final", "SF", "QF", "R16", "R32"], ascending=False)

    # save to excel file
    df_team_advancement_sorted.to_excel(f"{fn_tournament_predictions}", index=True)
    tournament_predictions_df.to_excel(f"{fn_match_predictions}", index=False)

    # 3rd places
    third_place_df = pd.concat(third_placement_info, ignore_index=True)
    third_place_df.to_excel("data/processed/football/wc2026_simulation_third_place_info.xlsx", index=False)

    return tournament_predictions_df, df_team_advancement_sorted, third_place_df

def fn(config, time = datetime.now().strftime("%Y%m%d_%H%M")):
    """
    get filenames from config and the time for storage of file.
    """
    # file names.
    fn_tournament_predictions = config.get('files', {}).get('save', {}).get('tournament_predictions')
    fn_match_predictions = config.get('files', {}).get('save', {}).get('match_predictions')
    # add tournament_simulations to the filename
    fn_tournament_predictions = f"{fn_tournament_predictions}_t_{config.get('simulations').get('tournaments')}_m_{config.get('simulations').get('match')}"    
    fn_match_predictions = f"{fn_match_predictions}_t_{config.get('simulations').get('tournaments')}_m_{config.get('simulations').get('match')}"
    
    # add time to fn
    fn_tournament_predictions = f"{fn_tournament_predictions}_{time}.xlsx"
    fn_match_predictions = f"{fn_match_predictions}_{time}.xlsx"

    return fn_tournament_predictions, fn_match_predictions

def normalize_column(team_strength_dict, column_name):
    """
    Normalize the values in a specified column across all teams in the team_strength_dict.
    Args:
    - team_strength_dict: dictionary containing the strength information for each team, which is updated after each simulation run.
    - column_name: string containing the name of the column to be normalized (e.g.,
    Updates:
    - team_strength_dict: dictionary containing the strength information for each team, with an additional key
    """
    # This function would take a column name (e.g., 'attack_mv', 'defence_mv', 'elo_rating') and normalize the values in that column across all teams in the team_strength_dict, adding a new key to each team's dictionary with the normalized value (e.g., 'attack_norm', 'defence_norm', 'elo_rating_norm').
    values = [strength[column_name] for strength in team_strength_dict.values()]
    min_val = min(values)
    max_val = max(values)
    
    # return dict with normalized values for the column_name with key column_name + '_norm' for each team
    for team, strength in team_strength_dict.items():
        if max_val - min_val == 0:
            strength[column_name + '_norm'] = 0.5  # If all values are the same, assign a neutral normalized value
        else:
            strength[column_name + '_norm'] = (strength[column_name] - min_val) / (max_val - min_val)

def combine_strengths(team_strength_dict, weight_attack=1, weight_defence=1, weight_elo=1):
    # This function would combine the normalized attack, defence and elo ratings into a single strength metric for each team, which can then be used in the match simulations.
    for team, strength in team_strength_dict.items():
        # columns attack_mv_norm, defence_mv_norm and elo_rating_norm should already be in the strength dict for each team after running the normalize_column function. We can use those values to calculate the combined strength.
        team_attack_strength = strength.get('attack_mv_norm', 0)
        team_defence_strength = strength.get('defence_mv_norm', 0)
        team_elo_strength = strength.get('elo_rating_norm', 0)
        combined_attack_strength = weight_attack * team_attack_strength + weight_elo * team_elo_strength
        combined_defence_strength = weight_defence * team_defence_strength + weight_elo * team_elo_strength
        
        # update the team strength in the team_strength_dict with the combined strength values with keys 'team_total_attack_strength' and 'team_total_defence_strength'
        strength['team_total_attack_strength'] = combined_attack_strength
        strength['team_total_defence_strength'] = combined_defence_strength
        
def update_elo_ratings(team_strength_dict = dict, team1=None, team2=None, most_common_score=None, k_factor=60):
    # This function would take the current Elo ratings of both teams and the most common score from the simulations to update the Elo ratings based on the match outcome.
    # Extract home and away goals from the most common score
    home_goals, away_goals = map(int, most_common_score.split('-'))

    # Determine match outcome for Elo update
    if home_goals > away_goals:
        outcome_a = 1  # Team A wins
        outcome_b = 0  # Team B loses
    elif away_goals > home_goals:
        outcome_a = 0  # Team A loses
        outcome_b = 1  # Team B wins
    else:
        outcome_a = 0.5  # Draw
        outcome_b = 0.5  # Draw
    
    # Current Elo ratings
    team_a_strength = team_strength_dict.get(team1, {"elo_rating": 1700})
    team_b_strength = team_strength_dict.get(team2, {"elo_rating": 1700})
    elo_a = team_a_strength.get('elo_rating', 1700)  # Default to 1500 if not found
    elo_b = team_b_strength.get('elo_rating', 1700)  # Default to 1500 if not found
    
    # Calculate expected scores
    expected_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    expected_b = 1 / (1 + 10 ** ((elo_a - elo_b) / 400))
    
    # Update Elo ratings
    new_elo_a = elo_a + k_factor * (outcome_a - expected_a)
    new_elo_b = elo_b + k_factor * (outcome_b - expected_b)
    # print initial elo of team 1 and updated elo.
    # update the elo ratings in the team_strength_dict for team1 and team2 with the new elo ratings, round to the nearest integer.
    team_strength_dict[team1]['elo_rating'] = int(np.floor(new_elo_a))
    team_strength_dict[team2]['elo_rating'] = int(np.floor(new_elo_b))

    return team_strength_dict

def update_mv(team_strength_dict, team_a, team_b, most_common_score):
    # if team won, then attack MV increases 2%, if lost, then defence MV increases 2%, if draw, then both attack and defence MV increase by 1%
    home_goals, away_goals = map(int, most_common_score.split('-'))
    if home_goals > away_goals:
        team_strength_dict[team_a]['attack_mv'] *= 1.005
        team_strength_dict[team_a]['defence_mv'] *= 1.005
        team_strength_dict[team_b]['attack_mv'] *= .995
        team_strength_dict[team_b]['defence_mv'] *= .995
    elif away_goals > home_goals:
        team_strength_dict[team_b]['attack_mv'] *= 1.005
        team_strength_dict[team_b]['defence_mv'] *= 1.005
        team_strength_dict[team_a]['attack_mv'] *= .995
        team_strength_dict[team_a]['defence_mv'] *= .995
 