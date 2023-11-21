# German Holidays Data

## Overview
This repository contains a Python script for creating a dataset of German holidays. The script, utilizing `FeiertagHandler`, generates a comprehensive database of holidays based on specified time ranges and geographical aggregations, with options to include Sundays and special non-public holidays in the analysis.

## Features
- Analyze holidays over a specified date range.
- Aggregate data by week or day, and by state or nationwide in Germany.
- Custom configurations for including Sundays and special holidays.

## Requirements
- Python 3.x
- Libraries: `numpy`, `pandas`, `argparse`
- Knowledge of German holidays and their occurrences.

## Installation
1. Ensure Python 3.x is installed on your system.
2. Install required libraries: `numpy`, `pandas`. These can be installed via pip:
```bash 
pip install numpy pandas
```
3. Clone or download this repository to your local machine.

## Usage
Run the script from the command line by providing the required parameters. For example:
```python 
python holidays.py "2023-01-01" "2023-12-31" --time_agg "week" --geo_agg "state" --count_sundays False --special_holidays True
```


### Parameters:
- `start_date`: The start date for the analysis (YYYY-MM-DD).
- `end_date`: The end date for the analysis (YYYY-MM-DD).
- `time_agg`: Time granularity (day or week).
- `geo_agg`: Geographical granularity (state or de).
- `count_sundays`: Count Sundays as holidays (`True` or `False`).
- `special_holidays`: Include special non-public holidays (`True` or `False`).

## Output
The script outputs a CSV file with detailed holiday data for the specified period and configurations. The file is named using the format `Export_holidays_[start_year]_[start_month]_[end_year]_[end_month].csv`.

## Contribution
Contributions are welcome! Please feel free to submit pull requests or open issues to discuss proposed changes or enhancements.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

---

