import torch
from torch import nn
import torch.nn.utils.rnn as rnn_utils
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.data.dataloader import default_collate
import torch.nn.functional as F


class RNN(nn.Module):
    def __init__(self, dataset, device):
        super().__init__()

        self.device = device
        self.vocab_size = dataset.vocab_size
        self.num_labels = len(dataset.label_set)
        self.embedding_size = 300
        self.hidden_size = 256
        self.num_layers = 1

        self.embedding = nn.Embedding(self.vocab_size, self.embedding_size)
        self.rnn = nn.RNN(input_size=self.embedding_size,
                          hidden_size=self.hidden_size,
                          num_layers=self.num_layers,
                          batch_first=True)
        self.fc = nn.Linear(self.hidden_size, self.num_labels)
        self.sigmoid = nn.Sigmoid()
        self.to(device=device)

    def forward(self, input_sequence, seq_lengths):
        batch_size = input_sequence.size(0)

        input_embedding = self.embedding(input_sequence)
        packed_input = rnn_utils.pack_padded_sequence(input_embedding,
                                                      seq_lengths.data.tolist(),
                                                      batch_first=True,
                                                      enforce_sorted=False)

        h0 = torch.empty(self.num_layers, batch_size, self.hidden_size).to(device=self.device)
        nn.init.xavier_normal_(h0)

        _, hidden = self.rnn(packed_input, h0)
        return self.fc(hidden).squeeze(0)


class Trainer:
    def __init__(self, dataset, model, device=None, batch_size=100):
        self.device = device if device is not None else torch.device('cpu')
        self.train_loader = DataLoader(dataset.train_dataset,
                                       batch_size=batch_size,
                                       shuffle=True,
                                       collate_fn=self._collate)
        self.model = model(dataset, self.device)
        self.criterion = nn.CrossEntropyLoss(weight=1/dataset.class_balance)
        self.optimizer = optim.Adam(self.model.parameters())
        self.val_loader = DataLoader(dataset.val_dataset,
                                     batch_size=batch_size,
                                     collate_fn=self._collate)

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
            self.optimizer.zero_grad()
            pred_score = self.model(input_sequence=batch['input_sequence'].to(device=self.device),
                                    seq_lengths=batch['seq_lengths'])
            loss = self.criterion(pred_score.cpu(), batch['labels'])
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
