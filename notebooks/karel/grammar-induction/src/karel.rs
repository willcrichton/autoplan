use super::grammar::{LabeledTree, Nonterminal, SelfRef};
use serde::{Deserialize, Serialize};
use smallvec::smallvec;
use std::any::{Any, TypeId};
use std::fmt;
use std::iter;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
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

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
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

#[derive(Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
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
  type Iter<'a, T>
  where
    T: 'a,
  = smallvec::IntoIter<[T; 2]>;

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

  fn children<'a>(&'a self) -> Self::Iter<'a, &'a SelfRef<Self>> {
    use Statement::*;
    let vec = match self {
      Action { .. } => smallvec![],
      If { then_, else_, .. } => match else_ {
        Some(else_) => smallvec![then_, else_],
        None => smallvec![then_],
      },
      While { body, .. } => smallvec![body],
      Seq { first, second } => smallvec![first, second],
    };
    vec.into_iter()
  }

  fn children_mut<'a>(&'a mut self) -> Self::Iter<'a, &'a mut SelfRef<Self>> {
    use Statement::*;
    let vec = match self {
      Action { .. } => smallvec![],
      If { then_, else_, .. } => match else_ {
        Some(else_) => smallvec![then_, else_],
        None => smallvec![then_],
      },
      While { body, .. } => smallvec![body],
      Seq { first, second } => smallvec![first, second],
    };
    vec.into_iter()
  }
}

#[test]
fn test() {
  use super::grammar::GrammarLearner;

  let progs = vec![
    Statement::Seq {
      first: SelfRef::Concrete(Box::new(Statement::Action {
        action: Action::Move,
      })),
      second: SelfRef::Concrete(Box::new(Statement::If {
        pred: Predicate::FrontIsClear,
        then_: SelfRef::Concrete(Box::new(Statement::Action {
          action: Action::Move,
        })),
        else_: None,
      })),
    },
    Statement::If {
      pred: Predicate::FrontIsClear,
      then_: SelfRef::Concrete(Box::new(Statement::Action {
        action: Action::TurnRight,
      })),
      else_: None,
    },
  ];
  let mut learner = GrammarLearner::build_lgcg(progs.clone());

  macro_rules! debug {
    () => {
      println!("{:#?}", learner.grammar);
      println!("{:.3?}", learner.grammar.parse(&progs[0]));
      // println!(
      //   "learner prior {:.3?}, data likelihood {:.3?}",
      //   learner.grammar_prior().exp(),
      //   learner.data_likelihood().exp()
      // );
      println!("=========");
    };
  };

  debug!();
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
}
