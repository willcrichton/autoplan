from torch import nn
import torch.nn.utils.rnn as rnn_utils
import torch


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
