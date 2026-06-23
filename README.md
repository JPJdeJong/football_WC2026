# Football World Cup 2026

A repository for tracking, analyzing, and managing information related to the FIFA World Cup 2026.

## Overview

This project provides a simulation of the FIFA WC 2026 for football enthusiasts. 

## Features

- **Team Information**: Details about participating nations, partly downloaded from Transfermarkt and Elo-ratings. The scraper is not comprehensive (yet)
- **Fixtures & Results**: Match schedules and outcomes
- **Standings**: Tournament table and group standings
- **Statistics**: Player and team performance metrics

## Getting Started

### Prerequisites

- Git
- Python 3.8+ (if applicable)
- [Add other dependencies]

### Installation

```bash
git clone https://github.com/yourusername/football_WC2026.git
cd football_WC2026
```

### Usage

in the config_wc_2026.yaml you can set several parameters to adjust.
e.g. actual_results : False, will give you the opportunity to run a pre-tournament simulation
Adjusting the weights will adjust values for team strength.

In Simulations you can set how often a match should be played, and how many Monte-Carlo simulations you make.
The max_goals parameter sets the maximum amount of goals for the Poisson distributed match simulation.

## Project Structure

```
football_WC2026/
├── README.md
├── data/
├── src/
└── doc/
```

## Contributing

Just hit me a message.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or suggestions, please open an issue on GitHub.
