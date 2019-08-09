from torch import nn
import torch
import torch.optim as optim
from .models import NeuralParser, ProgramClassifier
from collections import defaultdict
from sklearn.metrics import confusion_matrix
from dataclasses import dataclass
from typing import List
import numpy as np
from tqdm.auto import tqdm
import itertools
from collections import ChainMap


@dataclass
class ClassEvaluation:
    confusion_matrix: List[List[int]]
    classes: List[str]
    accuracy: float
    true: List[int]
    pred: List[int]

    @classmethod
    def from_preds(cls, true, pred, classes):
        true = np.array(true)
        pred = np.array(pred)
        return cls(
            confusion_matrix=confusion_matrix(true, pred),
            true=true,
            pred=pred,
            accuracy=(true == pred).sum() / len(true),
            classes=classes)

    def incorrect(self):
        wrong = self.true != self.pred
        return wrong.nonzero()[0]

    def plot_cm(self, title, ax=None, normalize=True):
        from .vis import plot_cm
        import matplotlib.pyplot as plt
        return plot_cm(plt.gca() if ax is None else ax,
                       title, self.confusion_matrix, self.classes, normalize)

    def print_incorrect(self, dataset, labels):
        idxs = self.incorrect()
        for idx in idxs:
            print(dataset[idx]['source'])
            print('Pred: {}\nTrue: {}'.format(
                str(labels(self.pred[idx])), str(labels(self.true[idx]))))
            print('='*30 + '\n')


class BaseTrainer:
    def eval(self):
        self.model.eval()
        train_eval = self.eval_on(self.train_loader)
        val_eval = self.eval_on(self.val_loader)
        self.model.train()
        return train_eval, val_eval

    def train(self, epochs, progress=True):
        iterator = tqdm(range(epochs)) if progress else range(epochs)
        losses = []
        train_eval = []
        val_eval = []

        for _ in iterator:
            loss = self.train_one_epoch()
            losses.append(loss)
            train, val = self.eval()
            train_eval.append(train)
            val_eval.append(val)

        return losses, train_eval, val_eval

    @classmethod
    def crossval(cls, dataset, k, epochs, *args, progress=False, **kwargs):
        all_eval = {
            'accuracy': [],
            'train_eval': [],
            'val_eval': [],
            'loss': []
        }

        it = tqdm(range(k)) if progress else range(k)
        for fold in it:
            trainer = cls(dataset, *args, **kwargs)
            loss, train_eval, val_eval = trainer.train(epochs, progress=False)
            all_eval['accuracy'].append(max([eval_.accuracy for eval_ in val_eval]))
            all_eval['train_eval'].append(train_eval)
            all_eval['val_eval'].append(val_eval)
            all_eval['loss'].append(loss)

        return all_eval

class ClassifierTrainer(BaseTrainer):
    def __init__(self, dataset, device=None, batch_size=100, val_frac=0.33, split=None, model_opts={}):
        self.device = device if device is not None else torch.device('cpu')

        # Create model from provided class
        self.model = ProgramClassifier(dataset, self.device, **model_opts)

        # If our classes are imbalanced, then the weights on the loss encourage the network
        # to not just predict the class balance after training.
        self.loss_fn = nn.CrossEntropyLoss(weight=1/dataset.class_balance)

        # Optimizer modulates how fast the network learns during training
        self.optimizer = optim.Adam(self.model.parameters())

        # Convert datasets into data loaders to fetch batches of sequences
        self.dataset = dataset
        (self.train_dataset, self.train_loader), \
            (self.val_dataset, self.val_loader) = split.set_train_val(val_frac)
        self.class_names = [str(cls).split('.')[1] for cls in dataset.label_set]

    def train_one_epoch(self):
        total_loss = 0
        for batch in self.train_loader:
            # Reset all gradients
            self.optimizer.zero_grad()

            # Get the predicted labels for the current batch
            pred_score = self.model.forward(program=batch['program'].to(device=self.device),
                                            program_len=batch['program_len'])

            # Compute the difference between the predict labels and the true labels
            loss = self.loss_fn(pred_score.cpu(), batch['labels'])

            # Apply backpropagation to update parameters based on the difference
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item()

        return total_loss

    def predict(self, program, program_len):
        pred_label = self.model(program=program.to(device=self.device),
                                program_len=program_len)
        return pred_label.topk(1, dim=1)[1].squeeze(-1).cpu()

    def eval_on(self, loader):
        true = []
        pred = []
        for batch in loader:
            true.extend(batch['labels'])
            pred.extend(self.predict(batch['program'], batch['program_len']).tolist())
        return ClassEvaluation.from_preds(true, pred, self.class_names)


class ParserTrainer(BaseTrainer):
    def __init__(self, dataset, device=None, batch_size=100, model_opts={}):
        self.model = NeuralParser(dataset, device, **model_opts)
        self.train_loader, self.val_loader = dataset.split_train_val()
        self.optimizer = optim.Adam(self.model.parameters())
        self.loss_fn = nn.CrossEntropyLoss(reduction='sum')
        self.dataset = dataset
        self.label_names = {
            k: [self._truncate(str(name)) for _, name in dataset.choices[k]]
            for k in dataset.choices
        }

    def _truncate(self, string, N=20):
        if len(string) > N:
            return string[:N-3] + '...'
        else:
            return string

    def train_one_epoch(self):
        total_loss = 0
        for batch in self.train_loader:
            self.optimizer.zero_grad()

            preds = self.model.forward(
                batch['program'], batch['program_len'], batch['trace'], batch['trace_len'], batch['choices'])

            loss = 0
            for i in range(len(preds)):
                for t in range(len(preds[i])):
                    # [t+1] for start token
                    loss += self.loss_fn(
                        preds[i][t].unsqueeze(0).cpu(),
                        batch['choices'][i][t+1].unsqueeze(0).cpu())

            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        return total_loss

    def eval_on(self, loader):
        choice_true = defaultdict(list)
        choice_pred = defaultdict(list)
        for batch in self.val_loader:
            pred_choices = self.model.predict(
                batch['program'], batch['program_len'], batch['trace'], batch['trace_len'], batch['choices'])
            for (trace, pred, true) in zip(batch['trace'], pred_choices, batch['choices']):
                # [1:] for start token
                for (choice_index, value_pred, value_true) in zip(trace[1:], pred, true[1:]):
                    choice_pred[choice_index.item()].append(value_pred.item())
                    choice_true[choice_index.item()].append(value_true.item())

        index_to_name = {v: k for k, v in self.dataset.choice_indices.items()}
        return {
            index_to_name[i]: ClassEvaluation.from_preds(
                choice_true[i], choice_pred[i], self.label_names[index_to_name[i]])
            for i in choice_true.keys()
        }


def option_combinations(options):
    return [
        dict(ChainMap(*opts))
        for opts in itertools.product(*[
                [{k: v} for v in vs]
                for (k, vs) in options
        ])
    ]
