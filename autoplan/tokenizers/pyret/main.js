// Adapted from extremely convenient lexing script
// https://github.com/brownplt/pyret-lang/blob/horizon/src/scripts/just-lex.js

// IMPORTANT: modify this path to your pyret-lang installation to call this script
// Also make sure to run `npm install`
const PYRET_PATH = '/home/wcrichto/pyret-lang';

const R = require("requirejs");

R.config({
  paths: {
    'jglr': `${PYRET_PATH}/lib/jglr`,
    'pyret-base': `${PYRET_PATH}/build/phaseA`,
    'src-base/js': `${PYRET_PATH}/src/js/base`
  }
});
R(["pyret-base/js/pyret-tokenizer", "fs",], function(T, fs) {
  var input = fs.readFileSync(0).toString();
  var t = T.Tokenizer;
  t.tokenizeFrom(input);

  var tokens = [];
  while (t.hasNext()) {
    tokens.push(t.next());
  }

  var cleaned_tokens = tokens.map((tok) => {
    return [tok.name, tok.value];
  });

  console.log(JSON.stringify(cleaned_tokens));
});
