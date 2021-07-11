from datetime import date, timedelta
import numpy as np
import pandas as pd

states_info = pd.read_excel('./states_de.xlsx')


def get_monday_date(day):
    return day - timedelta(days=day.weekday())


def get_month_date(day):
    return date(day.year, day.month, 1)


def ostern(year):
    """
    following function calculates the ostern date for a given year:
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
        ostern_date = np.datetime64(date(year, 4, OS - 31))
    else:
        ostern_date = np.datetime64(date(year, 3, OS))
    return ostern_date


class FeiertagHandler:
    """
    Data Service for German Holidays.
    """

    def __init__(self, start_date, end_date, time_agg="week", geo_agg="state",
                 bl_weights=None, count_sundays=False, special_holidays=True):
        self.start_date = start_date
        self.end_date = end_date
        self.time_agg = time_agg
        self.geo_agg = geo_agg
        self.bl_weights = bl_weights
        self.count_sundays = count_sundays
        self.special_holidays = special_holidays

        global states_info  # TODO: better define in config-files
        self.states_info = states_info

        if bl_weights:
            self.states_info['population_pct'] = bl_weights

        # reporting:
        self.db = self.create_db()
        self.report_db = self.report()

    def create_timeline(self):
        """
        following function creates daily date range with some additional time variables
        """
        date_range = pd.date_range(start=self.start_date, end=self.end_date)
        timeline = {
            'date': date_range,
            'week': date_range.strftime("%V"),  # ISO 8601 week as a decimal number
            'month': date_range.strftime("%m"),
            'year': date_range.strftime("%Y"),
            'day': date_range.strftime("%d"),
            'weekday': date_range.weekday  # The day of the week with Monday=0, Sunday=6.
        }

        timeline = pd.DataFrame(timeline)
        timeline['monday_date'] = timeline.apply(lambda x: get_monday_date(x['date']), axis=1)
        timeline['month_date'] = timeline.apply(lambda x: get_month_date(x['date']), axis=1)
        return timeline

    def create_db(self):
        """
        for a given time range create a data frame on level of each state
        """

        db = self.create_timeline()

        # holidays which are dependent on easter date:
        ostern_dates = [ostern(i) for i in
                        range(int(self.start_date.strftime("%Y")), int(self.end_date.strftime("%Y")) + 1)]

        # db['Ostersonntag'] = db.apply(lambda x: 1 if x['date'] in ostern_dates else 0, axis=1) # slow version
        db['Ostersonntag'] = [1 if date in ostern_dates else 0 for date in db['date']]
        db['Karfreitag'] = [1 if date in list(ostern_dates - np.timedelta64(2, 'D')) else 0 for date in db['date']]
        db['Ostermontag'] = [1 if date in list(ostern_dates + np.timedelta64(1, 'D')) else 0 for date in db['date']]
        db['Christi Himmelfahrt'] = [1 if date in list(ostern_dates + np.timedelta64(39, 'D')) else 0 for date in
                                     db['date']]
        db['Pfingstmontag'] = [1 if date in list(ostern_dates + np.timedelta64(50, 'D')) else 0 for date in db['date']]
        db['Pfingstsonntag'] = [1 if date in list(ostern_dates + np.timedelta64(49, 'D')) else 0 for date in db['date']]
        db['Fronleichnam'] = [1 if date in list(ostern_dates + np.timedelta64(60, 'D')) else 0 for date in db['date']]
        db['Rosenmontag'] = [1 if date in list(ostern_dates - np.timedelta64(48, 'D')) else 0 for date in db['date']]
        db['Fastnachtsdienstag'] = [1 if date in list(ostern_dates - np.timedelta64(47, 'D')) else 0 for date in
                                    db['date']]

        # public holidays for whole Germany (each country state):
        # slow version:
        # db['Neujahrstag'] = db.apply(lambda x: 1 if ((x['month']=='01') & (x['day']=='01')) else 0, axis=1)
        db['Neujahrstag'] = np.where((db['month'] == '01') & (db['day'] == '01'), 1, 0)
        db['Maifeiertag'] = np.where((db['month'] == '05') & (db['day'] == '01'), 1, 0)
        db['Tag der deutschen Einheit'] = np.where((db['month'] == '10') & (db['day'] == '03'), 1, 0)
        db['Erster Weihnachtstag'] = np.where((db['month'] == '12') & (db['day'] == '25'), 1, 0)
        db['Zweiter Weihnachtstag'] = np.where((db['month'] == '12') & (db['day'] == '26'), 1, 0)

        # specific holidays for country states:
        db['Heilige drei Koenige'] = np.where((db['month'] == '01') & (db['day'] == '06'), 1, 0)
        db['Frauentag'] = np.where((db['month'] == '03') & (db['day'] == '08') & (db['year'] >= '2019'), 1, 0)
        db['Maria Himmelfahrt'] = np.where((db['month'] == '08') & (db['day'] == '15'), 1, 0)

        db['Weltkindertag'] = np.where((db['month'] == '09') & (db['day'] == '20') & (db['year'] >= '2019'), 1, 0)
        db['Reformationstag'] = np.where((db['month'] == '10') & (db['day'] == '31'), 1, 0)
        db['Allerheiligen'] = np.where((db['month'] == '11') & (db['day'] == '01'), 1, 0)
        db['Buss- und Bettag'] = np.where(
            (db['month'] == '11') & (db['day'] < '23') & (db['day'] >= '16') & (db['weekday'] == 2), 1, 0)

        if self.special_holidays:
            # specific dates (not public holidays):
            db['Silvester'] = np.where((db['month'] == '12') & (db['day'] == '31'), 1, 0)
            db['Muttertag'] = np.where((db['month'] == '05') & (db['weekday'] == 6) &
                                       (db['day'] >= '08') & (db['day'] <= '14'), 1, 0)
            db['Valentinstag'] = np.where((db['month'] == '02') & (db['day'] == '14'), 1, 0)
            db['Nikolaustag'] = np.where((db['month'] == '12') & (db['day'] == '06'), 1, 0)

        # states_df is a data frame with information about states:
        states_df = self.states_info[['state', 'state_code']].copy()

        # create key column for purpose of crossjoin:
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
            'BW': ['Heilige drei Koenige', 'Fronleichnam', 'Allerheiligen'],
            'BY': ['Heilige drei Koenige', 'Fronleichnam', 'Maria Himmelfahrt', 'Allerheiligen', 'Buss- und Bettag'],
            'BE': ['Frauentag'],
            'BB': ['Ostersonntag', 'Pfingstsonntag', 'Reformationstag'],
            'HB': ['Reformationstag'],
            'HH': ['Reformationstag'],
            'HE': ['Ostersonntag', 'Pfingstsonntag', 'Fronleichnam'],
            'MV': ['Reformationstag'],
            'NI': ['Reformationstag'],
            'NW': ['Fronleichnam', 'Allerheiligen'],
            'RP': ['Fronleichnam', 'Allerheiligen'],
            'SL': ['Fronleichnam', 'Allerheiligen', 'Maria Himmelfahrt'],
            'SN': ['Fronleichnam', 'Buss- und Bettag', 'Reformationstag'],
            'ST': ['Heilige drei Koenige', 'Reformationstag'],
            'SH': ['Reformationstag'],
            'TH': ['Fronleichnam', 'Weltkindertag', 'Reformationstag']
        }
        for state_code in states_holidays:
            for special_holiday in states_holidays[state_code]:
                db['FT'] = np.where(db['state_code'] == state_code, db['FT'] + db[special_holiday], db['FT'])

        # Reformationstag first since 2018 in Bremen, Hamburg, Niedersachsen und Schleswig-Holstein
        # Before that it should be zero:
        db['FT'] = np.where(
            (db['year'] < '2018') & (db['Reformationstag'] == 1) & (
                db['state_code'].isin(['HB', 'HH', 'NI', 'SH'])), 0,
            db['FT'])

        # frow wikipedia:
        # Der 31. Oktober 2017 wurde im Gedenken an das 500. Jubiläum des Beginns
        # der Reformation einmalig als gesamtdeutscher Feiertag begangen.
        # Entsprechende Gesetze bzw. Verordnungen wurden von allen Bundesländern erlassen,
        # in denen der Reformationstag nicht ohnehin Feiertag ist.
        db['FT'] = np.where(db['date'] == date(2017, 10, 31), 1, db['FT'])

        # Open sales days (VOT = verkaufsoffene Tage):
        db['VOT'] = np.where(db['weekday'] != 6, 1 - db['FT'], 0)  # exclude sundays

        return db

    def report(self):
        """
        time_agg could be "day" or "week"
        geo_agg could be "state" or "de"
        """
        db = self.db

        if not self.count_sundays:
            # zeroing of holidays which fall on sunday:
            db['FT'] = np.where(db['weekday'] == 6, 0, db['FT'])

        if self.time_agg == "day":
            var = "date"
        elif self.time_agg == "week":
            var = "monday_date"
        else:
            print("wrong aggregation")

        db['date'] = db[var]
        db = db.drop(['day', 'month', 'week', 'year', 'weekday', 'monday_date', 'month_date'], 1)

        # aggregation on time-level:
        db = db.groupby(['state', 'state_code', 'date'], as_index=False).sum()

        # aggregation on DE-level:
        if self.geo_agg == "de":
            db = pd.merge(db, self.states_info[['state', 'population_pct']], on="state")
            columns_to_multiply = [
                col for col in list(db.columns) if col not in ['state', 'state_code', 'date', 'population_pct']]

            db[columns_to_multiply] = db[columns_to_multiply].multiply(
                db["population_pct"], axis="index")
            db = db.drop(['state', 'state_code', 'population_pct'], 1)
            db = db.groupby(['date'], as_index=False).sum()

        # convert columns to integer / float:
        columns_to_integer = [c for c in list(db.columns) if
                              c not in ('date', 'FT', 'VOT', 'state', 'state_code')]
        db[columns_to_integer] = db[columns_to_integer].astype('int32')
        db[['FT', 'VOT']] = db[['FT', 'VOT']].astype('float32')

        return db