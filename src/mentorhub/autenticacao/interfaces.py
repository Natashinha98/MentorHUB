"""Interface fornecida pelo componente de Autenticação: IAutenticacao.

No documento de especificação ela se chama IAutenticação. A interface que o
componente requer, IPersistencia, fica em mentorhub/persistencia/interfaces.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mentorhub.modelos import CodigoRecuperacao, Papel, ResultadoValidacao, Usuario


class IAutenticacao(ABC):
    """Cadastro, login e recuperação de acesso de mentores e mentorados."""

    @abstractmethod
    def validar_cadastro(
        self, nome: str, email: str, senha: str, papel: Papel
    ) -> ResultadoValidacao:
        """Confere os dados do cadastro sem criar nada.

        Regras: nome com pelo menos 2 letras; e-mail com formato válido e ainda
        não cadastrado; senha com 8 caracteres ou mais, com letra e número; papel
        mentor ou mentorado.
        Saída:        ResultadoValidacao, com a lista de regras desrespeitadas.
        Pós-condição: nada é alterado, é só uma consulta.
        """

    @abstractmethod
    def criar_conta(self, nome: str, email: str, senha: str, papel: Papel) -> Usuario:
        """Cria a conta de um novo usuário.

        Pré-condição:  os dados passam em `validar_cadastro` (senão DadosInvalidos).
        Saída:         o usuário criado.
        Pós-condição:  a conta fica salva, com a senha guardada só como hash com sal.
                       O usuário já pode entrar com o e-mail e a senha.
        """

    @abstractmethod
    def autenticar_usuario(self, email: str, senha: str) -> Usuario:
        """Confere e-mail e senha.

        Pré-condição:  a conta existe e a senha confere (senão CredenciaisInvalidas,
                       sem dizer qual dos dois estava errado).
        Saída:         o usuário dono da conta.
        Pós-condição:  nada é alterado.
        """

    @abstractmethod
    def recuperar_acesso(self, email: str) -> CodigoRecuperacao:
        """Começa a recuperação de acesso de quem esqueceu a senha.

        Pré-condição:  existe conta com o e-mail (senão ContaNaoEncontrada).
        Saída:         um código de 6 dígitos, válido por 15 minutos.
        Pós-condição:  só o hash do código fica guardado na conta. Um código novo
                       invalida o anterior. A entrega do código ao usuário não é
                       responsabilidade deste componente.
        """

    @abstractmethod
    def redefinir_senha(self, email: str, codigo: str, nova_senha: str) -> Usuario:
        """Termina a recuperação: troca a senha usando o código recebido.

        Pré-condição:  o código é o último gerado pra esse e-mail e ainda não venceu
                       (senão CodigoRecuperacaoInvalido); a nova senha respeita a
                       regra de senha (senão DadosInvalidos).
        Saída:         o usuário dono da conta.
        Pós-condição:  a senha nova vale, a antiga deixa de valer e o código não
                       pode ser usado de novo.
        """
