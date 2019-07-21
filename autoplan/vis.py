import seaborn as sns
import matplotlib.pyplot as plt
import math
import numpy as np

def plot_cm(ax, name, cm, classes):
    cm = cm / cm.sum(axis=1)[:, np.newaxis]
    sns.heatmap(cm, annot=True, ax=ax)
    ax.set_xlabel('Pred class')
    ax.set_ylabel('True class')
    ax.set_xticklabels(classes, rotation=45)
    ax.set_yticklabels(classes, rotation=45)
    ax.set_title(name)

def plot_all_cm(dataset, cms):
    fig, axes = plt.subplots(len(cms), 1)
    fig.set_size_inches(8, len(cms) * 5 )

    def truncate(string, N=20):
        if len(string) > N:
            return string[:N-3] + '...'
        else:
            return string

    for ax, k in zip(axes, cms):
        plot_cm(ax, k, cms[k], [truncate(str(name)) for _, name in dataset.choices[k]])

    plt.tight_layout()
