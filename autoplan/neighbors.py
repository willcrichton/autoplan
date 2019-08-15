from zss import Node, simple_distance
import numpy as np
import json
from iterextras import par_for
from .trainer import ClassEvaluation
from scipy.stats import mode
from .dataset import RandomSplit
from .token import TokenizerError
from torch.utils.data import Subset
import dataclasses

def json_to_tree(toplevel):
    prog = Node("toplevel")

    def helper(obj):
        if isinstance(obj, list):
            node = Node(obj[0])
            for kid in obj[1:]:
                node.addkid(helper(kid))
            return node
        else:
            return Node(obj)


    for fun in toplevel:
        prog.addkid(helper(fun))

    return prog

def compute_dists(tup):
    (trees, i) = tup
    dists = np.array([simple_distance(trees[i], t) for t in trees])
    return dists


class NNClassifier:
    def __init__(self, dataset, tokenizer):
        self.dataset = dataset
        self.tokenizer = tokenizer

        self.trees = self.compute_trees()
        self.dists = self.compute_distance_matrix(self.trees)
        self.class_names = [str(cls).split('.')[1] for cls in self.dataset.label_set]

    def compute_distance_matrix(self, trees):
        N = len(trees)
        dists = par_for(compute_dists, list(zip([trees for _ in range(N)], range(N))), process=True)
        return np.vstack(dists)

    def compute_trees(self):
        bad = []
        asts = []
        for i, item in enumerate(self.dataset.dataset):
            try:
                asts.append(self.tokenizer.parse(item['source']))
            except TokenizerError:
                bad.append(i)

        N = len(self.dataset.dataset)
        idxs = sorted(list(set(range(N)) - set(bad)))
        self.dataset = dataclasses.replace(self.dataset, dataset=Subset(self.dataset.dataset, idxs))

        trees = [json_to_tree(ast) for ast in asts]
        return trees

    def crossval(self, k=10, val_frac=0.33):
        N = len(self.trees)
        Ntrain = int(N * (1-val_frac))
        evals = []
        for i in range(k):
            idxs = np.random.permutation(N)
            train_idx, val_idx = (idxs[:Ntrain], idxs[Ntrain:])
            true = [self.dataset.dataset[i]['labels'].item() for i in val_idx]
            pred = [
                self.dataset.dataset[train_idx[np.argsort(self.dists[i, train_idx])[0]]]['labels'].item()
                for i in val_idx
            ]
            evals.append(ClassEvaluation.from_preds(true, pred, self.class_names))
        return evals

    def eval(self, k=1):
        N = len(self.trees)
        true = [self.dataset.dataset[i]['labels'].item() for i in range(N)]
        near = [[self.dataset.dataset[j]['labels'].item() for j in np.argsort(self.dists[i,:])[1:]]
                for i in range(N)]
        pred = [mode(n[:k])[0][0] for t, n in zip(true, near)]

        return ClassEvaluation.from_preds(true, pred, self.class_names)
