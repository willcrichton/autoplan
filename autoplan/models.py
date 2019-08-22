from torch import nn
import torch.nn.utils.rnn as rnn_utils
import torch
import torch.nn.functional as F


class ProgramEncoder(nn.Module):
    def __init__(self, dataset, device, model=nn.RNN, embedding_size=300, hidden_size=256, num_layers=1):
        super().__init__()

        # Setup various constants
        self.device = device
        self.embedding_size = embedding_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # Define graph architecture
        self.embedding = nn.Embedding(dataset.vocab_size, self.embedding_size)
        self.rnn = model(input_size=self.embedding_size,
                         hidden_size=self.hidden_size,
                         num_layers=self.num_layers,
                         batch_first=True)

        # Put graph onto appropriate device
        self.to(device=device)

    def forward(self, input_sequence, seq_lengths):
        batch_size = input_sequence.size(0)

        # Convert token indices into an embedding
        input_embedding = self.embedding(input_sequence)

        # Pack embedding into batched sequences
        packed_input = rnn_utils.pack_padded_sequence(input_embedding,
                                                      seq_lengths.data.tolist(),
                                                      batch_first=True,
                                                      enforce_sorted=False)

        # Initialize the hidden layer with random values
        h0 = torch.empty(self.num_layers, batch_size, self.hidden_size) \
                  .to(device=self.device)
        nn.init.xavier_normal_(h0)

        # Run the RNN on all sequences
        if isinstance(self.rnn, nn.LSTM):
            cell_state = torch.empty(self.num_layers, batch_size, self.hidden_size) \
                              .to(device=self.device)
            nn.init.xavier_normal_(cell_state)
            _, (hidden, _) = self.rnn(packed_input, (h0, cell_state))
        else:
            _, hidden = self.rnn(packed_input, h0)

        return hidden.squeeze(0)


class ProgramClassifier(nn.Module):
    def __init__(self, dataset, device, **kwargs):
        super().__init__()

        self.num_labels = len(dataset.label_set)
        self.encoder = ProgramEncoder(dataset, device, **kwargs)
        self.classifier = nn.Linear(self.encoder.hidden_size, self.num_labels)

        self.to(device=device)

    def forward(self, program, program_len):
        hidden = self.encoder(program, program_len)

        # Run the classifier on the hidden state to predict the final class
        return self.classifier(hidden)


class NeuralParser(nn.Module):
    def __init__(self, dataset, device, model=nn.LSTM, embedding_size=300, hidden_size=256, hidden_dropout=0.2):
        super().__init__()

        self.device = device
        self.embedding_size = embedding_size
        self.hidden_size = hidden_size
        self.choice_indices = dataset.choice_indices
        self.name_order = sorted(dataset.choices.keys(), key=lambda name: self.choice_indices[name])

        # Inputs
        self.encoder = ProgramEncoder(dataset, device, embedding_size=embedding_size, hidden_size=hidden_size,
                                      model=model)
        self.index_embedding = nn.Embedding(len(dataset.choices), self.embedding_size)
        self.choice_embedding = nn.ModuleList([
            nn.Embedding(len(dataset.choices[name]), self.embedding_size)
            for name in self.name_order
        ])

        # RNN
        self.rnn = nn.GRUCell(
            input_size=self.encoder.hidden_size + self.embedding_size * 2,
            hidden_size=self.hidden_size)
        self.dropout_layer = nn.Dropout(p=hidden_dropout)
        self.batchnorm_layer = nn.BatchNorm1d(self.hidden_size)

        # RV prediction
        self.inference = nn.ModuleList([
            nn.Linear(self.hidden_size, len(dataset.choices[name]))
            for name in self.name_order
        ])

        self.to(device=device)

    def init_hidden(self, batch_size):
        h0 = torch.empty(batch_size, self.hidden_size).to(device=self.device)
        nn.init.xavier_normal_(h0)
        return h0

    def step(self, prev_choice, cur_choice, program_emb, h, choices):
        index_emb = self.index_embedding(prev_choice)

        choice_value = choices.gather(dim=1, index=prev_choice.unsqueeze(-1))

        for i in range(len(prev_choice)):
            num_embs = self.choice_embedding[prev_choice[i]].num_embeddings
            if num_embs <= choice_value[i]:
                raise Exception('Choice {} ({}) has value {} greater than size {}'.format(
                    i, self.name_order[prev_choice[i]], choice_value[i].item(), num_embs))

        choice_emb = torch.cat([
            self.choice_embedding[prev_choice[i]](choice_value[i])
            for i in range(len(prev_choice))
        ], dim=0)

        input_emb = torch.cat((choice_emb, program_emb, index_emb), dim=1)

        h = self.batchnorm_layer(h)
        h = self.dropout_layer(h)
        h = self.rnn(input_emb, h)
        pred = [
            self.inference[cur_choice[i]](h[i, :])
            for i in range(len(cur_choice))
        ]

        return pred, h

    def forward(self, program, program_len, trace, trace_len, choices):
        program = program.to(self.device)
        program_len = program_len.to(self.device)
        trace = trace.to(self.device)
        trace_len = trace_len.to(self.device)
        choices = choices.to(self.device)

        batch_size = trace.size(0)
        max_trace_len = trace.size(1)

        program_emb = self.encoder(program, program_len)
        h = self.init_hidden(batch_size)

        preds = [[] for _ in range(batch_size)]
        for i in range(max_trace_len - 1):
            prev_choice = trace[:, i]
            cur_choice = trace[:, i+1]

            pred, h = self.step(
                prev_choice,
                cur_choice,
                program_emb,
                h,
                choices)

            not_ended = (cur_choice != 0).nonzero().squeeze(-1)
            for idx in not_ended:
                preds[idx].append(pred[idx])

        return preds

    def predict(self, *args, **kwargs):
        preds = self.forward(*args, **kwargs)
        return [
            torch.tensor([
                p.topk(1)[1].item()
                for p in pl
            ])
            for pl in preds
        ]

    def save(self, filename):
        torch.save(self.state_dict(), filename)

    def load(self, filename):
        self.load_state_dict(torch.load(filename))
