import torch
import subprocess as sp
import os
import json
from iterextras import par_for, unzip
from enum import Enum
import re

class TokenizerError(Exception):
    pass


class TokenType(Enum):
    Identifier = 0
    Number = 1
    String = 2


class Tokenizer:
    def __init__(self, exclude=[TokenType.String, TokenType.Number, TokenType.Identifier],
                 preprocess=True):
        self.exclude = exclude
        self.preprocess = preprocess

    def _token_types(self):
        raise NotImplementedError

    def _tokenize(self, program_string):
        raise NotImplementedError

    def tokenize(self, program_string):
        token_types = self._token_types()
        tokens, program = self._tokenize(program_string)

        def exclude(pair):
            (ty, val) = pair
            return ty if ty in token_types and token_types[ty] in self.exclude else pair

        return map(exclude, tokens), program

    def tokenize_all(self, program_strings, vocab_index=None):
        def map_tokenize(s):
            tokens, program = self.tokenize(s)
            return list(tokens), program
        tokens, programs = unzip(
            par_for(map_tokenize, program_strings, progress=False))

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

        return tokens, token_to_index, token_indices, programs

    def _call_process(self, dir_name, script_name, input):
        file_dir = os.path.dirname(os.path.abspath(__file__))
        binary = f'{file_dir}/tokenizers/{dir_name}/{script_name}'
        p = sp.Popen([binary], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE,
                     cwd=os.path.dirname(binary))
        stdout, stderr = p.communicate(input=input.encode())
        return stdout.decode('utf-8'), stderr.decode('utf-8')

    def _call_tokenizer_process(self, program_string, dir_name, check_stderr=True):
        if self.preprocess:
            program_string, stderr = self._call_process(dir_name, 'preprocess.sh',
                                                        program_string)
            if check_stderr and stderr != '':
                raise TokenizerError(program_string, stderr)

        token_json, stderr = self._call_process(dir_name, 'tokenize.sh', program_string)
        token_json = token_json.replace("\\", "\\\\")

        try:
            return json.loads(token_json), program_string
        except json.JSONDecodeError:
            raise TokenizerError(token_json, stderr)

    def parse(self, program_string):
        stdout, stderr = self._parse(program_string)
        if stderr.strip() != '':
            raise TokenizerError(program_string, stderr)
        return json.loads(stdout)


class JavaTokenizer(Tokenizer):
    def _token_types(self):
        import javalang.tokenizer as tokenizer
        return {
            tokenizer.String: TokenType.String,
            tokenizer.Identifier: TokenType.Identifier,
            tokenizer.Integer: TokenType.Number
        }

    def _tokenize(self, program_string):
        import javalang.tokenizer as tokenizer
        tokens = tokenizer.tokenize(program_string)
        return map(lambda token: (type(token), token.value)), program_string

class OCamlTokenizer(Tokenizer):
    def _token_types(self):
        return {
            'LIDENT': TokenType.Identifier,
            'UIDENT': TokenType.Identifier,
            'STRING': TokenType.String
        }

    def _parse(self, program_string):
        return self._call_process('ocaml', 'ast.native', program_string)

    def _tokenize(self, program_string):
        tokens, program = self._call_tokenizer_process(program_string, 'ocaml', check_stderr=False)
        return map(tuple, tokens), program


class PyretTokenizer(Tokenizer):
    def _token_types(self):
        return {
            'NAME': TokenType.Identifier,
            'NUMBER': TokenType.Number,
            'RATIONAL': TokenType.Number,
            'STRING': TokenType.String
        }

    def _tokenize(self, program_string):
        if self.preprocess:
            program_string = re.sub(r'where:.*?end', 'end', program_string, flags=re.DOTALL)

        tokens, program = self._call_tokenizer_process(program_string, 'pyret')

        return map(tuple, tokens), program

    def _parse(self, program_string):
        return self._call_process('pyret', 'ast.sh', program_string)
