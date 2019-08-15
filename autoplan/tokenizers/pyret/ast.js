const PYRET_PATH = '/home/wcrichto/pyret-lang';

const R = require("requirejs");

R.config({
  paths: {
    'jglr': `${PYRET_PATH}/lib/jglr`,
    'pyret-base': `${PYRET_PATH}/build/phaseC`,
  }
});

function ast_to_json(ast) {
  if (ast.name == 'fun-header') {
    return [ast.name];
  }

  let kids = ast.kids || [];
  kids = kids
    .filter((expr) => expr.name != expr.name.toUpperCase())
    .filter((expr) => !expr.name.includes('-ann'));

  return [ast.name].concat(kids.map(ast_to_json));
}

R(["pyret-base/js/pyret-tokenizer", "pyret-base/js/pyret-parser", "fs"], function(T, G, fs) {
  var input = fs.readFileSync(0).toString();

  var toks = T.Tokenizer;
  toks.tokenizeFrom(input);

  var parsed = G.PyretGrammar.parse(toks);
  if (parsed === undefined) {
    throw `Next token is ${toks.curTok.toRepr(true)} at ${toks.curTok.pos.toString(true)}`;
  }

  var ast = G.PyretGrammar.constructUniqueParse(parsed);
  console.log(JSON.stringify(ast_to_json(ast)));
});
