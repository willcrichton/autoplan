use super::grammar::{LabeledTree, Nonterminal, SelfRef};
use std::any::{Any, TypeId};
use std::fmt;
use std::iter;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum Action {
  Move,
  TurnRight,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum Predicate {
  FrontIsClear,
  RightIsClear,
}

#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Statement {
  Action(Action),
  If(Predicate, SelfRef<Statement>, Option<SelfRef<Statement>>),
  While(Predicate, SelfRef<Statement>),
  Seq(SelfRef<Statement>, SelfRef<Statement>),
}

impl fmt::Debug for Statement {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    use Statement::*;
    match self {
      Action(action) => write!(f, "{:?}", action)?,
      If(predicate, then_, else_) => {
        write!(f, "if ({:?}) {{ {:?} }}", predicate, then_)?;
        if let Some(else_) = else_ {
          write!(f, " else {{ {:?} }}", else_)?
        }
      }
      While(predicate, body) => write!(f, "while ({:?}) {{ {:?} }}", predicate, body)?,
      Seq(s1, s2) => write!(f, "{:?}; {:?}", s1, s2)?,
    };
    Ok(())
  }
}

impl LabeledTree for Statement {
  fn matches(&self, other: &Self) -> bool {
    use Statement::*;
    match (self, other) {
      (Action(action1), Action(action2)) => action1 == action2,
      (If(pred1, _, _), If(pred2, _, _)) => pred1 == pred2,
      (While(pred1, _), While(pred2, _)) => pred1 == pred2,
      (Seq(_, _), Seq(_, _)) => true,
      _ => false,
    }
  }

  fn children<'a>(&'a self) -> Box<dyn Iterator<Item = &'a SelfRef<Self>> + 'a> {
    use Statement::*;
    match self {
      Action(_) => Box::new(iter::empty()),
      If(_, then_, else_) => Box::new(iter::once(then_).chain(else_.iter())),
      While(_, body) => Box::new(iter::once(body)),
      Seq(s1, s2) => Box::new(iter::once(s1).chain(iter::once(s2))),
    }
  }

  fn children_mut<'a>(&'a mut self) -> Box<dyn Iterator<Item = &'a mut SelfRef<Self>> + 'a> {
    use Statement::*;
    match self {
      Action(_) => Box::new(iter::empty()),
      If(_, then_, else_) => Box::new(iter::once(then_).chain(else_.iter_mut())),
      While(_, body) => Box::new(iter::once(body)),
      Seq(s1, s2) => Box::new(iter::once(s1).chain(iter::once(s2))),
    }
  }
}

#[test]
fn test() {
  use super::grammar::Grammar;

  let prog = Statement::Seq(
    SelfRef::Concrete(Box::new(Statement::Action(Action::Move))),
    SelfRef::Concrete(Box::new(Statement::If(
      Predicate::FrontIsClear,
      SelfRef::Concrete(Box::new(Statement::Action(Action::Move))),
      None,
    ))),
  );
  let grammar = Grammar::build_lgcg(vec![prog.clone()]);
  println!("{:#?}", grammar);
  println!(
    "{:?}",
    grammar
      .parse(&prog)
      .into_iter()
      .map(|p| p.exp())
      .collect::<Vec<_>>()
  );
  println!("grammar prior {:?}, data likelihood {:?}", grammar.grammar_prior().exp(), grammar.data_likelihood().exp());
}
