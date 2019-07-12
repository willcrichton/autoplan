from torch import nn
import torch
import torch.optim as optim


class Trainer:
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

    # Compacts a list of sequences length [n1, n2, .. nk] into a tensor [k x max(n)]
    def _collate(self, batch):
        collated = default_collate([{k: v
                                     for k, v in item.items() if k is not 'input_sequence'}
                                    for item in batch])
        seqs = [item['input_sequence'] for item in batch]
        max_len = max([s.size(0) for s in seqs])
        collated['input_sequence'] = torch.stack(
            [F.pad(seq, [0, max_len - seq.size(0)]) for seq in seqs])
        return collated

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
