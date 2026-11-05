# Evidências: chamadas reais à API do Serviço de Sessões de Mentoria

Executado em 05/11/2026 15:46 contra `http://localhost:8765`.

## 1. Horários livres do mentor m1 (apoio)

**Requisição:** `GET /mentores/m1/disponibilidade` com parâmetros `{'data': '2026-11-06'}`

**Resposta:** HTTP 200 (esperado 200: OK)

```json
{
  "mentorId": "m1",
  "data": "2026-11-06",
  "horariosLivres": [
    "2026-11-06T10:00:00",
    "2026-11-06T14:00:00",
    "2026-11-06T16:00:00"
  ]
}
```

## 2. agendarSessao(): sucesso

**Requisição:** `POST /sessoes`

```json
{
  "mentorId": "m1",
  "mentoradoId": "a1",
  "horario": "2026-11-06T10:00:00"
}
```

**Resposta:** HTTP 201 (esperado 201: OK)

```json
{
  "sessaoId": "b9a763e4-cd15-4550-a127-76c603b6b2ee",
  "mentorId": "m1",
  "mentoradoId": "a1",
  "horario": "2026-11-06T10:00:00",
  "situacao": "marcada"
}
```

## 3. consultarSessao(): sucesso

**Requisição:** `GET /sessoes/b9a763e4-cd15-4550-a127-76c603b6b2ee`

**Resposta:** HTTP 200 (esperado 200: OK)

```json
{
  "sessaoId": "b9a763e4-cd15-4550-a127-76c603b6b2ee",
  "mentorId": "m1",
  "mentoradoId": "a1",
  "horario": "2026-11-06T10:00:00",
  "situacao": "marcada"
}
```

## 4. Horário deixou de ficar livre

**Requisição:** `GET /mentores/m1/disponibilidade` com parâmetros `{'data': '2026-11-06'}`

**Resposta:** HTTP 200 (esperado 200: OK)

```json
{
  "mentorId": "m1",
  "data": "2026-11-06",
  "horariosLivres": [
    "2026-11-06T14:00:00",
    "2026-11-06T16:00:00"
  ]
}
```

## 5. agendarSessao(): mesmo horário de novo (horário indisponível)

**Requisição:** `POST /sessoes`

```json
{
  "mentorId": "m1",
  "mentoradoId": "a2",
  "horario": "2026-11-06T10:00:00"
}
```

**Resposta:** HTTP 409 (esperado 409: OK)

```json
{
  "codigo": "HORARIO_INDISPONIVEL",
  "mensagem": "O horário 06/11/2026 10:00 não está livre para o mentor m1."
}
```

## 6. agendarSessao(): horário fora da agenda do mentor

**Requisição:** `POST /sessoes`

```json
{
  "mentorId": "m1",
  "mentoradoId": "a2",
  "horario": "2026-11-06T23:00:00"
}
```

**Resposta:** HTTP 409 (esperado 409: OK)

```json
{
  "codigo": "HORARIO_INDISPONIVEL",
  "mensagem": "O horário 06/11/2026 23:00 não está livre para o mentor m1."
}
```

## 7. agendarSessao(): mentor inexistente

**Requisição:** `POST /sessoes`

```json
{
  "mentorId": "m99",
  "mentoradoId": "a1",
  "horario": "2026-11-06T14:00:00"
}
```

**Resposta:** HTTP 404 (esperado 404: OK)

```json
{
  "codigo": "MENTOR_NAO_ENCONTRADO",
  "mensagem": "Mentor m99 não encontrado."
}
```

## 8. agendarSessao(): mentorado inexistente

**Requisição:** `POST /sessoes`

```json
{
  "mentorId": "m1",
  "mentoradoId": "a99",
  "horario": "2026-11-06T14:00:00"
}
```

**Resposta:** HTTP 404 (esperado 404: OK)

```json
{
  "codigo": "MENTORADO_NAO_ENCONTRADO",
  "mensagem": "Mentorado a99 não encontrado."
}
```

## 9. agendarSessao(): horário no passado

**Requisição:** `POST /sessoes`

```json
{
  "mentorId": "m1",
  "mentoradoId": "a1",
  "horario": "2026-11-04T15:46:27"
}
```

**Resposta:** HTTP 400 (esperado 400: OK)

```json
{
  "codigo": "DADOS_INVALIDOS",
  "mensagem": "O horário precisa ser posterior ao momento da solicitação."
}
```

## 10. agendarSessao(): campo obrigatório ausente

**Requisição:** `POST /sessoes`

```json
{
  "mentorId": "m1",
  "horario": "2026-11-06T14:00:00"
}
```

**Resposta:** HTTP 400 (esperado 400: OK)

```json
{
  "codigo": "DADOS_INVALIDOS",
  "mensagem": "mentoradoId: Field required"
}
```

## 11. cancelarSessao(): sucesso

**Requisição:** `POST /sessoes/b9a763e4-cd15-4550-a127-76c603b6b2ee/cancelamento`

**Resposta:** HTTP 200 (esperado 200: OK)

```json
{
  "sessaoId": "b9a763e4-cd15-4550-a127-76c603b6b2ee",
  "mentorId": "m1",
  "mentoradoId": "a1",
  "horario": "2026-11-06T10:00:00",
  "situacao": "cancelada"
}
```

## 12. Horário voltou a ficar livre

**Requisição:** `GET /mentores/m1/disponibilidade` com parâmetros `{'data': '2026-11-06'}`

**Resposta:** HTTP 200 (esperado 200: OK)

```json
{
  "mentorId": "m1",
  "data": "2026-11-06",
  "horariosLivres": [
    "2026-11-06T10:00:00",
    "2026-11-06T14:00:00",
    "2026-11-06T16:00:00"
  ]
}
```

## 13. cancelarSessao(): cancelar de novo (não permitido)

**Requisição:** `POST /sessoes/b9a763e4-cd15-4550-a127-76c603b6b2ee/cancelamento`

**Resposta:** HTTP 409 (esperado 409: OK)

```json
{
  "codigo": "CANCELAMENTO_NAO_PERMITIDO",
  "mensagem": "A sessão b9a763e4-cd15-4550-a127-76c603b6b2ee já está cancelada."
}
```

## 14. cancelarSessao(): sessão inexistente

**Requisição:** `POST /sessoes/nao-existe/cancelamento`

**Resposta:** HTTP 404 (esperado 404: OK)

```json
{
  "codigo": "SESSAO_NAO_ENCONTRADA",
  "mensagem": "Sessão nao-existe não encontrada."
}
```

## 15. consultarSessao(): sessão inexistente

**Requisição:** `GET /sessoes/nao-existe`

**Resposta:** HTTP 404 (esperado 404: OK)

```json
{
  "codigo": "SESSAO_NAO_ENCONTRADA",
  "mensagem": "Sessão nao-existe não encontrada."
}
```
