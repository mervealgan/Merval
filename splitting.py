import pandas as pd
from sklearn.model_selection import train_test_split

# Load the sentences data
df = pd.read_csv('data/500_sentences_mos.csv')

# Split the data into 80% training and 20% test-valid sets
train_df, temp_df = train_test_split(df, test_size=0.2, random_state=42)

# Further split the test-valid set into 50% validation and 50% test sets
valid_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)

# Save the training, validation, and test sets to CSV files
train_df.to_csv('data/training_set.csv', index=False)
valid_df.to_csv('data/valid_set.csv', index=False)
test_df.to_csv('data/test_set.csv', index=False)