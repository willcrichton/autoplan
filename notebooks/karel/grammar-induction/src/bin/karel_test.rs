use grammar_induction::{grammar::GrammarLearner, karel::Statement};
use std::{fs::File, io::BufReader};

fn main() {
  let file = File::open("../progs.json").unwrap();
  let reader = BufReader::new(file);
  let progs: Vec<Statement> = serde_json::from_reader(reader).unwrap();

  let mut learner = GrammarLearner::build_lgcg(progs[..50].to_vec());
  learner.mcmc(1000);
}
