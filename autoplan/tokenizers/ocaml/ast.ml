exception ParseError of string

let commasep = String.concat ","

let rec expr_to_json expr =
  let open Parsetree in
  match expr.pexp_desc with
  | Pexp_ident _ -> "\"ident\""
  | Pexp_constant _ -> "\"const\""
  | Pexp_let (_, vals, expr) ->
    Printf.sprintf "[\"let\", %s, %s]"
      (commasep (List.map (fun bnd -> expr_to_json bnd.pvb_expr) vals)) (expr_to_json expr)
  | Pexp_fun (_, _, _, expr) -> Printf.sprintf "[\"fun\", %s]" (expr_to_json expr)
  | Pexp_apply (fn, args) -> Printf.sprintf "[\"apply\", %s, %s]"
                               (expr_to_json fn) (commasep (List.map (fun (_, expr) -> expr_to_json expr) args))
  | Pexp_constraint (expr, _) -> expr_to_json expr
  | Pexp_match (expr, cases) -> Printf.sprintf "[\"match\", %s, %s]"
                                  (expr_to_json expr)
                                  (commasep (List.map (fun case -> expr_to_json case.pc_rhs) cases))
  | Pexp_tuple exprs -> Printf.sprintf "[\"tuple\", %s]" (commasep (List.map expr_to_json exprs))
  | Pexp_ifthenelse (if_, then_, else_) ->
    Printf.sprintf "[\"if\", %s, %s, %s]"
      (expr_to_json if_) (expr_to_json then_) (expr_to_json (Option.get else_))
  | Pexp_construct _ -> "\"construct\""
  | Pexp_try (expr, cases) ->
    Printf.sprintf "[\"try\", %s, %s]"
      (expr_to_json expr)
      (commasep (List.map (fun case -> expr_to_json case.pc_rhs) cases))
  | Pexp_sequence _ -> "\"sequence\""
  | _ -> raise (ParseError (Printast.expression 0 Format.str_formatter expr; Format.flush_str_formatter ()))

let main () =
  Lexer.init ();
  let lexbuf = Lexing.from_channel stdin in
  let phrases = Parse.use_file lexbuf in
  let funs = List.filter_map (fun phrase ->
    let open Parsetree in
    match phrase with
    | Ptop_def structure ->
      Some (List.filter_map (fun item ->
        match item.pstr_desc with
        | Pstr_value (_, vals) ->
          Some (Printf.sprintf "[\"fun\", %s]" (String.concat "," (List.map (fun vl -> expr_to_json vl.pvb_expr) vals)))
        | Pstr_eval (expr, _) ->
          Some (Printf.sprintf "[\"eval\", %s]" (expr_to_json expr))
        | _ -> None)
        structure)
    | _ -> None)
    phrases
  in
  Printf.printf "[%s]" (commasep (List.flatten funs))

let () = main ()
