import pandas as pd

# Load the merged dataset
merged_df = pd.read_csv('data/combined_features_mos.csv')

# Select the columns of interest (MOS and the readability metrics)
columns_of_interest = ['MOS', 'Kincaid', 'ARI', 'Coleman-Liau', 'FleschReadingEase', 'GunningFogIndex', 'LIX',
                       'SMOGIndex', 'RIX', 'REL', 'DaleChallIndex', 'KandelMoles']
selected_df = merged_df[columns_of_interest]

# Compute the correlation matrix
correlation_matrix = selected_df.corr()

# Print the correlation matrix
print(correlation_matrix)

# Optionally, visualize the correlation matrix using a heatmap
import matplotlib.pyplot as plt
import seaborn as sns

plt.figure(figsize=(16, 14))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Matrix between MOS and Readability Metrics')
plt.show()
plt.savefig('data/correlation_matrix.png')
