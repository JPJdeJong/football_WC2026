import numpy as np
import pandas as pd

def simulate_match(team_h, team_a, att_h, att_a, def_h, def_a, n_simulations=10000, max_goals=10):
    """
    Function to simulate a match between two teams using a Poisson distribution based on their attack and defence strengths. It runs a specified number of simulations and calculates the probabilities of a home win, away win, and draw, as well as the most common scoreline and its percentage occurrence in the simulations.
    Args:
        team_h: home team name
        team_a: away team name
        att_h: home team attack strength
        att_a: away team attack strength
        def_h: home team defence strength
        def_a: away team defence strength
        n_simulations: number of simulations to run for the match
        max_goals: maximum number of goals to consider in the simulations (to cap the Poisson distribution)
    Returns:
        A dictionary containing the probabilities of a home win, away win, and draw, as well as the most common scoreline and its percentage occurrence in the simulations.
    """
    # Calculate lambda (expected goals) for both teams
    lambda_home =  att_h + def_h #- att_a - def_a
    lambda_away =  att_a + def_a #- att_h - def_h
    lambda_home = max(lambda_home, 0.1)  # Ensure lambda is not negative
    lambda_away = max(lambda_away, 0.1)  # Ensure lambda is not negative
    
    # Generate Poisson distributions for the simulations
    home_goals_sim = np.random.poisson(lambda_home, n_simulations)
    away_goals_sim = np.random.poisson(lambda_away, n_simulations)
    # Cap the goals at the specified max_goals (5)
    home_goals_sim = np.clip(home_goals_sim, 0, max_goals)
    away_goals_sim = np.clip(away_goals_sim, 0, max_goals)
    
    # Initialize counters for outcomes
    home_wins = 0
    away_wins = 0
    draws = 0
    
    # Track exact scorelines for frequencies
    score_counts = {}
    
    for h, a in zip(home_goals_sim, away_goals_sim):
        # Count outcomes
        if h > a:
            home_wins += 1
        elif a > h:
            away_wins += 1
        else:
            draws += 1
            
        # Count exact scorelines
        score = f"{h}-{a}"
        score_counts[score] = score_counts.get(score, 0) + 1

    # Calculate probabilities
    p_home_win = (home_wins / n_simulations) * 100
    p_away_win = (away_wins / n_simulations) * 100
    p_draw = (draws / n_simulations) * 100
    
    # Find the most common scoreline
    most_common_score = max(score_counts, key=score_counts.get)
    most_common_pct = (score_counts[most_common_score] / n_simulations) * 100
    return {
        "home_win_prob": p_home_win,
        "away_win_prob": p_away_win,
        "draw_prob": p_draw,
        "most_common_score": most_common_score,
        "most_common_pct": most_common_pct
    }

