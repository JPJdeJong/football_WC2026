import time
import pandas as pd 
from datetime import datetime
import yaml
import copy 

from src.generic_functions import normalize_column, combine_strengths, update_elo_ratings, load_data, save_data, fn
from src.tournament_functions import main_group_stage_predictions, main_knockout_updated as knockout_main
import time



def main_tournament():
    """
    Main function to run the tournament simulations. It loads the data, initializes the team strength dictionary, runs the tournament simulations, and saves the results.
    """
    with open('./config_wc_2026.yaml', 'r') as file:
        config = yaml.safe_load(file)

    # add yyyymmdd_hhmm to the filename
    time = datetime.now().strftime("%Y%m%d_%H%M")
    # run match_prediction N times.
    # load data
    matches_df, teams_df, team_overview_df = load_data()
    matches_df = matches_df[matches_df.stage_id == 1] # only keep matches from the group stage
    matches_df_init = matches_df.copy()

    fn_tournament_predictions, fn_match_predictions = fn(config, time)

    # map team values for team dict.
    teams_map = dict(zip(teams_df["id"], teams_df["team_name"]))
    # replace values 4, 6,16,23,35,42 with Bosnia, Sweden,Turkey, Czech Republic Iraq, DR Congo respectively in teams_map
    teams_map.update({6: "Bosnia-Herzegovina", 23: "Sweden", 16: "Turkey", 4: "Czech Republic", 35: "Iraq", 42: "DR Congo",
                      19: "Ivory Coast", 27: "Iran", 30: "Cape Verde", 13: "United States"
                      })
   
    # initialize team_strength dict with team information
    team_strength_dict, initial_elo_ratings = team_information(team_overview_df, config)
    init_team_strength_dict = copy.deepcopy(team_strength_dict)  # make a copy of the initial team strength dict to reset after each simulation run
    tournaments, tournament_predictions, third_placement_info = run_tournament(config, 
                                                                               matches_df, 
                                                                               matches_df_init, 
                                                                               team_strength_dict, 
                                                                               initial_elo_ratings, 
                                                                               init_team_strength_dict)
    
    # create df tournaments.
    tournament_df = pd.DataFrame(tournaments)
    tournament_predictions_df = pd.concat(tournament_predictions, ignore_index=True)

    # get teams
    teams = team_strength_dict.keys()

    # get which team advanced.
    df_team_advancement = pd.DataFrame(0, index=teams, columns=["R32", "R16", "QF", "SF", "Final", "Winner"])
    for team in teams:
        #count how often team appears in a column in tournament_df and divide by the number of simulations to get a percentage
        for round in ["R32", "R16", "QF", "SF", "Final", "Winner"]:
            df_team_advancement.loc[team, round] = tournament_df[round].apply(lambda x: team in x).sum() / len(tournament_df) * 100

    if config.get('show', {}).get('tournament_predictions') == True:
    #tournament_df[team] = tournament_df.apply(lambda row: team in row.values, axis=1)
        print(df_team_advancement.sort_values(["Winner", "Final", "SF", "QF", "R16", "R32"], ascending=False))
     

    if config.get('files', {}).get('save', {}).get('save_predictions') == True:
        tournament_predictions_df, df_team_advancement_sorted, third_place_df = save_data(df_team_advancement, 
                                                                                          tournament_predictions_df, 
                                                                                          third_placement_info, 
                                                                                          fn_tournament_predictions, 
                                                                                          fn_match_predictions, config, 
                                                                                          time = time)
        print('\n saving files to processed folder..\n')

    if config.get('show', {}).get('most_common_scores') == True:
        # print the most common score for all matches in match_predictions_total_df
        most_common_scores = tournament_predictions_df.groupby(['home_team', 'away_team'])['most_common_score'].agg(lambda x: x.mode()[0] if not x.mode().empty else "0-0").reset_index()
        # print value count of most common scores and divide by simulation runs 
        print(most_common_scores['most_common_score'].value_counts())
    
    if config.get('show', {}).get('3rd_place_predictions') == True:
        # give an overview of when you advance. Group by amount of points and get the percentage of advancement for each group. Then sort by percentage of advancement in descending order.
        # sorted third_place df by points descending. 
        advancement_overview_3rd = third_place_df.groupby(['points'])['advancement'].value_counts(normalize=True).unstack().fillna(0) * 100
        advancement_overview_3rd = advancement_overview_3rd.reset_index().sort_values('points', ascending=False)
        print(advancement_overview_3rd.sort_values('advanced', ascending=False))

    # for every team in tournament_predictions_df, find the matches where match_label = 'Round of 32' and home_team or away_team is Netherlands. Then get the opponents of Netherlands in Round of 32 and count the chance that Netherlands is playing against the opponent in Round of 32 and divide by the number of simulations to get a percentage.
    r32_opponent_oppotunities = {}
    for team in teams:
        if config.get('show', {}).get('opponent_R32_options') == True:
            # find matches where match_label = 'Round of 32' and home_team or away_team is team.
            team_round_32 = tournament_predictions_df[(tournament_predictions_df['match_label'] == 'Round of 32') & ((tournament_predictions_df['home_team'] == team) | (tournament_predictions_df['away_team'] == team))]
            # get opponents of team in Round of 32 and 
            # count the chance that team is playing against the opponent in Round of 32 and divide by the number of simulations to get a percentage
            team_opponents = team_round_32.apply(lambda row: row['away_team'] if row['home_team'] == team else row['home_team'], axis=1)
            # round values by 1 decimal and sort by percentage in descending order
            team_opponent_counts = team_opponents.value_counts(normalize=True).round(3) * 100
            # add opponent for team to r32_opponent_oppotunities dict   
            r32_opponent_oppotunities[team] = team_opponent_counts
            if not team_opponent_counts.empty:
                # add amount of advancements.
                print(f"{team} advanced {len(team_round_32)}/{config['simulations']['tournaments']} simulations.")
                print(f"Round of 32 opponents: Top 5 by %")
                print(team_opponent_counts.head(5))    
    r32_opponent_oppotunities_df = pd.DataFrame(r32_opponent_oppotunities).fillna(0).round(3)
    # save r32_opponent_oppotunities_df to excel file
    r32_opponent_oppotunities_df.to_excel("data/processed/football/wc2026_simulation_r32_opponent_oppotunities.xlsx", index=True)  

def run_tournament(config = dict, matches_df = pd.DataFrame, matches_df_init = pd.DataFrame, team_strength_dict = dict, initial_elo_ratings = dict, init_team_strength_dict = dict):
    """
    Function to run the tournament simulations. It runs the group stage predictions and then the knockout stage predictions for a specified number of simulation runs, and collects the results in lists.
    Args:
    - config: dictionary containing the configuration parameters for the simulations.
    - matches_df: DataFrame containing the match information for the group stage.
    - matches_df_init: DataFrame containing the initial match information for the group stage, which is used to reset the matches_df after each simulation run.
    - team_strength_dict: dictionary containing the strength information for each team, which is updated after
        each simulation run.
    - initial_elo_ratings: dictionary containing the initial Elo ratings for each team, which is used to reset the Elo ratings in the team_strength_dict after each simulation run.
    - init_team_strength_dict: dictionary containing the initial strength information for each team, which is used to reset the team_strength_dict after each simulation run.
    Returns:
    - tournaments: list of DataFrames containing the teams that advanced to each round of the knockout stage for each simulation run.
    - tournament_predictions: list of DataFrames containing the match predictions for both the group stage and
    - third_placement_info: list of DataFrames containing the information about the third-placed teams in the group stage and whether they advanced to the knockout stage or not for each simulation run.
    """

    tournaments =[]
    tournament_predictions = []
    simulation_runs = config['simulations']['tournaments']
    third_placement_info = []
    for i in range(simulation_runs):
        print(f"Running simulation {i+1}/{simulation_runs}...")
        # change elo_rating in init_team_strength_dict back to initial elo ratings before each simulation run, so that we can see the effect of the group stage simulations on the knockout stage without the influence of the previous simulation runs.
        for team in init_team_strength_dict.keys():
            init_team_strength_dict[team]['elo_rating'] = initial_elo_ratings[team]
        # run for each match_day
        match_predictions_df, team_strength_dict = main_group_stage_predictions(matches_df, init_team_strength_dict, config)
        match_predictions_df['simulation_run'] = i
        # run knock out phase
        ko_teams, ko_match_predictions, third_places = knockout_main(matches_df = match_predictions_df, 
                                                       matches_df_raw = matches_df_init, 
                                                       teams_strength_dict = team_strength_dict, 
                                                       config = config)
        ko_teams['simulation_run'] = i
        ko_match_predictions['simulation_run'] = i
        # append tournaments
        tournaments.append(ko_teams)
        # change third_places to df
        third_places_df = pd.DataFrame(third_places).reset_index(drop=True)
        third_places_df['simulation_run'] = i
        # first 8 rows in third places advance, others eliminated
        third_places_df['rank'] = third_places_df.index + 1
        third_places_df['advancement'] = third_places_df['rank'].apply(lambda x: 'advanced' if x <= 8 else 'eliminated')
        third_placement_info.append(third_places_df)

        # contact match_prediction_df with ko_match_predictions and add a column to indicate whether the match is from the group stage or the knockout stage.
        ko_match_predictions['stage'] = 'knockout'
        # combination of Team 1 (Formula)	Team 2 (Formula)
        ko_match_predictions['matchday'] = ko_match_predictions['Team 1 (Formula)'] + " vs " + ko_match_predictions['Team 2 (Formula)']
        match_predictions_df['stage'] = 'group'
        # change columns in ko_match predictions.
        ko_match_predictions = ko_match_predictions.rename(columns={
            "Team 1": "home_team",
            "Team 2": "away_team",
            "Team 1 Attack Strength": "home_attack_strength",
            "Team 1 Defence Strength": "home_defence_strength",
            "Team 1 Elo Rating": "home_elo_rating",
            "Team 2 Attack Strength": "away_attack_strength",
            "Team 2 Defence Strength": "away_defence_strength",
            "P(Team 1 Win)": "home_win_prob",
            "P(Draw)": "draw_prob",
            "P(Team 2 Win)": "away_win_prob",
            "Most Common Score": "most_common_score",
            "Round" : "match_label",\
            "Match ID": "match_id"
        })
        # drop team 1 formula and team 2 formula columns from ko_match_predictions
        ko_match_predictions = ko_match_predictions.drop(columns=['Team 1 (Formula)', 'Team 2 (Formula)'])

        match_predictions_total_df = pd.concat([match_predictions_df, ko_match_predictions], ignore_index=True)
        tournament_predictions.append(match_predictions_total_df)

        # 

    return tournaments,  tournament_predictions, third_placement_info

def team_information(team_overview_df, config):
    """
    Function to create a team strength dictionary containing the attack, defence and Elo ratings for each team, which is used in the match simulations. It normalizes the attack and defence market values and combines them with the normalized Elo ratings to get a final attack and defence strength for each team.
    Args:
    - team_overview_df: DataFrame containing the overview information for each team, including their market values and Elo ratings.
    - config: dictionary containing the configuration parameters for the simulations, which may include weights for combining
    Returns:
    - team_strength_dict: dictionary containing the strength information for each team, which is updated after each simulation run.
    """
    # # team dict with team as key and keys/values of attack_dict_norm, defence_dict_norm and elo_rating_norm. Then map those values to matches_df for home and away teams.
    team_strength_dict = {}
    for team in team_overview_df['World Cup Country']:
        team_strength_dict[team] = {
            # attack mv is average of team attack mv and team midfield mv
            "attack_mv": (team_overview_df.loc[team_overview_df['World Cup Country'] == team, 'Forward Avg Market Value'].values[0] + team_overview_df.loc[team_overview_df['World Cup Country'] == team, 'Midfielder Avg Market Value'].values[0])/2, 
            # defence mv is average of defence and midfield mv
            "defence_mv": (team_overview_df.loc[team_overview_df['World Cup Country'] == team, 'Defender Avg Market Value'].values[0] + team_overview_df.loc[team_overview_df['World Cup Country'] == team, 'Midfielder Avg Market Value'].values[0])/2,  # get defence_mv for the team
            "elo_rating": team_overview_df.loc[team_overview_df['World Cup Country'] == team, 'rating'].values[0],  # get rating for the team
        }
    initial_elo_ratings = {team: strength['elo_rating'] for team, strength in team_strength_dict.items()}

    normalize_column(team_strength_dict, column_name='attack_mv')
    normalize_column(team_strength_dict, column_name='defence_mv')
    normalize_column(team_strength_dict, column_name='elo_rating')
    # set initial team attack and defence strength as the normalized market value for attack and defence respectively, then combine those with the normalized elo rating to get a final attack and defence strength for each team.
    mv_weigth = config.get('weights', {}).get('mv', 0.5)
    combine_strengths(team_strength_dict, weight_attack=mv_weigth, weight_defence=mv_weigth, weight_elo=config.get('weights', {}).get('elo', 0.5))

    return team_strength_dict, initial_elo_ratings

if __name__ == "__main__":

    main_tournament()
