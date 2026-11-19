# Roteiro do dígito verificador da conta

Confere se o cálculo do bot (`leiautes/irpf2026/dv_conta.py`, transcrito do `ValidadorDvContaCorrente`
do programa) dá o mesmo resultado que o programa, banco a banco.

- Os dois testes partem de `tests/manual/geral/base/` (DBK vazio sem o pagamento vazio) e lançam só
  contas correntes (06/01), uma por banco com regra de DV.
- **teste1_validas**: 17 contas com o DV que o bot calcula como certo (o Sicredi aceita qualquer DV).
  No programa, **nenhum** aviso "DV da conta inválido" deve aparecer.
- **teste2_invalidas**: as mesmas contas (menos o Sicredi) com outro DV. O bot avisa nas 16; no
  programa, **todos** os 16 bens devem ter o aviso.

As discriminações dizem o banco ("Conta teste banco 237 ...") para achar o bem quando o programa
mostrar o aviso. Os JSONs foram gerados por script a partir do próprio cálculo; os DVs que conferem
estão fixados em `tests/test_dv_conta.py`.
