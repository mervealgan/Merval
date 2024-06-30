import pandas as pd

# Load the CSV file
df = pd.read_csv('data/250_wikiset_mos.csv')

# Create a new DataFrame with 'sentence' and 'pair_id'
df = df.rename(columns={'index': 'pair_id'})
original_sentences = (df[['pair_id', 'sentence', 'avg_rating_original']]
                      .rename(columns={'avg_rating_original': 'MOS'}).copy())


simplified_sentences = (df[['pair_id', 'simplified', 'avg_rating_simplified']]
                        .rename(columns={'avg_rating_simplified': 'MOS', 'simplified': 'sentence'}).copy())


# Concatenate the original and simplified sentences
combined_df = pd.concat([original_sentences, simplified_sentences], ignore_index=True)

# Generate IDs
combined_df['ID'] = [f"{i+1}" for i in range(len(combined_df))]

# Reorder the columns
combined_df = combined_df[['ID', 'pair_id', 'sentence', 'MOS']]

# Save the combined DataFrame to a new CSV file
combined_df.to_csv('data/500_sentences_mos.csv', index=False)
