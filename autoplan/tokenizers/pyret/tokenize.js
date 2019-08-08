// Adapted from extremely convenient lexing script
// https://github.com/brownplt/pyret-lang/blob/horizon/src/scripts/just-lex.js

// IMPORTANT: modify this path to your pyret-lang installation to call this script
// Also make sure to run `npm install`
const PYRET_PATH = '/home/wcrichto/pyret-lang';

const R = require("requirejs");

R.config({
  paths: {
    'jglr': `${PYRET_PATH}/lib/jglr`,
    'pyret-base': `${PYRET_PATH}/build/phaseC`,
  }
});
R(["pyret-base/js/pyret-tokenizer", "pyret-base/js/pyret-parser", "fs"], function(T, G, fs) {
  var input = fs.readFileSync(0).toString();
  var toks = T.Tokenizer;
  toks.tokenizeFrom(input);

  var tokens = [];
  while (toks.hasNext()) {
    tokens.push(toks.next());
  }

  var cleaned_tokens = tokens.map((tok) => {
    return [tok.name, tok.value];
  });

  console.log(JSON.stringify(cleaned_tokens));
});
