import pandas as pd

# Load the sentences data
sentences_df = pd.read_csv('data/250_wikiset.csv')
# Load the aggregated ratings data
aggregated_ratings_df = pd.read_csv('data/aggregated_results.csv')

# Merge the aggregated ratings with the sentences data
merged_df = pd.merge(sentences_df, aggregated_ratings_df, left_on='index', right_on='sentence_id', how='left')

# Drop the sentence_id column
merged_df = merged_df.drop(columns=['sentence_id'])

# Save the final DataFrame to a new CSV file
merged_df.to_csv('data/250_wikiset_mos.csv', index=False)