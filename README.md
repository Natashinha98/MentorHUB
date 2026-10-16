# MentorHub

Projeto de Engenharia de Software (FEI). O MentorHub é uma plataforma de mentoria onde
mentorados procuram mentores. Aqui implementamos em Python os componentes de
**Autenticação** e **Busca de Mentores**, seguindo a especificação que fizemos nos
documentos da disciplina. Os outros componentes do sistema ainda não foram implementados.

**Equipe:** Natasha Trindade, Douglas Honda e Marcus Vinicius Zelenato.

## Tecnologias utilizadas

- **Python 3.10 ou mais novo** (testamos com o 3.13)
- **Biblioteca padrão do Python**: `abc` (para criar as interfaces), `dataclasses` e `enum`
  (para as classes de dados), `hashlib` (para guardar as senhas com hash), `logging` (para
  registrar falhas) e `http.server` (servidor da tela)
- **pytest** e **pytest-cov** para os testes e a cobertura (estão no `requirements.txt`)
- **HTML, CSS e JavaScript** simples na tela de demonstração, sem nenhum framework

## Estrutura dos componentes

Implementamos dois componentes: **Autenticação** e **Busca de Mentores**. Cada um fica na
sua pasta, com a interface, o componente e os erros dele.

```
mentorhub/
├── src/mentorhub/
│   ├── modelos.py              # classes de dados (Usuario, Conta, PerfilMentor, Avaliacao, ...)
│   ├── textos.py               # tira acento e deixa o texto minúsculo (usado na busca)
│   ├── autenticacao/           # COMPONENTE Autenticação
│   ├── busca/                  # COMPONENTE Busca de Mentores
│   ├── persistencia/           # APOIO: interface do banco + versão em memória
│   └── armazenamento/          # APOIO: interface das fotos + versão em memória
├── interface_web/              # tela de demonstração
├── tests/                      # testes automatizados
├── docs/evidencias/            # saída dos testes e prints da tela
├── demo.py                     # demonstração no terminal
├── pytest.ini
└── requirements.txt
```

Dentro de cada pasta de componente tem sempre três arquivos:

- `interfaces.py`: a interface que o componente oferece (classe abstrata)
- `componente.py`: a classe que implementa a interface
- `excecoes.py`: os erros próprios daquele componente

A **Persistência** e o **Armazenamento de imagens** são outros componentes da arquitetura,
mas não era o nosso foco implementar eles. Por isso criamos só as interfaces
(`IPersistencia` e `IArmazenamentoImagens`) e uma versão simples que guarda tudo na memória,
só para os nossos componentes terem com quem conversar.

## Interfaces e operações implementadas

No código os nomes não têm acento (`IPersistencia`); na documentação aparecem com acento.

| Componente | Interface que fornece | Interfaces que precisa |
|---|---|---|
| Autenticação | `IAutenticacao` | `IPersistencia` |
| Busca de Mentores | `IBuscaMentores` | `IPersistencia`, `IArmazenamentoImagens` |

### IAutenticacao

| Operação | O que faz | Erros possíveis |
|---|---|---|
| `validar_cadastro(nome, email, senha, papel)` | Confere os dados do cadastro e devolve a lista de regras que não foram cumpridas. Não cria nada | (não dá erro, só devolve a lista) |
| `criar_conta(nome, email, senha, papel)` | Cria a conta. A senha é guardada só como hash | `DadosInvalidos` |
| `autenticar_usuario(email, senha)` | Faz o login e devolve o usuário | `CredenciaisInvalidas` |
| `recuperar_acesso(email)` | Gera um código de 6 dígitos que vale 15 minutos | `ContaNaoEncontrada` |
| `redefinir_senha(email, codigo, nova_senha)` | Troca a senha usando o código | `CodigoRecuperacaoInvalido`, `DadosInvalidos` |

Regras do cadastro: nome com pelo menos 2 letras, e-mail válido e ainda não usado, senha com 8
caracteres ou mais (com letra e número) e papel mentor ou mentorado. No login, o erro é o
mesmo para e-mail errado ou senha errada, para não dar dica a quem tenta invadir. A
`redefinir_senha` não estava na lista da especificação, mas sem ela a recuperação de acesso
não termina, então colocamos como a segunda parte dela.

### IBuscaMentores

| Operação | O que faz | Erros possíveis |
|---|---|---|
| `pesquisar_mentores(area)` | Lista os mentores que atendem naquela área, dos mais bem avaliados para os menos, com nome, áreas, nota e foto | `AreaInvalida` (área vazia) |
| `consultar_perfil(mentor_id)` | Mostra a bio e as avaliações de um mentor | `PerfilNaoEncontrado` |

A pesquisa não diferencia maiúscula de minúscula nem acento (buscar "dados" ou "DADOS" dá o
mesmo resultado). Se a foto de um mentor não carregar, ele continua na lista, só sem foto.

### Interfaces de apoio

- `IPersistencia`: guarda e busca usuários, contas, perfis de mentores e avaliações
- `IArmazenamentoImagens`: `salvar_foto` e `recuperar_foto`

O contrato completo de cada operação (entradas, saída, pré e pós-condição) está escrito nas
docstrings dos arquivos `interfaces.py`.

## Como ocorre a comunicação entre os componentes

```
 quem usa (tela, demo.py ou testes)
      │
      ├──► IAutenticacao ──► Autenticação ──────► IPersistencia
      └──► IBuscaMentores ─► Busca de Mentores ─► IPersistencia
                                           └────► IArmazenamentoImagens
```

- Os componentes **só conversam por interfaces**. Por exemplo, a Busca de Mentores chama
  `IPersistencia` e nunca importa a classe `PersistenciaEmMemoria`. Com isso dá para
  trocar uma peça por outra (como o banco real no lugar do banco em memória) sem mexer no resto.
  Um teste automatizado confere isso.
- Cada componente recebe o que precisa **pelo construtor**, e quem junta tudo é o `demo.py`, os
  testes ou a tela. Exemplo: `ComponenteBuscaMentores(persistencia, imagens)`.
- Autenticação e Busca **não chamam um ao outro**. Eles se encontram nos mesmos dados, pela
  `IPersistencia`: uma conta de mentor criada na Autenticação, junto com o perfil dele, já
  aparece na Busca.
- Se a foto de um mentor não puder ser carregada, a Busca não quebra: o mentor aparece sem
  foto e o problema vai para o log.
- Quem controla "quem está logado" é a tela, porque os componentes não guardam sessão.

## Instruções para execução

Precisa ter o Python 3.10 ou mais novo instalado. Pelo terminal, dentro da pasta do projeto:

```bash
# 1. (opcional) criar um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate

# 2. instalar as dependências (pytest e pytest-cov)
pip install -r requirements.txt

# 3. rodar a demonstração no terminal
python demo.py

# 4. abrir a tela de demonstração em http://localhost:8000
python interface_web/servidor.py

# 5. rodar os testes
python -m pytest -v

# 6. rodar os testes com cobertura
python -m pytest --cov=mentorhub --cov-report=term-missing
```

- Se a porta 8000 estiver ocupada: `python interface_web/servidor.py --porta 8080`
- Para parar o servidor, é só apertar `Ctrl+C` no terminal
- Contas de teste da tela (senha de todas: `senha1234`): `ana@mentorhub.com` (mentora),
  `bruno@mentorhub.com` e `carla@mentorhub.com` (mentorados)
- Não precisa instalar o projeto: o `pytest.ini` já configura o caminho

## Testes realizados

Fizemos **87 testes automatizados**, com **99% de cobertura** do código dos componentes. A saída
dos testes está em `docs/evidencias/resultado_testes.txt`.

| Arquivo | O que testa |
|---|---|
| `test_autenticacao.py` | Cada regra do cadastro, se a senha nunca fica guardada em texto, login certo e errado, e a recuperação de acesso (código vencido, já usado ou substituído por outro) |
| `test_busca_mentores.py` | Pesquisa sem acento e sem diferenciar maiúscula, ordem por nota, área vazia, perfil com avaliações e mentor que continua na lista mesmo com a foto falhando |
| `test_integracao.py` | Os dois componentes de verdade juntos (criar conta → entrar → pesquisar → ver perfil) e um teste que confere que um componente não importa a implementação do outro |
| `test_persistencia_memoria.py` e `test_armazenamento_memoria.py` | Se as versões em memória se comportam como as interfaces prometem |
| `test_interface_web.py` | A camada da tela: login, cadastro, busca, perfil, recuperação de senha e o servidor |

Os testes dos componentes são feitos primeiro **isolados** (cada um com o banco em memória) e
depois **integrados** (os dois juntos).

## Demonstração

**No terminal (`demo.py`)**:

1. valida um cadastro com dados ruins e mostra a lista de erros
2. cria a conta de um mentorado e faz o login
3. tenta entrar com a senha errada e é recusado
4. recupera o acesso e troca a senha
5. pesquisa mentores de Python
6. abre o perfil de um mentor, com as avaliações
7. pesquisa com a área vazia e é recusado

**Na tela (`interface_web`)**: entrar, criar conta, esqueci a senha, pesquisar por área e ver
o perfil do mentor. Prints em `docs/evidencias/interface_*.png`.

## Limitações

- Os dados ficam só na memória e somem quando o programa fecha
- Os perfis e avaliações dos mentores vêm de uma carga inicial de teste, porque cadastrar isso
  não faz parte das operações da especificação
- A Autenticação não guarda sessão de login: ela só confere a senha. Quem guarda "quem está
  logado" é a tela, e só um usuário por vez (é uma demonstração local)
- Não sai e-mail de verdade: o código de recuperação aparece na tela
