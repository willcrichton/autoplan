import torch


class Tokenizer:
    def tokenize(self, program_string):
        raise NotImplementedError

    def tokenize_all(self, program_strings):
        tokens = [list(self.tokenize(s)) for s in program_strings]

        token_to_index = {}
        for l in tokens:
            for t in l:
                if not t in token_to_index:
                    token_to_index[t] = len(token_to_index)


        token_indices = [
            torch.tensor([token_to_index[t] for t in l], dtype=torch.long) for l in tokens
        ]

        return tokens, token_to_index, token_indices


class JavaTokenizer(Tokenizer):
    def tokenize(self, program_string):
        import javalang.tokenizer as tokenizer
        tokens = tokenizer.tokenize(program_string)
        for token in tokens:
            typ = type(token)
            value = token.value
            if typ == tokenizer.String:
                yield typ
            else:
                yield (typ, value)
