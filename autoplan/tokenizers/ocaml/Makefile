all: tokenize.native preprocess.native ast.native

%.native: %.ml
	ocamlbuild -use-ocamlfind $*.native

clean:
	rm -rf _build *.native
