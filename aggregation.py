import sqlite3
import pandas as pd

# Connect to your SQLite database
conn = sqlite3.connect('data/poll_results.db')

# Query to get all data from the ratings table
query = "SELECT * FROM ratings"

# Load the data into a DataFrame
df = pd.read_sql_query(query, conn)

# Close the database connection
conn.close()

# Define custom aggregation functions
def custom_mean_exclude_zeros(series):
    non_zero_series = series[series != 0]
    return non_zero_series.mean() if not non_zero_series.empty else 0

def custom_count_exclude_zeros(series):
    return (series != 0).sum()

# Perform aggregations using Pandas with custom functions
aggregated_df = df.groupby('sentence_id').agg(
    avg_rating_original=('rating_original', custom_mean_exclude_zeros),
    avg_rating_simplified=('rating_simplified', custom_mean_exclude_zeros),
).reset_index()

aggregated_df.to_csv('data/aggregated_results.csv', index=False)