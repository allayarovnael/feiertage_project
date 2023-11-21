from datetime import date, datetime
import numpy as np
import pandas as pd
import argparse

class FeiertagHandler:
    """
    A data service class for handling and analyzing German holidays. The class
    provides functionalities to generate a comprehensive database of holidays
    based on specified time ranges and geographical aggregations. It allows for
    custom configurations such as counting Sundays as holidays and including
    special non-public holidays.

    Attributes:
        start_date (datetime): The start date of the period for holiday analysis.
        end_date (datetime): The end date of the period for holiday analysis.
        time_agg (str): The time aggregation level, e.g., 'week' or 'day'.
        geo_agg (str): The geographical aggregation level, e.g., 'state' or 'de' (Germany).
        count_sundays (bool): Flag to include Sundays as holidays.
        special_holidays (bool): Flag to include special non-public holidays.

    Methods:
        easter_date(year): Calculates the Easter date for a given year using the
                           Gaussian Easter formula.
        create_timeline(): Creates a timeline dataframe with a daily date range and
                           additional time variables.
        create_db(): Constructs a database at the state level for the given time range.
        aggregated_report(): Aggregates the database based on the specified time and geo
                             granularity and generates a report.
    """
    def __init__(self, start_date, end_date, time_agg="week", geo_agg="state",
                 count_sundays=False, special_holidays=True):
        self.start_date = start_date
        self.end_date = end_date
        self.time_agg = time_agg
        self.geo_agg = geo_agg
        self.count_sundays = count_sundays
        self.special_holidays = special_holidays
        self.states_info = {
            # A dict containing population information about German states (in percent)
            'BW': 0.13352220384597055,
            'BY': 0.15802030065986025,
            'BE': 0.04406333514565102,
            'BB': 0.030437977949884957,
            'HB': 0.008179060146102285,
            'HH': 0.022277401351699335,
            'HE': 0.0756797745646923,
            'MV': 0.01937073416520042,
            'NI': 0.09624698474347271,
            'NW': 0.215568075490225,
            'RP': 0.04928614601803227,
            'SL': 0.011833210668877029,
            'SN': 0.026224318285684965,
            'ST': 0.04878767948508131,
            'SH': 0.03500539853084776,
            'TH': 0.02549739894871785,
        }
        # reporting:
        self.db, self.states_df = self.create_db()
        self.report_db = self.aggregated_report()

    def easter_date(self, year):
        """
        following function calculates the eastern date for a given year:
        https://de.wikipedia.org/wiki/Gau%C3%9Fsche_Osterformel
        """
        A = year % 19
        K = year // 100
        M = 15 + (3 * K + 3) // 4 - (8 * K + 13) // 25
        D = (19 * A + M) % 30
        S = 2 - (3 * K + 3) // 4
        R = D // 29 + (D // 28 - D // 29) * (A // 11)
        OG = 21 + D + R
        SZ = 7 - (year + year // 4 + S) % 7
        OE = 7 - (OG - SZ) % 7
        OS = (OG + OE)
        if OS > 31:
            eastern_date = np.datetime64(date(year, 4, OS - 31))
        else:
            eastern_date = np.datetime64(date(year, 3, OS))
        return eastern_date

    def create_timeline(self):
        """
        following function creates daily date range with some additional time variables
        """
        date_range = pd.date_range(start=self.start_date, end=self.end_date)
        timeline = pd.DataFrame({
            'date': date_range,
            'week': date_range.strftime("%V"),  # ISO 8601 week as a decimal number
            'month': date_range.strftime("%m"),
            'year': date_range.strftime("%Y"),
            'day': date_range.strftime("%d"),
            'weekday': date_range.weekday,          # The day of the week with Monday=0, Sunday=6.
            'monday_date': date_range - pd.to_timedelta(date_range.weekday, unit='D'),
            'month_date': pd.to_datetime(date_range.strftime('%Y-%m-01'))
        })
        return timeline

    def create_db(self):
        """
        for a given time range create a data frame on level of each state
        """
        db = self.create_timeline()

        # holidays which are dependent on eastern date:
        eastern_dates = [
            self.easter_date(i) for i in range(int(self.start_date.strftime("%Y")), int(self.end_date.strftime("%Y")) + 1)
        ]

        easter_related_holidays = {
            'Ostersonntag': 0, 'Karfreitag': -2,
            'Ostermontag': 1, 'Christi Himmelfahrt': 39,
            'Pfingstmontag': 50, 'Pfingstsonntag': 49,
            'Fronleichnam': 60, 'Rosenmontag': -48,
            'Fastnachtsdienstag': -47
        }

        for holiday, offset in easter_related_holidays.items():
            db[holiday] = db['date'].isin([d + np.timedelta64(offset, 'D') for d in eastern_dates]).astype(int)

        # Define fixed-date holidays
        fixed_date_holidays = {
            'Neujahrstag': ('01', '01'),
            'Maifeiertag': ('05', '01'),
            'Tag der deutschen Einheit': ('10', '03'),
            'Erster Weihnachtstag': ('12', '25'),
            'Zweiter Weihnachtstag': ('12', '26'),
            'Heilige drei Koenige': ('01', '06'),
            'Frauentag': ('03', '08'),
            'Maria Himmelfahrt': ('08', '15'),
            'Weltkindertag': ('09', '20'),
            'Reformationstag': ('10', '31'),
            'Allerheiligen': ('11', '01'),
            'Buss- und Bettag': ('11', '16-22')  # Wednesday between 16th and 22nd November
        }

        # public holidays for whole Germany (each country state):
        for holiday, (month, day) in fixed_date_holidays.items():
            db[holiday] = ((db['month'] == month) &
                           (db['day'] == day if '-' not in day else db['day'].between(*day.split('-')))).astype(int)

        if self.special_holidays:
            # specific dates (not public holidays):
            db['Silvester'] = np.where((db['month'] == '12') & (db['day'] == '31'), 1, 0)
            db['Muttertag'] = np.where((db['month'] == '05') & (db['weekday'] == 6) &
                                       (db['day'] >= '08') & (db['day'] <= '14'), 1, 0)
            db['Valentinstag'] = np.where((db['month'] == '02') & (db['day'] == '14'), 1, 0)
            db['Nikolaustag'] = np.where((db['month'] == '12') & (db['day'] == '06'), 1, 0)


        # states_df is a data frame with information about states:
        states_df = pd.DataFrame.from_dict(self.states_info, orient='index')
        states_df.reset_index(inplace=True)
        states_df.columns = ['state_code', 'population_pct']

        # create key column for the purpose of crossjoin:
        db['key'] = 0
        states_df['key'] = 0
        db = pd.merge(states_df, db, how='outer').drop(['key'], axis=1)

        # Public Holidays in each state of Germany:
        public_german_holidays = [
            'Neujahrstag',
            'Karfreitag',
            'Ostermontag',
            'Maifeiertag',
            'Christi Himmelfahrt',
            'Pfingstmontag',
            'Tag der deutschen Einheit',
            'Erster Weihnachtstag',
            'Zweiter Weihnachtstag'
        ]
        db['FT'] = 0
        for feiertag in public_german_holidays:
            db['FT'] += db[feiertag]  # add each german official holiday

        # Special Holidays: individual for each state:
        states_holidays = {
            'BW': ['Heilige drei Koenige','Fronleichnam','Allerheiligen'],
            'BY': ['Heilige drei Koenige','Fronleichnam','Maria Himmelfahrt','Allerheiligen','Buss- und Bettag'],
            'BE': ['Frauentag'],
            'BB': ['Ostersonntag','Pfingstsonntag','Reformationstag'],
            'HB': ['Reformationstag'],
            'HH': ['Reformationstag'],
            'HE': ['Ostersonntag','Pfingstsonntag','Fronleichnam'],
            'MV': ['Reformationstag'],
            'NI': ['Reformationstag'],
            'NW': ['Fronleichnam','Allerheiligen'],
            'RP': ['Fronleichnam','Allerheiligen'],
            'SL': ['Fronleichnam','Allerheiligen','Maria Himmelfahrt'],
            'SN': ['Fronleichnam','Buss- und Bettag','Reformationstag'],
            'ST': ['Heilige drei Koenige','Reformationstag'],
            'SH': ['Reformationstag'],
            'TH': ['Fronleichnam','Weltkindertag','Reformationstag']
        }
        for state_code in states_holidays:
            for special_holiday in states_holidays[state_code]:
                db['FT'] = np.where(db['state_code'] == state_code, db['FT'] + db[special_holiday], db['FT'])

        # Reformationstag adjustment: first since 2018 in Bremen, Hamburg, Niedersachsen und Schleswig-Holstein
        # Before that it should be zero:
        db['FT'] = np.where(
            (db['year'] < '2018') & (db['Reformationstag'] == 1) & (
                db['state_code'].isin(['HB', 'HH', 'NI', 'SH'])), 0,
            db['FT'])

        # from wikipedia:
        # Der 31. Oktober 2017 wurde im Gedenken an das 500. Jubiläum des Beginns
        # der Reformation einmalig als gesamtdeutscher Feiertag begangen.
        # Entsprechende Gesetze bzw. Verordnungen wurden von allen Bundesländern erlassen,
        # in denen der Reformationstag nicht ohnehin Feiertag ist.
        db['FT'] = np.where(db['date'] == date(2017, 10, 31), 1, db['FT'])

        # Open sales days (VOT = verkaufsoffene Tage):
        db['VOT'] = np.where(db['weekday'] != 6, 1 - db['FT'], 0)  # exclude sundays

        return db, states_df

    def aggregated_report(self):
        """
        time_agg could be "day" or "week"
        geo_agg could be "state" or "de"
        """
        db = self.db
        states_df = self.states_df

        if not self.count_sundays:
            # zeroing of holidays which fall on sunday:
            db['FT'] = np.where(db['weekday'] == 6, 0, db['FT'])

        if self.time_agg == "day":
            var = "date"
        elif self.time_agg == "week":
            var = "monday_date"
        else:
            raise ValueError("wrong aggregation")

        db['date'] = db[var]
        db = db.drop(columns=['day','month','week','year','weekday','monday_date','month_date'], axis=1)

        # aggregation on time-level:
        db = db.groupby(['state_code','date'], as_index=False).sum().drop(columns=['population_pct'])
        db = pd.merge(db, states_df, on=['state_code'], how='left')

        # aggregation on DE-level:
        if self.geo_agg == "de":
            columns_to_multiply = [
                col for col in list(db.columns) if col not in ['state_code','date','population_pct']]
            db[columns_to_multiply] = db[columns_to_multiply].multiply(
                db["population_pct"], axis="index")
            db = db.drop(columns=['state_code', 'population_pct'], axis=1)
            db = db.groupby(['date'], as_index=False).sum()

        # convert columns to integer / float:
        columns_to_integer = [c for c in list(db.columns) if
                              c not in ('date','FT','VOT','state_code')]
        db[columns_to_integer] = db[columns_to_integer].astype('int32')
        db[['FT','VOT']] = db[['FT','VOT']].astype('float32')
        if 'key' in db.columns:
            db = db.drop(columns=['key'],axis=1)
        if 'population_pct' in db.columns:
            db = db.drop(columns=['population_pct'],axis=1)
        return db


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process start and end dates.")

    # Adding arguments for start date and end date
    parser.add_argument("start_date", type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                        help="Start date in YYYY-MM-DD format")
    parser.add_argument("end_date", type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                        help="End date in YYYY-MM-DD format")
    parser.add_argument('--time_agg', type=str, default='week', help='Time granularity: day or week')
    parser.add_argument('--geo_agg', type=str, default='de', help='Geo granularity: state or de')
    parser.add_argument('--count_sundays', type=bool, default='False', help='Count sundays as holidays?')
    parser.add_argument('--special_holidays', type=bool, default='True', help='Include special holidays?')
    # Parse the arguments
    args = parser.parse_args()

    holidays = FeiertagHandler(
        start_date=args.start_date.date(),
        end_date=args.end_date.date(),
        time_agg=args.time_agg,
        geo_agg=args.geo_agg,
        count_sundays=args.count_sundays,
        special_holidays=args.special_holidays
    )

    holidays.report_db.to_csv(
        f'Export_holidays_{args.start_date.year}_{args.start_date.month}_{args.end_date.year}_{args.end_date.month}.csv'
        , index=False
    )