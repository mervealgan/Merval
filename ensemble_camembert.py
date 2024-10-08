import hashlib
import os
import sys
from os.path import realpath, join, dirname

import numpy as np
import pandas as pd
import tensorflow as tf
import torch
from keras.layers import Dense, Input
from keras.models import Sequential
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from tensorflow.python.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.python.keras.models import load_model
from transformers import (
    AutoTokenizer,
    TrainingArguments,
    AutoModelForSequenceClassification,
    set_seed,
)
# TODO mek we should remove this (find a way i dont care)
sys.path.insert(0, realpath(join(dirname(__file__), '..')))

from util.helpers import (
    compute_metrics,
    load_dataset_with_features_fr, get_hugging_face_name, TCCDataset, RegressionTrainer,
    compute_metrics_for_regression, OptimizedESCallback
)

os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

gpus = tf.config.experimental.list_physical_devices('GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)

print(gpus)

BOOTSTRAP_SIZE = 1000  # 1000
MAX_ENSEMBLE_SIZE = 60  # 60
ENSEMBLE_POOL_SIZE = 100  # 100
N_FOLDS = 5
MODEL_NAME = 'camembert'  # ['gbert', 'gelectra', 'gottbert', 'gerpt']
TRAIN_BATCH_SIZE = 16
VALID_BATCH_SIZE = 16
N_EVAL_STEPS = 23

EXPERIMENT_NAME = f'ensemble_{MODEL_NAME}'
EXPERIMENT_DIR = f'cache/{EXPERIMENT_NAME}'

df_train, feature_columns = load_dataset_with_features_fr('training', data_root_path='data')


def get_predictions(
        df_train_folds,
        df_val_fold,
        n_epochs=100,
        n_log_steps=10,
):
    # store predictions in dataframe
    # columns: Sentence, Prediction of Model 1, Prediction of Model 2, ...
    df_predictions_val_fold = df_val_fold[['ID', 'sentence']].copy()

    # get tokenizer
    tokenizer = AutoTokenizer.from_pretrained(get_hugging_face_name(MODEL_NAME))

    X_val_fold = df_val_fold['sentence'].values
    X_val_fold_features = df_val_fold[feature_columns].values

    # tokenize
    tokens_val_fold = tokenizer(X_val_fold.tolist(), padding='max_length', return_tensors='pt', truncation=True,
                                max_length=128)

    for k in range(ENSEMBLE_POOL_SIZE):
        df_early_stopping = df_train_folds.sample(frac=0.1, random_state=k)
        df_train_no_es = df_train_folds.drop(
            df_train_folds[
                df_train_folds['ID'].isin(df_early_stopping['ID'])
            ].index
        )

        ## Or use this simplified code to drop rows whose 'ID' is in df_early_stopping['ID']
        # df_train_no_es = df_train_folds[~df_train_folds['ID'].isin(df_early_stopping['ID'])]

        X_early_stopping = df_early_stopping['sentence'].values
        X_early_stopping_features = df_early_stopping[feature_columns].values
        y_early_stopping = df_early_stopping['MOS'].values

        X_training = df_train_no_es['sentence'].values
        X_training_features = df_train_no_es[feature_columns].values
        y_training = df_train_no_es['MOS'].values

        # tokenize
        tokens_early_stopping = tokenizer(X_early_stopping.tolist(), padding='max_length', return_tensors='pt',
                                          truncation=True, max_length=128)

        tokens_training = tokenizer(X_training.tolist(), padding='max_length', return_tensors='pt', truncation=True,
                                    max_length=128)

        hash = (
                hashlib.sha256(
                    pd.util.hash_pandas_object(df_train_no_es['ID'], index=True).values
                ).hexdigest()
                + '_'
                + get_hugging_face_name(MODEL_NAME)[
                  get_hugging_face_name(MODEL_NAME).find('/') + 1:
                  ]
        )

        # load model and, if necessary, train it
        try:
            print(f'{EXPERIMENT_DIR}/models/{MODEL_NAME}/{hash}')
            model = AutoModelForSequenceClassification.from_pretrained(
                f'{EXPERIMENT_DIR}/models/{MODEL_NAME}/{hash}', local_files_only=True, num_labels=1
            )
        except EnvironmentError:
            # create training dataset
            early_stopping_dataset = TCCDataset(tokens_early_stopping, y_early_stopping)
            training_dataset = TCCDataset(tokens_training, y_training)

            training_args = TrainingArguments(
                output_dir=f'{EXPERIMENT_DIR}/{MODEL_NAME}_trainer/',
                num_train_epochs=n_epochs,
                per_device_train_batch_size=TRAIN_BATCH_SIZE,
                per_device_eval_batch_size=VALID_BATCH_SIZE,
                warmup_ratio=0.3,
                learning_rate=5e-5,
                no_cuda=False,
                metric_for_best_model='root_mean_squared_error',
                greater_is_better=False,
                load_best_model_at_end=True,
                save_steps=N_EVAL_STEPS * 100_000,
                # we never want to save a model through this function, but the parameter must be set, because of load_best_model_at_end=True
                save_total_limit=1,  # can be 1, because we only save, when we find a better model
                eval_steps=N_EVAL_STEPS,
                # `evaluation_strategy` is deprecated, Use `eval_strategy` instead
                evaluation_strategy='steps',
                seed=k,
                logging_steps=n_log_steps,
                logging_dir=f'{EXPERIMENT_DIR}/logs/member_{k}',
                logging_strategy='steps',
            )

            set_seed(training_args.seed)
            model = AutoModelForSequenceClassification.from_pretrained(
                get_hugging_face_name(MODEL_NAME), num_labels=1
            )

            trainer = RegressionTrainer(
                model=model,
                args=training_args,
                train_dataset=training_dataset,
                eval_dataset=early_stopping_dataset,
                compute_metrics=compute_metrics_for_regression,
                callbacks=[OptimizedESCallback(patience=5, initial_steps_wo_save=300)],
            )
            # training
            trainer.train()

            # save model
            model.save_pretrained(f'{EXPERIMENT_DIR}/models/{MODEL_NAME}/{hash}')

        # load hidden states of model for validation and test data
        hidden_state_val_fold = extract_hidden_state(model, tokens_val_fold)

        # normalize data with StandardScaler
        scaler = StandardScaler()
        scaler.fit(df_train_folds[feature_columns].values)
        X_val_fold_features_scaled = scaler.transform(X_val_fold_features)
        X_val_fold_with_features = np.concatenate((hidden_state_val_fold.detach().numpy(), X_val_fold_features_scaled),
                                                  axis=1)

        # load MLP model and, if necessary, train it
        try:
            mlp = load_model(f'{EXPERIMENT_DIR}/models/mlp/{hash}_mlp.h5')
        except Exception:
            hidden_state_train = extract_hidden_state(model, tokens_training)
            hidden_state_early_stopping = extract_hidden_state(model, tokens_early_stopping)

            np.random.seed(k)
            mlp = Sequential(
                [
                    Input(shape=(model.config.hidden_size + len(feature_columns),), name='input'),
                    Dense(model.config.hidden_size, activation='relu', name='layer1'),
                    Dense(1, activation='linear', name='layer2'),
                ]
            )
            mlp.compile(
                optimizer='rmsprop',
                loss=tf.keras.losses.MeanSquaredError(),
                metrics=[tf.keras.metrics.RootMeanSquaredError()],
            )
            es = EarlyStopping(monitor='val_root_mean_squared_error', mode='min', verbose=1, patience=100)
            mc = ModelCheckpoint(f'{EXPERIMENT_DIR}/models/mlp/{hash}_mlp.h5',
                                 monitor='val_root_mean_squared_error',
                                 mode='min', verbose=1, save_best_only=True)

            # normalize data with StandardScaler
            scaler = StandardScaler()
            scaler.fit(X_training_features)
            X_train_features_scaled = scaler.transform(X_training_features)
            X_es_features_scaled = scaler.transform(X_early_stopping_features)

            X_train_with_features = np.concatenate((hidden_state_train.detach().numpy(), X_train_features_scaled),
                                                   axis=1)
            X_es_with_features = np.concatenate((hidden_state_early_stopping.detach().numpy(), X_es_features_scaled),
                                                axis=1)

            mlp.fit(X_train_with_features, y_training,
                    validation_data=(X_es_with_features, y_early_stopping),
                    batch_size=TRAIN_BATCH_SIZE,
                    epochs=5000, callbacks=[es, mc])
            mlp = load_model(f'{EXPERIMENT_DIR}/models/mlp/{hash}_mlp.h5')

        # predict MLP on validation and test sets
        prediction_val_fold = mlp.predict(X_val_fold_with_features, batch_size=VALID_BATCH_SIZE)

        df_predictions_val_fold[f'{MODEL_NAME}_prediction_{k}'] = prediction_val_fold

    return df_predictions_val_fold


def extract_hidden_state(model, tokens, batch_size=16):
    last_last_hidden_state = torch.zeros((len(tokens.input_ids), model.config.hidden_size))
    model = model.cuda().eval()
    with torch.no_grad():
        for i in range(0, len(tokens.input_ids), batch_size):
            if i + batch_size > len(tokens.input_ids):
                input_i = tokens.input_ids[i:]
            else:
                input_i = tokens.input_ids[i:i + batch_size]
            output = model(input_i.cuda(), output_hidden_states=True)
            last_hidden_state = output.hidden_states[-1].cpu()
            idx_last_token = torch.zeros(len(input_i)).long()
            last_last_hidden_state[i:i + len(idx_last_token)] = last_hidden_state[
                torch.arange(len(idx_last_token)), idx_last_token]
    return last_last_hidden_state


# dataframe for each metric for each model for each ensemble size
# 3d array: [ensemble_size, model_index, metric_index]
df_macro_ensemble_scores = pd.DataFrame(
    columns=[
        'ensemble_size',
        'model_name',
        'mean_absolute_error_mean',
        'mean_absolute_error_std',
        'mean_squared_error_mean',
        'mean_squared_error_std',
        'root_mean_squared_error_mean',
        'root_mean_squared_error_std',
    ]
)

for fold, (train_idx, val_idx) in enumerate(KFold(n_splits=N_FOLDS).split(df_train)):
    df_train_folds = df_train.loc[train_idx]
    df_val_fold = df_train.loc[val_idx]
    # fill na with mean of columns of train data
    df_train_folds = df_train_folds.fillna(df_train_folds.mean(numeric_only=True))
    df_val_fold = df_val_fold.fillna(df_train_folds.mean(numeric_only=True))

    y_val_fold = df_val_fold['MOS'].values

    pool_predictions_val_fold = get_predictions(df_train_folds, df_val_fold)

    for current_ensemble_size in range(1, MAX_ENSEMBLE_SIZE + 1):
        np.random.seed(current_ensemble_size)
        idx = np.random.choice(
            ENSEMBLE_POOL_SIZE,
            size=(BOOTSTRAP_SIZE, current_ensemble_size),
        )

        idx_mapped = np.array(
            [
                np.array(
                    [pool_predictions_val_fold[f'{MODEL_NAME}_prediction_{k}'] for k in j]
                )
                for j in idx
            ]
        )

        ensemble_predictions = np.array(
            [np.sum(j, axis=0) / len(j) for j in idx_mapped]
        )

        ensemble_scores = [
            compute_metrics(y_val_fold, pred) for pred in ensemble_predictions
        ]

        df_ensemble_scores = pd.DataFrame(ensemble_scores).sort_index(axis=1)

        # add to dataframe
        df_macro_ensemble_scores = df_macro_ensemble_scores.append(
            {
                'ensemble_size': current_ensemble_size,
                'model_name': MODEL_NAME,
                'mean_absolute_error_mean': df_ensemble_scores[
                    'mean_absolute_error'
                ].mean(),
                'mean_absolute_error_std': df_ensemble_scores[
                    'mean_absolute_error'
                ].std(),
                'mean_squared_error_mean': df_ensemble_scores[
                    'mean_squared_error'
                ].mean(),
                'mean_squared_error_std': df_ensemble_scores[
                    'mean_squared_error'
                ].std(),
                'root_mean_squared_error_mean': df_ensemble_scores[
                    'root_mean_squared_error'
                ].mean(),
                'root_mean_squared_error_std': df_ensemble_scores[
                    'root_mean_squared_error'
                ].std(),
            },
            ignore_index=True,
        )

# write to csv for each model_name
df_macro_ensemble_scores[
    df_macro_ensemble_scores['model_name'] == MODEL_NAME
    ].to_csv(
    f'ensemble_scores_{MODEL_NAME}.csv', index=False, sep=';', encoding='utf-8'
)
