from torch import nn
import torch.nn.utils.rnn as rnn_utils
import torch


class ProgramEncoder(nn.Module):
    def __init__(self, dataset, device, embedding_size=300, hidden_size=256):
        super().__init__()

        # Setup various constants
        self.device = device
        self.embedding_size = embedding_size
        self.hidden_size = hidden_size
        self.num_layers = 1

        # Define graph architecture
        self.embedding = nn.Embedding(dataset.vocab_size, self.embedding_size)
        self.rnn = nn.RNN(input_size=self.embedding_size,
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
        h0 = torch.empty(self.num_layers, batch_size, self.hidden_size).to(device=self.device)
        nn.init.xavier_normal_(h0)

        # Run the RNN on all sequences
        _, hidden = self.rnn(packed_input, h0)

        return hidden


class ProgramClassifier(nn.Module):
    def __init__(self, dataset, device):
        super().__init__()

        self.num_labels = len(dataset.label_set)
        self.encoder = ProgramEncoder(dataset, device)
        self.classifier = nn.Linear(self.encoder.hidden_size, self.num_labels)
        self.to(device=device)

    def forward(self, input_sequence, seq_lengths):
        hidden = self.encoder(input_sequence, seq_lengths)

        # Run the classifier on the hidden state to predict the final class
        return self.classifier(hidden).squeeze(0)


class GrammarInference(nn.Module):
    def __init__(self, dataset, device):
        super().__init__()

        self.device = device
        self.hidden_size = 256
        self.embedding_size = 300
        self.choice_indices = dataset.choice_indices

        # Inputs
        self.encoder = ProgramEncoder(dataset, device)
        self.choice_embedding = nn.ModuleDict({
            name: nn.Embedding(len(opts), self.embedding_size)
            for name, opts in dataset.choices.items()
        })
        self.index_embedding = nn.Embedding(
            num_embeddings=len(dataset.choices),
            embedding_dim=self.embedding_size)

        # RNN
        self.rnn = nn.GRUCell(
            input_size=self.encoder.hidden_size + self.embedding_size * 2,
            hidden_size=self.hidden_size)

        # RV prediction
        self.inference = nn.ModuleDict({
            name: nn.Linear(self.hidden_size, len(opts))
            for name, opts in dataset.choices.items()
        })

        self.to(device=device)

    def init_hidden(self, batch_size):
        h0 = torch.empty(1, batch_size, self.hidden_size).to(device=self.device)
        nn.init.xavier_normal_(h0)
        return h0

    def step(self, prev_choice, cur_choice, program_emb, h, choices):
        index_emb = self.index_embedding(prev_choice)

        choice = choices.gather(dim=1, index=prev_choice.unsqueeze(-1))
        choice_emb = self.choice_embedding[prev_choice](choice)

        input_emb = torch.cat((choice_emb, program_emb, index_emb))

        h = self.rnn(input_emb, h)

        return self.inference[cur_choice](h), h

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

        preds = []
        for i in range(max_trace_len - 1):
            prev_choice = trace[:, i]
            cur_choice = trace[:, i+1]
            pred, h = self.step(prev_choice, cur_choice, program_emb, h, choices)
            preds.append(pred)

        return preds
