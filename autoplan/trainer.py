from torch import nn
import torch
import torch.optim as optim
from .models import NeuralParser, ProgramClassifier
from collections import defaultdict
from sklearn.metrics import confusion_matrix

# TODO: this class is out of date since datasets changed
class ClassifierTrainer:
    def __init__(self, model, dataset, device=None, batch_size=100):
        self.device = device if device is not None else torch.device('cpu')

        # Create model from provided class
        self.model = ProgramClassifier(dataset, self.device)

        # If our classes are imbalanced, then the weights on the loss encourage the network
        # to not just predict the class balance after training.
        self.loss_fn = nn.CrossEntropyLoss(weight=1/dataset.class_balance)

        # Optimizer modulates how fast the network learns during training
        self.optimizer = optim.Adam(self.model.parameters())

        # Convert datasets into data loaders to fetch batches of sequences
        self.train_loader = dataset.loader(dataset.train_dataset)
        self.val_loader = dataset.loader(dataset.val_dataset)


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
        return pred_label.topk(1, dim=1)[1].squeeze().cpu()

    def eval(self):
        correct = 0
        total = 0
        for batch in self.val_loader:
            pred_label = self.predict(batch['program'], batch['program_len'])
            correct += (pred_label == batch['labels']).sum().item()
            total += pred_label.numel()
        return correct / total


class ParserTrainer:
    def __init__(self, dataset, device=None, batch_size=100, model_params={}):
        self.model = NeuralParser(dataset, device, **model_params)
        self.train_loader = dataset.loader(dataset.train_dataset)
        self.val_loader = dataset.loader(dataset.val_dataset)
        self.optimizer = optim.Adam(self.model.parameters())
        self.loss_fn = nn.CrossEntropyLoss()
        self.dataset = dataset

    def train_one_epoch(self):
        total_loss = 0
        for batch in self.train_loader:
            self.optimizer.zero_grad()

            preds = self.model.forward(
                batch['program'], batch['program_len'], batch['trace'], batch['trace_len'], batch['choices'])

            loss = 0
            for i in range(len(preds)):
                for t in range(len(preds[i])):
                    loss += self.loss_fn(
                        preds[i][t].unsqueeze(0).cpu(),
                        batch['choices'][i][t+1].unsqueeze(0).cpu())

            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        return total_loss

    def eval(self):
        self.model.eval()

        choice_true = defaultdict(list)
        choice_pred = defaultdict(list)
        num_correct = 0
        total = 0
        for batch in self.val_loader:
            pred_choices = self.model.predict(
                batch['program'], batch['program_len'], batch['trace'], batch['trace_len'], batch['choices'])
            for (trace, pred, true) in zip(batch['trace'], pred_choices, batch['choices']):
                for (choice_index, value_pred, value_true) in zip(trace[1:], pred, true[1:]):
                    choice_pred[choice_index.item()].append(value_pred.item())
                    choice_true[choice_index.item()].append(value_true.item())

                correct = pred == true[1:]
                num_correct += correct.sum().item()
                total += pred.size(0)

        index_to_name = {v: k for k, v in self.dataset.choice_indices.items()}
        cms = {
            index_to_name[i]: confusion_matrix(choice_true[i], choice_pred[i])
            for i in choice_true.keys()
        }

        self.model.train()
        return num_correct / total, cms
