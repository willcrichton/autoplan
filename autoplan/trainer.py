from torch import nn
import torch
import torch.optim as optim
from .models import NeuralParser
from .parsing import Parser


# TODO: this class is out of date since datasets changed
class ClassifierTrainer:
    def __init__(self, dataset, model, device=None, batch_size=100):
        self.device = device if device is not None else torch.device('cpu')

        # Create model from provided class
        self.model = model(dataset, self.device)

        # If our classes are imbalanced, then the weights on the loss encourage the network
        # to not just predict the class balance after training.
        self.criterion = nn.CrossEntropyLoss(weight=1/dataset.class_balance)

        # Optimizer modulates how fast the network learns during training
        self.optimizer = optim.Adam(self.model.parameters())

        # Convert datasets into data loaders to fetch batches of sequences
        self.train_loader = DataLoader(dataset.train_dataset,
                                       batch_size=batch_size,
                                       shuffle=True,
                                       collate_fn=self._collate)
        self.val_loader = DataLoader(dataset.val_dataset,
                                     batch_size=batch_size,
                                     collate_fn=self._collate)

    def train_one_epoch(self):
        total_loss = 0
        for batch in self.train_loader:
            # Reset all gradients
            self.optimizer.zero_grad()

            # Get the predicted labels for the current batch
            pred_score = self.model(input_sequence=batch['input_sequence'].to(device=self.device),
                                    seq_lengths=batch['seq_lengths'])

            # Compute the difference between the predict labels and the true labels
            loss = self.criterion(pred_score.cpu(), batch['labels'])

            # Apply backpropagation to update parameters based on the difference
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item()

        return total_loss

    def predict(self, input_sequence, seq_lengths):
        pred_label = self.model(input_sequence=input_sequence.to(device=self.device),
                                seq_lengths=seq_lengths)
        return pred_label.topk(1, dim=1)[1].squeeze().cpu()

    def eval(self):
        correct = 0
        total = 0
        for batch in self.val_loader:
            pred_label = self.predict(batch['input_sequence'], batch['seq_lengths'])
            correct += (pred_label == batch['labels']).sum().item()
            total += pred_label.numel()
        return correct / total


class ParserTrainer:
    def __init__(self, grammar, dataset, device=None, batch_size=100):
        self.model = NeuralParser(dataset, device)
        self.train_loader = dataset.loader(dataset.train_dataset)
        self.val_loader = dataset.loader(dataset.val_dataset)
        self.optimizer = optim.Adam(self.model.parameters())
        self.loss_fn = nn.CrossEntropyLoss()

    def train_one_epoch(self):
        total_loss = 0
        for batch in self.train_loader:
            self.optimizer.zero_grad()

            preds = self.model.forward(**batch)

            loss = 0
            for i in range(len(preds)):
                for t in range(len(preds[i]) - 1):
                    loss += self.loss_fn(
                        preds[i][t].unsqueeze(0).cpu(),
                        batch['choices'][i][t+1].unsqueeze(0).cpu())

            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        return total_loss

    def eval(self):
        correct = 0
        total = 0
        for batch in self.val_loader:
            pred_choices = self.model.predict(**batch)
            for (pred, true) in zip(pred_choices, batch['choices']):
                correct += (pred == true[1:]).sum().item()
                total += pred.size(0)

        return correct / total
