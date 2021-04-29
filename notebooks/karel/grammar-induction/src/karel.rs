use super::grammar::{LabeledTree, Nonterminal, SelfRef};
use pyo3::prelude::*;
use serde::Deserialize;
use std::any::{Any, TypeId};
use std::fmt;
use std::iter;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Deserialize)]
#[serde(tag = "type")]
pub enum Action {
  Move,
  TurnRight,
  TurnLeft,
  TurnAround,
  PutBeeper,
  PickBeeper,
  PaintCorner,
  Stop,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Deserialize)]
#[serde(tag = "type")]
pub enum Predicate {
  FrontIsClear,
  RightIsClear,
  LeftIsClear,
  FrontIsBlocked,
  LeftIsBlocked,
  RightIsBlocked,
  BeepersPresent,
  NoBeepersPresent,
  BeepersInBag,
  NoBeepersInBag,
  FacingNorth,
  FacingEast,
  FacingSouth,
  FacingWest,
  NotFacingNorth,
  NotFacingEast,
  NotFacingSouth,
  NotFacingWest,
  CornerColorIs,
}

#[derive(Clone, PartialEq, Eq, Hash, Deserialize)]
#[serde(tag = "type")]
pub enum Statement {
  Action {
    action: Action,
  },
  If {
    pred: Predicate,
    then_: SelfRef<Statement>,
    else_: Option<SelfRef<Statement>>,
  },
  While {
    pred: Predicate,
    body: SelfRef<Statement>,
  },
  Seq {
    first: SelfRef<Statement>,
    second: SelfRef<Statement>,
  },
}

impl fmt::Debug for Statement {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    use Statement::*;
    match self {
      Action { action } => write!(f, "{:?}", action)?,
      If { pred, then_, else_ } => {
        write!(f, "if ({:?}) {{ {:?} }}", pred, then_)?;
        if let Some(else_) = else_ {
          write!(f, " else {{ {:?} }}", else_)?
        }
      }
      While { pred, body } => write!(f, "while ({:?}) {{ {:?} }}", pred, body)?,
      Seq { first, second } => write!(f, "{:?}; {:?}", first, second)?,
    };
    Ok(())
  }
}

impl LabeledTree for Statement {
  fn label_matches(&self, other: &Self) -> bool {
    use Statement::*;
    match (self, other) {
      (Action { action: action1 }, Action { action: action2 }) => action1 == action2,
      (If { pred: pred1, .. }, If { pred: pred2, .. }) => pred1 == pred2,
      (While { pred: pred1, .. }, While { pred: pred2, .. }) => pred1 == pred2,
      (Seq { .. }, Seq { .. }) => true,
      _ => false,
    }
  }

  fn children<'a>(&'a self) -> Box<dyn Iterator<Item = &'a SelfRef<Self>> + 'a> {
    use Statement::*;
    match self {
      Action { .. } => Box::new(iter::empty()),
      If { then_, else_, .. } => Box::new(iter::once(then_).chain(else_.iter())),
      While { body, .. } => Box::new(iter::once(body)),
      Seq { first, second } => Box::new(iter::once(first).chain(iter::once(second))),
    }
  }

  fn children_mut<'a>(&'a mut self) -> Box<dyn Iterator<Item = &'a mut SelfRef<Self>> + 'a> {
    use Statement::*;
    match self {
      Action { .. } => Box::new(iter::empty()),
      If { then_, else_, .. } => Box::new(iter::once(then_).chain(else_.iter_mut())),
      While { body, .. } => Box::new(iter::once(body)),
      Seq { first, second } => Box::new(iter::once(first).chain(iter::once(second))),
    }
  }
}

#[test]
fn json() {
  use super::grammar::GrammarLearner;
  use std::{fs::File, io::BufReader};

  let file = File::open("../progs.json").unwrap();
  let reader = BufReader::new(file);
  let progs: Vec<Statement> = serde_json::from_reader(reader).unwrap();

  let mut learner = GrammarLearner::build_lgcg(progs[..10].to_vec());
  learner.mcmc(100);
}

// #[test]
// fn test() {
//   use super::grammar::GrammarLearner;

//   let progs = vec![
//     Statement::Seq(
//       SelfRef::Concrete(Box::new(Statement::Action(Action::Move))),
//       SelfRef::Concrete(Box::new(Statement::If(
//         Predicate::FrontIsClear,
//         SelfRef::Concrete(Box::new(Statement::Action(Action::Move))),
//         None,
//       ))),
//     ),
//     Statement::If(
//       Predicate::FrontIsClear,
//       SelfRef::Concrete(Box::new(Statement::Action(Action::TurnRight))),
//       None,
//     ),
//   ];
//   let mut learner = GrammarLearner::build_lgcg(progs.clone());

//   macro_rules! debug {
//     () => {
//       println!("{:#?}", learner.grammar);
//       println!("{:.3?}", learner.grammar.parse(&progs[0], &mut None).exp());
//       // println!(
//       //   "learner prior {:.3?}, data likelihood {:.3?}",
//       //   learner.grammar_prior().exp(),
//       //   learner.data_likelihood().exp()
//       // );
//       println!("=========");
//     };
//   };

//   debug!();
//   learner.mcmc(1000);
//   //debug!();

//   //debug!();
//   // println!("{:.3?}", learner.structure_prior());
//   // learner.merge_random();
//   // learner.update_params();
//   // println!("{:.3?}", learner.structure_prior());
//   // debug!();
//   // learner.merge_random();
//   // learner.update_params();
//   // debug!();
//   // learner.split_random();
//   // learner.update_params();
//   // debug!();
// }
