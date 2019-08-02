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
  console.log(input);

  /* var toks = T.Tokenizer;
   * toks.tokenizeFrom(input);

   * var parsed = G.PyretGrammar.parse(toks);
   * if (parsed === undefined) {
   *   throw `Next token is ${toks.curTok.toRepr(true)} at ${toks.curTok.pos.toString(true)}`;
   * }

   * var ast = G.PyretGrammar.constructUniqueParse(parsed); */
});
