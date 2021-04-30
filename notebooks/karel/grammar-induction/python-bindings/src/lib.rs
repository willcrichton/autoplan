#![feature(generic_associated_types)]
#![allow(warnings)]

use pyo3::wrap_pyfunction;
use pyo3::{prelude::*, types::PyList};
use pythonize::{depythonize, pythonize};

use grammar_induction::{grammar::GrammarLearner, karel::Statement};

/// Formats the sum of two numbers as string.
#[pyfunction]
fn test(py: Python, progs: &PyList) -> PyResult<PyObject> {
  let progs = progs
    .iter()
    .map(|prog| depythonize::<Statement>(prog))
    .collect::<Result<Vec<_>, _>>()?;

  let mut learner = GrammarLearner::build_lgcg(progs);
  let mcmc_output = learner.mcmc(1000);

  Ok(pythonize(py, &mcmc_output)?)
}

/// A Python module implemented in Rust.
#[pymodule]
fn grammar_induction(py: Python, m: &PyModule) -> PyResult<()> {
  m.add_function(wrap_pyfunction!(test, m)?)?;

  Ok(())
}
