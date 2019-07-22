import torch
import subprocess as sp
import os
import json
from iterextras import par_for

class TokenizerError(Exception):
    pass

class Tokenizer:
    def tokenize(self, program_string):
        raise NotImplementedError

    def tokenize_all(self, program_strings, vocab_index=None):
        tokens = par_for(lambda s: list(self.tokenize(s)), program_strings)

        if vocab_index is None:
            token_to_index = {}
            for l in tokens:
                for t in l:
                    if not t in token_to_index:
                        token_to_index[t] = len(token_to_index)

            token_to_index['UNK'] = len(token_to_index)

            token_indices = [
                torch.tensor([token_to_index[t] for t in l], dtype=torch.long) for l in tokens
            ]
        else:
            token_to_index = vocab_index
            token_indices = [
                torch.tensor([
                    vocab_index[t] if t in token_to_index else vocab_index['UNK'] for t in l
                ],
                    dtype=torch.long)
                for l in tokens
            ]

        return tokens, token_to_index, token_indices

    def _call_tokenizer_process(self, program_string, rel_path):
        file_dir = os.path.dirname(os.path.abspath(__file__))
        binary = f'{file_dir}/tokenizers/{rel_path}'
        p = sp.Popen([binary], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE,
                     cwd=os.path.dirname(binary))
        stdout, stderr = p.communicate(input=program_string.encode())
        try:
            return json.loads(stdout.decode('utf-8'))
        except json.JSONDecodeError:
            raise TokenizerError(stdout, stderr)


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


class OCamlTokenizer(Tokenizer):
    def tokenize(self, program_string):
        tokens = self._call_tokenizer_process(program_string, 'ocaml/main.native')
        for [k, v] in tokens:
            if k in ['LIDENT', 'UIDENT', 'STRING']:
                yield k
            else:
                yield (k, v)


class PyretTokenizer(Tokenizer):
    def tokenize(self, program_string):
        tokens = self._call_tokenizer_process(program_string, 'pyret/main.sh')
        for [k, v] in tokens:
            if k in ['NAME', 'STRING', 'NUMBER', 'RATIONAL']:
                yield k
            else:
                yield (k, v)
