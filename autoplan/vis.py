import seaborn as sns
import matplotlib.pyplot as plt
import math
import numpy as np
import pandas as pd

def plot_accuracy(evals, ax=None):
    return pd.Series([e.accuracy for e in evals]).plot(ax=ax)

def plot_cm(ax, name, cm, classes):
    cm = cm / cm.sum(axis=1)[:, np.newaxis]
    sns.heatmap(cm, annot=True, ax=ax)
    ax.set_xlabel('Pred class')
    ax.set_ylabel('True class')
    ax.set_xticklabels(classes, rotation=45)
    ax.set_yticklabels(classes, rotation=45)
    ax.set_title(name)

def plot_all_cm(eval):
    fig, axes = plt.subplots(len(eval), 1)
    fig.set_size_inches(8, len(eval) * 5)

    for ax, k in zip(axes, eval):
        eval[k].plot_cm(ax=ax, title=k)

    plt.tight_layout()


def plot_all_accuracy(evals):
    N = len(evals[0])
    fig, axes = plt.subplots(math.ceil(N/2), 2)
    fig.set_size_inches(8, N/2 * 3)
    axes = [ax for l in axes for ax in l]

    for ax, k in zip(axes, evals[0]):
        plot_accuracy([e[k] for e in evals], ax=ax)
        ax.set_title(k)
        ax.set_ylim(0, 1)

    plt.tight_layout()
