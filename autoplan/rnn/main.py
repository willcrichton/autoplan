# Vendors
import pandas as pd
import torch
import os

# Locals
from src.trainer import ClassifierTrainer
from src.dataset import PrelabeledDataset
from src.vis import plot_accuracy, plot_cm

if __name__ == "__main__": 
    # data
    dataset_name = 'T1'
    dataset = PrelabeledDataset.load(f'{REPO_DIR}/data/rainfall/{dataset_name}.pkl')

    # set trainer
    trainer = ClassifierTrainer(dataset, device=device, val_frac=0.3, model_opts={'embedding_size': 32, 'hidden_size': 64})
    losses = []
    train_eval = []
    val_eval = []

    # train and eval
    for _ in range(100):
        losses.append(trainer.train_one_epoch())
        train, val = trainer.eval()
        train_eval.append(train)
        val_eval.append(val)

    # visualize
    pd.Series(losses).plot()
    plot_accuracy(train_eval)
    plot_accuracy(val_eval)
    train_eval[-1].plot_cm()
    val_eval[-1].plot_cm()