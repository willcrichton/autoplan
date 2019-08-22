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
import nltk

def compute_tree_distance(tup):
    (trees, other_trees, i) = tup
    dists = np.array([simple_distance(other_trees[i], t) for t in trees])
    return dists


def compute_token_distance(tup):
    (tokens, other_tokens, i) = tup
    dists = np.array([nltk.edit_distance(other_tokens[i], t) for t in tokens])
    return dists


class NNClassifier:
    def __init__(self, dataset, tokenizer):
        self.dataset = dataset
        self.tokenizer = tokenizer
        self.class_names = [str(cls).split('.')[1] for cls in self.dataset.label_set]
        self.programs, self.dataset = self.compute_programs(self.dataset)

    def compute_distance_matrix(self, other_programs):
        N = len(other_programs)
        dists = par_for(
            self.metric(), list(zip([self.programs for _ in range(N)], [other_programs for _ in range(N)], range(N))),
            process=True)
        return np.vstack(dists)

    def nearest(self, i, dists):
        return self.dataset.dataset[np.argsort(dists[i, :])[1]]

    def crossval(self, dists, folds=10, k=1, val_frac=0.33):
        N = len(self.programs)
        Ntrain = int(N * (1-val_frac))
        evals = []
        val = []
        closest = []
        for i in range(folds):
            idxs = np.random.permutation(N)
            train_idx, val_idx = (idxs[:Ntrain], idxs[Ntrain:])
            true = [self.dataset.dataset[i]['labels'].item() for i in val_idx]
            close = [
                train_idx[np.argsort(dists[i, train_idx])[:k]]
                for i in val_idx
            ]
            pred = [
                mode([self.dataset.dataset[j]['labels'].item() for j in cl])[0][0]
                for cl in close
            ]
            evals.append(ClassEvaluation.from_preds(true, pred, self.class_names))
            closest.append(close)
            val.append(val_idx)
        return evals, closest, val

    def eval(self, dataset, mtx, k=1):
        N = len(dataset.dataset)
        true = [dataset.dataset[i]['labels'].item() for i in range(N)]
        near = [[self.dataset.dataset[j]['labels'].item() for j in np.argsort(mtx[i,:])[1:]]
                for i in range(N)]
        pred = [mode(n[:k])[0][0] for t, n in zip(true, near)]

        return ClassEvaluation.from_preds(true, pred, self.class_names)


class TreeNNClassifier(NNClassifier):
    metric = lambda _: compute_tree_distance

    def json_to_tree(self, toplevel):
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

    def compute_programs(self, dataset):
        bad = []
        asts = []

        def parse(item):
            try:
                return self.tokenizer.parse(item['source'])
            except TokenizerError:
                return None
        maybe_asts = par_for(parse, dataset.dataset)
        asts = [ast for ast in maybe_asts if ast is not None]
        bad = [i for i, ast in enumerate(maybe_asts) if ast is None]

        N = len(self.dataset.dataset)
        idxs = sorted(list(set(range(N)) - set(bad)))
        dataset = dataclasses.replace(dataset, dataset=Subset(dataset.dataset, idxs))

        trees = [self.json_to_tree(ast) for ast in asts]
        return trees, dataset


class TokenNNClassifier(NNClassifier):
    metric = lambda _: compute_token_distance

    def compute_programs(self, dataset):
        return [item['program'] for item in dataset.dataset], dataset
