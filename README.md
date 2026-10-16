# MentorHub – Componentes de Autenticação, Busca de Mentores, Agendamento e Notificações

Implementação em Python de quatro componentes do **MentorHub**, plataforma de mentoria
(Engenharia de Software, FEI), com uma interface visual para demonstrar como eles se
comunicam. Os componentes seguem a especificação e a modelagem de componentes do projeto
(`Especificacao_e_Modelagem_de_Componentes_MentorHub.docx`); o Lab 4 pede em especial
Agendamento e Notificações (`Especificacao_de_Componentes_Implementacao_MentorHub.docx`).

**Equipe:** Natasha Trindade, Douglas Honda e Marcus Vinicius Zelenato.

## Tecnologias

- Python 3.10 ou superior (testado com 3.13)
- `abc` (interfaces), `dataclasses` e `enum` (modelo), `logging` (registro de falhas), biblioteca padrão
- `pytest` e `pytest-cov` para os testes (únicas dependências, em `requirements.txt`)

## Estrutura

```
mentorhub/
├── src/mentorhub/
│   ├── modelos.py                  # Usuario, Sessao, Conta, PerfilMentor, Avaliacao, Foto, ...
│   ├── textos.py                   # normalização de texto (sem acento, minúsculo)
│   ├── autenticacao/               # COMPONENTE: Autenticação
│   │   ├── interfaces.py           #   IAutenticacao (fornecida)
│   │   ├── componente.py           #   ComponenteAutenticacao
│   │   └── excecoes.py             #   DadosInvalidos, CredenciaisInvalidas, ...
│   ├── busca/                      # COMPONENTE: Busca de Mentores
│   │   ├── interfaces.py           #   IBuscaMentores (fornecida)
│   │   ├── componente.py           #   ComponenteBuscaMentores
│   │   └── excecoes.py             #   AreaInvalida, PerfilNaoEncontrado
│   ├── agendamento/                # COMPONENTE: Agendamento
│   │   ├── interfaces.py           #   IAgendamento (fornecida)
│   │   ├── componente.py           #   ComponenteAgendamento
│   │   └── excecoes.py             #   erros do domínio de agendamento
│   ├── notificacoes/               # COMPONENTE: Notificações
│   │   ├── interfaces.py           #   INotificacao (fornecida) e IEmail (requerida)
│   │   ├── componente.py           #   ComponenteNotificacoes
│   │   └── excecoes.py             #   EmailInvalido, FalhaEnvioEmail
│   ├── persistencia/               # APOIO (componente não implementado)
│   │   ├── interfaces.py           #   IPersistencia
│   │   └── memoria.py              #   PersistenciaEmMemoria (substituto em memória)
│   ├── armazenamento/              # APOIO (componente não implementado)
│   │   ├── interfaces.py           #   IArmazenamentoImagens
│   │   └── memoria.py              #   ArmazenamentoEmMemoria (substituto em memória)
│   └── externos/
│       └── email_simulado.py       # APOIO: EmailSimulado (serviço de e-mail de mentira)
├── interface_web/                  # INTERFACE VISUAL da demonstração
│   ├── aplicacao.py                #   monta Autenticação e Busca de Mentores com dados de teste
│   ├── servidor.py                 #   servidor local (biblioteca padrão)
│   └── index.html                  #   tela
├── tests/                          # testes automatizados
├── docs/evidencias/                # saídas salvas dos testes e da demonstração, e prints da interface
├── demo.py                         # demonstração no terminal
├── pytest.ini
└── requirements.txt
```

Os componentes implementados são **Autenticação**, **Busca de Mentores**, **Agendamento** e
**Notificações** (o Lab 4 cobra Agendamento e Notificações). A **Persistência** e o
**Armazenamento de Perfil** são outros componentes da arquitetura que não foram
implementados aqui: só as interfaces `IPersistencia` e `IArmazenamentoImagens` existem,
cada uma com um substituto em memória para os componentes terem com quem conversar. O
serviço de e-mail também é externo ao MentorHub e foi simulado (`EmailSimulado`).

## Interfaces

Nos arquivos o código não usa acento (`INotificacao`, `IPersistencia`); no documento de
especificação os nomes são `INotificação` e `IPersistência`.

| Componente | Fornece | Requer |
|---|---|---|
| Autenticação | `IAutenticacao` | `IPersistencia` |
| Busca de Mentores | `IBuscaMentores` | `IPersistencia`, `IArmazenamentoImagens` |
| Agendamento | `IAgendamento` | `IPersistencia`, `INotificacao` |
| Notificações | `INotificacao` | `IEmail` (serviço externo) |

### IAutenticacao (fornecida pela Autenticação)

| Operação | O que faz | Pré-condição | Erros |
|---|---|---|---|
| `validar_cadastro(nome, email, senha, papel) -> ResultadoValidacao` | Confere os dados sem criar nada e lista cada regra desrespeitada | Nenhuma (é consulta) | Não levanta erro: devolve `valido=False` com a lista |
| `criar_conta(nome, email, senha, papel) -> Usuario` | Cria a conta; a senha fica guardada só como hash com sal (PBKDF2-SHA256) | Dados passam em `validar_cadastro` | `DadosInvalidos` |
| `autenticar_usuario(email, senha) -> Usuario` | Confere e-mail e senha | Conta existe e senha confere | `CredenciaisInvalidas` (mesma mensagem para e-mail ou senha errados) |
| `recuperar_acesso(email) -> CodigoRecuperacao` | Gera um código de 6 dígitos, válido por 15 minutos, guardado só como hash | Conta existe | `ContaNaoEncontrada` |
| `redefinir_senha(email, codigo, nova_senha) -> Usuario` | Termina a recuperação: troca a senha; o código só vale uma vez | Código certo e dentro do prazo; senha nova válida | `CodigoRecuperacaoInvalido`, `DadosInvalidos` |

Regras de cadastro: nome com 2 letras ou mais; e-mail com formato válido e ainda não cadastrado; senha
com 8 caracteres ou mais, com letras e números; papel mentor ou mentorado. A `redefinir_senha` completa o
fluxo alternativo "esqueci a senha": a especificação lista só "recuperar acesso", e a troca da senha é a
segunda metade dessa operação. A Autenticação não manda e-mail (não requer `INotificacao` na arquitetura), então
quem entrega o código ao usuário é de fora do componente.

### IBuscaMentores (fornecida pela Busca de Mentores)

| Operação | O que faz | Pré-condição | Erros |
|---|---|---|---|
| `pesquisar_mentores(area) -> list[ResumoMentor]` | Lista os mentores com alguma área que contenha o termo (sem diferenciar maiúsculas e acentos), do mais bem avaliado pro menos, com nome, áreas, nota média e foto | Área não vazia | `AreaInvalida` |
| `consultar_perfil(mentor_id) -> PerfilCompleto` | Resumo, bio e avaliações do mentor | Mentor existe e tem perfil | `PerfilNaoEncontrado` |

Se a foto de um mentor não puder ser carregada, ele continua na lista, só sem foto.

### IAgendamento (fornecida pelo Agendamento)

| Operação | O que faz | Pré-condição | Erros |
|---|---|---|---|
| `verificar_disponibilidade(mentor_id, data) -> list[datetime]` | Lista os horários livres do mentor na data, em ordem | Mentor existe | `MentorNaoEncontrado` |
| `agendar_sessao(mentor_id, mentorado_id, horario) -> Sessao` | Marca a sessão, tira o horário da lista de livres e pede o aviso de confirmação | Horário livre; mentor e mentorado existem | `HorarioIndisponivel`, `MentorNaoEncontrado`, `MentoradoNaoEncontrado` |
| `cancelar_sessao(sessao_id) -> Sessao` | Cancela, devolve o horário à agenda e pede o aviso de cancelamento | Sessão existe, está marcada e ainda não aconteceu | `SessaoNaoEncontrada`, `CancelamentoNaoPermitido` |

### INotificacao (fornecida pelas Notificações)

| Operação | O que faz | Pré-condição | Saída |
|---|---|---|---|
| `enviar_notificacao_confirmacao(sessao_id, email_mentor, email_mentorado, data_hora)` | Envia e-mail de confirmação aos dois | E-mails válidos (senão `EmailInvalido`, e nada é enviado) | `ResultadoEnvio(enviado, falhas)` |
| `enviar_notificacao_cancelamento(sessao_id, email_mentor, email_mentorado, data_hora)` | Envia e-mail de cancelamento aos dois | Idem | `ResultadoEnvio(enviado, falhas)` |

### Interfaces de apoio

- `IPersistencia`: `buscar_usuario`, `listar_horarios_livres`, `ocupar_horario`, `liberar_horario`, `salvar_sessao`, `buscar_sessao` (Agendamento); `salvar_conta`, `buscar_conta_por_email` (Autenticação); `salvar_perfil_mentor`, `buscar_perfil_mentor`, `listar_perfis_por_area`, `salvar_avaliacao`, `listar_avaliacoes` (Busca de Mentores). O `ocupar_horario` confere e reserva de uma vez só, por isso dois agendamentos do mesmo horário nunca dão certo ao mesmo tempo.
- `IArmazenamentoImagens`: `salvar_foto(usuario_id, foto)` e `recuperar_foto(usuario_id)`.
- `IEmail`: `enviar(destinatario, assunto, corpo)`, que levanta `FalhaEnvioEmail` se o envio não for possível.

Os contratos completos (entradas, saída, pré e pós-condições) estão nas docstrings de
cada interface, em `interfaces.py`.

## Como os componentes se comunicam

```
 interface web / demo.py / testes
      │
      ├──► IAutenticacao ─── ComponenteAutenticacao ───► IPersistencia
      ├──► IBuscaMentores ── ComponenteBuscaMentores ──► IPersistencia
      │                                         └──────► IArmazenamentoImagens
      └──► IAgendamento ──── ComponenteAgendamento ────► IPersistencia
                                         └──────► INotificacao
                                                    ComponenteNotificacoes ──► IEmail

 IPersistencia  ◄── PersistenciaEmMemoria      IArmazenamentoImagens ◄── ArmazenamentoEmMemoria
 IEmail         ◄── EmailSimulado
```

- Cada componente recebe o que precisa **pelo construtor** (injeção de dependência):
  `ComponenteAgendamento(persistencia, notificacao)`, `ComponenteNotificacoes(email)`,
  `ComponenteAutenticacao(persistencia)` e `ComponenteBuscaMentores(persistencia, imagens)`.
- O Agendamento só conhece a interface `INotificacao`. Ele não importa a classe
  `ComponenteNotificacoes`. Quem liga as peças é o `demo.py` (ou os testes, ou a interface web).
  Os quatro componentes são desacoplados desse jeito.
  Isso é conferido por um teste automatizado (`test_componente_nao_importa_a_implementacao_do_outro`).
- Autenticação, Busca de Mentores e Agendamento não se chamam entre si: eles se encontram
  nos mesmos dados, pela `IPersistencia`. Uma conta criada pela Autenticação já é
  reconhecida pelo Agendamento (o `buscar_usuario` enxerga as contas).
- Depois de agendar ou cancelar, o Agendamento busca os e-mails do mentor e do
  mentorado na persistência e chama `INotificacao`.
- **Regra de erro:** uma falha na notificação nunca desfaz o agendamento ou o
  cancelamento, só é registrada no log. Já um e-mail mal formado é erro de
  pré-condição (`EmailInvalido`), enquanto uma falha de transporte do e-mail volta como
  `ResultadoEnvio(enviado=False)`.

## Como executar

```bash
# 1. (opcional) ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. dependências
pip install -r requirements.txt

# 3. demonstração no terminal
python demo.py

# 4. demonstração visual (abre http://localhost:8000 no navegador)
python interface_web/servidor.py

# 5. testes
python -m pytest -v

# 6. testes com cobertura
python -m pytest --cov=mentorhub --cov-report=term-missing
```

Se a porta 8000 estiver ocupada: `python interface_web/servidor.py --porta 8080`.

O `pytest.ini` já configura o `pythonpath`, então não precisa instalar o pacote.

## Testes

São 149 testes, com **99% de cobertura** dos componentes (a única linha de fora é o `print` do e-mail simulado,
que só roda no `demo.py`). A saída completa está em `docs/evidencias/resultado_testes.txt`, e a da demonstração
em `docs/evidencias/demo.txt`.

| Arquivo | O que testa |
|---|---|
| `tests/test_agendamento.py` | Agendamento isolado (notificação trocada por uma espiã): cada operação com caso normal, pré-condições violadas e pós-condições. Inclui horário duplicado, sessão já cancelada, sessão que já aconteceu e falha de aviso sem desfazer a operação |
| `tests/test_notificacoes.py` | Notificações isoladas (e-mail simulado): conteúdo dos e-mails, e-mails inválidos (parametrizado), serviço fora do ar, falha com um só destinatário |
| `tests/test_integracao.py` | Os componentes de verdade conversando (inclusive o caminho login → busca → perfil → agendamento): agendar gera e-mails reais no `EmailSimulado`, fluxo completo verificar → agendar → cancelar, erros de e-mail que não desfazem a sessão, e a checagem de que um componente não importa a implementação do outro |
| `tests/test_autenticacao.py` | Autenticação isolada: cada regra de cadastro, hash de senha (nunca em texto, sal diferente por conta), login (mesma mensagem para e-mail ou senha errados) e recuperação de acesso (código de uso único, vencido, substituído) |
| `tests/test_busca_mentores.py` | Busca isolada: pesquisa sem acento e sem diferenciar maiúsculas, ordenação por nota, área vazia, perfil e avaliações, e mentor que continua na lista mesmo com falha na foto |
| `tests/test_armazenamento_memoria.py`, `tests/test_persistencia_memoria.py` | Os substitutos em memória se comportam como as interfaces prometem |
| `tests/test_interface_web.py` | A camada da interface visual: login, cadastro, busca, perfil, recuperação de senha e o servidor HTTP |

## Cenário da demonstração (`demo.py`)

1. Verifica os horários livres de uma mentora
2. Agenda uma sessão (e-mails de confirmação aparecem na tela)
3. Tenta agendar o mesmo horário e é recusado
4. Cancela a sessão (e-mails de cancelamento) e o horário volta à lista
5. Tenta cancelar de novo e é recusado
6. Deixa o serviço de e-mail fora do ar: o agendamento continua valendo, com aviso no log

## Interface visual

`python interface_web/servidor.py` sobe uma tela com os dois componentes de entrada do sistema:
**Autenticação** e **Busca de Mentores**. Ela não reimplementa nada: chama os mesmos componentes do
projeto pelas interfaces `IAutenticacao` e `IBuscaMentores`.

**1. Conta** (Autenticação)
- **Entrar:** botões de "contas de teste" preenchem o formulário (senha `senha1234`).
- **Criar conta:** a tela chama `validar_cadastro` e depois `criar_conta`. Dados ruins mostram a lista de regras desrespeitadas. Quem se cadastra como mentor informa áreas e bio e já aparece na busca.
- **Esqueci a senha:** `recuperar_acesso` gera o código (mostrado na tela, já que não há e-mail de verdade) e `redefinir_senha` troca a senha.

**2. Buscar mentores** (Busca de Mentores)
- Pesquisa por área, com atalhos. Cada resultado traz foto, áreas, nota média e total de avaliações; **Ver perfil** mostra bio e avaliações.

A busca só funciona com alguém logado. Essa regra, e o "quem está logado", ficam na camada da
interface (`interface_web/aplicacao.py`), porque os componentes não têm o conceito de usuário logado.

Os componentes de Agendamento e Notificações continuam no projeto e podem ser vistos pelo
`demo.py` e pelos testes.

Prints em `docs/evidencias/interface_*.png`.

## Limitações conhecidas

- A persistência é em memória: os dados somem quando o programa termina.
- O cadastro de horários livres (`cadastrar_horario_livre`), de perfis e de avaliações de mentores
  fica fora das operações especificadas. Na demonstração, esses dados vêm de uma carga inicial
  (e, no cadastro de um mentor novo, de um passo de apoio da interface).
- A Autenticação não mantém sessão de login nem token: confere as credenciais e devolve o usuário.
  A interface web guarda quem está logado (um usuário por vez, por ser uma demonstração local).
- O envio de e-mail é simulado; não sai nenhum e-mail de verdade.
