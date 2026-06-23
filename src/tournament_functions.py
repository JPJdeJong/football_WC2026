import pandas as pd 
import numpy as np

from src.generic_functions import normalize_column, combine_strengths, update_elo_ratings
from src.match_functions import simulate_match

# ignore warnings for cleaner output
import warnings
warnings.filterwarnings("ignore")

THIRD_SLOTS = {
    74: set("ABCDF"),
    77: set("CDFGH"),
    79: set("CEFHI"),
    80: set("EHIJK"),
    81: set("BEFIJ"),
    82: set("AEHIJ"),
    85: set("EFGIJ"),
    87: set("DEIJL"),
}

GROUPS = {
    "A": ["Mexico",        "South Africa",           "South Korea",  "Czech Republic"],
    "B": ["Canada",        "Bosnia and Herzegovina", "Switzerland",  "Qatar"],
    "C": ["Brazil",        "Morocco",                "Scotland",     "Haiti"],
    "D": ["United States", "Paraguay",               "Australia",    "Turkey"],
    "E": ["Germany",       "Ivory Coast",            "Ecuador",      "Curacao"],
    "F": ["Netherlands",   "Japan",                  "Sweden",       "Tunisia"],
    "G": ["Belgium",       "Egypt",                  "Iran",         "New Zealand"],
    "H": ["Spain",         "Cape Verde",             "Saudi Arabia", "Uruguay"],
    "I": ["France",        "Senegal",                "Norway",       "Iraq"],
    "J": ["Argentina",     "Algeria",                "Austria",      "Jordan"],
    "K": ["Portugal",      "DR Congo",               "Uzbekistan",   "Colombia"],
    "L": ["England",       "Croatia",                "Ghana",        "Panama"],
}

ALL_TEAMS  = [t for teams in GROUPS.values() for t in teams]
TEAM_GROUP = {t: g for g, ts in GROUPS.items() for t in ts}

def main_group_stage_predictions(matches_df, team_strength_dict = dict, config = dict):
    """
    Function to run the group stage simulation of the WC2026
    Args:
        matches_df: DataFrame containing the information for all group stage matches, including home and away teams, match labels, and actual results if available.
        team_strength_dict: dictionary containing the strength information for each team, with an additional key
        config: dictionary containing configuration settings for the simulation
    Returns:    
        match_predictions: DataFrame containing the predictions for each match, including probabilities for home win, draw, and away win, as well as the most common score and its percentage.
        team_strength_dict: updated dictionary containing the strength information for each team after running the simulations for the group stage matches.

    """
    # This function would contain the logic to run simulations for all group stage matches and return predictions.
    # list match outcomes
    match_predictions = []

    # split the matches df per match_day and run the simulations for each match day, then update the elo ratings after each match day before running the next match day simulations. This way we can capture the dynamic changes in team strength throughout the group stage.
    matchday_df = matches_df.groupby('group_round')
    match_round_outcomes = {}
    match_predictions = []
    for matchday, matches in matchday_df:
        matches = matches.reset_index(drop=True)
        # only keep first 5 rows of matches for testing
        for index, row in matches.iterrows():
            team_a_strength = team_strength_dict.get(row['home_team_id'], {"team_total_attack_strength": 1, "team_total_defence_strength": 1})
            team_b_strength = team_strength_dict.get(row['away_team_id'], {"team_total_attack_strength": 1, "team_total_defence_strength": 1})
            weight_team_attack = config.get('weights', {}).get('team_attack_strength', 2)
            weight_team_defense = config.get('weights', {}).get('team_defense_strength', 2)
            match_outcome = simulate_match(team_h = row['home_team_id'],
                                            team_a = row['away_team_id'],
                                            att_h = weight_team_attack * team_a_strength["team_total_attack_strength"], 
                                            att_a = weight_team_attack * team_b_strength["team_total_attack_strength"],
                                            def_h = weight_team_defense * team_a_strength["team_total_defence_strength"],
                                            def_a = weight_team_defense * team_b_strength["team_total_defence_strength"], 
                                            n_simulations = config.get('simulations', {}).get('match', 1),
                                            max_goals=config.get('simulations', {}).get('max_goals', 6))
            
            # # if matches actual result is not empty. Fill in the score into most_common_score and set most_common_pct to 100%. This way we can use the actual score for updating elo ratings and market values, while still keeping the simulated probabilities for win/draw/loss.
            if config.get('data', {}).get('actual_results') == True:
                if pd.notna(row['actual_result']):
                # if pd.notna(row['actual_result']):
                    match_outcome['most_common_score'] = row['actual_result']
                    match_outcome['most_common_pct'] = 100.0

            match_round_outcomes[(row['home_team_id'], row['away_team_id'])] = match_outcome
            match_predictions.append({
                "match_id": row['id'],
                "home_team": row['home_team_id'],
                "away_team": row['away_team_id'],
                "home_win_prob": match_outcome["home_win_prob"],
                "draw_prob": match_outcome["draw_prob"],
                "away_win_prob": match_outcome["away_win_prob"],
                "most_common_score": match_outcome["most_common_score"],
                "most_common_pct": match_outcome["most_common_pct"],
                "matchday": matchday,
                "match_label": row['match_label'],
                "home_attack_strength": team_a_strength["team_total_attack_strength"],
                "home_defence_strength": team_a_strength["team_total_defence_strength"],
                "home_elo_rating": team_a_strength["elo_rating"],
                "home_total_attack_strength": team_a_strength["team_total_attack_strength"],
                "home_total_defence_strength": team_a_strength["team_total_defence_strength"],
                "away_attack_strength": team_b_strength["team_total_attack_strength"],
                "away_defence_strength": team_b_strength["team_total_defence_strength"],
                "away_elo_rating": team_b_strength["elo_rating"],
                "away_total_attack_strength": team_b_strength["team_total_attack_strength"],
                "away_total_defence_strength": team_b_strength["team_total_defence_strength"],
            })
            team_strength_dict = update_elo_ratings(team_strength_dict, row['home_team_id'], row['away_team_id'], match_outcome["most_common_score"])
            
            # update_mv(team_strength_dict, row['home_team_id'], row['away_team_id'], match_outcome["most_common_score"])
            # print team a elo rating and team b elo rating after the update
        # after each matchday, update the normalized values and update the combined strength.
        normalize_column(team_strength_dict, column_name='attack_mv')
        normalize_column(team_strength_dict, column_name='defence_mv')
        normalize_column(team_strength_dict, column_name='elo_rating')
        combine_strengths(team_strength_dict, 
                          weight_attack=config.get('weights', {}).get('mv', 0.4), 
                          weight_defence=config.get('weights', {}).get('mv', 0.4), 
                          weight_elo=config.get('weights', {}).get('elo', 0.6))
    return pd.DataFrame(match_predictions), team_strength_dict


def generate_group_standings(matches_df, teams_strength_dict):
    """
    Turns a DataFrame of group match results into a final standings table.
    Implements the 2026 FIFA rule: Head-to-Head record comes before Overall Goal Difference.
    
    Args:
    - matches_df: DataFrame containing the matches for a specific group, with columns for home team, away team, and most common score.
    - teams_strength_dict: dictionary containing the strength information for each team, which may be used for tiebreakers if needed.
    Returns:
    - df: DataFrame representing the final standings for the group, sorted by points, head-to-head record, goal difference, and goals scored.
    """
    teams = list(set(matches_df['home_team']).union(set(matches_df['away_team'])))
    standings = {team: {'P': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'Pts': 0} for team in teams}
    
    # 1. Accumulate basic records
    for _, row in matches_df.iterrows():
        t1, t2, s1, s2 = row['home_team'], row['away_team'], int(row['most_common_score'][0]), int(row['most_common_score'][2])
        
        standings[t1]['P'] += 1
        standings[t2]['P'] += 1
        standings[t1]['GF'] += s1
        standings[t1]['GA'] += s2
        standings[t2]['GF'] += s2
        standings[t2]['GA'] += s1
        
        if s1 > s2:
            standings[t1]['W'] += 1; standings[t1]['Pts'] += 3
            standings[t2]['L'] += 1
        elif s2 > s1:
            standings[t2]['W'] += 1; standings[t2]['Pts'] += 3
            standings[t1]['L'] += 1
        else:
            standings[t1]['D'] += 1; standings[t1]['Pts'] += 1
            standings[t2]['D'] += 1; standings[t2]['Pts'] += 1

    df = pd.DataFrame.from_dict(standings, orient='index')
    df['GD'] = df['GF'] - df['GA']
    df = df.reset_index().rename(columns={'index': 'Team'})
    
    # 2. Apply Custom 2026 Sort Logic (Points -> Head-to-Head via manual bubble adjustment -> Overall GD -> Overall GF)
    df = df.sort_values(by=['Pts', 'GD', 'GF'], ascending=False).reset_index(drop=True)
    h2h_match_result = None
    # Check for direct point ties to evaluate Head-to-Head rule
    for i in range(len(df) - 1):
        if df.loc[i, 'Pts'] == df.loc[i+1, 'Pts']:
            team_a, team_b = df.loc[i, 'Team'], df.loc[i+1, 'Team']
            # Find the match played between these two specific teams
            h2h_match = matches_df[((matches_df['home_team'] == team_a) & (matches_df['away_team'] == team_b)) | 
                                   ((matches_df['home_team'] == team_b) & (matches_df['away_team'] == team_a))]
            if not h2h_match.empty:
                m = h2h_match.iloc[0]
                # Determine who won the head-to-head
                winner = None
                if m['home_team'] == team_a and m['most_common_score'][0] > m['most_common_score'][2]: winner = team_a
                elif m['home_team'] == team_a and m['most_common_score'][2] > m['most_common_score'][0]: winner = team_b
                elif m['away_team'] == team_a and m['most_common_score'][0] > m['most_common_score'][2]: winner = team_b
                elif m['away_team'] == team_a and m['most_common_score'][2] > m['most_common_score'][0]: winner = team_a
                
                # Swap rows if the lower-ranked team in the initial sort won the Head-to-Head
                if winner == team_b:
                    df.iloc[i], df.iloc[i+1] = df.iloc[i+1].copy(), df.iloc[i].copy()
                # if draw, set h2h_match_result to draw. No change in order needed.
                if m['home_team'] == team_a and m['most_common_score'][0] == m['most_common_score'][2] \
                or m['away_team'] == team_a and m['most_common_score'][0] == m['most_common_score'][2]:
                    # print(f"H2H is draw. base on ELO..")
                    h2h_match_result = 'Draw'
                    # No change in order needed for a draw, but we could log this if desired.  

        # if pts, GD and GF are the same, and h2h_match_result is draw, then sort by Elo rating as the final tiebreaker
        if df.loc[i, 'Pts'] == df.loc[i+1, 'Pts'] and \
            df.loc[i, 'GD'] == df.loc[i+1, 'GD'] and \
                df.loc[i, 'GF'] == df.loc[i+1, 'GF']:
            if h2h_match_result == 'Draw':
                # get from team strength dict the latest elo rating for each team and add to a dict {team: elo_rating}    
                team_elo_dict = {team: info['elo_rating'] for team, info in teams_strength_dict.items()}
                df['Elo Rating'] = df['Team'].map(team_elo_dict)
                # sort standings by points, then head-to-head (already applied), then goal difference, then goals scored, then Elo rating
                df = df.sort_values(by=['Pts', 'Elo Rating'], ascending=False).reset_index(drop=True)

    df['Pos'] = df.index + 1
    
    return df.reset_index()

def build_knockout_roster():
    """
    Returns a master DataFrame containing the structure and pairings of the 2026 World Cup 
    knockout bracket from the Round of 32 up to the Final.
    """
    roster = []
    
    # --- ROUND OF 32 (Matches 73 to 88) ---
    r32_pairings = [
        (73, "Runner-up Group A", "Runner-up Group B"),
        (74, "Winner Group E", "3rd Group A/B/C/D/F"),
        (75, "Winner Group F", "Runner-up Group C"),
        (76, "Winner Group C", "Runner-up Group F"),
        (77, "Winner Group I", "3rd Group C/D/F/G/H"),
        (78, "Runner-up Group E", "Runner-up Group I"),
        (79, "Winner Group A", "3rd Group C/E/F/H/I"),
        (80, "Winner Group L", "3rd Group E/H/I/J/K"),
        (81, "Winner Group D", "3rd Group B/E/F/I/J"),
        (82, "Winner Group G", "3rd Group A/E/H/I/J"),
        (83, "Runner-up Group K", "Runner-up Group L"),
        (84, "Winner Group H", "Runner-up Group J"),
        (85, "Winner Group B", "3rd Group E/F/G/I/J"),
        (86, "Winner Group J", "Runner-up Group H"),
        (87, "Winner Group K", "3rd Group D/E/I/J/L"),
        (88, "Runner-up Group D", "Runner-up Group G")
    ]
    for m_id, t1, t2 in r32_pairings:
        roster.append({'Round': 'Round of 32', 'Match ID': m_id, 'Team 1 (Formula)': t1, 'Team 2 (Formula)': t2})
        
    # --- ROUND OF 16 (Matches 89 to 96) ---
    r16_pairings = [
        (89, "Winner Match 73", "Winner Match 75"),
        (90, "Winner Match 74", "Winner Match 77"),
        (91, "Winner Match 76", "Winner Match 78"),
        (92, "Winner Match 79", "Winner Match 80"),
        (93, "Winner Match 83", "Winner Match 84"),
        (94, "Winner Match 81", "Winner Match 82"),
        (95, "Winner Match 86", "Winner Match 88"),
        (96, "Winner Match 85", "Winner Match 87")
    ]
    for m_id, t1, t2 in r16_pairings:
        roster.append({'Round': 'Round of 16', 'Match ID': m_id, 'Team 1 (Formula)': t1, 'Team 2 (Formula)': t2})

    # --- QUARTERFINALS (Matches 97 to 100) ---
    qf_pairings = [
        (97, "Winner Match 89", "Winner Match 90"),
        (98, "Winner Match 93", "Winner Match 94"),
        (99, "Winner Match 91", "Winner Match 92"),
        (100, "Winner Match 95", "Winner Match 96")
    ]
    for m_id, t1, t2 in qf_pairings:
        roster.append({'Round': 'Quarterfinals', 'Match ID': m_id, 'Team 1 (Formula)': t1, 'Team 2 (Formula)': t2})

    # --- SEMIFINALS (Matches 101 to 102) ---
    sf_pairings = [
        (101, "Winner Match 97", "Winner Match 98"),
        (102, "Winner Match 99", "Winner Match 100")
    ]
    for m_id, t1, t2 in sf_pairings:
        roster.append({'Round': 'Semifinals', 'Match ID': m_id, 'Team 1 (Formula)': t1, 'Team 2 (Formula)': t2})

    # --- FINAL & 3RD PLACE (Matches 103 & 104) ---
    roster.append({'Round': 'Third Place Playoff', 'Match ID': 103, 'Team 1 (Formula)': 'Loser Match 101', 'Team 2 (Formula)': 'Loser Match 102'})
    roster.append({'Round': 'Final', 'Match ID': 104, 'Team 1 (Formula)': 'Winner Match 101', 'Team 2 (Formula)': 'Winner Match 102'})

    return pd.DataFrame(roster)

def assign_third_place(best_thirds):
    """
    Assign the 8 best third-place teams to their Round-of-32 slots.
    Each slot only accepts thirds from specific source groups (FIFA rules).
    Uses backtracking to find a valid assignment.

    Args:
    - best_thirds: list of dicts with keys 'group' and 'team' for the 8 best third-place teams.
    Returns:
    - assignment: dict mapping Round-of-32 match IDs to team names for the third-place qualifiers.
    """
    thirds_by_group = {info["group"]: info["team"] for info in best_thirds}

    # Sort slots from most constrained (fewest eligible groups) to least
    slots = sorted(THIRD_SLOTS.keys(), key=lambda s: len(THIRD_SLOTS[s]))
    assignment = {}

    def backtrack(idx, remaining_groups):
        if idx == len(slots):
            return len(remaining_groups) == 0
        slot = slots[idx]
        for group in list(remaining_groups):
            if group in THIRD_SLOTS[slot]:
                assignment[slot] = thirds_by_group[group]
                remaining_groups.discard(group)
                if backtrack(idx + 1, remaining_groups):
                    return True
                remaining_groups.add(group)
                del assignment[slot]
        return False

    remaining = set(thirds_by_group.keys())
    if not backtrack(0, remaining):
        # Fallback: unconstrained assignment (rare edge case)
        groups_list = list(thirds_by_group.keys())
        for i, slot in enumerate(THIRD_SLOTS.keys()):
            if i < len(groups_list):
                assignment[slot] = thirds_by_group[groups_list[i]]
    return assignment

def select_and_assign_thirds(group_results, strengths):
    """
    Pick the 8 best predicted third-place teams and assign them to bracket slots.
    Updates standings_detail in-place with 'Advances (3rd)' where applicable.
    Returns third_assignment dict {match_id: team_name}.
    """
    # group results is a group
    thirds2 = []
    # from group results get the teams in third place and their points, goal difference, and goals for each group
    for grp, standings in group_results:

        third_team = standings.iloc[2]  # third place team
        # from third place team get points, goal difference, and goals form the standings df
        points = standings.loc[2, 'Pts']
        goal_diff = standings.loc[2, 'GD']
        goals_for = standings.loc[2, 'GF']

        thirds2.append({
            "team":      third_team,
            "group":     grp,
            "points":    points,
            "goal_diff": goal_diff,
            "goals_for": goals_for,
        })

    # sort thirds2 by points, then goal difference, then goals for
    thirds2_sorted = sorted(thirds2, key=lambda x: (-x["points"], -x["goal_diff"], -x["goals_for"]))

    # # Sort: best third-place teams by points, then GD, then GF
    # sorted_thirds = sorted(thirds, key=lambda x: (-x["exp_pts"], -x["exp_gd"], -x["exp_gf"]))
    best_8 = thirds2_sorted[:8]
    qualified_groups = {t["group"] for t in best_8}

    # Convert to format expected by assign_third_place
    best_8_info = [{"group": t["group"], "team": t["team"]} for t in best_8]
    third_assignment = assign_third_place(best_8_info)
    return third_assignment, thirds2_sorted

def add_ko_team_strength(df, teams_strength_dict):
    for idx, row in df.iterrows():
        team1 = row['Team 1']
        team2 = row['Team 2']
        if team1 in teams_strength_dict:
            df.at[idx, 'Team 1 Attack Strength'] = teams_strength_dict[team1]['team_total_attack_strength']
            df.at[idx, 'Team 1 Defence Strength'] = teams_strength_dict[team1]['team_total_defence_strength']
        if team2 in teams_strength_dict:
            df.at[idx, 'Team 2 Attack Strength'] = teams_strength_dict[team2]['team_total_attack_strength']
            df.at[idx, 'Team 2 Defence Strength'] = teams_strength_dict[team2]['team_total_defence_strength']
    return df

def run_round(df, previous_round_winners=None, team_strength_dict=None, config=None):
    """
    Run a knock out round.
    Args:
    - df: DataFrame containing the matches for the current round, with columns for 'Team 1 (Formula)' and 'Team 2 (Formula)' which may reference winners from previous matches.
    - previous_round_winners: dict mapping match IDs from the previous round to the winning team
    - team_strength_dict: dict containing the strength information for each team, which may be used for simulating matches and updating ratings.
    - config: dict containing configuration settings for the simulation, such as weights for attack/defense strength and the number of simulations to run for each match.
    Returns:
    - df: updated DataFrame with actual team names for 'Team 1' and 'Team 2', as well as simulation results for each match.
    - match_winners: dict mapping match IDs for the current round to the winning team, which can be used for the next round's simulations.
    """
    # get team stuff
    df.loc[:, 'Team 1'] = df.apply(lambda row: previous_round_winners.get(int(row['Team 1 (Formula)'].split()[-1]), "TBD") if row['Team 1 (Formula)'].startswith("Winner Match ") else row['Team 1'], axis=1)
    df.loc[:, 'Team 2'] = df.apply(lambda row: previous_round_winners.get(int(row['Team 2 (Formula)'].split()[-1]), "TBD") if row['Team 2 (Formula)'].startswith("Winner Match ") else row['Team 2'], axis=1)
    
    # add strengths for teams in the current round
    df = add_ko_team_strength(df, team_strength_dict)

    # iterate over round matches, and simulate.
    match_winners = {}
    for idx, row in df.iterrows():
        team1 = row['Team 1']
        team2 = row['Team 2']
        att_h = row['Team 1 Attack Strength']
        def_h = row['Team 1 Defence Strength']
        att_a = row['Team 2 Attack Strength']
        def_a = row['Team 2 Defence Strength']
        weigth_attack = config.get('weigths', {}).get('team_ko_attack_strength', 1)
        weigth_defense = config.get('weigths', {}).get('team_ko_defense_strength', 1)
        sim_result = simulate_match(team_h= team1, 
                                    team_a= team2,            
                                    att_h= weigth_attack * att_h, 
                                    att_a= weigth_attack * att_a, 
                                    def_h= weigth_defense * def_h, 
                                    def_a= weigth_defense * def_a,
                                    n_simulations = config.get('simulations', {}).get('match', 1),  # default 1 sim
                                    max_goals=config.get('simulations', {}).get('ko_max_goals', 6)) # default max 6 goals.
        
        df.at[idx, 'P(Team 1 Win)'] = sim_result['home_win_prob']
        df.at[idx, 'P(Team 2 Win)'] = sim_result['away_win_prob']
        df.at[idx, 'P(Draw)'] = sim_result['draw_prob']
        df.at[idx, 'most_common_score'] = sim_result['most_common_score']    
        df.at[idx, 'most_common_pct'] = sim_result['most_common_pct']   
        if sim_result.get('most_common_score') in ['0-0', '1-1', '2-2', '3-3', '4-4', '5-5']:
            # random draw winner by 50% chance.
            winner = team1 if np.random.rand() < 0.5 else team2
        else:
            winner = team1 if sim_result['home_win_prob'] >= sim_result['away_win_prob'] else team2
        match_winners[df.at[idx, 'Match ID']] = winner
    
        team_a_strength = team_strength_dict.get(team1, {"team_total_attack_strength": 0, "team_total_defence_strength": 0})
        team_b_strength = team_strength_dict.get(team2, {"team_total_attack_strength": 0, "team_total_defence_strength": 0})
        df.at[idx, 'home_total_attack_strength'] = team_a_strength.get('team_total_attack_strength', 0)
        df.at[idx, 'home_total_defence_strength'] = team_a_strength.get('team_total_defence_strength', 0)
        df.at[idx, 'away_total_attack_strength'] = team_b_strength.get('team_total_attack_strength', 0)
        df.at[idx, 'away_total_defence_strength'] = team_b_strength.get('team_total_defence_strength', 0)
        # get match outcom and updates values
        match_outcome = sim_result.copy()
        update_elo_ratings(team_strength_dict, team1, team2, match_outcome["most_common_score"])
        # update_mv(team_strength_dict, team1, team2, match_outcome["most_common_score"])
    # after each matchday, update the normalized values and update the combined strength.
    normalize_column(team_strength_dict, column_name='attack_mv')
    normalize_column(team_strength_dict, column_name='defence_mv')
    normalize_column(team_strength_dict, column_name='elo_rating')
    weight_mv = config.get('strength_weights', {}).get('mv', 0.4)
    weight_elo = config.get('strength_weights', {}).get('elo', 0.6)
    combine_strengths(team_strength_dict, weight_attack=weight_mv, weight_defence=weight_mv, weight_elo=weight_elo)
    return df, match_winners


def main_knockout_updated(matches_df=None, matches_df_raw=None, teams_strength_dict= None, config=None):
    """
    Function to run the knockout stage simulation of the WC2026
    Args:
        matches_df: DataFrame containing the matches for the knockout stage, with columns for home team, away team, and most common score.
        matches_df_raw: DataFrame containing the raw match data.
        teams_strength_dict: dictionary containing the strength information for each team.
        config: configuration dictionary containing various settings for the simulation.
    Returns:
        knockout_predictions_df: DataFrame containing the predictions for each knockout match, including probabilities for home win, draw, and away win, as well as the most common score and its percentage.
        advancing_teams: dictionary containing the teams that advance from each knockout round (Round of 32, Round of 16, Quarterfinals, Semifinals).
        best_8_info: list of teams that finish in third place in their groups.
    """
    # matches_df = pd.read_excel("data/processed/football/match_predictions.xlsx")
    # get original matches df from raw
    matches_df_raw = pd.read_csv("data/raw/football/matches.csv")
    # get roster where stage is not 1 
    matches_df_raw = matches_df_raw[matches_df_raw['stage_id'] != 1]
    # teams_info = pd.read_excel('data/processed/football/world_cup_2026_team_overview.xlsx')
    knockout_roster_df = build_knockout_roster()

    # make list of df per group
    group_dfs = []
    for group in matches_df['match_label'].unique():
        group_df = matches_df[matches_df['match_label'] == group]
        group_dfs.append((group, group_df))

    # generate standings per group.
    standings_lst = []
    for group_name, group_df in group_dfs:
        standings_df = generate_group_standings(group_df, teams_strength_dict)
        standings_lst.append((group_name, standings_df))
  
    team_elo_dict = {team: info['elo_rating'] for team, info in teams_strength_dict.items()}
    # teams_info.set_index('World Cup Country')['rating'].to_dict()
    third_assignment, best_8_info  = select_and_assign_thirds(group_results = standings_lst, strengths = team_elo_dict)
    third_assignment_dict = {match_id: team.Team for match_id, team in third_assignment.items()}
    
    knockout_roster_df['Match ID'] = knockout_roster_df['Match ID'].astype(int)
    # fill knockout roster df with actual team names based on group standings and third place assignment
    for idx, row in knockout_roster_df.iterrows():
        match_id = row['Match ID']
        home_slot = row['Team 1 (Formula)']
        away_slot = row['Team 2 (Formula)']
        # resolve home team
        if home_slot.startswith("Winner Group "):
            group = home_slot.split()[-1]
            knockout_roster_df.at[idx, 'Team 1'] = standings_lst[[g[0] for g in standings_lst].index(f'Group {group}')][1].iloc[0]['Team']
        elif home_slot.startswith("Runner-up Group "):
            group = home_slot.split()[-1]
            knockout_roster_df.at[idx, 'Team 1'] = standings_lst[[g[0] for g in standings_lst].index(f'Group {group}')][1].iloc[1]['Team']
       
        if away_slot.startswith("Winner Group "):
            group = away_slot.split()[-1]
            knockout_roster_df.at[idx, 'Team 2'] = standings_lst[[g[0] for g in standings_lst].index(f'Group {group}')][1].iloc[0]['Team']
        elif away_slot.startswith("Runner-up Group "):
            group = away_slot.split()[-1]
            knockout_roster_df.at[idx, 'Team 2'] = standings_lst[[g[0] for g in standings_lst].index(f'Group {group}')][1].iloc[1]['Team']
        elif away_slot.startswith("3rd Group "): 
               
            # get based on third assignment dict the third place team assigned to that slot
            if match_id in third_assignment_dict:
                knockout_roster_df.loc[knockout_roster_df['Match ID'] == match_id, 'Team 2'] = third_assignment_dict[match_id]
    
    # get round rosters
    r32 = knockout_roster_df[knockout_roster_df['Round'] == 'Round of 32']
    r16 = knockout_roster_df[knockout_roster_df['Round'] == 'Round of 16']
    qf = knockout_roster_df[knockout_roster_df['Round'] == 'Quarterfinals']
    sf = knockout_roster_df[knockout_roster_df['Round'] == 'Semifinals']
    final = knockout_roster_df[knockout_roster_df['Round'] == 'Final']
    
    # simulate each round
    r32, match_winners_r32 = run_round(r32, team_strength_dict = teams_strength_dict, config=config)
    r16, match_winners_r16 = run_round(r16, match_winners_r32, team_strength_dict=teams_strength_dict, config=config)
    qf, match_winners_qf = run_round(qf, match_winners_r16, team_strength_dict=teams_strength_dict, config=config)
    sf, match_winners_sf = run_round(sf, match_winners_qf, team_strength_dict=teams_strength_dict, config=config)
    final, match_winners_final = run_round(final, match_winners_sf, team_strength_dict=teams_strength_dict, config=config)
    
    # merge al KO-match outputs to 1 df with all matches and their predicted winners and scores.
    knockout_predictions_df = pd.concat([r32, r16, qf, sf, final], ignore_index=True)

    # return dict with advancing teams for each ko round.
    advancing_teams = {
        "R32": list(knockout_roster_df[knockout_roster_df['Round'] == 'Round of 32']['Team 1']) + list(knockout_roster_df[knockout_roster_df['Round'] == 'Round of 32']['Team 2']),
        "R16": list(match_winners_r32.values()),
        "QF": list(match_winners_r16.values()),
        "SF": list(match_winners_qf.values()),
        "Final": list(match_winners_sf.values()),
        "Winner": list(match_winners_final.values())
    }

    return advancing_teams, knockout_predictions_df, best_8_info
