import pandas as pd
import numpy as np
import readability
import syntok.segmenter as segmenter


def get_features(text):
    tokenized = '\n\n'.join(
        '\n'.join(' '.join(token.value for token in sentence)
                  for sentence in paragraph)
        for paragraph in segmenter.analyze(text))
    return readability.getmeasures(tokenized, lang='fr', merge=True)


for dataset in ['training', 'valid', 'test']:
    print(f"Processing {dataset} dataset...")
    CSV_URL = f'data/{dataset}_set.csv'

    # Read and preprocess the data
    df = pd.read_csv(CSV_URL)
    df.drop_duplicates(inplace=True)
    df = df.sample(frac=1, random_state=9).reset_index(drop=True)
    df_reduced = pd.DataFrame(df[['ID', 'sentence']])

    # Apply the readability features
    features = df['sentence'].apply(get_features)

    # Extract feature names and values
    feature_names = []
    for idx, row in features.items():
        for k, v in row.items():
            if k not in feature_names:
                feature_names.append(k)
    features_dict = {name: np.full(len(df), np.nan) for name in feature_names}
    for idx, row in features.items():
        for k, v in row.items():
            features_dict[k][idx] = v

        # Create DataFrame from the features
    df_features = pd.DataFrame.from_dict(features_dict)
    df_features = df_reduced.join(df_features)

    # Save the features to a CSV file

    output_path = f'data/features/features_{dataset}_readability_fr.csv'
    df_features.to_csv(output_path, index=False)
    print(f"Saved features to {output_path}")

print("Processing complete for all datasets.")
